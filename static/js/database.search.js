const ADVANCED_DB_SEARCH_LIMIT = 200;
const ADVANCED_POSITION_SCORE_STEPS = [10, 15, 18];
const ADVANCED_DB_BASE_FIELDS = [
    ['age', '年龄'],
    ['ca', 'CA'],
    ['pa', 'PA'],
];
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
};

function createEmptyDatabaseAdvancedFilters() {
    return {
        age: {min: '', max: ''},
        ca: {min: '', max: ''},
        pa: {min: '', max: ''},
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
    nextState.age = normalizeAdvancedRangeState(rawFilters.age);
    nextState.ca = normalizeAdvancedRangeState(rawFilters.ca);
    nextState.pa = normalizeAdvancedRangeState(rawFilters.pa);

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
    ['age', 'ca', 'pa'].forEach(field => {
        if (isRangeActive(filters[field])) total += 1;
    });
    total += Object.values(filters.attributes || {}).filter(isRangeActive).length;
    total += Object.keys(filters.positions || {}).length;
    return total;
}

function hasActiveAdvancedFilters() {
    return countActiveAdvancedFilters() > 0;
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
    ['age', 'ca', 'pa'].forEach(field => {
        const text = formatRangeSummary(ADVANCED_DB_FIELD_LABEL_MAP[field], filters[field]);
        if (text) summary.push(text);
    });
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

    ['age', 'ca', 'pa'].forEach(field => {
        if (!isRangeActive(filters[field])) return;
        payload[field] = {};
        if (filters[field].min) payload[field].min = Number(filters[field].min);
        if (filters[field].max) payload[field].max = Number(filters[field].max);
    });

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
    const baseFieldsMarkup = ADVANCED_DB_BASE_FIELDS
        .map(([field, label]) => buildAdvancedRangeFieldMarkup(field, label, filters[field]))
        .join('');
    const groupMarkup = ADVANCED_DB_ATTRIBUTE_GROUPS.map(group => `
        <details class="database-advanced-group" ${group.key === 'technical' || group.key === 'mental' ? 'open' : ''}>
            <summary>
                <span>${group.label}</span>
                <span class="database-advanced-group-count">${group.fields.length} 项</span>
            </summary>
            <div class="database-advanced-field-grid">
                ${group.fields.map(([field, label]) => buildAdvancedRangeFieldMarkup(field, label, filters.attributes[field] || {}, true)).join('')}
            </div>
        </details>
    `).join('');

    panel.innerHTML = `
        <form class="database-advanced-panel-card" onsubmit="event.preventDefault();applyAdvancedSearchAndRun();">
            <div class="database-advanced-head">
                <div>
                    <div class="panel-kicker">Advanced Search</div>
                    <h3 id="dbAdvancedSearchTitle">高级搜索条件</h3>
                    <p class="database-advanced-helper">在当前版本球员库上叠加范围和位置筛选。保留现有关键词时会做联合搜索。</p>
                </div>
                <button class="database-advanced-close" type="button" onclick="toggleAdvancedSearchPanel(false)" aria-label="关闭高级搜索">×</button>
            </div>
            <div class="database-advanced-summary-row">
                <span class="query-chip ${countActiveAdvancedFilters() ? '' : 'is-muted'}">已启用 <strong>${countActiveAdvancedFilters()}</strong> 个高级条件</span>
                ${Object.keys(filters.positions || {}).length ? `<span class="query-chip">位置 <strong>${Object.keys(filters.positions).join(' / ')}</strong></span>` : ''}
            </div>
            <section class="database-advanced-section">
                <div class="database-advanced-section-head">
                    <h4>基础区间</h4>
                    <span>年龄 / CA / PA</span>
                </div>
                <div class="database-advanced-field-grid database-advanced-field-grid-base">
                    ${baseFieldsMarkup}
                </div>
            </section>
            <section class="database-advanced-section">
                <div class="database-advanced-section-head">
                    <h4>位置要求</h4>
                    <span>点击微型球场增加搜索要求</span>
                </div>
                ${buildAdvancedSearchPositionMap()}
            </section>
            <section class="database-advanced-section">
                <div class="database-advanced-section-head">
                    <h4>属性上下限</h4>
                    <span>按技术 / 精神 / 身体 / 门将 / 隐藏属性分组</span>
                </div>
                <div class="database-advanced-groups">
                    ${groupMarkup}
                </div>
            </section>
            <div class="database-advanced-actions">
                <button class="btn btn-secondary" type="button" onclick="clearAdvancedDatabaseFilters({rerenderPanel: true})">清空条件</button>
                <button class="btn btn-primary" type="submit">应用并搜索</button>
            </div>
        </form>
    `;
}

function renderAdvancedSearchTriggerState() {
    const button = document.getElementById('dbAdvancedSearchToggle');
    const countNode = document.getElementById('dbAdvancedSearchCount');
    if (!button || !countNode) return;
    const activeCount = countActiveAdvancedFilters();
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
    currentDbAdvancedFilters[field][boundary] = sanitizeNumericInput(value, {min: 0, max: field === 'age' ? 99 : 200});
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
    title.textContent = `球员库搜索结果${versionText ? ` (${versionText})` : ''}${summary.query || summary.applied_filters_summary.length ? ` (${playerCount} 名球员)` : ''}`;

    if (!summary.query && !summary.applied_filters_summary.length) {
        meta.textContent = '请输入球员姓名或 UID，或打开高级搜索筛选条件。';
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
        const payload = buildAdvancedSearchRequestPayload(query, {version});
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
    const shouldSyncHistory = options.pushHistory !== false;
    const historyMode = options.historyMode || 'push';
    currentDatabaseSubtab = 'search';
    syncDatabaseSubtabUI();
    await loadAttributeVersionCatalog();
    refreshAttributeVersionBanner();
    ensureCurrentDbAdvancedFilters();
    const name = nameOverride ?? document.getElementById('dbPlayerSearch').value.trim();
    const searchInput = document.getElementById('dbPlayerSearch');
    if (nameOverride !== null && searchInput) {
        searchInput.value = name;
    }
    activateDatabaseView('list');

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

function clearAdvancedFiltersFromResults() {
    const currentQuery = document.getElementById('dbPlayerSearch')?.value.trim() || '';
    clearAdvancedDatabaseFilters({rerenderPanel: false, closePanel: true});
    if (currentQuery) {
        searchDatabase(currentQuery, {pushHistory: true, historyMode: 'replace'});
        return;
    }
    renderDatabaseSearchPlaceholder('请输入球员姓名或 UID，或打开高级搜索配置筛选条件。');
    if (typeof syncAppHistory === 'function') {
        syncAppHistory('replace');
    }
}

async function loadReactionLeaderboard(options = {}) {
    const shouldSyncHistory = options.pushHistory !== false;
    const historyMode = options.historyMode || 'push';
    currentDatabaseSubtab = 'leaderboard';
    syncDatabaseSubtabUI();
    activateDatabaseView('leaderboard');
    await loadAttributeVersionCatalog();
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
        const response = await fetch(`/api/reactions/leaderboard?${params.toString()}`);
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
        table.innerHTML = '<div class="no-data">当前筛选条件下还没有互动数据</div>';
        return;
    }

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
                        <td><span class="player-link" onclick="showPlayerDetail(${item.uid}, {returnTab: 'database', returnSubtab: 'leaderboard', version: '${escapeHtml(item.data_version)}'})">${escapeHtml(item.name)}</span></td>
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

function showDatabaseSubtab(subtab, options = {}) {
    currentDatabaseSubtab = subtab === 'leaderboard' ? 'leaderboard' : 'search';
    syncDatabaseSubtabUI();
    if (currentDatabaseSubtab === 'leaderboard') {
        loadReactionLeaderboard(options);
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

function renderDbPlayers(players) {
    renderDatabaseSearchSummary();
    if (!players.length) {
        document.getElementById('dbPlayersTable').innerHTML = '<div class="no-data">没有找到符合条件的球员</div>';
        return;
    }
    const sortedPlayers = getSortedDbPlayers(players);
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
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    document.getElementById('dbPlayersTable').innerHTML = html;
}

async function viewPlayerInDatabase(uid) {
    if (typeof selectRosterPlayer === 'function') {
        selectRosterPlayer(uid);
    }
    await showPlayerDetail(uid, {returnTab: 'players', returnSubtab: currentDatabaseSubtab || 'search'});
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
