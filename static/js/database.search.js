var fetchWithTimeout = globalThis.fetchWithTimeout || ((...args) => globalThis.fetch(...args));

const ADVANCED_DB_SEARCH_LIMIT = 200;
const ADVANCED_POSITION_SCORE_STEPS = [10, 15, 18];
var currentAdvancedSearchTab = 'base';
var databaseSearchRequestSequence = 0;
const ADVANCED_DB_BASE_FIELDS = [
    ['age', '年龄'],
    ['ca', 'CA'],
    ['pa', 'PA'],
    ['weighted_power', '加权战力值'],
    ['height', '身高'],
    ['left_foot', '左脚'],
    ['right_foot', '右脚'],
];
const ADVANCED_DB_TOP_LEVEL_RANGE_FIELDS = new Set(['age', 'ca', 'pa', 'weighted_power']);
const ADVANCED_DB_BASE_RANGE_LIMITS = {
    age: {min: 0, max: 99},
    ca: {min: 0, max: 200},
    pa: {min: 0, max: 200},
    weighted_power: {min: 0, max: 100},
    height: {min: 100, max: 250},
    left_foot: {min: 1, max: 20},
    right_foot: {min: 1, max: 20},
};
const ADVANCED_DB_ATTRIBUTE_GROUPS = [
    {
        key: 'technical',
        label: '技术属性',
        fields: [
            ['passing', '传球'], ['crossing', '传中'], ['dribbling', '盘带'], ['finishing', '射门'],
            ['first_touch', '停球'], ['free_kick', '任意球'], ['heading', '头球'], ['long_shots', '远射'],
            ['long_throws', '界外球'], ['marking', '盯人'], ['penalty', '点球'], ['tackling', '抢断'], ['technique', '技术'],
        ],
    },
    {
        key: 'mental',
        label: '精神属性',
        fields: [
            ['aggression', '侵略性'], ['anticipation', '预判'], ['bravery', '勇敢'], ['composure', '镇定'],
            ['concentration', '集中'], ['decisions', '决断'], ['determination', '意志力'], ['flair', '想象力'],
            ['leadership', '领导力'], ['off_the_ball', '无球跑动'], ['positioning', '站位'], ['teamwork', '团队合作'],
            ['vision', '视野'], ['work_rate', '工作投入'],
        ],
    },
    {
        key: 'physical',
        label: '身体属性',
        fields: [
            ['acceleration', '爆发力'], ['agility', '灵活'], ['balance', '平衡'], ['jumping', '弹跳'],
            ['natural_fitness', '体质'], ['pace', '速度'], ['stamina', '耐力'], ['strength', '强壮'],
        ],
    },
    {
        key: 'goalkeeper',
        label: '门将属性',
        fields: [
            ['aerial_ability', '制空能力'], ['command_of_area', '拦截传中'], ['communication', '指挥防守'],
            ['eccentricity', '神经指数'], ['handling', '手控球'], ['kicking', '大脚开球'],
            ['one_on_ones', '一对一'], ['reflexes', '反应'], ['rushing_out', '出击'],
            ['tendency_to_punch', '击球倾向'], ['throwing', '手抛球'],
        ],
    },
    {
        key: 'hidden',
        label: '隐藏属性',
        fields: [
            ['consistency', '稳定性'], ['dirtiness', '肮脏'], ['important_matches', '大赛发挥'],
            ['injury_proneness', '受伤倾向'], ['versatility', '多样性'], ['adaptability', '适应性'],
            ['ambition', '野心'], ['controversy', '争议'], ['loyalty', '忠诚'],
            ['pressure', '抗压'], ['professionalism', '职业素养'], ['sportsmanship', '体育精神'],
            ['temperament', '情绪控制'],
        ],
    },
];
const ADVANCED_DB_FIELD_LABEL_MAP = Object.fromEntries(
    [...ADVANCED_DB_BASE_FIELDS, ...ADVANCED_DB_ATTRIBUTE_GROUPS.flatMap(group => group.fields)]
);
const DEFAULT_DB_SEARCH_META = {
    mode: 'basic',
    query: '',
    truncated: false,
    limit: ADVANCED_DB_SEARCH_LIMIT,
    applied_filters_summary: [],
    data_version: '',
    batch_scope_count: 0,
    batch_unmatched_count: 0,
    scope_type: 'none',
    scope_label: '',
};
var databaseBatchScope = {
    raw: '',
    tokens: [],
    players: [],
    unmatched: [],
    version: '',
};
var candidateAdminListFilter = 'all';
var candidateAdminListQuery = '';
var candidateAdminPlayerQuery = '';
var candidateAdminPlayerStatus = 'all';
var candidateAdminPlayerSort = {field: 'uid', order: 'asc'};
var candidateAdminSelectedUids = new Set();
var candidateAdminPlayersCache = {
    listId: null,
    items: [],
    totalCount: 0,
    matchedCount: 0,
    missingCount: 0,
};
var candidatePublicListQuery = '';
var candidatePublicListSort = 'published_desc';
var candidatePublicListView = (() => {
    try {
        return localStorage.getItem('heigo_candidate_list_view_v2') === 'table' ? 'table' : 'card';
    } catch (error) {
        return 'card';
    }
})();

function getAdvancedSearchTabs() {
    return [
        {key: 'base', label: '基础区间+位置熟练度'},
        {key: 'physical', label: '身体属性'},
        {key: 'mental', label: '精神属性'},
        {key: 'technical', label: '技术属性'},
        {key: 'goalkeeper', label: '门将属性'},
        {key: 'hidden', label: '隐藏属性'},
        {key: 'batch', label: '批量范围'},
    ];
}

function getAdvancedAttributeGroup(key) {
    return ADVANCED_DB_ATTRIBUTE_GROUPS.find(group => group.key === key) || null;
}

function createEmptyDatabaseAdvancedFilters() {
    return {
        ...Object.fromEntries(ADVANCED_DB_BASE_FIELDS.map(([field]) => [field, {min: '', max: ''}])),
        sea_status: '',
        attributes: {},
        positions: {},
    };
}

function sanitizeNumericInput(value, options = {}) {
    const digits = String(value ?? '').replace(/[^\d]/g, '');
    if (!digits) return '';
    const numeric = Number.parseInt(digits, 10);
    if (!Number.isFinite(numeric)) return '';
    const minimum = Number.isFinite(options.min) ? options.min : 0;
    const maximum = Number.isFinite(options.max) ? options.max : numeric;
    return String(Math.max(minimum, Math.min(maximum, numeric)));
}

function normalizeAdvancedRangeState(rangeValue, options = {}) {
    const normalized = rangeValue && typeof rangeValue === 'object' ? rangeValue : {};
    return {
        min: sanitizeNumericInput(normalized.min, options),
        max: sanitizeNumericInput(normalized.max, options),
    };
}

function normalizeAdvancedDatabaseFilters(rawFilters = {}) {
    const nextState = createEmptyDatabaseAdvancedFilters();
    ADVANCED_DB_BASE_FIELDS.forEach(([field]) => {
        nextState[field] = normalizeAdvancedRangeState(rawFilters[field], ADVANCED_DB_BASE_RANGE_LIMITS[field]);
    });
    nextState.sea_status = ['in_sea', 'not_in_sea'].includes(rawFilters.sea_status) ? rawFilters.sea_status : '';

    const attributes = rawFilters.attributes && typeof rawFilters.attributes === 'object' ? rawFilters.attributes : {};
    Object.entries(attributes).forEach(([field, value]) => {
        if (!ADVANCED_DB_FIELD_LABEL_MAP[field] || ADVANCED_DB_BASE_FIELDS.some(([key]) => key === field)) return;
        const normalized = normalizeAdvancedRangeState(value, {min: 1, max: 20});
        if (normalized.min || normalized.max) {
            nextState.attributes[field] = normalized;
        }
    });

    const positions = rawFilters.positions && typeof rawFilters.positions === 'object' ? rawFilters.positions : {};
    Object.entries(positions).forEach(([position, score]) => {
        const normalizedPosition = String(position || '').trim().toUpperCase();
        if (!POSITION_MARKERS.some(marker => marker.label === normalizedPosition)) return;
        const numericScore = Number.parseInt(String(score), 10);
        if (ADVANCED_POSITION_SCORE_STEPS.includes(numericScore)) {
            nextState.positions[normalizedPosition] = numericScore;
        }
    });

    return nextState;
}

function ensureCurrentDbAdvancedFilters() {
    currentDbAdvancedFilters = normalizeAdvancedDatabaseFilters(currentDbAdvancedFilters || {});
    return currentDbAdvancedFilters;
}

function cloneAdvancedDatabaseFilters() {
    return normalizeAdvancedDatabaseFilters(ensureCurrentDbAdvancedFilters());
}

function isRangeActive(rangeValue = {}) {
    return Boolean(String(rangeValue.min || '').trim() || String(rangeValue.max || '').trim());
}

function countActiveAdvancedFilters() {
    const filters = ensureCurrentDbAdvancedFilters();
    let total = 0;
    ADVANCED_DB_BASE_FIELDS.forEach(([field]) => {
        if (isRangeActive(filters[field])) total += 1;
    });
    if (filters.sea_status) total += 1;
    total += Object.values(filters.attributes || {}).filter(isRangeActive).length;
    total += Object.keys(filters.positions || {}).length;
    return total;
}

function hasActiveAdvancedFilters() {
    return countActiveAdvancedFilters() > 0;
}

function normalizeDatabaseLookupText(value) {
    return String(value || '').trim().toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, '');
}

function parseDatabaseBatchTokens(rawValue) {
    return String(rawValue || '')
        .split(/[\n\r\t,，;；]+/)
        .map(item => item.trim())
        .filter(Boolean);
}

function hasDatabaseBatchScope() {
    return Boolean(databaseBatchScope.raw.trim());
}

function resetDatabaseSearchScope() {
    databaseSearchScope = {
        type: 'none',
        id: null,
        name: '',
        dataVersion: '',
        uids: [],
        players: [],
        missingUids: [],
        raw: '',
        unmatched: [],
    };
}

function setDatabaseSearchScope(scope) {
    databaseSearchScope = {
        type: scope?.type || 'none',
        id: scope?.id ?? null,
        name: scope?.name || '',
        dataVersion: scope?.dataVersion || getCurrentAttributeVersion(),
        uids: Array.isArray(scope?.uids) ? [...scope.uids] : [],
        players: Array.isArray(scope?.players) ? dedupeDatabasePlayers(scope.players) : [],
        missingUids: Array.isArray(scope?.missingUids) ? [...scope.missingUids] : [],
        raw: scope?.raw || '',
        unmatched: Array.isArray(scope?.unmatched) ? [...scope.unmatched] : [],
    };
}

function hasDatabaseSearchScope() {
    return databaseSearchScope && databaseSearchScope.type && databaseSearchScope.type !== 'none';
}

function getDatabaseSearchScopeLabel() {
    if (!hasDatabaseSearchScope()) return '';
    if (databaseSearchScope.type === 'candidate_list') {
        return `候选名单：${databaseSearchScope.name || databaseSearchScope.id || ''}`;
    }
    if (databaseSearchScope.type === 'batch') {
        return '批量范围';
    }
    return databaseSearchScope.name || '筛选范围';
}

function getDatabaseBatchRawValue() {
    const input = document.getElementById('dbBatchSearch');
    return input ? input.value : (databaseBatchScope.raw || '');
}

function setDatabaseBatchRawValue(rawValue) {
    const raw = String(rawValue || '');
    const input = document.getElementById('dbBatchSearch');
    if (input) input.value = raw;
    databaseBatchScope.raw = raw;
}

function dedupeDatabasePlayers(players) {
    const seen = new Set();
    const result = [];
    (players || []).forEach(player => {
        const key = getPlayerVersionKey(player);
        if (seen.has(key)) return;
        seen.add(key);
        result.push(player);
    });
    return result;
}

async function applyDatabaseBatchScope(rawValue, options = {}) {
    const raw = String(rawValue || '');
    const version = options.version || getCurrentAttributeVersion();
    const tokens = parseDatabaseBatchTokens(raw);
    if (!tokens.length) {
        databaseBatchScope = {raw, tokens: [], players: [], unmatched: [], version};
        if (databaseSearchScope.type === 'batch') {
            resetDatabaseSearchScope();
        }
        return databaseBatchScope;
    }

    const response = await fetchWithTimeout('/api/attributes/batch-lookup', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({tokens, version}),
    });
    let payload = null;
    try {
        payload = await response.json();
    } catch (error) {
        payload = null;
    }
    if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || `HTTP ${response.status}`);
    }

    databaseBatchScope = {
        raw,
        tokens: payload?.tokens || tokens,
        players: dedupeDatabasePlayers(Array.isArray(payload?.items) ? payload.items : []),
        unmatched: Array.isArray(payload?.unmatched) ? payload.unmatched : [],
        version: payload?.data_version || version,
    };
    setDatabaseSearchScope({
        type: 'batch',
        name: '批量范围',
        dataVersion: databaseBatchScope.version,
        uids: databaseBatchScope.players.map(player => Number(player.uid)).filter(Number.isFinite),
        players: databaseBatchScope.players,
        raw,
        unmatched: databaseBatchScope.unmatched,
    });
    return databaseBatchScope;
}

function getDatabasePlayerAttributeValue(player, field) {
    if (!player || !field) return null;
    if (field === 'weighted_power' && typeof calculateWeightedPower === 'function') {
        return calculateWeightedPower(player).score;
    }
    if (player[field] !== undefined && player[field] !== null) return player[field];
    if (player.attributes && player.attributes[field] !== undefined && player.attributes[field] !== null) return player.attributes[field];
    return null;
}

function databasePlayerMatchesRange(player, field, rangeValue = {}) {
    if (!isRangeActive(rangeValue)) return true;
    const numeric = Number(getDatabasePlayerAttributeValue(player, field));
    if (!Number.isFinite(numeric)) return false;
    if (rangeValue.min && numeric < Number(rangeValue.min)) return false;
    if (rangeValue.max && numeric > Number(rangeValue.max)) return false;
    return true;
}

function databasePlayerMatchesAdvancedFilters(player) {
    const filters = ensureCurrentDbAdvancedFilters();
    if (!ADVANCED_DB_BASE_FIELDS.every(([field]) => databasePlayerMatchesRange(player, field, filters[field]))) {
        return false;
    }
    const clubName = String(player?.heigo_club || '').trim();
    const isSeaPlayer = !clubName || clubName === '大海' || clubName === '85大海';
    if (filters.sea_status === 'in_sea' && !isSeaPlayer) return false;
    if (filters.sea_status === 'not_in_sea' && isSeaPlayer) return false;
    const attributesMatch = Object.entries(filters.attributes || {}).every(([field, rangeValue]) => (
        databasePlayerMatchesRange(player, field, rangeValue)
    ));
    if (!attributesMatch) return false;

    const positionRequirements = Object.entries(filters.positions || {});
    if (!positionRequirements.length) return true;
    const positionRatings = player.position_ratings || player.positions || {};
    return positionRequirements.some(([position, minScore]) => {
        const score = Number(positionRatings[position] ?? positionRatings[position.toLowerCase()] ?? 0);
        if (Number.isFinite(score) && score >= Number(minScore)) return true;
        const positionText = normalizeDatabaseLookupText(player.position);
        return positionText.split(/[,\s/]+/).includes(position.toLowerCase()) && Number(minScore) <= 10;
    });
}

function databasePlayerMatchesKeyword(player, query) {
    const normalizedQuery = normalizeDatabaseLookupText(query);
    if (!normalizedQuery) return true;
    return String(player.uid || '').includes(String(query || '').trim())
        || normalizeDatabaseLookupText(player.name).includes(normalizedQuery)
        || normalizeDatabaseLookupText(player.heigo_club).includes(normalizedQuery)
        || normalizeDatabaseLookupText(player.club).includes(normalizedQuery)
        || normalizeDatabaseLookupText(player.nationality).includes(normalizedQuery);
}

function filterDatabaseBatchPlayersLocally(query) {
    const sourcePlayers = hasDatabaseSearchScope() ? databaseSearchScope.players : databaseBatchScope.players;
    return dedupeDatabasePlayers(sourcePlayers)
        .filter(player => databasePlayerMatchesKeyword(player, query))
        .filter(databasePlayerMatchesAdvancedFilters);
}

function captureAdvancedDatabaseFilters() {
    return cloneAdvancedDatabaseFilters();
}

function setCurrentDbSearchMeta(meta = {}) {
    currentDbSearchMeta = {
        ...DEFAULT_DB_SEARCH_META,
        ...(currentDbSearchMeta || {}),
        ...(meta || {}),
        applied_filters_summary: Array.isArray(meta?.applied_filters_summary)
            ? [...meta.applied_filters_summary]
            : Array.isArray(currentDbSearchMeta?.applied_filters_summary)
                ? [...currentDbSearchMeta.applied_filters_summary]
                : [],
    };
    renderDatabaseSearchSummary();
}

function resetCurrentDbSearchMeta() {
    currentDbSearchMeta = {...DEFAULT_DB_SEARCH_META};
    renderDatabaseSearchSummary();
}

function formatRangeSummary(label, rangeValue = {}) {
    const min = String(rangeValue.min || '').trim();
    const max = String(rangeValue.max || '').trim();
    if (!min && !max) return '';
    if (min && max) return `${label} ${min}-${max}`;
    if (min) return `${label} ≥ ${min}`;
    return `${label} ≤ ${max}`;
}

function buildAppliedAdvancedFilterSummary() {
    const filters = ensureCurrentDbAdvancedFilters();
    const summary = [];
    ADVANCED_DB_BASE_FIELDS.forEach(([field]) => {
        const text = formatRangeSummary(ADVANCED_DB_FIELD_LABEL_MAP[field], filters[field]);
        if (text) summary.push(text);
    });
    if (filters.sea_status) {
        summary.push(filters.sea_status === 'in_sea' ? '仅大海球员' : '排除大海球员');
    }
    Object.entries(filters.attributes || {}).forEach(([field, value]) => {
        const text = formatRangeSummary(ADVANCED_DB_FIELD_LABEL_MAP[field] || field, value);
        if (text) summary.push(text);
    });
    Object.entries(filters.positions || {}).forEach(([position, score]) => {
        summary.push(`${position} ≥ ${score}`);
    });
    return summary;
}

function buildAdvancedSearchRequestPayload(query, options = {}) {
    const filters = ensureCurrentDbAdvancedFilters();
    const payload = {
        query: String(query || '').trim(),
        version: options.version || getCurrentAttributeVersion(),
        limit: ADVANCED_DB_SEARCH_LIMIT,
        attributes: {},
        positions: [],
    };

    ADVANCED_DB_BASE_FIELDS.forEach(([field]) => {
        if (!isRangeActive(filters[field])) return;
        const target = {};
        if (filters[field].min) target.min = Number(filters[field].min);
        if (filters[field].max) target.max = Number(filters[field].max);
        if (ADVANCED_DB_TOP_LEVEL_RANGE_FIELDS.has(field)) {
            payload[field] = target;
        } else {
            payload.attributes[field] = target;
        }
    });
    if (filters.sea_status) payload.sea_status = filters.sea_status;
    if (Array.isArray(options.uids) && options.uids.length) {
        payload.uids = [...new Set(options.uids.map(Number).filter(Number.isFinite))].slice(0, 1000);
    }

    Object.entries(filters.attributes || {}).forEach(([field, value]) => {
        if (!isRangeActive(value)) return;
        payload.attributes[field] = {};
        if (value.min) payload.attributes[field].min = Number(value.min);
        if (value.max) payload.attributes[field].max = Number(value.max);
    });

    Object.entries(filters.positions || {}).forEach(([position, score]) => {
        payload.positions.push({position, min_score: Number(score)});
    });

    return payload;
}

function getAdvancedPositionNextScore(position) {
    const filters = ensureCurrentDbAdvancedFilters();
    const currentScore = Number(filters.positions?.[position]) || 0;
    const currentIndex = ADVANCED_POSITION_SCORE_STEPS.indexOf(currentScore);
    return currentIndex === -1 ? ADVANCED_POSITION_SCORE_STEPS[0] : (ADVANCED_POSITION_SCORE_STEPS[currentIndex + 1] || 0);
}

function getAdvancedPositionMarkerClass(score) {
    if (!score) return 'pitch-rating-gray';
    return getPitchMarkerTone(score);
}

function buildAdvancedSearchPositionMap() {
    const filters = ensureCurrentDbAdvancedFilters();
    const markers = POSITION_MARKERS.map(marker => {
        const score = Number(filters.positions?.[marker.label]) || 0;
        const markerClass = getAdvancedPositionMarkerClass(score);
        const selectedClass = score ? 'is-selected' : '';
        const tooltipClasses = getPitchTooltipClasses(marker);
        const stateText = score ? `要求 ≥ ${score}` : '未要求';
        return `
            <button
                class="pitch-marker advanced-search-position-marker ${markerClass} ${selectedClass}"
                style="left:${marker.x}%;top:${marker.y}%;background:none;border:none;padding:0;"
                type="button"
                onclick="cycleAdvancedPositionFilter('${marker.label}')"
                aria-pressed="${score ? 'true' : 'false'}"
                aria-label="${marker.label} ${stateText}"
            >
                <span class="pitch-marker-core">${marker.label}</span>
                <span class="advanced-search-position-state">${score || '·'}</span>
                <span class="pitch-marker-tooltip ${tooltipClasses}">${marker.label} · ${stateText}</span>
            </button>
        `;
    }).join('');

    return `
        <div class="position-map-card database-position-filter-card">
            <h4>位置熟练度图</h4>
            <p class="database-advanced-helper">点击球场位置循环切换为 <strong>≥10</strong>、<strong>≥15</strong>、<strong>≥18</strong> 或关闭。多位置按“任一位置满足”处理。</p>
            <div class="pitch-board">
                <div class="pitch-field">
                    <span class="pitch-half-line"></span>
                    <span class="pitch-center-circle"></span>
                    <span class="pitch-center-spot"></span>
                    <span class="pitch-top-box"></span>
                    <span class="pitch-bottom-box"></span>
                    <span class="pitch-top-goal-box"></span>
                    <span class="pitch-bottom-goal-box"></span>
                    ${markers}
                </div>
            </div>
        </div>
    `;
}

function buildAdvancedRangeFieldMarkup(field, label, value = {min: '', max: ''}, attributeField = false) {
    const inputHandler = attributeField
        ? `updateAdvancedAttributeRange('${field}', event.target.dataset.boundary, event.target.value)`
        : `updateAdvancedBaseRange('${field}', event.target.dataset.boundary, event.target.value)`;
    return `
        <label class="database-advanced-range-field">
            <span class="database-advanced-range-label">${label}</span>
            <div class="database-advanced-range-inputs">
                <input type="text" inputmode="numeric" placeholder="最低" data-boundary="min" value="${escapeHtml(value.min || '')}" oninput="${inputHandler}">
                <span class="database-advanced-range-separator">-</span>
                <input type="text" inputmode="numeric" placeholder="最高" data-boundary="max" value="${escapeHtml(value.max || '')}" oninput="${inputHandler}">
            </div>
        </label>
    `;
}

function buildDatabaseBatchScopePanel() {
    const scopeCount = Number(databaseBatchScope.players?.length || 0);
    const unmatchedCount = Number(databaseBatchScope.unmatched?.length || 0);
    return `
        <section class="database-advanced-tab-panel database-batch-tab-panel">
            <div class="database-advanced-section-head">
                <h4>批量查询范围</h4>
                <span>${scopeCount ? `${scopeCount} 名已选范围` : '先粘贴名单或 UID'}</span>
            </div>
            <div class="database-batch-filter database-batch-filter-in-panel">
                <div class="form-group database-batch-input">
                    <label for="dbBatchSearch">球员姓名或 UID</label>
                    <textarea id="dbBatchSearch" rows="8" placeholder="粘贴球员姓名或 UID，每行一个，也支持逗号、分号或制表符分隔" oninput="setDatabaseBatchRawValue(this.value)">${escapeHtml(databaseBatchScope.raw || '')}</textarea>
                </div>
                <div class="database-batch-actions">
                    <button class="btn btn-secondary" type="button" onclick="applyDatabaseBatchScopeAndSearch()">应用范围</button>
                    <button class="btn btn-secondary" type="button" onclick="clearDatabaseBatchScope()">清空范围</button>
                </div>
            </div>
            <div class="database-advanced-summary-row database-batch-summary-row">
                <span class="query-chip ${scopeCount ? '' : 'is-muted'}">当前范围 <strong>${scopeCount}</strong> 名</span>
                ${unmatchedCount ? `<span class="query-chip">未匹配 <strong>${unmatchedCount}</strong></span>` : ''}
            </div>
        </section>
    `;
}

function buildAdvancedSearchPositionMap() {
    const filters = ensureCurrentDbAdvancedFilters();
    const markers = POSITION_MARKERS.map(marker => {
        const score = Number(filters.positions?.[marker.label]) || 0;
        const markerClass = getAdvancedPositionMarkerClass(score);
        const selectedClass = score ? 'is-selected' : '';
        const tooltipClasses = getPitchTooltipClasses(marker);
        const stateText = score ? `>= ${score}` : '未启用';
        return `
            <button
                class="pitch-marker advanced-search-position-marker ${markerClass} ${selectedClass}"
                style="left:${marker.x}%;top:${marker.y}%;background:none;border:none;padding:0;"
                type="button"
                onclick="cycleAdvancedPositionFilter('${marker.label}')"
                aria-pressed="${score ? 'true' : 'false'}"
                aria-label="${marker.label} ${stateText}"
            >
                <span class="pitch-marker-core">${marker.label}</span>
                <span class="pitch-marker-tooltip ${tooltipClasses}">${marker.label} · ${stateText}</span>
            </button>
        `;
    }).join('');

    return `
        <div class="position-map-card database-position-filter-card">
            <h4>位置熟练度图</h4>
            <p class="database-advanced-helper">点击球场位置循环切换为 <strong>>=10</strong>、<strong>>=15</strong>、<strong>>=18</strong> 或关闭。多位置会按“同时满足”处理。</p>
            <div class="pitch-board">
                <div class="pitch-field">
                    <span class="pitch-half-line"></span>
                    <span class="pitch-center-circle"></span>
                    <span class="pitch-center-spot"></span>
                    <span class="pitch-top-box"></span>
                    <span class="pitch-bottom-box"></span>
                    <span class="pitch-top-goal-box"></span>
                    <span class="pitch-bottom-goal-box"></span>
                    ${markers}
                </div>
            </div>
        </div>
    `;
}

function renderDatabaseAdvancedSearchPanel() {
    ensureCurrentDbAdvancedFilters();
    const panel = document.getElementById('dbAdvancedSearchPanel');
    if (!panel) return;

    const filters = currentDbAdvancedFilters;
    const tabs = getAdvancedSearchTabs();
    if (!tabs.some(tab => tab.key === currentAdvancedSearchTab)) {
        currentAdvancedSearchTab = 'base';
    }
    const baseFieldsMarkup = ADVANCED_DB_BASE_FIELDS
        .map(([field, label]) => buildAdvancedRangeFieldMarkup(field, label, filters[field]))
        .join('');
    const seaStatusMarkup = `
        <label class="database-advanced-choice-field">
            <span class="database-advanced-range-label">大海状态</span>
            <select onchange="updateAdvancedSeaStatus(this.value)">
                <option value="" ${filters.sea_status ? '' : 'selected'}>全部球员</option>
                <option value="in_sea" ${filters.sea_status === 'in_sea' ? 'selected' : ''}>仅大海球员</option>
                <option value="not_in_sea" ${filters.sea_status === 'not_in_sea' ? 'selected' : ''}>排除大海球员</option>
            </select>
        </label>
    `;
    const activeGroup = getAdvancedAttributeGroup(currentAdvancedSearchTab);
    const tabButtons = tabs.map(tab => `
        <button
            class="database-advanced-tab ${currentAdvancedSearchTab === tab.key ? 'active' : ''}"
            type="button"
            onclick="setAdvancedSearchTab('${tab.key}')"
            aria-selected="${currentAdvancedSearchTab === tab.key ? 'true' : 'false'}"
        >${escapeHtml(tab.label)}</button>
    `).join('');
    const activePanel = currentAdvancedSearchTab === 'batch'
        ? buildDatabaseBatchScopePanel()
        : currentAdvancedSearchTab === 'base'
        ? `
            <section class="database-advanced-tab-panel">
                <div class="database-advanced-section-head">
                    <h4>基础区间</h4>
                    <span>基础资料、加权战力、双脚能力与名单状态</span>
                </div>
                <div class="database-advanced-field-grid database-advanced-field-grid-base">
                    ${baseFieldsMarkup}
                    ${seaStatusMarkup}
                </div>
                <div class="database-advanced-section-head">
                    <h4>位置熟练度</h4>
                    <span>点击球场位置增加搜索要求</span>
                </div>
                ${buildAdvancedSearchPositionMap()}
            </section>
        `
        : `
            <section class="database-advanced-tab-panel">
                <div class="database-advanced-section-head">
                    <h4>${escapeHtml(activeGroup?.label || '属性')}</h4>
                    <span>${Number(activeGroup?.fields?.length || 0)} 项</span>
                </div>
                <div class="database-advanced-field-grid database-advanced-field-grid-attributes">
                    ${(activeGroup?.fields || []).map(([field, label]) => buildAdvancedRangeFieldMarkup(field, label, filters.attributes[field] || {}, true)).join('')}
                </div>
            </section>
        `;

    panel.innerHTML = `
        <form class="database-advanced-panel-card" onsubmit="event.preventDefault();applyAdvancedSearchAndRun();">
            <div class="database-advanced-head">
                <div>
                    <div class="panel-kicker">Advanced Search</div>
                    <h3 id="dbAdvancedSearchTitle">高级搜索条件</h3>
                    <p class="database-advanced-helper">在当前版本球员库上叠加范围和位置筛选。保留现有关键词时会做联合搜索。</p>
                </div>
                <button class="database-advanced-close" type="button" onclick="toggleAdvancedSearchPanel(false)" aria-label="关闭高级搜索">${uiIconSvg('close')}</button>
            </div>
            <div class="database-advanced-summary-row">
                <span class="query-chip ${countActiveAdvancedFilters() ? '' : 'is-muted'}">已启用 <strong>${countActiveAdvancedFilters()}</strong> 个高级条件</span>
                ${Object.keys(filters.positions || {}).length ? `<span class="query-chip">位置 <strong>${Object.keys(filters.positions).join(' / ')}</strong></span>` : ''}
            </div>
            <div class="database-advanced-tabs" role="tablist" aria-label="高级搜索条件分类">
                ${tabButtons}
            </div>
            ${activePanel}
            <div class="database-advanced-actions">
                <button class="btn btn-secondary" type="button" onclick="clearAdvancedDatabaseFilters({rerenderPanel: true})">清空条件</button>
                <button class="btn btn-primary" type="submit">应用并搜索</button>
            </div>
        </form>
    `;
}

function setAdvancedSearchTab(tabKey) {
    const nextTab = String(tabKey || '').trim();
    if (!getAdvancedSearchTabs().some(tab => tab.key === nextTab)) return;
    currentAdvancedSearchTab = nextTab;
    renderDatabaseAdvancedSearchPanel();
}

function renderAdvancedSearchTriggerState() {
    const button = document.getElementById('dbAdvancedSearchToggle');
    const countNode = document.getElementById('dbAdvancedSearchCount');
    if (!button || !countNode) return;
    const activeCount = countActiveAdvancedFilters() + (hasDatabaseSearchScope() ? 1 : 0);
    button.classList.toggle('is-active', activeCount > 0);
    countNode.hidden = activeCount <= 0;
    countNode.textContent = String(activeCount);
}

function isAdvancedSearchPanelOpen() {
    const panel = document.getElementById('dbAdvancedSearchPanel');
    return Boolean(panel && !panel.hidden);
}

function toggleAdvancedSearchPanel(force) {
    const panel = document.getElementById('dbAdvancedSearchPanel');
    const overlay = document.getElementById('dbAdvancedSearchOverlay');
    const button = document.getElementById('dbAdvancedSearchToggle');
    if (!panel || !overlay || !button) return;
    const nextOpen = typeof force === 'boolean' ? force : panel.hidden;
    if (nextOpen) {
        renderDatabaseAdvancedSearchPanel();
    }
    panel.hidden = !nextOpen;
    overlay.hidden = !nextOpen;
    button.setAttribute('aria-expanded', nextOpen ? 'true' : 'false');
    document.body.classList.toggle('database-advanced-open', nextOpen);
}

function updateAdvancedBaseRange(field, boundary, value) {
    ensureCurrentDbAdvancedFilters();
    if (!currentDbAdvancedFilters[field]) currentDbAdvancedFilters[field] = {min: '', max: ''};
    currentDbAdvancedFilters[field][boundary] = sanitizeNumericInput(value, ADVANCED_DB_BASE_RANGE_LIMITS[field] || {min: 0, max: 200});
    renderAdvancedSearchTriggerState();
}

function updateAdvancedSeaStatus(value) {
    ensureCurrentDbAdvancedFilters();
    currentDbAdvancedFilters.sea_status = ['in_sea', 'not_in_sea'].includes(value) ? value : '';
    renderAdvancedSearchTriggerState();
}

function updateAdvancedAttributeRange(field, boundary, value) {
    ensureCurrentDbAdvancedFilters();
    const sanitized = sanitizeNumericInput(value, {min: 1, max: 20});
    const nextValue = {
        ...(currentDbAdvancedFilters.attributes[field] || {min: '', max: ''}),
        [boundary]: sanitized,
    };
    if (isRangeActive(nextValue)) {
        currentDbAdvancedFilters.attributes[field] = nextValue;
    } else {
        delete currentDbAdvancedFilters.attributes[field];
    }
    renderAdvancedSearchTriggerState();
}

function cycleAdvancedPositionFilter(position) {
    ensureCurrentDbAdvancedFilters();
    const normalizedPosition = String(position || '').trim().toUpperCase();
    const nextScore = getAdvancedPositionNextScore(normalizedPosition);
    if (nextScore) {
        currentDbAdvancedFilters.positions[normalizedPosition] = nextScore;
    } else {
        delete currentDbAdvancedFilters.positions[normalizedPosition];
    }
    renderAdvancedSearchTriggerState();
    renderDatabaseAdvancedSearchPanel();
}

function applyAdvancedDatabaseFiltersState(state, options = {}) {
    currentDbAdvancedFilters = normalizeAdvancedDatabaseFilters(state || {});
    renderAdvancedSearchTriggerState();
    if (options.renderPanel) {
        renderDatabaseAdvancedSearchPanel();
    }
}

function clearAdvancedDatabaseFilters(options = {}) {
    currentDbAdvancedFilters = createEmptyDatabaseAdvancedFilters();
    renderAdvancedSearchTriggerState();
    if (options.rerenderPanel) {
        renderDatabaseAdvancedSearchPanel();
    }
    if (options.closePanel) {
        toggleAdvancedSearchPanel(false);
    }
}

function renderDatabaseSearchSummary() {
    const title = document.getElementById('dbTableTitle');
    const meta = document.getElementById('dbTableMeta');
    const chips = document.getElementById('dbQueryChips');
    if (!title || !meta || !chips) return;

    const summary = {
        ...DEFAULT_DB_SEARCH_META,
        ...(currentDbSearchMeta || {}),
    };
    const versionText = summary.data_version || getCurrentAttributeVersion();
    const playerCount = Array.isArray(currentDbPlayers) ? currentDbPlayers.length : 0;
    const hasScope = Number(summary.batch_scope_count || 0) > 0 || summary.scope_type === 'candidate_list';
    const hasResultContext = Boolean(summary.query || summary.applied_filters_summary.length || hasScope);
    const scopeLabel = summary.scope_label || getDatabaseSearchScopeLabel();
    const searchLabel = document.querySelector('label[for="dbPlayerSearch"]');
    const searchCount = `<span id="dbPlayerSearchCount">${hasResultContext ? playerCount.toLocaleString() : '-'}</span>`;
    if (searchLabel) {
        searchLabel.innerHTML = summary.scope_type === 'candidate_list'
            ? `搜索名单内球员 (${searchCount} 球员)`
            : `搜索球员库 (${searchCount} 球员)`;
    }
    title.textContent = `球员库搜索结果${versionText ? ` (${versionText})` : ''}${summary.query || summary.applied_filters_summary.length || hasScope ? ` (${playerCount} 名球员)` : ''}`;

    if (!summary.query && !summary.applied_filters_summary.length && !hasScope) {
        meta.textContent = '请输入球员姓名或 UID，或打开高级搜索筛选条件。';
    } else if (hasScope) {
        const scopeText = `${scopeLabel || '筛选范围'} ${summary.batch_scope_count || playerCount} 名`;
        const searchText = summary.query ? ` + 关键词“${summary.query}”` : '';
        const filterText = summary.applied_filters_summary.length ? ` + ${countActiveAdvancedFilters()} 个高级条件` : '';
        meta.textContent = `${scopeText}${searchText}${filterText} 的筛选结果。`;
    } else if (summary.mode === 'advanced') {
        const filterCount = countActiveAdvancedFilters();
        meta.textContent = summary.truncated
            ? `${summary.query ? `关键词“${summary.query}” + ` : ''}${filterCount} 个高级条件，当前仅展示前 ${summary.limit} 条结果，请继续收紧条件。`
            : `${summary.query ? `关键词“${summary.query}” + ` : ''}${filterCount} 个高级条件筛选结果。`;
    } else if (summary.query) {
        meta.textContent = `关键词“${summary.query}”搜索结果。`;
    } else {
        meta.textContent = '请输入球员姓名或 UID，或打开高级搜索筛选条件。';
    }

    const chipItems = [];
    if (summary.query) {
        chipItems.push(`<span class="query-chip">关键词 <strong>${escapeHtml(summary.query)}</strong></span>`);
    }
    if (hasScope) {
        chipItems.push(`<span class="query-chip">${escapeHtml(scopeLabel || '筛选范围')} <strong>${Number(summary.batch_scope_count || 0)}</strong> 名</span>`);
        chipItems.push('<button class="query-chip query-chip-action" type="button" onclick="clearDatabaseSearchScopeAndSearch()">清空范围</button>');
    }
    if (Number(summary.batch_unmatched_count || 0) > 0) {
        chipItems.push(`<span class="query-chip">未匹配 <strong>${Number(summary.batch_unmatched_count || 0)}</strong></span>`);
    }
    (summary.applied_filters_summary || []).forEach(item => {
        chipItems.push(`<span class="query-chip">${escapeHtml(item)}</span>`);
    });
    if (hasActiveAdvancedFilters()) {
        chipItems.push('<button class="query-chip query-chip-action" type="button" onclick="clearAdvancedFiltersFromResults()">清空高级条件</button>');
    }
    chips.innerHTML = chipItems.length ? chipItems.join('') : '<span class="query-chip is-muted">未应用筛选</span>';
}

function renderDatabaseSearchPlaceholder(message, options = {}) {
    setCurrentDbSearchMeta({
        ...DEFAULT_DB_SEARCH_META,
        ...(options.meta || {}),
        data_version: options.meta?.data_version || getCurrentAttributeVersion(),
    });
    currentDbPlayers = [];
    const table = document.getElementById('dbPlayersTable');
    if (table) {
        table.innerHTML = `<div class="no-data">${escapeHtml(message)}</div>`;
    }
}

async function executeDatabaseSearchRequest(name, options = {}) {
    const query = String(name || '').trim();
    const version = options.version || getCurrentAttributeVersion();
    if (hasActiveAdvancedFilters()) {
        const payload = buildAdvancedSearchRequestPayload(query, {version, uids: options.uids});
        const result = await fetchDatabaseAdvancedSearchResults(payload);
        return {
            mode: 'advanced',
            query,
            items: Array.isArray(result?.items) ? result.items : [],
            data_version: result?.data_version || version,
            truncated: Boolean(result?.truncated),
            limit: Number(result?.limit) || ADVANCED_DB_SEARCH_LIMIT,
            applied_filters_summary: Array.isArray(result?.applied_filters_summary)
                ? result.applied_filters_summary
                : buildAppliedAdvancedFilterSummary(),
        };
    }

    const items = await fetchDatabaseSearchResults(query, {version});
    return {
        mode: 'basic',
        query,
        items: Array.isArray(items) ? items : [],
        data_version: version,
        truncated: false,
        limit: ADVANCED_DB_SEARCH_LIMIT,
        applied_filters_summary: [],
    };
}

async function searchDatabase(nameOverride = null, options = {}) {
    const requestId = ++databaseSearchRequestSequence;
    const isLatestRequest = () => requestId === databaseSearchRequestSequence;
    const shouldSyncHistory = options.pushHistory !== false;
    const historyMode = options.historyMode || 'push';
    currentDatabaseSubtab = 'search';
    syncDatabaseSubtabUI();
    await loadAttributeVersionCatalog();
    if (!isLatestRequest()) return;
    refreshAttributeVersionBanner();
    ensureCurrentDbAdvancedFilters();
    const name = nameOverride ?? document.getElementById('dbPlayerSearch').value.trim();
    const searchInput = document.getElementById('dbPlayerSearch');
    const batchRaw = getDatabaseBatchRawValue();
    if (nameOverride !== null && searchInput) {
        searchInput.value = name;
    }
    activateDatabaseView('list');

    if (databaseSearchScope.type !== 'candidate_list' && (batchRaw !== databaseBatchScope.raw || getCurrentAttributeVersion() !== databaseBatchScope.version)) {
        document.getElementById('dbPlayersTable').innerHTML = '<div class="loading">正在解析批量范围...</div>';
        await applyDatabaseBatchScope(batchRaw, {version: getCurrentAttributeVersion()});
        if (!isLatestRequest()) return;
    }

    if (hasDatabaseSearchScope()) {
        let scopedResult = null;
        if (databaseSearchScope.type === 'candidate_list' && hasActiveAdvancedFilters()) {
            document.getElementById('dbPlayersTable').innerHTML = '<div class="loading">正在筛选候选名单...</div>';
            try {
                scopedResult = await executeDatabaseSearchRequest(name, {
                    version: databaseSearchScope.dataVersion || getCurrentAttributeVersion(),
                    uids: databaseSearchScope.uids,
                });
            } catch (error) {
                if (!isLatestRequest()) return;
                renderDatabaseSearchPlaceholder(`搜索失败：${error?.message || '请稍后重试'}`, {
                    meta: {
                        mode: 'advanced',
                        query: name,
                        applied_filters_summary: buildAppliedAdvancedFilterSummary(),
                        data_version: databaseSearchScope.dataVersion || getCurrentAttributeVersion(),
                        batch_scope_count: databaseSearchScope.players.length,
                        scope_type: databaseSearchScope.type,
                        scope_label: getDatabaseSearchScopeLabel(),
                    },
                });
                return;
            }
            if (!isLatestRequest()) return;
        }
        currentDbPlayers = scopedResult?.items || filterDatabaseBatchPlayersLocally(name);
        setCurrentDbSearchMeta({
            mode: hasActiveAdvancedFilters() ? 'advanced' : 'basic',
            query: name,
            truncated: Boolean(scopedResult?.truncated),
            limit: Number(scopedResult?.limit) || ADVANCED_DB_SEARCH_LIMIT,
            applied_filters_summary: scopedResult?.applied_filters_summary || (hasActiveAdvancedFilters() ? buildAppliedAdvancedFilterSummary() : []),
            data_version: scopedResult?.data_version || databaseSearchScope.dataVersion || getCurrentAttributeVersion(),
            batch_scope_count: databaseSearchScope.players.length,
            batch_unmatched_count: databaseSearchScope.unmatched.length,
            scope_type: databaseSearchScope.type,
            scope_label: getDatabaseSearchScopeLabel(),
        });
        renderAdvancedSearchTriggerState();
        renderDbPlayers(currentDbPlayers);
        if (shouldSyncHistory && typeof syncAppHistory === 'function') {
            syncAppHistory(historyMode);
        }
        return;
    }

    if (!name && !hasActiveAdvancedFilters()) {
        renderDatabaseSearchPlaceholder('请输入球员姓名或 UID，或打开高级搜索配置筛选条件。');
        if (shouldSyncHistory && typeof syncAppHistory === 'function') {
            syncAppHistory(historyMode);
        }
        return;
    }

    if (/^\d+$/.test(name) && !hasActiveAdvancedFilters()) {
        await showPlayerDetail(name, {
            returnTab: 'database',
            returnSubtab: 'search',
            pushHistory: shouldSyncHistory,
            historyMode,
            version: getCurrentAttributeVersion(),
        });
        return;
    }

    document.getElementById('dbPlayersTable').innerHTML = '<div class="loading">搜索中...</div>';
    try {
        const result = await executeDatabaseSearchRequest(name, {version: getCurrentAttributeVersion()});
        if (!isLatestRequest()) return;
        currentDbPlayers = result.items;
        setCurrentDbSearchMeta({
            mode: result.mode,
            query: result.query,
            truncated: result.truncated,
            limit: result.limit,
            applied_filters_summary: result.applied_filters_summary,
            data_version: result.data_version,
        });
        renderDbPlayers(currentDbPlayers);
    } catch (error) {
        if (!isLatestRequest()) return;
        renderDatabaseSearchPlaceholder(`搜索失败：${error?.message || '请稍后重试'}`, {
            meta: {
                mode: hasActiveAdvancedFilters() ? 'advanced' : 'basic',
                query: name,
                applied_filters_summary: hasActiveAdvancedFilters() ? buildAppliedAdvancedFilterSummary() : [],
                data_version: getCurrentAttributeVersion(),
            },
        });
    }
    if (shouldSyncHistory && typeof syncAppHistory === 'function') {
        syncAppHistory(historyMode);
    }
}

function applyAdvancedSearchAndRun() {
    toggleAdvancedSearchPanel(false);
    searchDatabase(null, {pushHistory: true, historyMode: 'replace'});
}

async function applyDatabaseBatchScopeAndSearch() {
    const table = document.getElementById('dbPlayersTable');
    if (table) table.innerHTML = '<div class="loading">正在解析批量范围...</div>';
    await searchDatabase(null, {pushHistory: true, historyMode: 'replace'});
    renderDatabaseAdvancedSearchPanel();
}

function clearDatabaseBatchScope() {
    setDatabaseBatchRawValue('');
    databaseBatchScope = {raw: '', tokens: [], players: [], unmatched: [], version: getCurrentAttributeVersion()};
    if (databaseSearchScope.type === 'batch') {
        resetDatabaseSearchScope();
    }
    renderAdvancedSearchTriggerState();
    renderDatabaseAdvancedSearchPanel();
    searchDatabase(null, {pushHistory: true, historyMode: 'replace'});
}

function clearDatabaseSearchScopeAndSearch() {
    if (databaseSearchScope.type === 'batch') {
        setDatabaseBatchRawValue('');
        databaseBatchScope = {raw: '', tokens: [], players: [], unmatched: [], version: getCurrentAttributeVersion()};
    }
    resetDatabaseSearchScope();
    renderAdvancedSearchTriggerState();
    renderDatabaseAdvancedSearchPanel();
    searchDatabase(null, {pushHistory: true, historyMode: 'replace'});
}

function clearAdvancedFiltersFromResults() {
    const currentQuery = document.getElementById('dbPlayerSearch')?.value.trim() || '';
    clearAdvancedDatabaseFilters({rerenderPanel: false, closePanel: true});
    if (currentQuery || hasDatabaseSearchScope()) {
        searchDatabase(currentQuery, {pushHistory: true, historyMode: 'replace'});
        return;
    }
    renderDatabaseSearchPlaceholder('请输入球员姓名或 UID，或打开高级搜索配置筛选条件。');
    if (typeof syncAppHistory === 'function') {
        syncAppHistory('replace');
    }
}

function getCandidateListTypeLabel(type) {
    const labels = {transfer: '转会', recommendation: '推荐', review: '复核', custom: '自定义'};
    return labels[type] || '自定义';
}

function getCandidateListStatusLabel(status) {
    const labels = {draft: '草稿', published: '教练可见', archived: '已停用'};
    return labels[status] || status || '-';
}

function getCandidateListVisibilityText(item) {
    return item?.status === 'published' ? '教练可见' : '仅管理员可见';
}

function isCandidateListMaintaining(item) {
    return Number(activeCandidateList?.id || 0) === Number(item?.id || 0);
}

function buildCandidateBadge(text, tone = '') {
    const toneClass = tone ? ` is-${tone}` : '';
    return `<span class="candidate-badge${toneClass}">${escapeHtml(text)}</span>`;
}

function buildCandidateListBadges(item) {
    const badges = [
        buildCandidateBadge(getCandidateListTypeLabel(item?.type), 'type'),
        buildCandidateBadge(getCandidateListVisibilityText(item), item?.status === 'published' ? 'published' : 'private'),
    ];
    if (isCandidateListMaintaining(item)) {
        badges.push(buildCandidateBadge('维护中', 'active'));
    }
    return badges.join('');
}

function normalizeCandidateSearchText(value) {
    return String(value || '').trim().toLowerCase();
}

function candidateListMatchesQuery(item) {
    const query = normalizeCandidateSearchText(candidateAdminListQuery);
    if (!query) return true;
    const haystack = [
        item?.name,
        item?.description,
        item?.base_data_version,
        getCandidateListTypeLabel(item?.type),
        getCandidateListVisibilityText(item),
    ].map(value => String(value || '').toLowerCase()).join(' ');
    return haystack.includes(query);
}

function candidateListMatchesFilter(item) {
    if (!item || item.status === 'archived') return false;
    if (candidateAdminListFilter === 'published') return item.status === 'published';
    if (candidateAdminListFilter === 'private') return item.status !== 'published';
    if (candidateAdminListFilter === 'maintaining') return isCandidateListMaintaining(item);
    return true;
}

function getVisibleAdminCandidateLists() {
    return adminCandidateLists
        .filter(candidateListMatchesFilter)
        .filter(candidateListMatchesQuery);
}

function buildCandidateAdminTabs() {
    const visibleLists = adminCandidateLists.filter(item => item.status !== 'archived');
    const counts = {
        all: visibleLists.length,
        published: visibleLists.filter(item => item.status === 'published').length,
        private: visibleLists.filter(item => item.status !== 'published').length,
        maintaining: visibleLists.filter(isCandidateListMaintaining).length,
    };
    const tabs = [
        ['all', '全部'],
        ['published', '教练可见'],
        ['private', '仅管理员'],
        ['maintaining', '维护中'],
    ];
    return tabs.map(([key, label]) => `
        <button class="candidate-admin-tab ${candidateAdminListFilter === key ? 'active' : ''}" type="button" onclick="setCandidateAdminListFilter('${key}')">
            <span>${escapeHtml(label)}</span>
            <strong>${Number(counts[key] || 0)}</strong>
        </button>
    `).join('');
}

function buildCandidateAdminListItems(selectedId = currentCandidateListId) {
    const lists = getVisibleAdminCandidateLists();
    if (!lists.length) {
        return '<div class="no-data candidate-admin-empty">没有符合条件的名单。</div>';
    }
    return lists.map(item => {
        const playerCount = getCandidateListPlayerCount(item);
        const publishedCount = Number(item.published_player_count || 0);
        const publishedSnapshotText = item.status === 'published' && publishedCount !== playerCount
            ? ` · 发布时 ${publishedCount.toLocaleString()} 人`
            : '';
        const isSelected = Number(item.id) === Number(selectedId);
        return `
            <button class="candidate-admin-item ${isSelected ? 'active' : ''}" type="button" onclick="selectCandidateListForAdmin(${Number(item.id)})">
                <span class="candidate-admin-item-title">${escapeHtml(item.name)}</span>
                <span class="candidate-admin-item-meta">${playerCount.toLocaleString()} 名当前球员${publishedSnapshotText} · ${escapeHtml(item.base_data_version || '-')} 版本</span>
                <span class="candidate-admin-item-badges">${buildCandidateListBadges(item)}</span>
            </button>
        `;
    }).join('');
}

function setCandidateAdminListFilter(filter) {
    candidateAdminListFilter = ['all', 'published', 'private', 'maintaining'].includes(filter) ? filter : 'all';
    renderCandidateAdminListNavigation();
}

function setCandidateAdminListSearch(value) {
    candidateAdminListQuery = value || '';
    renderCandidateAdminListNavigation();
}

function renderCandidateAdminListNavigation() {
    const tabs = document.getElementById('candidateListTopTabs');
    const items = document.getElementById('candidateAdminItems');
    if (tabs) {
        tabs.hidden = !canManageCandidateLists;
        tabs.innerHTML = canManageCandidateLists ? buildCandidateAdminTabs() : '';
    }
    if (items) items.innerHTML = buildCandidateAdminListItems(currentCandidateListId);
}

function updateCandidateListPageHeader() {
    const head = document.querySelector('.candidate-lists-head');
    const title = document.getElementById('candidateListPageTitle');
    const description = document.getElementById('candidateListPageDescription');
    if (head) head.classList.remove('is-public-search-style');
    if (title) title.textContent = '候选名单';
    if (description) {
        description.textContent = canManageCandidateLists
            ? '管理候选范围、维护名单球员；名单发布后，后续编辑会实时公开给教练。'
            : '查看已发布的候选范围；名单内容会随维护实时更新。';
    }
}

function getCandidateListPlayerCount(item) {
    const currentCount = Number(item?.player_count);
    if (Number.isFinite(currentCount)) return currentCount;
    return Number(item?.published_player_count || 0);
}

function getCandidatePublicResultLabel(count = candidateLists.length) {
    return `${Number(count || 0).toLocaleString()} 个结果`;
}

function candidatePublicListMatchesQuery(item) {
    const query = normalizeCandidateSearchText(candidatePublicListQuery);
    if (!query) return true;
    const haystack = [
        item?.name,
        item?.description,
        item?.base_data_version,
        getCandidateListTypeLabel(item?.type),
        getCandidateListVisibilityText(item),
        getCandidateListStatusLabel(item?.status),
    ].map(value => String(value || '').toLowerCase()).join(' ');
    return haystack.includes(query);
}

function getFilteredPublicCandidateLists() {
    const lists = candidateLists.filter(candidatePublicListMatchesQuery);
    const sortKey = candidatePublicListSort || 'published_desc';
    return lists.sort((left, right) => {
        if (sortKey === 'name') {
            return String(left.name || '').localeCompare(String(right.name || ''), 'zh-Hans-CN');
        }
        if (sortKey === 'players_desc') {
            return getCandidateListPlayerCount(right) - getCandidateListPlayerCount(left);
        }
        if (sortKey === 'version_desc') {
            return String(right.base_data_version || '').localeCompare(String(left.base_data_version || ''), undefined, {numeric: true});
        }
        const leftTime = Date.parse(left.published_at || left.updated_at || left.created_at || '') || 0;
        const rightTime = Date.parse(right.published_at || right.updated_at || right.created_at || '') || 0;
        return rightTime - leftTime || Number(right.id || 0) - Number(left.id || 0);
    });
}

function setCandidatePublicListSearch(value) {
    const activeInput = document.getElementById('candidatePublicListSearchInput');
    const shouldRefocus = document.activeElement === activeInput;
    const cursor = Number(activeInput?.selectionStart ?? String(value || '').length);
    candidatePublicListQuery = value || '';
    renderCandidateListsBoard();
    if (shouldRefocus) {
        const nextInput = document.getElementById('candidatePublicListSearchInput');
        if (nextInput) {
            nextInput.focus();
            nextInput.setSelectionRange(cursor, cursor);
        }
    }
}

function setCandidatePublicListSort(value) {
    candidatePublicListSort = ['published_desc', 'name', 'players_desc', 'version_desc'].includes(value) ? value : 'published_desc';
    renderCandidateListsBoard();
}

function setCandidatePublicListView(view) {
    candidatePublicListView = view === 'table' ? 'table' : 'card';
    try {
        localStorage.setItem('heigo_candidate_list_view_v2', candidatePublicListView);
    } catch (error) {
        // localStorage can be unavailable in restricted browser modes.
    }
    renderCandidateListsBoard();
}

function buildCandidatePublicViewToggle() {
    return `
        <div class="candidate-public-view-toggle" role="group" aria-label="切换候选名单视图">
            <button class="${candidatePublicListView === 'card' ? 'active' : ''}" type="button" onclick="setCandidatePublicListView('card')">卡片</button>
            <button class="${candidatePublicListView === 'table' ? 'active' : ''}" type="button" onclick="setCandidatePublicListView('table')">表格</button>
        </div>
    `;
}

function buildCandidateListSummaryBadges(item) {
    const statusText = item?.status === 'published' ? '已发布' : getCandidateListStatusLabel(item?.status);
    return `
        ${buildCandidateBadge(getCandidateListTypeLabel(item?.type), 'type')}
        ${buildCandidateBadge(statusText, item?.status === 'published' ? 'success' : 'private')}
    `;
}

function buildCandidatePublicCard(item) {
    const listId = Number(item.id);
    const count = getCandidateListPlayerCount(item);
    return `
        <article class="candidate-public-card">
            <div class="candidate-public-card-head">
                <h4>${escapeHtml(item.name || '未命名名单')}</h4>
                <span class="candidate-public-card-arrow">→</span>
            </div>
            <div class="candidate-public-card-badges">${buildCandidateListSummaryBadges(item)}</div>
            <div class="candidate-public-card-stats">
                <span><strong>${count.toLocaleString()}</strong><em>名球员</em></span>
                <span><strong>${escapeHtml(item.base_data_version || '-')}</strong><em>数据版本</em></span>
            </div>
            <p>${escapeHtml(item.description || '可继续按位置、能力和俱乐部筛选。')}</p>
            <button class="candidate-public-enter" type="button" onclick="enterCandidateListScope(${listId})">进入名单范围 <span>→</span></button>
        </article>
    `;
}

function buildCandidatePublicTable(lists) {
    return `
        <div class="candidate-public-table-wrap">
            <table class="db-players-table candidate-public-table">
                <thead>
                    <tr>
                        <th>名单名称</th>
                        <th>类型</th>
                        <th class="numeric-cell">球员数</th>
                        <th class="numeric-cell">数据版本</th>
                        <th>状态</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${lists.map(item => `
                        <tr>
                            <td class="candidate-public-table-name">
                                <strong>${escapeHtml(item.name || '未命名名单')}</strong>
                                <span>${escapeHtml(item.description || '进入后继续筛选球员')}</span>
                            </td>
                            <td>${buildCandidateBadge(getCandidateListTypeLabel(item.type), 'type')}</td>
                            <td class="numeric-cell">${getCandidateListPlayerCount(item).toLocaleString()}</td>
                            <td class="numeric-cell">${escapeHtml(item.base_data_version || '-')}</td>
                            <td>${buildCandidateBadge(item.status === 'published' ? '已发布' : getCandidateListStatusLabel(item.status), item.status === 'published' ? 'success' : 'private')}</td>
                            <td><button class="btn btn-secondary btn-small candidate-public-table-enter" type="button" onclick="enterCandidateListScope(${Number(item.id)})">进入</button></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

function renderPublicCandidateListsBoard() {
    const board = document.getElementById('candidateListsBoard');
    if (!board) return;
    const filteredLists = getFilteredPublicCandidateLists();
    const resultSummary = getCandidatePublicResultLabel(filteredLists.length);
    board.innerHTML = `
        <div class="search-section candidate-public-search-section database-filter-card surface-card">
            <div class="candidate-public-compact-head">
                <div>
                    <h2>候选名单</h2>
                    <p>查看已发布的候选范围；名单内容会随维护实时更新。</p>
                </div>
                <span>${escapeHtml(resultSummary)}</span>
            </div>
            <div class="search-controls candidate-public-search-controls">
                <div class="form-group candidate-public-search-group">
                    <label for="candidatePublicListSearchInput">搜索候选名单 (<span id="candidatePublicListCount">${escapeHtml(resultSummary)}</span>)</label>
                    <input id="candidatePublicListSearchInput" type="search" value="${escapeHtml(candidatePublicListQuery)}" placeholder="搜索名单名称、说明或版本" oninput="setCandidatePublicListSearch(this.value)">
                </div>
                <div class="form-group candidate-public-sort-group">
                    <label for="candidatePublicListSort">排序</label>
                    <select id="candidatePublicListSort" onchange="setCandidatePublicListSort(this.value)">
                        <option value="published_desc" ${candidatePublicListSort === 'published_desc' ? 'selected' : ''}>最新发布</option>
                        <option value="name" ${candidatePublicListSort === 'name' ? 'selected' : ''}>名单名称</option>
                        <option value="players_desc" ${candidatePublicListSort === 'players_desc' ? 'selected' : ''}>球员数最多</option>
                        <option value="version_desc" ${candidatePublicListSort === 'version_desc' ? 'selected' : ''}>数据版本</option>
                    </select>
                </div>
                <button class="btn btn-primary" type="button" onclick="renderCandidateListsBoard()">搜索</button>
            </div>
        </div>
        <div class="table-container candidate-public-results-panel database-results-panel surface-card">
            <div class="table-header-row">
                <div class="database-table-heading">
                    <h2 class="table-title">候选名单列表</h2>
                    <p class="database-table-meta">${candidateLists.length ? `${escapeHtml(resultSummary)} · 进入名单后可继续使用球员库筛选。` : '当前还没有已发布的候选名单。'}</p>
                </div>
                <div class="candidate-public-header-tools">
                    <div class="query-chip-row">
                        <span class="query-chip ${candidatePublicListQuery ? '' : 'is-muted'}">${candidatePublicListQuery ? `关键词：${escapeHtml(candidatePublicListQuery)}` : '未应用筛选'}</span>
                    </div>
                    ${candidateLists.length ? buildCandidatePublicViewToggle() : ''}
                </div>
            </div>
            <div class="candidate-public-results-body">
                ${candidateLists.length
                    ? (filteredLists.length
                        ? (candidatePublicListView === 'table'
                            ? buildCandidatePublicTable(filteredLists)
                            : `<div class="candidate-public-card-grid">${filteredLists.map(buildCandidatePublicCard).join('')}</div>`)
                        : '<div class="no-data candidate-public-empty">没有符合条件的候选名单。</div>')
                    : '<div class="no-data candidate-public-empty">当前还没有已发布的候选名单。</div>'}
            </div>
        </div>
    `;
}

async function fetchCandidateJson(url, options = {}) {
    const response = await fetchWithTimeout(url, {
        credentials: 'same-origin',
        ...options,
        headers: {
            ...(options.headers || {}),
        },
    });
    let payload = null;
    try {
        payload = await response.json();
    } catch (error) {
        payload = null;
    }
    if (!response.ok) {
        throw new Error(payload?.detail || payload?.message || `HTTP ${response.status}`);
    }
    return payload;
}

function getActiveCandidateListId() {
    return Number(activeCandidateList?.id || 0);
}

function hasActiveCandidateList() {
    return canManageCandidateLists && Number.isFinite(getActiveCandidateListId()) && getActiveCandidateListId() > 0;
}

function getActiveCandidateUidSet() {
    return new Set((activeCandidateListPlayers || []).map(player => Number(player.uid)).filter(Number.isFinite));
}

function isPlayerInActiveCandidateList(uid) {
    return hasActiveCandidateList() && getActiveCandidateUidSet().has(Number(uid));
}

function renderCandidateDock() {
    const dock = document.getElementById('candidateDock');
    if (!dock) return;
    const activeTab = document.body.dataset.activeTab || document.querySelector('.tab-content.active')?.id || 'home';
    const shouldShowDock = hasActiveCandidateList() && activeTab === 'database';
    document.body.classList.toggle('has-candidate-dock', shouldShowDock);
    document.body.classList.toggle('has-expanded-candidate-dock', shouldShowDock && candidateDockExpanded);
    dock.hidden = !shouldShowDock;
    dock.classList.toggle('is-hidden', !shouldShowDock);
    if (!shouldShowDock) {
        dock.innerHTML = '';
        return;
    }

    const players = Array.isArray(activeCandidateListPlayers) ? activeCandidateListPlayers : [];
    const playerCount = players.length;
    const shownPlayers = players.slice(0, 80);
    const statusText = getCandidateListVisibilityText(activeCandidateList);
    dock.innerHTML = `
        <div class="candidate-dock-shell ${candidateDockExpanded ? 'is-expanded' : 'is-collapsed'} ${playerCount ? 'has-items' : 'is-empty'}">
            ${candidateDockExpanded ? `
                <div class="candidate-dock-card">
                    <div class="candidate-dock-head">
                        <div>
                            <span class="panel-kicker">Candidate Folder</span>
                            <h4>候选名单夹</h4>
                            <div class="candidate-dock-summary">
                                <strong>${escapeHtml(activeCandidateList.name || '未命名名单')}</strong>
                                <span>${escapeHtml(statusText)} · ${playerCount.toLocaleString()} 人</span>
                            </div>
                        </div>
                        <button class="compare-dock-clear" type="button" onclick="endCandidateListMaintenance()">结束</button>
                    </div>
                    <div class="candidate-dock-actions">
                        <button class="btn btn-primary" type="button" onclick="addCurrentDbResultsToCandidateList(${getActiveCandidateListId()})" ${candidateDockBusy ? 'disabled' : ''}>添加当前结果</button>
                        <button class="btn btn-secondary" type="button" onclick="openCandidateBatchAddModal(${getActiveCandidateListId()})" ${candidateDockBusy ? 'disabled' : ''}>批量添加</button>
                        ${activeCandidateList.status === 'published'
                            ? `<button class="btn btn-secondary" type="button" onclick="unpublishCandidateList(${getActiveCandidateListId()})" ${candidateDockBusy ? 'disabled' : ''}>隐藏名单</button>`
                            : `<button class="btn btn-primary" type="button" onclick="publishCandidateList(${getActiveCandidateListId()})" ${candidateDockBusy ? 'disabled' : ''}>发布给教练</button>`}
                    </div>
                    <div class="candidate-dock-list-head">
                        <span>名单球员</span>
                        ${playerCount ? '<button class="candidate-dock-link" type="button" onclick="removeSelectedCandidateDockPlayers()">移除选中</button>' : ''}
                    </div>
                    <div class="candidate-dock-list">
                        ${shownPlayers.length ? shownPlayers.map(player => `
                            <label class="candidate-dock-player">
                                <input type="checkbox" class="candidate-dock-select" value="${Number(player.uid)}">
                                <span class="candidate-dock-player-main">
                                    <strong>${escapeHtml(player.name || `UID ${player.uid}`)}</strong>
                                    <small>UID ${escapeHtml(player.uid)} · ${escapeHtml(player.heigo_club || player.club || '-')} · CA ${escapeHtml(player.ca ?? '-')}</small>
                                </span>
                                <button class="candidate-dock-remove" type="button" onclick="event.preventDefault(); removeCandidatePlayer(${getActiveCandidateListId()}, ${Number(player.uid)})">移除</button>
                            </label>
                        `).join('') : '<div class="candidate-dock-empty">还没有球员。去球员库搜索后点击“加入名单”。</div>'}
                    </div>
                    ${playerCount > shownPlayers.length ? `<div class="candidate-dock-more">已显示前 ${shownPlayers.length} 名，可在名单管理中查看完整列表。</div>` : ''}
                </div>
            ` : ''}
            <button
                class="candidate-dock-handle ${playerCount ? 'has-items' : 'is-empty'} ${candidateDockExpanded ? 'is-expanded' : ''}"
                type="button"
                onclick="toggleCandidateDock()"
                aria-expanded="${candidateDockExpanded}"
                aria-label="${candidateDockExpanded ? '收起候选名单夹' : '展开候选名单夹'}"
            >
                <span class="candidate-dock-handle-dot">${playerCount || '+'}</span>
                <span class="candidate-dock-handle-label">${candidateDockExpanded ? '收起' : '名单夹'}</span>
                <span class="candidate-dock-handle-meta">${escapeHtml(statusText)}</span>
            </button>
        </div>
    `;
}

function toggleCandidateDock() {
    candidateDockExpanded = !candidateDockExpanded;
    if (
        candidateDockExpanded &&
        typeof isMobileViewport === 'function' &&
        isMobileViewport() &&
        typeof compareDockExpanded !== 'undefined' &&
        compareDockExpanded
    ) {
        compareDockExpanded = false;
        if (typeof renderCompareDock === 'function') {
            renderCompareDock();
        }
    }
    renderCandidateDock();
}

async function refreshActiveCandidateList(options = {}) {
    if (!hasActiveCandidateList()) {
        renderCandidateDock();
        return;
    }
    const listId = getActiveCandidateListId();
    try {
        const detail = await fetchCandidateJson(`/api/admin/candidate-lists/${listId}`);
        const version = detail.base_data_version || getCurrentAttributeVersion();
        activeCandidateList = detail;
        const payload = await fetchCandidateJson(`/api/admin/candidate-lists/${listId}/players?limit=1000&version=${encodeURIComponent(version)}`);
        activeCandidateListPlayers = Array.isArray(payload.items) ? payload.items : [];
        if (options.renderResults !== false && Array.isArray(currentDbPlayers)) {
            renderDbPlayers(currentDbPlayers);
        }
    } catch (error) {
        showModal('候选名单夹', `刷新名单失败：${escapeHtml(error.message || '请稍后重试')}`);
    }
    renderCandidateDock();
}

async function startCandidateListMaintenance(listId) {
    if (!canManageCandidateLists) {
        showModal('候选名单夹', '当前账号没有候选名单维护权限。');
        return;
    }
    candidateDockBusy = true;
    candidateDockExpanded = true;
    activeCandidateList = {id: Number(listId), name: '加载中...', status: 'draft'};
    activeCandidateListPlayers = [];
    renderCandidateDock();
    try {
        const detail = await fetchCandidateJson(`/api/admin/candidate-lists/${Number(listId)}`);
        activeCandidateList = detail;
        if (detail.base_data_version) {
            setCurrentAttributeVersion(detail.base_data_version);
            refreshAttributeVersionBanner();
        }
        await refreshActiveCandidateList({renderResults: true});
        currentDatabaseSubtab = 'search';
        syncDatabaseSubtabUI();
        activateDatabaseView('list');
        showTab('database', null, {syncHistory: true, historyMode: 'replace'});
    } finally {
        candidateDockBusy = false;
        renderCandidateDock();
    }
}

function endCandidateListMaintenance() {
    activeCandidateList = null;
    activeCandidateListPlayers = [];
    candidateDockExpanded = false;
    renderCandidateDock();
    if (Array.isArray(currentDbPlayers)) {
        renderDbPlayers(currentDbPlayers);
    }
}

async function loadCandidateLists(options = {}) {
    const board = document.getElementById('candidateListsBoard');
    if (board && options.silent !== true) {
        board.innerHTML = '<div class="loading">加载中...</div>';
    }
    try {
        candidateLists = await fetchCandidateJson('/api/candidate-lists');
        renderCandidateListsBoard();
        if (canManageCandidateLists) {
            await loadAdminCandidateLists({silent: true});
        } else {
            renderCandidateListAdminPanel();
        }
    } catch (error) {
        if (board) board.innerHTML = `<div class="no-data">候选名单加载失败：${escapeHtml(error.message || '请稍后重试')}</div>`;
    }
}

function renderCandidateListsBoard() {
    const board = document.getElementById('candidateListsBoard');
    const actions = document.getElementById('candidateListTopActions');
    const topTabs = document.getElementById('candidateListTopTabs');
    if (!board) return;
    updateCandidateListPageHeader();
    if (actions) {
        actions.innerHTML = canManageCandidateLists
            ? '<button class="btn btn-secondary candidate-refresh-button" type="button" onclick="loadCandidateLists()"><span class="candidate-refresh-icon" aria-hidden="true">↻</span>刷新</button><button class="btn btn-primary" type="button" onclick="showCandidateListCreateForm()">新建名单</button>'
            : '';
    }
    if (topTabs) {
        topTabs.hidden = !canManageCandidateLists;
        topTabs.innerHTML = canManageCandidateLists ? buildCandidateAdminTabs() : '';
    }
    if (canManageCandidateLists) {
        board.innerHTML = '';
        renderCandidateListAdminPanel();
        return;
    }
    renderPublicCandidateListsBoard();
    renderCandidateListAdminPanel();
}

async function enterCandidateListScope(listId, options = {}) {
    await loadAttributeVersionCatalog();
    const detail = await fetchCandidateJson(`/api/candidate-lists/${Number(listId)}`);
    const version = detail.base_data_version || getCurrentAttributeVersion();
    const query = typeof options.query === 'string' ? options.query : '';
    setCurrentAttributeVersion(version);
    refreshAttributeVersionBanner();
    const playersPayload = await fetchCandidateJson(`/api/candidate-lists/${Number(listId)}/players?limit=1000&version=${encodeURIComponent(version)}`);
    const players = Array.isArray(playersPayload.items) ? playersPayload.items.filter(item => !item.missing) : [];
    const missingUids = (playersPayload.items || []).filter(item => item.missing).map(item => Number(item.uid)).filter(Number.isFinite);
    setDatabaseBatchRawValue('');
    databaseBatchScope = {raw: '', tokens: [], players: [], unmatched: [], version};
    setDatabaseSearchScope({
        type: 'candidate_list',
        id: Number(listId),
        name: detail.name,
        dataVersion: version,
        uids: players.map(player => Number(player.uid)).filter(Number.isFinite),
        players,
        missingUids,
    });
    currentCandidateListId = Number(listId);
    document.getElementById('dbPlayerSearch').value = query;
    currentDatabaseSubtab = 'search';
    syncDatabaseSubtabUI();
    activateDatabaseView('list');
    await searchDatabase(query, {pushHistory: options.pushHistory !== false, historyMode: options.historyMode || 'push'});
}

async function loadAdminCandidateLists(options = {}) {
    if (!canManageCandidateLists) {
        adminCandidateLists = [];
        renderCandidateListAdminPanel();
        return;
    }
    adminCandidateLists = await fetchCandidateJson('/api/admin/candidate-lists');
    renderCandidateListAdminPanel();
}

function renderCandidateListAdminPanel(selectedId = currentCandidateListId) {
    const panel = document.getElementById('candidateListAdminPanel');
    if (!panel) return;
    panel.hidden = !canManageCandidateLists;
    if (!canManageCandidateLists) {
        panel.innerHTML = '';
        return;
    }
    const visibleAdminLists = adminCandidateLists.filter(item => item.status !== 'archived');
    const selected = visibleAdminLists.find(item => Number(item.id) === Number(selectedId)) || visibleAdminLists[0] || null;
    currentCandidateListId = selected ? Number(selected.id) : null;
    panel.innerHTML = `
        <div class="candidate-admin-workspace">
            <div class="candidate-admin-layout">
            <aside class="candidate-admin-list">
                <div class="candidate-admin-list-head">
                    <h4>名单</h4>
                    <span>${visibleAdminLists.length.toLocaleString()} 个</span>
                </div>
                <label class="candidate-admin-search">
                    <span>搜索名单</span>
                    <input id="candidateAdminListSearchInput" type="search" value="${escapeHtml(candidateAdminListQuery)}" placeholder="输入名单名、说明或版本" oninput="setCandidateAdminListSearch(this.value)">
                </label>
                <div class="candidate-admin-items">
                    <div id="candidateAdminItems">${buildCandidateAdminListItems(currentCandidateListId)}</div>
                </div>
            </aside>
            <section class="candidate-admin-detail" id="candidateAdminDetail">
                ${selected ? buildCandidateAdminDetailMarkup(selected) : buildCandidateListFormMarkup()}
            </section>
            </div>
        </div>
    `;
    if (selected) {
        loadCandidateAdminPlayers(selected.id);
    }
}

function buildCandidateListFormMarkup(item = null) {
    return `
        <form class="candidate-admin-form" onsubmit="event.preventDefault();saveCandidateList(${item ? Number(item.id) : 'null'});">
            <div class="candidate-admin-form-head">
                <div>
                    <span class="panel-kicker">${item ? 'Edit list' : 'New list'}</span>
                    <h3>${item ? '编辑名单信息' : '新建候选名单'}</h3>
                </div>
            </div>
            <div class="candidate-admin-fields">
                <label>名单名称<input id="candidateListNameInput" type="text" value="${escapeHtml(item?.name || '')}" placeholder="例如：86届中期强制转会名单"></label>
                <label>类型
                    <select id="candidateListTypeInput">
                        ${['transfer', 'recommendation', 'review', 'custom'].map(type => `<option value="${type}" ${item?.type === type ? 'selected' : ''}>${escapeHtml(getCandidateListTypeLabel(type))}</option>`).join('')}
                    </select>
                </label>
                <label>数据版本<input id="candidateListVersionInput" type="text" value="${escapeHtml(item?.base_data_version || getCurrentAttributeVersion() || '')}" placeholder="默认当前版本"></label>
                <label class="candidate-admin-wide">说明<textarea id="candidateListDescriptionInput" rows="3" placeholder="给教练查看的说明">${escapeHtml(item?.description || '')}</textarea></label>
            </div>
            <div class="candidate-admin-actions">
                <button class="btn btn-primary" type="submit">${item ? '保存信息' : '创建名单'}</button>
                ${item ? `<button class="btn btn-secondary" type="button" onclick="renderCandidateListAdminPanel(${Number(item.id)})">取消</button>` : ''}
            </div>
        </form>
    `;
}

function buildCandidateAdminMoreMenu(item) {
    const listId = Number(item.id);
    return `
        <details class="candidate-admin-more">
            <summary>更多</summary>
            <div class="candidate-admin-more-menu">
                <button type="button" onclick="enterCandidateListScope(${listId})">进入名单范围</button>
                <button type="button" onclick="showCandidateListEditForm(${listId})">编辑信息</button>
                <button type="button" onclick="duplicateCandidateList(${listId})">复制名单</button>
                ${item.status === 'published'
                    ? `<button type="button" onclick="unpublishCandidateList(${listId})">隐藏名单</button>`
                    : `<button type="button" onclick="publishCandidateList(${listId})">发布给教练</button>`}
                <button class="is-danger" type="button" onclick="deleteCandidateList(${listId})">删除名单</button>
            </div>
        </details>
    `;
}

function buildCandidateAdminDetailMarkup(item) {
    const isActive = Number(activeCandidateList?.id) === Number(item.id);
    const playerCount = getCandidateListPlayerCount(item);
    const publishedCount = Number(item.published_player_count || 0);
    return `
        <div class="candidate-admin-detail-head">
            <div class="candidate-admin-detail-title">
                <div class="candidate-admin-badges">${buildCandidateListBadges(item)}</div>
                <h3>${escapeHtml(item.name)}</h3>
                <p>${escapeHtml(item.description || '暂无说明')}</p>
            </div>
            <div class="candidate-admin-detail-actions">
                <button class="btn btn-primary" type="button" onclick="startCandidateListMaintenance(${Number(item.id)})">${isActive ? '继续维护' : '开始维护'}</button>
                ${buildCandidateAdminMoreMenu(item)}
            </div>
        </div>
        <div class="candidate-admin-overview">
            <div class="candidate-admin-stat">
                <strong>${playerCount.toLocaleString()}</strong>
                <span>当前名单球员</span>
            </div>
            <div class="candidate-admin-stat">
                <strong>${item.status === 'published' ? publishedCount.toLocaleString() : '-'}</strong>
                <span>发布时人数</span>
            </div>
            <div class="candidate-admin-stat">
                <strong>${escapeHtml(item.base_data_version || '-')}</strong>
                <span>数据版本</span>
            </div>
            <div class="candidate-admin-stat">
                <strong id="candidateAdminMatchedMetric">-</strong>
                <span>当前版本可匹配</span>
            </div>
            <div class="candidate-admin-stat">
                <strong id="candidateAdminMissingMetric">-</strong>
                <span>缺失</span>
            </div>
        </div>
        <div id="candidateAdminPlayers"><div class="loading">加载名单球员...</div></div>
    `;
}

function selectCandidateListForAdmin(listId) {
    currentCandidateListId = Number(listId);
    renderCandidateListAdminPanel(currentCandidateListId);
}

function showCandidateListCreateForm() {
    const panel = document.getElementById('candidateListAdminPanel');
    if (panel) panel.hidden = false;
    const detail = document.getElementById('candidateAdminDetail') || panel;
    if (detail) detail.innerHTML = buildCandidateListFormMarkup();
}

function showCandidateListEditForm(listId) {
    const item = adminCandidateLists.find(entry => Number(entry.id) === Number(listId));
    const detail = document.getElementById('candidateAdminDetail');
    if (item && detail) detail.innerHTML = buildCandidateListFormMarkup(item);
}

async function saveCandidateList(listId = null) {
    const payload = {
        name: document.getElementById('candidateListNameInput')?.value || '',
        type: document.getElementById('candidateListTypeInput')?.value || 'custom',
        base_data_version: document.getElementById('candidateListVersionInput')?.value || getCurrentAttributeVersion(),
        description: document.getElementById('candidateListDescriptionInput')?.value || '',
        source_filters: {},
    };
    const url = listId ? `/api/admin/candidate-lists/${Number(listId)}` : '/api/admin/candidate-lists';
    const method = listId ? 'PATCH' : 'POST';
    const result = await fetchCandidateJson(url, {
        method,
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    });
    currentCandidateListId = result.list?.id || currentCandidateListId;
    await loadAdminCandidateLists({silent: true});
    await loadCandidateLists({silent: true});
}

function parseCandidateTokenInput() {
    return parseDatabaseBatchTokens(
        document.getElementById('candidateBatchAddTokensInput')?.value
        || ''
    );
}

async function previewCandidatePlayers(listId, options = {}) {
    const tokens = Array.isArray(options.tokens) ? options.tokens : parseCandidateTokenInput();
    const result = await fetchCandidateJson(`/api/admin/candidate-lists/${Number(listId)}/players/preview`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({tokens, version: getCurrentAttributeVersion()}),
    });
    renderCandidatePreviewResult(result, options.targetId || 'candidatePreviewResult');
    return result;
}

function renderCandidatePreviewResult(result = {}, targetId = 'candidatePreviewResult') {
    const node = document.getElementById(targetId);
    if (!node) return;
    const matched = Array.isArray(result.matched) ? result.matched : [];
    const ambiguous = Array.isArray(result.ambiguous) ? result.ambiguous : [];
    const unmatched = Array.isArray(result.unmatched) ? result.unmatched : [];
    const alreadyExists = Array.isArray(result.already_exists) ? result.already_exists : [];
    node.innerHTML = `
        <div class="query-chip-row">
            <span class="query-chip">可添加 <strong>${Number(result.will_add_count || matched.length || 0)}</strong></span>
            <span class="query-chip">需确认 <strong>${Number(ambiguous.length || 0)}</strong></span>
            <span class="query-chip">未匹配 <strong>${Number(unmatched.length || 0)}</strong></span>
            <span class="query-chip">已在名单 <strong>${Number(alreadyExists.length || 0)}</strong></span>
        </div>
        ${matched.length ? `<div class="candidate-preview-section">
            <h4>可直接添加</h4>
            <div class="candidate-preview-player-grid">
                ${matched.map(player => `<span>${escapeHtml(player.name)} <small>UID ${escapeHtml(player.uid)}</small></span>`).join('')}
            </div>
        </div>` : ''}
        ${ambiguous.length ? `<div class="candidate-preview-section"><h4>需要确认</h4><div class="candidate-ambiguous-list">${ambiguous.map(item => `
            <div class="candidate-ambiguous-item">
                <strong>${escapeHtml(item.token)}</strong>
                <div class="candidate-ambiguous-options">
                    ${item.candidates.map(candidate => `
                        <label class="candidate-ambiguous-option">
                            <input type="checkbox" class="candidate-confirmed-uid" value="${Number(candidate.uid)}">
                            <span>${escapeHtml(candidate.name)} · UID ${escapeHtml(candidate.uid)} · CA ${escapeHtml(candidate.ca ?? '-')}</span>
                        </label>
                    `).join('')}
                </div>
            </div>
        `).join('')}</div></div>` : ''}
        ${alreadyExists.length ? `<div class="candidate-preview-section"><h4>已在名单</h4><p>${alreadyExists.map(player => escapeHtml(player.name || `UID ${player.uid}`)).join('、')}</p></div>` : ''}
        ${unmatched.length ? `<div class="candidate-preview-section is-warning"><h4>未匹配</h4><p>${unmatched.map(escapeHtml).join('、')}</p></div>` : ''}
    `;
}

function collectCandidateConfirmedUids() {
    return [...document.querySelectorAll('.candidate-confirmed-uid:checked')]
        .map(input => Number(input.value))
        .filter(Number.isFinite);
}

async function commitCandidatePlayers(listId, extraUids = []) {
    const confirmedUids = [...collectCandidateConfirmedUids(), ...extraUids];
    const result = await fetchCandidateJson(`/api/admin/candidate-lists/${Number(listId)}/players/commit`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({tokens: parseCandidateTokenInput(), uids: extraUids, confirmed_uids: confirmedUids, version: getCurrentAttributeVersion()}),
    });
    renderCandidatePreviewResult(result.preview || {}, document.getElementById('candidateBatchPreviewResult') ? 'candidateBatchPreviewResult' : 'candidatePreviewResult');
    await loadAdminCandidateLists({silent: true});
    await loadCandidateAdminPlayers(listId);
    await loadCandidateLists({silent: true});
    await refreshActiveCandidateList({renderResults: true});
    return result;
}

function openCandidateBatchAddModal(listId = getActiveCandidateListId()) {
    const targetListId = Number(listId);
    if (!targetListId) {
        showModal('批量添加球员', '请先选择一个候选名单。');
        return;
    }
    showModal('批量添加球员', `
        <div class="candidate-batch-modal">
            <label class="candidate-modal-field">
                <span>球员 UID / 姓名</span>
                <textarea id="candidateBatchAddTokensInput" rows="8" placeholder="每行一个 UID 或球员名，也支持逗号、分号分隔"></textarea>
            </label>
            <div class="candidate-modal-actions">
                <button class="btn btn-secondary" type="button" onclick="previewCandidateBatchAddFromModal(${targetListId})">预览</button>
                <button class="btn btn-primary" type="button" onclick="commitCandidateBatchAddFromModal(${targetListId})">确认添加</button>
            </div>
            <div id="candidateBatchPreviewResult" class="candidate-preview-result"></div>
        </div>
    `);
}

async function previewCandidateBatchAddFromModal(listId) {
    const tokens = parseCandidateTokenInput();
    if (!tokens.length) {
        renderCandidatePreviewResult({unmatched: []}, 'candidateBatchPreviewResult');
        showModal('批量添加球员', `
            <div class="candidate-batch-modal">
                <label class="candidate-modal-field">
                    <span>球员 UID / 姓名</span>
                    <textarea id="candidateBatchAddTokensInput" rows="8" placeholder="每行一个 UID 或球员名，也支持逗号、分号分隔"></textarea>
                </label>
                <div class="candidate-modal-actions">
                    <button class="btn btn-secondary" type="button" onclick="previewCandidateBatchAddFromModal(${Number(listId)})">预览</button>
                    <button class="btn btn-primary" type="button" onclick="commitCandidateBatchAddFromModal(${Number(listId)})">确认添加</button>
                </div>
                <div class="candidate-preview-result"><div class="no-data">请先输入球员 UID 或姓名。</div></div>
            </div>
        `);
        return null;
    }
    return previewCandidatePlayers(listId, {tokens, targetId: 'candidateBatchPreviewResult'});
}

async function commitCandidateBatchAddFromModal(listId) {
    const tokens = parseCandidateTokenInput();
    if (!tokens.length) {
        showModal('批量添加球员', '请先输入球员 UID 或姓名。');
        return;
    }
    const result = await commitCandidatePlayers(listId);
    const addedCount = Number(result?.added_count || 0);
    if (typeof closeModal === 'function') closeModal();
    showSuccessToast(`已添加 ${addedCount} 名球员`);
}

async function addCurrentDbResultsToCandidateList(listId) {
    const uids = (currentDbPlayers || []).map(player => Number(player.uid)).filter(Number.isFinite);
    if (!uids.length) {
        showModal('候选名单', '当前没有可加入的搜索结果。');
        return;
    }
    const result = await commitCandidatePlayers(listId, uids);
    showSuccessToast(`已添加 ${Number(result?.added_count || 0)} 名球员`);
}

function getCandidateAdminListVersion(listId) {
    const item = adminCandidateLists.find(entry => Number(entry.id) === Number(listId));
    return item?.base_data_version || getCurrentAttributeVersion();
}

async function loadCandidateAdminPlayers(listId) {
    const node = document.getElementById('candidateAdminPlayers');
    if (!node) return;
    const targetListId = Number(listId);
    const version = getCandidateAdminListVersion(targetListId);
    const payload = await fetchCandidateJson(`/api/admin/candidate-lists/${targetListId}/players?limit=1000&version=${encodeURIComponent(version)}`);
    if (Number(candidateAdminPlayersCache.listId) !== targetListId) {
        candidateAdminSelectedUids = new Set();
        candidateAdminPlayerQuery = '';
        candidateAdminPlayerStatus = 'all';
        candidateAdminPlayerSort = {field: 'uid', order: 'asc'};
    }
    candidateAdminPlayersCache = {
        listId: targetListId,
        items: Array.isArray(payload.items) ? payload.items : [],
        totalCount: Number(payload.total_count || 0),
        matchedCount: Number(payload.matched_count || 0),
        missingCount: Number(payload.missing_count || 0),
    };
    const matchedMetric = document.getElementById('candidateAdminMatchedMetric');
    const missingMetric = document.getElementById('candidateAdminMissingMetric');
    if (matchedMetric) matchedMetric.textContent = candidateAdminPlayersCache.matchedCount.toLocaleString();
    if (missingMetric) missingMetric.textContent = candidateAdminPlayersCache.missingCount.toLocaleString();
    node.innerHTML = `
        <div class="candidate-admin-player-panel">
            <div class="candidate-admin-player-head">
                <div>
                    <strong>名单球员</strong>
                    <span id="candidateAdminPlayerSummary"></span>
                </div>
                <button class="btn btn-secondary btn-small" type="button" onclick="openCandidateBatchAddModal(${targetListId})">批量添加</button>
            </div>
            <div class="candidate-admin-player-tools">
                <label>
                    <span>搜索球员</span>
                    <input id="candidateAdminPlayerSearchInput" type="search" value="${escapeHtml(candidateAdminPlayerQuery)}" placeholder="姓名、UID、俱乐部或位置" oninput="setCandidateAdminPlayerSearch(this.value)">
                </label>
                <label>
                    <span>状态</span>
                    <select id="candidateAdminPlayerStatusSelect" onchange="setCandidateAdminPlayerStatus(this.value)">
                        <option value="all" ${candidateAdminPlayerStatus === 'all' ? 'selected' : ''}>全部</option>
                        <option value="matched" ${candidateAdminPlayerStatus === 'matched' ? 'selected' : ''}>可匹配</option>
                        <option value="missing" ${candidateAdminPlayerStatus === 'missing' ? 'selected' : ''}>缺失</option>
                    </select>
                </label>
                <div class="candidate-admin-bulk-actions">
                    <span id="candidateAdminSelectedCount">已选 0</span>
                    <button id="candidateAdminBulkRemove" class="btn btn-danger btn-small" type="button" onclick="removeSelectedCandidateAdminPlayers(${targetListId})" disabled>批量移除</button>
                </div>
            </div>
            <div id="candidateAdminPlayerTableWrap" class="candidate-admin-table-wrap"></div>
        </div>
    `;
    renderCandidateAdminPlayerTable();
}

function setCandidateAdminPlayerSearch(value) {
    candidateAdminPlayerQuery = value || '';
    renderCandidateAdminPlayerTable();
}

function setCandidateAdminPlayerStatus(value) {
    candidateAdminPlayerStatus = ['all', 'matched', 'missing'].includes(value) ? value : 'all';
    renderCandidateAdminPlayerTable();
}

function sortCandidateAdminPlayers(field) {
    if (candidateAdminPlayerSort.field === field) {
        candidateAdminPlayerSort.order = candidateAdminPlayerSort.order === 'asc' ? 'desc' : 'asc';
    } else {
        candidateAdminPlayerSort = {field, order: ['ca', 'pa'].includes(field) ? 'desc' : 'asc'};
    }
    renderCandidateAdminPlayerTable();
}

function getCandidateAdminPlayerSortValue(player, field) {
    if (['uid', 'ca', 'pa'].includes(field)) {
        const value = Number(player?.[field]);
        return Number.isFinite(value) ? value : -Infinity;
    }
    return String(player?.[field] || '').toLowerCase();
}

function getFilteredCandidateAdminPlayers() {
    const query = normalizeCandidateSearchText(candidateAdminPlayerQuery);
    const filtered = candidateAdminPlayersCache.items.filter(player => {
        if (candidateAdminPlayerStatus === 'matched' && player.missing) return false;
        if (candidateAdminPlayerStatus === 'missing' && !player.missing) return false;
        if (!query) return true;
        const haystack = [player.uid, player.name, player.position, player.club, player.heigo_club]
            .map(value => String(value || '').toLowerCase())
            .join(' ');
        return haystack.includes(query);
    });
    const direction = candidateAdminPlayerSort.order === 'desc' ? -1 : 1;
    return filtered.sort((left, right) => {
        const leftValue = getCandidateAdminPlayerSortValue(left, candidateAdminPlayerSort.field);
        const rightValue = getCandidateAdminPlayerSortValue(right, candidateAdminPlayerSort.field);
        if (leftValue > rightValue) return direction;
        if (leftValue < rightValue) return -direction;
        return Number(left.uid || 0) - Number(right.uid || 0);
    });
}

function buildCandidateAdminSortButton(field, label) {
    const isActive = candidateAdminPlayerSort.field === field;
    const arrow = isActive ? (candidateAdminPlayerSort.order === 'asc' ? '↑' : '↓') : '';
    return `<button class="candidate-admin-sort ${isActive ? 'active' : ''}" type="button" onclick="sortCandidateAdminPlayers('${field}')">${escapeHtml(label)} ${arrow}</button>`;
}

function renderCandidateAdminPlayerTable() {
    const wrap = document.getElementById('candidateAdminPlayerTableWrap');
    if (!wrap) return;
    const players = getFilteredCandidateAdminPlayers();
    const summary = document.getElementById('candidateAdminPlayerSummary');
    if (summary) {
        summary.textContent = `显示 ${players.length.toLocaleString()} / ${candidateAdminPlayersCache.totalCount.toLocaleString()}，可匹配 ${candidateAdminPlayersCache.matchedCount.toLocaleString()}，缺失 ${candidateAdminPlayersCache.missingCount.toLocaleString()}`;
    }
    if (!players.length) {
        wrap.innerHTML = '<div class="no-data candidate-admin-empty">没有符合条件的球员。</div>';
        updateCandidateAdminSelectionUI();
        return;
    }
    wrap.innerHTML = `
        <table class="db-players-table candidate-admin-player-table">
            <thead>
                <tr>
                    <th class="candidate-admin-check-cell"><input id="candidateAdminSelectAll" type="checkbox" onchange="setCandidateAdminVisibleSelection(this.checked)"></th>
                    <th>${buildCandidateAdminSortButton('uid', 'UID')}</th>
                    <th>${buildCandidateAdminSortButton('name', '姓名')}</th>
                    <th>${buildCandidateAdminSortButton('position', '位置')}</th>
                    <th class="numeric-cell">${buildCandidateAdminSortButton('ca', 'CA')}</th>
                    <th class="numeric-cell">${buildCandidateAdminSortButton('pa', 'PA')}</th>
                    <th>${buildCandidateAdminSortButton('club', '俱乐部')}</th>
                    <th>状态</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                ${players.map(player => {
                    const uid = Number(player.uid);
                    const checked = candidateAdminSelectedUids.has(uid) ? 'checked' : '';
                    const status = player.missing
                        ? buildCandidateBadge('缺失', 'warning')
                        : buildCandidateBadge('可匹配', 'success');
                    return `
                        <tr>
                            <td class="candidate-admin-check-cell"><input type="checkbox" value="${uid}" ${checked} onchange="toggleCandidateAdminPlayerSelection(${uid}, this.checked)"></td>
                            <td class="uid-column">${escapeHtml(player.uid)}</td>
                            <td class="candidate-admin-player-name">${escapeHtml(player.name || '-')}</td>
                            <td>${escapeHtml(player.position || '-')}</td>
                            <td class="numeric-cell">${escapeHtml(player.ca ?? '-')}</td>
                            <td class="numeric-cell">${escapeHtml(player.pa ?? '-')}</td>
                            <td>${escapeHtml(player.heigo_club || player.club || '-')}</td>
                            <td>${status}</td>
                            <td><button class="btn btn-danger btn-small" type="button" onclick="confirmRemoveCandidatePlayer(${Number(candidateAdminPlayersCache.listId)}, ${uid})">移除</button></td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
    updateCandidateAdminSelectionUI();
}

function setCandidateAdminVisibleSelection(checked) {
    getFilteredCandidateAdminPlayers().forEach(player => {
        const uid = Number(player.uid);
        if (!Number.isFinite(uid)) return;
        if (checked) {
            candidateAdminSelectedUids.add(uid);
        } else {
            candidateAdminSelectedUids.delete(uid);
        }
    });
    renderCandidateAdminPlayerTable();
}

function toggleCandidateAdminPlayerSelection(uid, checked) {
    const numericUid = Number(uid);
    if (!Number.isFinite(numericUid)) return;
    if (checked) {
        candidateAdminSelectedUids.add(numericUid);
    } else {
        candidateAdminSelectedUids.delete(numericUid);
    }
    updateCandidateAdminSelectionUI();
}

function updateCandidateAdminSelectionUI() {
    const selectedCount = document.getElementById('candidateAdminSelectedCount');
    const bulkRemove = document.getElementById('candidateAdminBulkRemove');
    const selectAll = document.getElementById('candidateAdminSelectAll');
    const count = candidateAdminSelectedUids.size;
    if (selectedCount) selectedCount.textContent = `已选 ${count.toLocaleString()}`;
    if (bulkRemove) bulkRemove.disabled = count === 0;
    if (selectAll) {
        const players = getFilteredCandidateAdminPlayers();
        const selectable = players.map(player => Number(player.uid)).filter(Number.isFinite);
        const selectedVisible = selectable.filter(uid => candidateAdminSelectedUids.has(uid)).length;
        selectAll.checked = selectable.length > 0 && selectedVisible === selectable.length;
        selectAll.indeterminate = selectedVisible > 0 && selectedVisible < selectable.length;
    }
}

async function confirmRemoveCandidatePlayer(listId, uid) {
    const player = candidateAdminPlayersCache.items.find(item => Number(item.uid) === Number(uid));
    const label = player?.name ? `${player.name}（UID ${uid}）` : `UID ${uid}`;
    if (!await showConfirmDialog({title: '移除候选球员', message: `将 ${label} 从当前候选名单移除。`, confirmLabel: '确认移除', danger: true})) return;
    await removeCandidatePlayer(listId, uid);
}

async function removeSelectedCandidateAdminPlayers(listId) {
    const uids = [...candidateAdminSelectedUids].map(Number).filter(Number.isFinite);
    if (!uids.length) return;
    if (!await showConfirmDialog({title: '批量移除候选球员', message: `将从当前候选名单移除 ${uids.length} 名球员。`, confirmLabel: '确认移除', danger: true})) return;
    await fetchCandidateJson(`/api/admin/candidate-lists/${Number(listId)}/players/batch-remove`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({uids}),
    });
    candidateAdminSelectedUids = new Set();
    await loadAdminCandidateLists({silent: true});
    await loadCandidateAdminPlayers(listId);
    await loadCandidateLists({silent: true});
    await refreshActiveCandidateList({renderResults: true});
}

async function removeCandidatePlayer(listId, uid) {
    await fetchCandidateJson(`/api/admin/candidate-lists/${Number(listId)}/players/batch-remove`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({uids: [Number(uid)]}),
    });
    await loadAdminCandidateLists({silent: true});
    await loadCandidateAdminPlayers(listId);
    await loadCandidateLists({silent: true});
    await refreshActiveCandidateList({renderResults: true});
}

async function removeSelectedCandidateDockPlayers() {
    const listId = getActiveCandidateListId();
    const uids = [...document.querySelectorAll('.candidate-dock-select:checked')]
        .map(input => Number(input.value))
        .filter(Number.isFinite);
    if (!listId || !uids.length) {
        showModal('候选名单夹', '请先勾选要移除的球员。');
        return;
    }
    if (!await showConfirmDialog({title: '移除已选球员', message: `将从当前名单移除 ${uids.length} 名球员。`, confirmLabel: '确认移除', danger: true})) return;
    await fetchCandidateJson(`/api/admin/candidate-lists/${listId}/players/batch-remove`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({uids}),
    });
    await loadAdminCandidateLists({silent: true});
    await loadCandidateLists({silent: true});
    await refreshActiveCandidateList({renderResults: true});
}

async function addPlayerToActiveCandidateList(uid) {
    const listId = getActiveCandidateListId();
    if (!listId) {
        showModal('候选名单夹', '请先在候选名单管理中开始维护一个名单。');
        return;
    }
    candidateDockBusy = true;
    renderCandidateDock();
    try {
        await commitCandidatePlayers(listId, [Number(uid)]);
    } finally {
        candidateDockBusy = false;
        renderCandidateDock();
    }
}

async function removePlayerFromActiveCandidateList(uid) {
    const listId = getActiveCandidateListId();
    if (!listId) return;
    await removeCandidatePlayer(listId, uid);
}

function buildCandidateResultActionCell(player) {
    if (!hasActiveCandidateList()) return '';
    const uid = Number(player.uid);
    const inList = isPlayerInActiveCandidateList(uid);
    return `
        <td class="candidate-result-action-cell">
            ${inList
                ? `<button class="candidate-result-action is-added" type="button" onclick="removePlayerFromActiveCandidateList(${uid})">已加入</button>`
                : `<button class="candidate-result-action" type="button" onclick="addPlayerToActiveCandidateList(${uid})">加入名单</button>`}
        </td>
    `;
}

async function publishCandidateList(listId) {
    const preview = await fetchCandidateJson(`/api/admin/candidate-lists/${Number(listId)}/publish-preview`, {method: 'POST'});
    const ok = await showConfirmDialog({title: '发布候选名单', message: `当前 ${preview.current_count} 人，新增 ${preview.added_uids.length}，移除 ${preview.removed_uids.length}，缺失 ${preview.missing_count}。`, confirmLabel: '发布给教练'});
    if (!ok) return;
    await fetchCandidateJson(`/api/admin/candidate-lists/${Number(listId)}/publish`, {method: 'POST'});
    await loadAdminCandidateLists({silent: true});
    await loadCandidateLists({silent: true});
    await refreshActiveCandidateList({renderResults: true});
}

async function unpublishCandidateList(listId) {
    await fetchCandidateJson(`/api/admin/candidate-lists/${Number(listId)}/unpublish`, {method: 'POST'});
    await loadAdminCandidateLists({silent: true});
    await loadCandidateLists({silent: true});
    await refreshActiveCandidateList({renderResults: true});
}

async function duplicateCandidateList(listId) {
    const result = await fetchCandidateJson(`/api/admin/candidate-lists/${Number(listId)}/duplicate`, {method: 'POST'});
    currentCandidateListId = result.list?.id || currentCandidateListId;
    await loadAdminCandidateLists({silent: true});
    await loadCandidateLists({silent: true});
}

async function deleteCandidateList(listId) {
    const targetId = Number(listId);
    const item = adminCandidateLists.find(entry => Number(entry.id) === targetId);
    const name = item?.name || `名单 ${targetId}`;
    const ok = await showConfirmDialog({title: '删除候选名单', message: `“${name}”将对教练不可见，并从管理员列表移除。`, confirmLabel: '确认删除', danger: true});
    if (!ok) return;
    await fetchCandidateJson(`/api/admin/candidate-lists/${targetId}/archive`, {method: 'POST'});
    if (Number(activeCandidateList?.id || 0) === targetId) {
        endCandidateListMaintenance();
    }
    currentCandidateListId = null;
    await loadAdminCandidateLists({silent: true});
    await loadCandidateLists({silent: true});
}

async function loadReactionLeaderboard(options = {}) {
    const shouldSyncHistory = options.pushHistory !== false;
    const historyMode = options.historyMode || 'push';
    currentDatabaseSubtab = 'leaderboard';
    syncDatabaseSubtabUI();
    activateDatabaseView('leaderboard');
    await loadAttributeVersionCatalog();
    if (typeof ensureTeamsLoaded === 'function') await ensureTeamsLoaded();
    refreshAttributeVersionBanner();
    populateReactionLeaderboardTeamSelect();

    const metric = document.getElementById('dbReactionMetricSelect')?.value || 'flowers';
    const limit = document.getElementById('dbReactionLimitSelect')?.value || '20';
    const team = document.getElementById('dbReactionTeamSelect')?.value || '';
    const title = document.getElementById('dbReactionLeaderboardTitle');
    const table = document.getElementById('dbReactionLeaderboardTable');
    if (title) {
        title.textContent = `${getDatabaseLeaderboardMetricLabel(metric)} (${limit})`;
    }
    if (table) {
        table.innerHTML = '<div class="loading">加载中...</div>';
    }

    const params = new URLSearchParams({
        metric,
        limit: String(limit),
    });
    if (team) {
        params.set('team', team);
    }
    const version = getCurrentAttributeVersion();
    if (version) {
        params.set('version', version);
    }
    try {
        const response = await fetchWithTimeout(`/api/reactions/leaderboard?${params.toString()}`);
        let payload = null;
        try {
            payload = await response.json();
        } catch (error) {
            payload = null;
        }
        if (!response.ok) {
            throw new Error(payload?.detail || payload?.message || `HTTP ${response.status}`);
        }
        renderReactionLeaderboard(payload);
    } catch (error) {
        renderReactionLeaderboardError({
            metric,
            limit,
            dataVersion: version,
            message: error?.message || '互动排行榜加载失败，请稍后重试。',
        });
    }
    if (shouldSyncHistory && typeof syncAppHistory === 'function') {
        syncAppHistory(historyMode);
    }
}

function renderReactionLeaderboardError({metric = 'flowers', limit = '20', dataVersion = '', message = ''} = {}) {
    const table = document.getElementById('dbReactionLeaderboardTable');
    const title = document.getElementById('dbReactionLeaderboardTitle');
    if (!table) return;

    const versionLabel = dataVersion ? ` · ${escapeHtml(dataVersion)}` : '';
    if (title) {
        title.textContent = `${getDatabaseLeaderboardMetricLabel(metric)} (${limit})${versionLabel}`;
    }

    const fallbackMessage = message ? `互动排行榜加载失败：${message}` : '互动排行榜加载失败，请稍后重试。';
    table.innerHTML = `<div class="no-data">${escapeHtml(fallbackMessage)}</div>`;
}

function renderReactionLeaderboard(payload) {
    const table = document.getElementById('dbReactionLeaderboardTable');
    const title = document.getElementById('dbReactionLeaderboardTitle');
    if (!table) return;

    const metric = payload?.metric || document.getElementById('dbReactionMetricSelect')?.value || 'flowers';
    const limit = payload?.limit || document.getElementById('dbReactionLimitSelect')?.value || '20';
    const versionLabel = payload?.data_version ? ` · ${escapeHtml(payload.data_version)}` : '';
    if (title) {
        title.textContent = `${getDatabaseLeaderboardMetricLabel(metric)} (${limit})${versionLabel}`;
    }

    const items = Array.isArray(payload?.items) ? payload.items : [];
    if (!items.length) {
        table.innerHTML = '<div class="database-empty-state"><strong>当前筛选条件下还没有互动数据</strong><small>可以切换榜单类型、球队或显示数量后重试。</small></div>';
        return;
    }

    const playerAction = item => `showPlayerDetail(${item.uid}, {returnTab: 'database', returnSubtab: 'leaderboard', version: '${escapeHtml(item.data_version)}'})`;
    table.innerHTML = `
        <table class="db-reaction-table" aria-label="球员互动排行榜">
            <thead>
                <tr>
                    <th class="numeric-column">排名</th>
                    <th>球员</th>
                    <th class="numeric-column">UID</th>
                    <th>HEIGO球队</th>
                    <th>位置</th>
                    <th class="numeric-column">CA</th>
                    <th class="numeric-column">PA</th>
                    <th class="numeric-column">鲜花</th>
                    <th class="numeric-column">鸡蛋</th>
                    <th class="numeric-column">净值</th>
                </tr>
            </thead>
            <tbody>
                ${items.map((item, index) => `
                    <tr>
                        <td class="numeric-cell"><span class="leaderboard-rank-badge">${index + 1}</span></td>
                        <td><button class="player-link reaction-player-link" type="button" onclick="${playerAction(item)}">${escapeHtml(item.name)}</button></td>
                        <td class="numeric-cell">${escapeHtml(item.uid)}</td>
                        <td class="${item.heigo_club !== '大海' ? 'heigo-club' : ''}">${escapeHtml(item.heigo_club || '大海')}</td>
                        <td>${escapeHtml(item.position || '-')}</td>
                        <td class="numeric-cell">${escapeHtml(item.ca ?? '-')}</td>
                        <td class="numeric-cell">${escapeHtml(item.pa ?? '-')}</td>
                        <td class="numeric-cell leaderboard-flower">${escapeHtml(item.flowers ?? 0)}</td>
                        <td class="numeric-cell leaderboard-egg">${escapeHtml(item.eggs ?? 0)}</td>
                        <td class="numeric-cell"><strong>${escapeHtml(item.net_score ?? 0)}</strong></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
        <div class="mobile-reaction-ranking is-${escapeHtml(metric)}" aria-label="球员互动排行榜移动列表">
            ${items.map((item, index) => `
                <article class="reaction-ranking-card">
                    <span class="reaction-card-rank">${index + 1}</span>
                    <div class="reaction-card-main"><button class="reaction-card-name" type="button" onclick="${playerAction(item)}">${escapeHtml(item.name)}</button><span>${escapeHtml(item.heigo_club || '大海')} · ${escapeHtml(item.position || '-')}</span><small>CA ${escapeHtml(item.ca ?? '-')} · PA ${escapeHtml(item.pa ?? '-')} · UID ${escapeHtml(item.uid)}</small></div>
                    <div class="reaction-card-scores"><span class="${metric === 'flowers' ? 'is-active' : ''}"><small>鲜花</small><strong>${escapeHtml(item.flowers ?? 0)}</strong></span><span class="${metric === 'eggs' ? 'is-active' : ''}"><small>鸡蛋</small><strong>${escapeHtml(item.eggs ?? 0)}</strong></span><span class="${metric === 'net' ? 'is-active' : ''}"><small>净值</small><strong>${escapeHtml(item.net_score ?? 0)}</strong></span></div>
                </article>
            `).join('')}
        </div>
    `;
}

function resetReactionLeaderboardFilters() {
    const metricSelect = document.getElementById('dbReactionMetricSelect');
    const limitSelect = document.getElementById('dbReactionLimitSelect');
    const teamSelect = document.getElementById('dbReactionTeamSelect');
    if (metricSelect) metricSelect.value = 'flowers';
    if (limitSelect) limitSelect.value = '20';
    if (teamSelect) teamSelect.value = '';
    loadReactionLeaderboard({pushHistory: true, historyMode: 'replace'});
}

function getPowerShapeLabel(shape) {
    if (shape === 'current') return '当前形态';
    if (/^[1-5]$/.test(String(shape))) return `+${shape} 形态`;
    return '全部形态';
}

function getTopPercentLabel(value) {
    const numeric = Number(value);
    return Math.max(1, Math.ceil((Number.isFinite(numeric) ? numeric : 100) - 0.000001));
}

async function loadPowerRanking(options = {}) {
    const shouldSyncHistory = options.pushHistory !== false;
    currentDatabaseSubtab = 'power';
    syncDatabaseSubtabUI();
    activateDatabaseView('power');
    await loadAttributeVersionCatalog();
    if (typeof ensureTeamsLoaded === 'function') await ensureTeamsLoaded();
    refreshAttributeVersionBanner();
    populatePowerRankingTeamSelect();
    const shape = document.getElementById('dbPowerShapeSelect')?.value || 'all';
    const limit = document.getElementById('dbPowerLimitSelect')?.value || '50';
    const team = document.getElementById('dbPowerTeamSelect')?.value || '';
    const table = document.getElementById('dbPowerRankingTable');
    if (table) table.innerHTML = '<div class="loading">正在推算各成长形态战力...</div>';
    const params = new URLSearchParams({shape, limit: String(limit)});
    if (team) params.set('team', team);
    const version = getCurrentAttributeVersion();
    if (version) params.set('version', version);
    try {
        const response = await fetchWithTimeout(`/api/attributes/power-ranking?${params.toString()}`);
        const payload = await response.json();
        if (!response.ok) throw new Error(payload?.detail || `HTTP ${response.status}`);
        renderPowerRanking(payload);
    } catch (error) {
        if (table) table.innerHTML = `<div class="no-data">${escapeHtml(error?.message || '战力排行榜加载失败，请稍后重试。')}</div>`;
    }
    if (shouldSyncHistory && typeof syncAppHistory === 'function') syncAppHistory(options.historyMode || 'push');
}

function renderPowerRanking(payload) {
    const table = document.getElementById('dbPowerRankingTable');
    const title = document.getElementById('dbPowerRankingTitle');
    if (!table) return;
    const items = Array.isArray(payload?.items) ? payload.items : [];
    const versionLabel = payload?.data_version ? ` · ${payload.data_version}` : '';
    const limitLabel = payload?.limit === 'all' ? `全部 ${items.length} 条` : `Top ${payload?.limit || items.length}`;
    if (title) title.textContent = `战力排行榜 · ${getPowerShapeLabel(payload?.shape || 'all')} · ${limitLabel}${versionLabel}`;
    if (!items.length) {
        table.innerHTML = '<div class="no-data">当前筛选条件下没有符合资格的外场球员形态</div>';
        return;
    }
    const playerLink = item => `<button class="power-player-link" type="button" onclick="showPlayerDetail(${item.uid}, {returnTab: 'database', returnSubtab: 'power', version: '${escapeHtml(item.data_version)}', previewStep: ${Number(item.growth_step || 0)}})">${escapeHtml(item.name)}${item.growth_step ? ` <span class="power-growth-badge">+${item.growth_step}</span>` : ''}</button>`;
    table.innerHTML = `
        <table class="db-power-table" aria-label="球员加权战力排行榜"><thead><tr><th class="numeric-column">排名</th><th>球员</th><th>形态</th><th class="numeric-column">加权战力</th><th>HEIGO战力 / 联赛位置</th><th class="numeric-column">当前 CA</th><th class="numeric-column">推算 CA</th><th class="numeric-column">PA</th><th class="numeric-column">潜力空间</th><th>位置</th><th>HEIGO 球队</th><th>现实俱乐部</th></tr></thead>
        <tbody>${items.map(item => `<tr><td class="numeric-cell"><span class="leaderboard-rank-badge">${item.rank}</span></td><td>${playerLink(item)}</td><td><span class="power-shape-pill ${item.growth_step ? 'is-growth' : ''}">${item.growth_step ? `+${item.growth_step}` : '当前'}</span></td><td class="numeric-cell"><strong class="power-score-value">${Number(item.weighted_power).toFixed(2)}</strong></td><td><span class="power-relative-inline"><strong>${Number(item.heigo_power).toFixed(2)}</strong><small>前 ${getTopPercentLabel(item.top_percent)}%</small></span></td><td class="numeric-cell">${item.ca}</td><td class="numeric-cell"><strong>${item.projected_ca}</strong></td><td class="numeric-cell">${item.pa}</td><td class="numeric-cell">${item.potential_gap}</td><td>${escapeHtml(item.position || '-')}</td><td class="${item.heigo_club !== '大海' ? 'heigo-club' : ''}">${escapeHtml(item.heigo_club || '大海')}</td><td>${escapeHtml(item.club || '-')}</td></tr>`).join('')}</tbody></table>
        <div class="mobile-power-ranking">${items.map(item => `<article class="power-ranking-card"><div class="power-card-rank">#${item.rank}</div><div class="power-card-main"><div class="power-card-name">${playerLink(item)}</div><div class="power-card-meta"><span>${escapeHtml(item.position || '-')}</span><span>${escapeHtml(item.heigo_club || '大海')}</span><span>CA ${item.ca} → ${item.projected_ca} / PA ${item.pa}</span></div></div><div class="power-card-score"><strong>${Number(item.weighted_power).toFixed(2)}</strong><small>加权战力</small><span class="power-relative-inline"><b>${Number(item.heigo_power).toFixed(2)}</b><em>前 ${getTopPercentLabel(item.top_percent)}%</em></span></div></article>`).join('')}</div>`;
}

function resetPowerRankingFilters() {
    const shape = document.getElementById('dbPowerShapeSelect');
    const limit = document.getElementById('dbPowerLimitSelect');
    const team = document.getElementById('dbPowerTeamSelect');
    if (shape) shape.value = 'all';
    if (limit) limit.value = '50';
    if (team) team.value = '';
    loadPowerRanking({pushHistory: true, historyMode: 'replace'});
}

async function showDatabaseSubtab(subtab, options = {}) {
    currentDatabaseSubtab = subtab === 'tactics' ? 'tactics' : subtab === 'power' ? 'power' : subtab === 'leaderboard' ? 'leaderboard' : subtab === 'candidates' ? 'candidates' : 'search';
    syncDatabaseSubtabUI();
    if (currentDatabaseSubtab === 'tactics') {
        activateDatabaseView('tactics');
        await ensureAppModule('database-tactics');
        loadDatabaseTacticsBoard(options);
        return;
    }
    if (currentDatabaseSubtab === 'leaderboard') {
        loadReactionLeaderboard(options);
        return;
    }
    if (currentDatabaseSubtab === 'power') {
        loadPowerRanking(options);
        return;
    }
    if (currentDatabaseSubtab === 'candidates') {
        activateDatabaseView('candidates');
        loadCandidateLists(options);
        if (options.pushHistory !== false && typeof syncAppHistory === 'function') {
            syncAppHistory(options.historyMode || 'push');
        }
        return;
    }
    activateDatabaseView('list');
    renderDatabaseSearchSummary();
    if (options.pushHistory !== false && typeof syncAppHistory === 'function') {
        syncAppHistory(options.historyMode || 'push');
    }
}

function sortDbPlayers() {
    renderDbPlayers(currentDbPlayers);
}

function getDbMobileSortValue() {
    if (!currentDbSort?.field) return '';
    return `${currentDbSort.field}_${currentDbSort.order || getDefaultDbSortOrder(currentDbSort.type || 'number')}`;
}

function setDbMobileSort(value) {
    const raw = String(value || '');
    if (!raw) {
        currentDbSort = {field: '', order: '', type: 'number'};
    } else {
        const [field, order] = raw.split('_');
        const config = DB_SORT_FIELD_CONFIG[field] || {type: 'text'};
        currentDbSort = {
            field,
            type: config.type,
            order: order === 'asc' ? 'asc' : 'desc',
        };
    }
    renderDbPlayers(currentDbPlayers);
    if (typeof syncAppHistory === 'function') {
        syncAppHistory('replace');
    }
}

function findCurrentDbPlayer(uid, dataVersion = '') {
    const targetUid = Number(uid);
    const targetVersion = String(dataVersion || '').trim();
    return (currentDbPlayers || []).find(player => (
        Number(player.uid) === targetUid &&
        (!targetVersion || getPlayerDataVersion(player) === targetVersion)
    )) || (currentDbPlayers || []).find(player => Number(player.uid) === targetUid) || null;
}

function queueDbResultPlayerForCompare(uid, dataVersion = '') {
    const player = findCurrentDbPlayer(uid, dataVersion);
    if (!player || typeof queuePlayerForCompare !== 'function') return;
    queuePlayerForCompare(player);
}

function getMobileDbPowerMetrics(player) {
    const weightedPower = Number(player?.weighted_power);
    const heigoPower = Number(player?.heigo_power);
    const topPercent = Number(player?.top_percent);
    if (!Number.isFinite(weightedPower) || !Number.isFinite(heigoPower)) return null;
    return {
        weightedPower,
        heigoPower,
        topPercent: Number.isFinite(topPercent) ? topPercent : 100,
        tone: getHeigoPowerTone(heigoPower),
    };
}

function buildMobileDbCandidateAction(player) {
    if (!hasActiveCandidateList()) return '';
    const uid = Number(player.uid || 0);
    if (!uid) return '';
    const inList = isPlayerInActiveCandidateList(uid);
    return inList
        ? `<button class="mobile-db-card-action is-added" type="button" onclick="removePlayerFromActiveCandidateList(${uid})">已加入</button>`
        : `<button class="mobile-db-card-action" type="button" onclick="addPlayerToActiveCandidateList(${uid})">加入名单</button>`;
}

function renderMobileDbResultToolbar(players) {
    const sortedValue = getDbMobileSortValue();
    const summary = {
        ...DEFAULT_DB_SEARCH_META,
        ...(currentDbSearchMeta || {}),
    };
    const scopeLabel = summary.scope_label || getDatabaseSearchScopeLabel();
    const hasScope = hasDatabaseSearchScope();
    return `
        <div class="mobile-db-result-toolbar">
            <div class="mobile-db-result-toolbar-main">
                <span>当前结果</span>
                <strong>${Number(players.length || 0).toLocaleString()} 人</strong>
            </div>
            <button class="mobile-db-tool-button" type="button" onclick="toggleAdvancedSearchPanel()">高级筛选</button>
            <label class="mobile-db-sort-control">
                <span>排序</span>
                <select onchange="setDbMobileSort(this.value)" aria-label="移动端排序">
                    <option value="" ${sortedValue === '' ? 'selected' : ''}>默认</option>
                    <option value="ca_desc" ${sortedValue === 'ca_desc' ? 'selected' : ''}>CA 高到低</option>
                    <option value="pa_desc" ${sortedValue === 'pa_desc' ? 'selected' : ''}>PA 高到低</option>
                    <option value="weighted_power_desc" ${sortedValue === 'weighted_power_desc' ? 'selected' : ''}>加权战力高到低</option>
                    <option value="heigo_power_desc" ${sortedValue === 'heigo_power_desc' ? 'selected' : ''}>HEIGO战力高到低</option>
                    <option value="age_asc" ${sortedValue === 'age_asc' ? 'selected' : ''}>年龄小到大</option>
                    <option value="name_asc" ${sortedValue === 'name_asc' ? 'selected' : ''}>姓名 A-Z</option>
                </select>
            </label>
            <span class="mobile-db-view-pill">卡片</span>
        </div>
        ${hasScope ? `
            <div class="mobile-db-scope-banner">
                <div>
                    <span>当前范围</span>
                    <strong>${escapeHtml(scopeLabel || '筛选范围')}</strong>
                    <em>${Number(summary.batch_scope_count || databaseSearchScope.players?.length || players.length || 0).toLocaleString()} 名 · ${escapeHtml(summary.data_version || databaseSearchScope.dataVersion || getCurrentAttributeVersion() || '-')} 版本</em>
                </div>
                <button type="button" onclick="clearDatabaseSearchScopeAndSearch()">清空</button>
            </div>
        ` : ''}
    `;
}

function renderMobileDbPlayerCard(player) {
    const version = getPlayerDataVersion(player);
    const versionArg = htmlJsString(version);
    const uid = Number(player.uid || 0);
    const club = player.heigo_club || player.club || '-';
    const power = getMobileDbPowerMetrics(player);
    const powerMarkup = power ? `
        <div class="mobile-db-power-panel ${power.tone}" aria-label="加权战力值 ${power.weightedPower.toFixed(2)}，HEIGO战力 ${power.heigoPower.toFixed(2)}，前 ${getTopPercentLabel(power.topPercent)}%">
            <div class="mobile-db-power-metric">
                <em>加权战力值</em>
                <strong>${power.weightedPower.toFixed(2)}</strong>
            </div>
            <div class="mobile-db-power-metric is-heigo">
                <div><em>HEIGO战力</em><small>前 ${getTopPercentLabel(power.topPercent)}%</small></div>
                <strong>${power.heigoPower.toFixed(2)}</strong>
            </div>
        </div>
    ` : '<div class="mobile-db-power-unavailable">门将暂不计入外场战力模型</div>';
    return `
        <article class="mobile-db-player-card">
            <div class="mobile-db-player-head">
                <div class="mobile-db-player-title">
                    <button class="mobile-db-player-name" type="button" onclick="showPlayerDetail(${uid}, {returnTab: 'database', returnSubtab: 'search', version: ${versionArg}})">${escapeHtml(player.name || '-')}</button>
                    <span>UID ${escapeHtml(player.uid || '-')} · ${escapeHtml(player.age ?? '-')} 岁 · ${escapeHtml(player.position || '-')}</span>
                </div>
                <div class="mobile-db-rating-stack">
                    <span><em>CA</em><strong>${escapeHtml(player.ca ?? '-')}</strong></span>
                    <span><em>PA</em><strong>${escapeHtml(player.pa ?? '-')}</strong></span>
                </div>
            </div>
            <div class="mobile-db-player-meta">
                <span title="${escapeHtml(club)}">${escapeHtml(club)}</span>
                <span title="${escapeHtml(player.nationality || '-')}">${escapeHtml(formatCompactNationality(player.nationality, {maxLength: 18}))}</span>
            </div>
            ${powerMarkup}
            <div class="mobile-db-card-actions">
                <button class="mobile-db-card-action is-primary" type="button" onclick="showPlayerDetail(${uid}, {returnTab: 'database', returnSubtab: 'search', version: ${versionArg}})">详情</button>
                <button class="mobile-db-card-action" type="button" onclick="queueDbResultPlayerForCompare(${uid}, ${versionArg})">对比</button>
                ${buildMobileDbCandidateAction(player)}
            </div>
        </article>
    `;
}

function renderMobileDbPlayerResults(players) {
    return `
        <div class="mobile-db-results">
            ${renderMobileDbResultToolbar(players)}
            <div class="mobile-db-player-list">
                ${players.map(renderMobileDbPlayerCard).join('')}
            </div>
        </div>
    `;
}

function renderDbPlayers(players) {
    renderDatabaseSearchSummary();
    renderCandidateDock();
    if (!players.length) {
        document.getElementById('dbPlayersTable').innerHTML = '<div class="no-data">没有找到符合条件的球员</div>';
        return;
    }
    const sortedPlayers = getSortedDbPlayers(players);
    const showCandidateAction = hasActiveCandidateList();
    const html = `
        <table class="db-players-table">
            <thead>
                <tr>
                    ${buildDbHeader('姓名', 'name')}
                    ${buildDbHeader('位置', 'position')}
                    ${buildDbHeader('年龄', 'age', true)}
                    ${buildDbHeader('CA', 'ca', true)}
                    ${buildDbHeader('PA', 'pa', true)}
                    ${buildDbHeader('国籍', 'nationality')}
                    ${buildDbHeader('HEIGO俱乐部', 'heigo_club')}
                    ${buildDbHeader('现实俱乐部', 'club')}
                    ${showCandidateAction ? '<th>候选名单</th>' : ''}
                </tr>
            </thead>
            <tbody>
                ${sortedPlayers.map(p => `
                    <tr>
                        <td><span class="player-link" onclick="showPlayerDetail(${p.uid}, {returnTab: 'database', returnSubtab: 'search', version: '${escapeHtml(p.data_version)}'})">${escapeHtml(p.name)}</span></td>
                        <td>${escapeHtml(p.position || '-')}</td>
                        <td class="numeric-cell">${escapeHtml(p.age ?? '-')}</td>
                        <td class="numeric-cell"><strong>${escapeHtml(p.ca ?? '-')}</strong></td>
                        <td class="numeric-cell">${escapeHtml(p.pa ?? '-')}</td>
                        <td title="${escapeHtml(p.nationality || '-')}">${escapeHtml(formatCompactNationality(p.nationality, {maxLength: 16}))}</td>
                        <td class="${p.heigo_club !== '大海' ? 'heigo-club' : ''}">${escapeHtml(p.heigo_club || '-')}</td>
                        <td class="real-club">${escapeHtml(p.club || '-')}</td>
                        ${showCandidateAction ? buildCandidateResultActionCell(p) : ''}
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    document.getElementById('dbPlayersTable').innerHTML = `${html}${renderMobileDbPlayerResults(sortedPlayers)}`;
}

function initializeDatabaseAdvancedSearchUI() {
    ensureCurrentDbAdvancedFilters();
    renderAdvancedSearchTriggerState();
    renderDatabaseSearchSummary();

    document.getElementById('dbAdvancedSearchOverlay')?.addEventListener('click', () => {
        toggleAdvancedSearchPanel(false);
    });

    document.addEventListener('mousedown', event => {
        if (!isAdvancedSearchPanelOpen()) return;
        const panel = document.getElementById('dbAdvancedSearchPanel');
        const button = document.getElementById('dbAdvancedSearchToggle');
        if (panel?.contains(event.target) || button?.contains(event.target)) return;
        toggleAdvancedSearchPanel(false);
    });
}

initializeDatabaseAdvancedSearchUI();
