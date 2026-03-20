var currentDbSort = {field: '', order: '', type: 'number'};

const DB_SORT_FIELD_CONFIG = {
    name: {label: '姓名', type: 'text'},
    position: {label: '位置', type: 'text'},
    age: {label: '年龄', type: 'number'},
    ca: {label: 'CA', type: 'number'},
    pa: {label: 'PA', type: 'number'},
    nationality: {label: '国籍', type: 'text'},
    heigo_club: {label: 'HEIGO俱乐部', type: 'text'},
    club: {label: '现实俱乐部', type: 'text'},
};

function getDefaultDbSortOrder(type) {
    return type === 'text' ? 'asc' : 'desc';
}

function compareDbValues(left, right, type, order) {
    if (type === 'text') {
        const lhs = String(left || '').trim();
        const rhs = String(right || '').trim();
        const result = lhs.localeCompare(rhs, ['en', 'zh-CN'], {numeric: true, sensitivity: 'base'});
        return order === 'asc' ? result : -result;
    }
    const lhs = Number(left || 0);
    const rhs = Number(right || 0);
    return order === 'asc' ? lhs - rhs : rhs - lhs;
}

function getSortedDbPlayers(players) {
    if (!currentDbSort.field) return [...players];
    const sorted = [...players];
    sorted.sort((left, right) => compareDbValues(
        left[currentDbSort.field],
        right[currentDbSort.field],
        currentDbSort.type || 'number',
        currentDbSort.order || 'desc'
    ));
    return sorted;
}

function toggleDbSort(field) {
    const config = DB_SORT_FIELD_CONFIG[field] || {type: 'text'};
    if (currentDbSort.field === field) {
        currentDbSort.order = currentDbSort.order === 'asc' ? 'desc' : 'asc';
    } else {
        currentDbSort = {
            field,
            type: config.type,
            order: getDefaultDbSortOrder(config.type),
        };
    }
    renderDbPlayers(currentDbPlayers);
    if (typeof syncAppHistory === 'function') {
        syncAppHistory('replace');
    }
}

function getDbSortIndicator(field) {
    if (currentDbSort.field !== field) return '<span class="sort-indicator">↕</span>';
    return `<span class="sort-indicator is-active">${currentDbSort.order === 'asc' ? '↑' : '↓'}</span>`;
}

function buildDbHeader(label, field, numeric = false) {
    const className = numeric ? 'sortable-header numeric-column' : 'sortable-header';
    return `<th class="${className}" role="button" tabindex="0" onclick="toggleDbSort('${field}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();toggleDbSort('${field}');}"><span class="sortable-label">${label}</span>${getDbSortIndicator(field)}</th>`;
}

function getPlayerDataVersion(player) {
    return String(player?.data_version || getCurrentAttributeVersion() || '').trim();
}

function getPlayerVersionKey(playerOrUid, dataVersion = '') {
    if (typeof playerOrUid === 'object' && playerOrUid !== null) {
        return `${playerOrUid.uid}:${getPlayerDataVersion(playerOrUid)}`;
    }
    return `${playerOrUid}:${String(dataVersion || getCurrentAttributeVersion() || '').trim()}`;
}

function getAttributeVersionLabel(version) {
    return version ? `${version} 版本` : '未命名版本';
}

function renderDatabaseSearchVersionPicker() {
    const select = document.getElementById('dbAttributeVersionSelect');
    if (!select) return;

    const versionSource = (availableAttributeVersions && availableAttributeVersions.length)
        ? availableAttributeVersions
        : [getCurrentAttributeVersion()].filter(Boolean);
    const activeVersion = getCurrentAttributeVersion() || versionSource[0] || '';

    select.innerHTML = versionSource.length
        ? versionSource.map(version => `<option value="${escapeHtml(version)}">${escapeHtml(version)}</option>`).join('')
        : '<option value="">未加载</option>';
    select.value = activeVersion;
    select.disabled = versionSource.length <= 1;
}

function refreshAttributeVersionBanner() {
    const banner = document.getElementById('attributeVersionBanner');
    renderDatabaseSearchVersionPicker();
    if (!banner) return;
    const version = getCurrentAttributeVersion();
    const available = Array.isArray(availableAttributeVersions) ? availableAttributeVersions.join(' / ') : '';
    banner.innerHTML = version
        ? `当前球员库版本：<strong>${escapeHtml(version)}</strong>${available ? `，可切换版本：${escapeHtml(available)}` : ''}`
        : '当前球员库版本尚未加载。';
}

async function handleDatabaseSearchVersionChange(version) {
    await handleAttributeVersionChange(version);
}

function activateDatabaseView(viewName = 'list') {
    const isDetailView = viewName === 'detail';
    const dbListView = document.getElementById('dbListView');
    const dbDetailView = document.getElementById('dbDetailView');
    if (dbListView) {
        dbListView.classList.toggle('active', !isDetailView);
    }
    if (dbDetailView) {
        dbDetailView.classList.toggle('active', isDetailView);
    }
    if (!isDetailView) {
        const detailToolbar = document.getElementById('playerDetailToolbar');
        if (detailToolbar) detailToolbar.innerHTML = '';
    }
}

async function searchDatabase(nameOverride = null, options = {}) {
    const shouldSyncHistory = options.pushHistory !== false;
    const historyMode = options.historyMode || 'push';
    await loadAttributeVersionCatalog();
    refreshAttributeVersionBanner();
    const name = nameOverride ?? document.getElementById('dbPlayerSearch').value.trim();
    const searchInput = document.getElementById('dbPlayerSearch');
    if (nameOverride !== null && searchInput) {
        searchInput.value = name;
    }
    activateDatabaseView('list');
    if (!name) {
        document.getElementById('dbPlayersTable').innerHTML = '<div class="no-data">请输入球员姓名或 UID 进行搜索</div>';
        currentDbPlayers = [];
        if (shouldSyncHistory && typeof syncAppHistory === 'function') {
            syncAppHistory(historyMode);
        }
        return;
    }
    if (/^\d+$/.test(name)) {
        await showPlayerDetail(name, {
            returnTab: 'database',
            pushHistory: shouldSyncHistory,
            historyMode,
            version: getCurrentAttributeVersion(),
        });
        return;
    }
    document.getElementById('dbPlayersTable').innerHTML = '<div class="loading">搜索中...</div>';
    currentDbPlayers = await fetchDatabaseSearchResults(name, {version: getCurrentAttributeVersion()});
    renderDbPlayers(currentDbPlayers);
    if (shouldSyncHistory && typeof syncAppHistory === 'function') {
        syncAppHistory(historyMode);
    }
}

function sortDbPlayers() {
    renderDbPlayers(currentDbPlayers);
}

function renderDbPlayers(players) {
    if (players.length === 0) {
        document.getElementById('dbPlayersTable').innerHTML = '<div class="no-data">没有找到符合条件的球员</div>';
        return;
    }
    const activeVersion = getCurrentAttributeVersion();
    document.getElementById('dbTableTitle').textContent = `球员库搜索结果 ${activeVersion ? `(${activeVersion}) ` : ''}(${players.length} 名球员)`;
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
                        <td><span class="player-link" onclick="showPlayerDetail(${p.uid}, {returnTab: 'database', version: '${escapeHtml(p.data_version)}'})">${escapeHtml(p.name)}</span></td>
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
    await showPlayerDetail(uid, {returnTab: 'players'});
}

async function showPlayerDetail(uid, options = {}) {
    const returnTab = options.returnTab || 'database';
    const shouldSyncHistory = options.pushHistory !== false;
    const historyMode = options.historyMode || 'push';
    const preservePreviewStep = options.preservePreviewStep === true;
    await loadAttributeVersionCatalog();
    const requestedVersion = options.version || getCurrentAttributeVersion();
    setCurrentAttributeVersion(requestedVersion);
    refreshAttributeVersionBanner();
    dbDetailReturnState = {tab: returnTab};
    if (!preservePreviewStep) {
        currentGrowthPreviewStep = 0;
    }
    currentDetailMobileSection = 'overview';
    playerReactionSubmitting = false;
    clearPlayerReactionCooldownTimer();
    clearPlayerReactionBounce();
    showTab('database', null, {syncHistory: false});
    activateDatabaseView('detail');
    document.getElementById('playerDetailContent').innerHTML = '<div class="loading">加载中...</div>';
    const detailToolbar = document.getElementById('playerDetailToolbar');
    if (detailToolbar) detailToolbar.innerHTML = '';
    const res = await fetch(buildAttributeVersionedPath(`/api/attributes/${uid}`, getCurrentAttributeVersion()));
    const player = await res.json();
    if (!player) {
        document.getElementById('playerDetailContent').innerHTML = `<div class="no-data">${escapeHtml(getCurrentAttributeVersion() || '当前')} 版本下找不到球员信息</div>`;
        return;
    }
    setCurrentAttributeVersion(player.data_version);
    refreshAttributeVersionBanner();
    if (typeof selectRosterPlayer === 'function') {
        selectRosterPlayer(uid);
    }
    currentDetailPlayer = player;
    syncComparedPlayerState(player);
    renderPlayerDetail(player);
    if (shouldSyncHistory && typeof syncAppHistory === 'function') {
        syncAppHistory(historyMode);
    }
}

function getAttrClass(val) {
    const normalized = Math.min(20, Math.max(1, Number(val) || 1));
    if (normalized <= 4) return 'attr-tier-1';
    if (normalized <= 8) return 'attr-tier-2';
    if (normalized <= 12) return 'attr-tier-3';
    if (normalized <= 16) return 'attr-tier-4';
    return 'attr-tier-5';
}

function renderAttributeList(attrs) {
    return attrs.map(attr => {
        const value = Number(attr.value) || 0;
        return `<div class="attribute-bar ${getAttrClass(value)}"><span class="attr-name">${escapeHtml(attr.label)}</span><span class="attr-value">${value}</span></div>`;
    }).join('');
}

function formatRadarValue(value) {
    const numeric = Number(value) || 0;
    return numeric % 1 === 0 ? String(numeric) : numeric.toFixed(2).replace(/\.0+$/, '').replace(/(\.\d*[1-9])0+$/, '$1');
}

function averageValues(values) {
    const numericValues = values.map(item => Number(item) || 0).filter(item => item > 0);
    if (!numericValues.length) return 0;
    const total = numericValues.reduce((sum, item) => sum + item, 0);
    return total / numericValues.length;
}

const HALF_STEP_PREVIEW_KEYS = new Set(['bravery', 'leadership']);
const STATIC_PREVIEW_KEYS = new Set(['aggression', 'determination', 'natural_fitness', 'flair']);
const DETAIL_PREVIEW_KEYS = [
    'reflexes', 'aerial_ability', 'kicking', 'handling', 'command_of_area', 'throwing', 'one_on_ones', 'communication',
    'tendency_to_punch', 'rushing_out', 'eccentricity',
    'passing', 'crossing', 'marking', 'technique', 'dribbling', 'tackling', 'finishing', 'first_touch', 'heading', 'long_shots',
    'penalty', 'corner', 'long_throws', 'free_kick',
    'flair', 'positioning', 'work_rate', 'concentration', 'decisions', 'leadership', 'aggression', 'vision',
    'teamwork', 'off_the_ball', 'determination', 'bravery', 'anticipation', 'composure',
    'acceleration', 'jumping', 'agility', 'stamina', 'balance', 'strength', 'pace', 'natural_fitness',
    'consistency', 'adaptability', 'pressure', 'ambition', 'professionalism', 'important_matches', 'injury_proneness',
    'versatility', 'sportsmanship', 'temperament', 'loyalty',
];
const GOALKEEPER_TECHNICAL_FIELDS = [
    ['reflexes', '反应'], ['aerial_ability', '制空能力'], ['kicking', '大脚开球'], ['handling', '手控球'],
    ['command_of_area', '拦截传中'], ['throwing', '手抛球'], ['one_on_ones', '一对一'], ['communication', '指挥防守'],
    ['tendency_to_punch', '击球倾向'], ['rushing_out', '出击'], ['eccentricity', '神经指数'],
];
const OUTFIELD_TECHNICAL_FIELDS = [
    ['passing', '传球'], ['crossing', '传中'], ['marking', '盯人'], ['technique', '技术'],
    ['dribbling', '盘带'], ['tackling', '抢断'], ['finishing', '射门'], ['first_touch', '停球'],
    ['heading', '头球'], ['long_shots', '远射'],
];
const SET_PIECE_FIELDS = [
    ['penalty', '罚点球'], ['corner', '角球'], ['long_throws', '界外球'], ['free_kick', '任意球'],
];
const MENTAL_FIELDS = [
    ['flair', '想象力'], ['positioning', '防守站位'], ['work_rate', '工作投入'], ['concentration', '集中'],
    ['decisions', '决断'], ['leadership', '领导力'], ['aggression', '侵略性'], ['vision', '视野'],
    ['teamwork', '团队合作'], ['off_the_ball', '无球跑动'], ['determination', '意志力'], ['bravery', '勇敢'],
    ['anticipation', '预判'], ['composure', '镇定'],
];
const PHYSICAL_FIELDS = [
    ['acceleration', '爆发力'], ['jumping', '弹跳'], ['agility', '灵活'], ['stamina', '耐力'],
    ['balance', '平衡'], ['strength', '强壮'], ['pace', '速度'], ['natural_fitness', '体质'],
];
const HIDDEN_FIELDS = [
    ['consistency', '稳定性'], ['adaptability', '适应性'], ['pressure', '抗压能力'], ['ambition', '野心'],
    ['professionalism', '职业素养'], ['important_matches', '大赛发挥'], ['injury_proneness', '受伤倾向'], ['versatility', '多样性'],
    ['sportsmanship', '体育精神'], ['temperament', '情绪控制'], ['loyalty', '忠诚'],
];
var playerDetailExportBusy = false;
var detailExportToastTimer = null;
var playerReactionSubmitting = false;
var playerReactionCooldownTimer = null;
var playerReactionAnimatingType = '';
var playerReactionAnimationTimer = null;
var compareDockExpanded = false;

const DETAIL_MOBILE_SECTIONS = [
    {key: 'overview', label: '概览'},
    {key: 'skills', label: '能力'},
    {key: 'charts', label: '图表'},
];

function clampAttributeValue(value) {
    return Math.max(1, Math.min(20, Math.floor(Number(value) || 0)));
}

function getPreviewCaGain(step) {
    const lookup = [0, 11, 30, 50, 70, 90];
    return lookup[clampGrowthPreviewStep(step)] || 0;
}

function getWeakFootPreview(player, step) {
    if (clampGrowthPreviewStep(step) < 5) return null;
    const left = Number(player.left_foot) || 0;
    const right = Number(player.right_foot) || 0;
    if (!left || !right || left === right) return null;
    return left < right ? {label: '左脚', value: Math.min(20, left + 1)} : {label: '右脚', value: Math.min(20, right + 1)};
}

function buildPreviewPlayer(player, step) {
    const previewStep = clampGrowthPreviewStep(step);
    const previewPlayer = {...player};

    DETAIL_PREVIEW_KEYS.forEach(key => {
        const baseValue = Number(player[key]);
        if (!Number.isFinite(baseValue) || baseValue <= 0) return;
        if (STATIC_PREVIEW_KEYS.has(key)) {
            previewPlayer[key] = clampAttributeValue(baseValue);
            return;
        }
        const gain = HALF_STEP_PREVIEW_KEYS.has(key) ? Math.floor(previewStep / 2) : previewStep;
        previewPlayer[key] = clampAttributeValue(baseValue + gain);
    });

    const weakFootPreview = getWeakFootPreview(player, previewStep);
    if (weakFootPreview) {
        if (weakFootPreview.label === '左脚') {
            previewPlayer.left_foot = weakFootPreview.value;
        } else {
            previewPlayer.right_foot = weakFootPreview.value;
        }
    }

    previewPlayer.preview_step = previewStep;
    previewPlayer.preview_ca = (Number(player.ca) || 0) + getPreviewCaGain(previewStep);
    previewPlayer.preview_weak_foot = weakFootPreview;
    return previewPlayer;
}

function buildRadarProfile(player) {
    const isGoalkeeper = Number(player.pos_gk) >= 15;
    if (isGoalkeeper) {
        const profile = [
            ['拦截射门', averageValues([player.one_on_ones, player.reflexes])],
            ['身体', averageValues([player.agility, player.balance, player.stamina, player.strength])],
            ['速度', averageValues([player.acceleration, player.pace])],
            ['精神', averageValues([player.anticipation, player.bravery, player.concentration, player.decisions, player.determination, player.teamwork])],
            ['指挥防守', averageValues([player.command_of_area, player.communication])],
            ['意外性', Number(player.eccentricity) || 0],
            ['制空', averageValues([player.aerial_ability, player.handling])],
            ['大脚', averageValues([player.kicking, player.throwing])],
        ];
        return profile.map(([label, value]) => ({label, value: value || 0}));
    }

    return [
        ['防守', averageValues([player.marking, player.tackling, player.positioning])],
        ['身体', averageValues([player.agility, player.balance, player.stamina, player.strength])],
        ['速度', averageValues([player.acceleration, player.pace])],
        ['创造', averageValues([player.passing, player.flair, player.vision])],
        ['进攻', averageValues([player.finishing, player.composure, player.off_the_ball])],
        ['技术', averageValues([player.dribbling, player.first_touch, player.technique])],
        ['制空', averageValues([player.heading, player.jumping])],
        ['精神', averageValues([player.anticipation, player.bravery, player.concentration, player.decisions, player.determination, player.teamwork])],
    ].map(([label, value]) => ({label, value: value || 0}));
}

function buildComparisonRadarProfile(player) {
    const isGoalkeeper = Number(player.pos_gk) >= 15;
    if (isGoalkeeper) {
        return [
            ['防守', averageValues([player.command_of_area, player.one_on_ones, player.positioning, player.anticipation])],
            ['身体', averageValues([player.acceleration, player.agility, player.balance, player.strength, player.jumping])],
            ['速度', averageValues([player.acceleration, player.pace, player.agility, player.rushing_out])],
            ['创造', averageValues([player.throwing, player.kicking, player.passing, player.vision])],
            ['进攻', averageValues([player.one_on_ones, player.rushing_out, player.eccentricity])],
            ['技术', averageValues([player.reflexes, player.handling, player.kicking, player.throwing])],
            ['制空', averageValues([player.aerial_ability, player.jumping, player.command_of_area, player.bravery])],
            ['精神', averageValues([player.communication, player.concentration, player.decisions, player.determination, player.leadership])],
        ].map(([label, value]) => ({label, value: value || 0}));
    }

    return buildRadarProfile(player);
}

function getRadarThemePalette() {
    if (document.body.classList.contains('light-mode')) {
        return {
            gridStroke: 'rgba(76,79,105,0.08)',
            axisMetricStroke: 'rgba(76,79,105,0.1)',
            shapeFill: 'rgba(30, 102, 245, 0.14)',
            shapeStroke: 'rgba(30, 102, 245, 0.84)',
            pointFill: '#ffffff',
            pointStroke: 'rgba(30, 102, 245, 0.88)',
            labelFill: '#6c6f85',
        };
    }
    return {
        gridStroke: 'rgba(255,255,255,0.08)',
        axisMetricStroke: 'rgba(255,255,255,0.1)',
        shapeFill: 'rgba(122, 162, 247, 0.18)',
        shapeStroke: 'rgba(122, 162, 247, 0.94)',
        pointFill: '#f8fafc',
        pointStroke: 'rgba(122, 162, 247, 0.96)',
        labelFill: '#9aa5ce',
    };
}

function getComparisonRadarThemePalette() {
    if (document.body.classList.contains('light-mode')) {
        return {
            gridStroke: 'rgba(76,79,105,0.08)',
            labelFill: '#6c6f85',
            blueFill: 'rgba(32, 156, 255, 0.16)',
            blueStroke: 'rgba(32, 156, 255, 0.92)',
            redFill: 'rgba(255, 92, 114, 0.16)',
            redStroke: 'rgba(255, 92, 114, 0.92)',
        };
    }
    return {
        gridStroke: 'rgba(255,255,255,0.08)',
        labelFill: '#9aa5ce',
        blueFill: 'rgba(32, 156, 255, 0.16)',
        blueStroke: 'rgba(32, 156, 255, 0.92)',
        redFill: 'rgba(255, 92, 114, 0.16)',
        redStroke: 'rgba(255, 92, 114, 0.92)',
    };
}

function buildRadarShell(profile, options = {}) {
    if (!profile.length) return '';
    const size = options.size || 224;
    const center = size / 2;
    const radius = options.radius || 72;
    const labelRadius = options.labelRadius || 94;
    const stepCount = options.stepCount || 5;
    const labelInset = options.labelInset || 0;
    const shapeClass = options.shapeClass || 'radar-shape';
    const pointClass = options.pointClass || 'radar-point';
    const metricClass = options.metricClass || 'radar-metric';
    const palette = getRadarThemePalette();

    const getPoint = (index, value, distance) => {
        const angle = (-Math.PI / 2) + (index / profile.length) * Math.PI * 2;
        return {
            x: center + Math.cos(angle) * distance * value,
            y: center + Math.sin(angle) * distance * value,
        };
    };

    const grid = Array.from({length: stepCount}, (_, index) => {
        const ratio = (index + 1) / stepCount;
        const points = profile.map((_, axisIndex) => {
            const point = getPoint(axisIndex, ratio, radius);
            return `${point.x.toFixed(2)},${point.y.toFixed(2)}`;
        }).join(' ');
        return `<polygon class="radar-grid" points="${points}" style="fill:none;stroke:${palette.gridStroke};stroke-width:1;"></polygon>`;
    }).join('');

    const axes = profile.map((_, axisIndex) => {
        const edge = getPoint(axisIndex, 1, radius);
        return `<line class="radar-axis" x1="${center}" y1="${center}" x2="${edge.x.toFixed(2)}" y2="${edge.y.toFixed(2)}" style="fill:none;stroke:${palette.gridStroke};stroke-width:1;"></line>`;
    }).join('');

    const shapePoints = profile.map((item, axisIndex) => {
        const point = getPoint(axisIndex, Math.max(0, Math.min(20, item.value)) / 20, radius);
        return `${point.x.toFixed(2)},${point.y.toFixed(2)}`;
    }).join(' ');

    const metrics = profile.map((item, axisIndex) => {
        const normalized = Math.max(0, Math.min(20, item.value)) / 20;
        const point = getPoint(axisIndex, normalized, radius);
        const edge = getPoint(axisIndex, 1, radius);
        const label = getPoint(axisIndex, 1, labelRadius);
        const textAnchor = label.x < center - 10 ? 'end' : label.x > center + 10 ? 'start' : 'middle';
        const labelX = textAnchor === 'end'
            ? label.x + labelInset
            : textAnchor === 'start'
                ? label.x - labelInset
                : label.x;
        const labelY = label.y > center ? label.y + 10 : label.y - 4;
        return `
            <g class="${metricClass}" tabindex="0" aria-label="${escapeHtml(item.label)} ${formatRadarValue(item.value)}">
                <line class="radar-axis-metric" x1="${point.x.toFixed(2)}" y1="${point.y.toFixed(2)}" x2="${edge.x.toFixed(2)}" y2="${edge.y.toFixed(2)}" style="stroke:${palette.axisMetricStroke};stroke-width:1;"></line>
                <circle class="${pointClass}" cx="${point.x.toFixed(2)}" cy="${point.y.toFixed(2)}" r="4" style="fill:${palette.pointFill};stroke:${palette.pointStroke};stroke-width:1.35;"></circle>
                <text class="radar-label" x="${labelX.toFixed(2)}" y="${labelY.toFixed(2)}" text-anchor="${textAnchor}" style="fill:${palette.labelFill};">${escapeHtml(item.label)}</text>
                <circle class="radar-hit" cx="${point.x.toFixed(2)}" cy="${point.y.toFixed(2)}" r="12" style="fill:transparent;stroke:transparent;"></circle>
                <title>${escapeHtml(item.label)}：${formatRadarValue(item.value)}</title>
            </g>
        `;
    }).join('');

    return `
        <svg class="player-radar-svg" viewBox="0 0 ${size} ${size}" role="img" aria-label="球员能力雷达图">
            ${grid}
            ${axes}
            <polygon class="${shapeClass}" points="${shapePoints}" style="fill:${palette.shapeFill};stroke:${palette.shapeStroke};stroke-width:1.8;"></polygon>
            ${metrics}
        </svg>
    `;
}

function buildRadarSvg(profile, options = {}) {
    if (!profile.length) return '';
    const cardClassName = options.cardClassName || 'player-radar-card';
    const title = options.title === false ? '' : (options.title || '能力雷达');
    const figureClassName = options.figureClassName || 'player-radar-figure';
    return `
        <div class="${cardClassName}">
            ${title ? `<div class="player-radar-title">${escapeHtml(title)}</div>` : ''}
            <div class="${figureClassName}">
                ${buildRadarShell(profile, options)}
            </div>
        </div>
    `;
}

function buildComparisonRadarSvg(leftPlayer, rightPlayer) {
    const bothGoalkeepers = Number(leftPlayer.pos_gk) >= 15 && Number(rightPlayer.pos_gk) >= 15;
    const leftProfile = bothGoalkeepers ? buildRadarProfile(leftPlayer) : buildComparisonRadarProfile(leftPlayer);
    const rightProfile = bothGoalkeepers ? buildRadarProfile(rightPlayer) : buildComparisonRadarProfile(rightPlayer);
    if (!leftProfile.length || !rightProfile.length) return '';

    const size = 288;
    const center = size / 2;
    const radius = 96;
    const labelRadius = 122;
    const stepCount = 5;
    const palette = getComparisonRadarThemePalette();

    const getPoint = (index, value, distance) => {
        const angle = (-Math.PI / 2) + (index / leftProfile.length) * Math.PI * 2;
        return {
            x: center + Math.cos(angle) * distance * value,
            y: center + Math.sin(angle) * distance * value,
        };
    };

    const buildPoints = profile => profile.map((item, axisIndex) => {
        const point = getPoint(axisIndex, Math.max(0, Math.min(20, item.value)) / 20, radius);
        return `${point.x.toFixed(2)},${point.y.toFixed(2)}`;
    }).join(' ');

    const grid = Array.from({length: stepCount}, (_, index) => {
        const ratio = (index + 1) / stepCount;
        const points = leftProfile.map((_, axisIndex) => {
            const point = getPoint(axisIndex, ratio, radius);
            return `${point.x.toFixed(2)},${point.y.toFixed(2)}`;
        }).join(' ');
        return `<polygon class="comparison-radar-grid" points="${points}" style="fill:none;stroke:${palette.gridStroke};stroke-width:1;"></polygon>`;
    }).join('');

    const axes = leftProfile.map((item, axisIndex) => {
        const edge = getPoint(axisIndex, 1, radius);
        const label = getPoint(axisIndex, 1, labelRadius);
        const textAnchor = label.x < center - 10 ? 'end' : label.x > center + 10 ? 'start' : 'middle';
        const labelY = label.y > center ? label.y + 10 : label.y - 4;
        return `
            <line class="comparison-radar-axis" x1="${center}" y1="${center}" x2="${edge.x.toFixed(2)}" y2="${edge.y.toFixed(2)}" style="fill:none;stroke:${palette.gridStroke};stroke-width:1;"></line>
            <text class="comparison-radar-label" x="${label.x.toFixed(2)}" y="${labelY.toFixed(2)}" text-anchor="${textAnchor}" style="fill:${palette.labelFill};">${escapeHtml(item.label)}</text>
        `;
    }).join('');

    return `
        <section class="comparison-radar-card">
            <div class="comparison-radar-head">
                <div class="comparison-radar-legend">
                    <span class="comparison-legend-item is-blue"><span class="comparison-legend-swatch"></span>${escapeHtml(leftPlayer.name)}</span>
                    <span class="comparison-legend-item is-red"><span class="comparison-legend-swatch"></span>${escapeHtml(rightPlayer.name)}</span>
                </div>
            </div>
            <div class="comparison-radar-shell">
                <svg class="comparison-radar-svg" viewBox="0 0 ${size} ${size}" role="img" aria-label="球员对比雷达图">
                    ${grid}
                    ${axes}
                    <polygon class="comparison-radar-shape comparison-radar-shape-blue" points="${buildPoints(leftProfile)}" style="fill:${palette.blueFill};stroke:${palette.blueStroke};stroke-width:2.2;"></polygon>
                    <polygon class="comparison-radar-shape comparison-radar-shape-red" points="${buildPoints(rightProfile)}" style="fill:${palette.redFill};stroke:${palette.redStroke};stroke-width:2.2;"></polygon>
                </svg>
            </div>
        </section>
    `;
}

const POSITION_MARKERS = [
    {key: 'pos_st', label: 'ST', x: 50, y: 12},
    {key: 'pos_aml', label: 'AML', x: 10.5, y: 24},
    {key: 'pos_amc', label: 'AMC', x: 50, y: 24},
    {key: 'pos_amr', label: 'AMR', x: 89.5, y: 24},
    {key: 'pos_ml', label: 'ML', x: 10.5, y: 42},
    {key: 'pos_mc', label: 'MC', x: 50, y: 42},
    {key: 'pos_mr', label: 'MR', x: 89.5, y: 42},
    {key: 'pos_dm', label: 'DM', x: 50, y: 62},
    {key: 'pos_wbl', label: 'WBL', x: 10.5, y: 62},
    {key: 'pos_wbr', label: 'WBR', x: 89.5, y: 62},
    {key: 'pos_dl', label: 'DL', x: 10.5, y: 82},
    {key: 'pos_dc', label: 'DC', x: 50, y: 82},
    {key: 'pos_dr', label: 'DR', x: 89.5, y: 82},
    {key: 'pos_gk', label: 'GK', x: 50, y: 94},
];
const POSITION_COMPARISON_FIELDS = POSITION_MARKERS.map(({key, label}) => [key, label]);

function getPitchMarkerTone(score) {
    if (score <= 1) return 'pitch-rating-gray';
    if (score <= 9) return 'pitch-rating-red';
    if (score <= 14) return 'pitch-rating-yellow';
    return 'pitch-rating-green';
}

function getPitchTooltipClasses(marker) {
    const classes = [];
    if (marker.y <= 24) classes.push('tooltip-below');
    if (marker.x <= 12) classes.push('tooltip-align-left');
    if (marker.x >= 88) classes.push('tooltip-align-right');
    return classes.join(' ');
}

function buildPositionMap(player, options = {}) {
    const activeMarkers = POSITION_MARKERS
        .map(marker => ({...marker, score: Number(player[marker.key]) || 0}))
        .filter(marker => marker.score > 1);

    if (!activeMarkers.length) return '';
    const cardClassName = options.cardClassName || 'position-map-card';
    const title = options.title === false ? '' : (options.title || '位置熟练度图');

    const markers = activeMarkers.map(marker => `
        <button class="pitch-marker ${getPitchMarkerTone(marker.score)}" style="left:${marker.x}%;top:${marker.y}%;background:none;border:none;padding:0;" type="button" aria-label="${marker.label} \u719f\u7ec3\u5ea6 ${marker.score}">
            <span class="pitch-marker-core">${marker.label}</span>
            <span class="pitch-marker-tooltip ${getPitchTooltipClasses(marker)}">${marker.label} \u00b7 \u719f\u7ec3\u5ea6 ${marker.score}</span>
        </button>
    `).join('');

    return `
        <div class="${cardClassName}">
            ${title ? `<h4>${escapeHtml(title)}</h4>` : ''}
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

function clampGrowthPreviewStep(step) {
    return Math.max(0, Math.min(5, Number(step) || 0));
}

function mapFieldCollection(definitions, player) {
    return definitions.map(([key, label]) => ({key, label, value: player[key]}));
}

function getPlayerFieldCollections(player) {
    const isGoalkeeper = Number(player.pos_gk) >= 15;
    return {
        isGoalkeeper,
        technical: mapFieldCollection(isGoalkeeper ? GOALKEEPER_TECHNICAL_FIELDS : OUTFIELD_TECHNICAL_FIELDS, player),
        setPieces: isGoalkeeper ? [] : mapFieldCollection(SET_PIECE_FIELDS, player),
        mental: mapFieldCollection(MENTAL_FIELDS, player),
        physical: mapFieldCollection(PHYSICAL_FIELDS, player),
        hidden: mapFieldCollection(HIDDEN_FIELDS, player),
        positions: mapFieldCollection(POSITION_COMPARISON_FIELDS, player),
    };
}

function formatHeight(value) {
    const height = Number(value);
    if (!height) return '-';
    return `${height} cm`;
}

function buildPlayerInfoRows(player, previewPlayer) {
    const caGrowth = getPreviewCaGain(currentGrowthPreviewStep);
    return [
        ['国籍', player.nationality || '-'],
        ['年龄', player.age ?? '-'],
        ['生日', player.birth_date || '未知'],
        ['位置', player.position || '-'],
        ['CA / PA', `<strong>${escapeHtml(previewPlayer.preview_ca ?? player.ca ?? '-')}</strong>${caGrowth > 0 ? `<span class="growth-indicator growth-positive">(+${caGrowth})</span>` : ''} / ${escapeHtml(player.pa ?? '-')}`, true],
        ['左脚 / 右脚', `${previewPlayer.left_foot ?? '-'} / ${previewPlayer.right_foot ?? '-'}`],
        ['身高', formatHeight(player.height)],
        ['HEIGO俱乐部', `<span class="${player.heigo_club !== '大海' ? 'heigo-club' : ''}">${escapeHtml(player.heigo_club || '-')}</span>`, true],
        ['现实俱乐部', `<span class="real-club">${escapeHtml(player.club || '-')}</span>`, true],
    ];
}

function normalizeDetailMobileSection(section) {
    if (DETAIL_MOBILE_SECTIONS.some(item => item.key === section)) return section;
    return 'overview';
}

function buildDetailMobileNav() {
    const activeSection = normalizeDetailMobileSection(currentDetailMobileSection);
    return `
        <div class="player-detail-mobile-nav" role="tablist" aria-label="球员详情区块">
            ${DETAIL_MOBILE_SECTIONS.map(section => `
                <button
                    class="player-detail-mobile-tab ${section.key === activeSection ? 'is-active' : ''}"
                    type="button"
                    role="tab"
                    data-section="${section.key}"
                    aria-selected="${section.key === activeSection ? 'true' : 'false'}"
                    onclick="setDetailMobileSection('${section.key}')"
                >
                    ${section.label}
                </button>
            `).join('')}
        </div>
    `;
}

function syncDetailMobileSectionUI() {
    const shell = document.querySelector('#playerDetailContent .player-detail-shell');
    if (!shell) return;
    currentDetailMobileSection = normalizeDetailMobileSection(currentDetailMobileSection);
    shell.dataset.mobileSection = currentDetailMobileSection;
    shell.querySelectorAll('.player-detail-mobile-tab').forEach(button => {
        const isActive = button.dataset.section === currentDetailMobileSection;
        button.classList.toggle('is-active', isActive);
        button.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
}

function setDetailMobileSection(section) {
    currentDetailMobileSection = normalizeDetailMobileSection(section);
    syncDetailMobileSectionUI();
}

function normalizeReactionSummary(summary = {}) {
    const cooldownSeconds = Math.max(0, Number(summary.cooldown_seconds) || 0);
    return {
        flowers: Math.max(0, Number(summary.flowers) || 0),
        eggs: Math.max(0, Number(summary.eggs) || 0),
        can_react: summary.can_react !== false && cooldownSeconds === 0,
        cooldown_seconds: cooldownSeconds,
        next_available_at: summary.next_available_at || null,
    };
}

function clearPlayerReactionCooldownTimer() {
    if (playerReactionCooldownTimer) {
        window.clearInterval(playerReactionCooldownTimer);
        playerReactionCooldownTimer = null;
    }
}

function ensurePlayerReactionSummary(player) {
    if (!player) return normalizeReactionSummary();
    player.reaction_summary = normalizeReactionSummary(player.reaction_summary);
    return player.reaction_summary;
}

function renderPlayerReactionControls(player) {
    const reactionHost = document.getElementById('playerReactionControls');
    if (!reactionHost || !player) return;

    const summary = ensurePlayerReactionSummary(player);
    const cooldownSeconds = Math.max(0, Number(summary.cooldown_seconds) || 0);
    const disabled = playerReactionSubmitting || cooldownSeconds > 0;
    const flowerAnimating = playerReactionAnimatingType === 'flower';
    const eggAnimating = playerReactionAnimatingType === 'egg';
    const flowerTitle = playerReactionSubmitting
        ? '正在送花'
        : cooldownSeconds > 0
            ? `${cooldownSeconds} 秒后可再次送花`
            : '送花';
    const eggTitle = playerReactionSubmitting
        ? '正在踩鸡蛋'
        : cooldownSeconds > 0
            ? `${cooldownSeconds} 秒后可再次踩鸡蛋`
            : '踩鸡蛋';

    reactionHost.innerHTML = `
        <div class="player-reaction-panel" aria-label="球员互动">
            <div class="player-reaction-buttons">
                <button
                    class="player-reaction-button is-flower ${flowerAnimating ? 'is-bouncing' : ''}"
                    type="button"
                    onclick="submitPlayerReaction('flower')"
                    title="${flowerTitle}"
                    aria-label="送花 ${summary.flowers}"
                    ${disabled ? 'disabled' : ''}
                >
                    <span class="player-reaction-icon is-flower" aria-hidden="true"></span>
                    <span class="player-reaction-count ${flowerAnimating ? 'is-popping' : ''}">${summary.flowers}</span>
                </button>
                <button
                    class="player-reaction-button is-egg ${eggAnimating ? 'is-bouncing' : ''}"
                    type="button"
                    onclick="submitPlayerReaction('egg')"
                    title="${eggTitle}"
                    aria-label="踩鸡蛋 ${summary.eggs}"
                    ${disabled ? 'disabled' : ''}
                >
                    <span class="player-reaction-icon is-egg" aria-hidden="true"></span>
                    <span class="player-reaction-count ${eggAnimating ? 'is-popping' : ''}">${summary.eggs}</span>
                </button>
            </div>
        </div>
    `;
}

function syncPlayerReactionControls() {
    if (!currentDetailPlayer) return;
    renderPlayerReactionControls(currentDetailPlayer);
}

function clearPlayerReactionBounce() {
    playerReactionAnimatingType = '';
    if (playerReactionAnimationTimer) {
        window.clearTimeout(playerReactionAnimationTimer);
        playerReactionAnimationTimer = null;
    }
}

function triggerPlayerReactionBounce(reactionType) {
    clearPlayerReactionBounce();
    playerReactionAnimatingType = reactionType;
    if (currentDetailPlayer) {
        renderPlayerReactionControls(currentDetailPlayer);
    }
    playerReactionAnimationTimer = window.setTimeout(() => {
        playerReactionAnimatingType = '';
        playerReactionAnimationTimer = null;
        if (currentDetailPlayer) {
            renderPlayerReactionControls(currentDetailPlayer);
        }
    }, 320);
}

function startPlayerReactionCooldownTimer() {
    clearPlayerReactionCooldownTimer();
    if (!currentDetailPlayer) return;

    const summary = ensurePlayerReactionSummary(currentDetailPlayer);
    if (summary.cooldown_seconds <= 0) return;

    playerReactionCooldownTimer = window.setInterval(() => {
        if (!currentDetailPlayer) {
            clearPlayerReactionCooldownTimer();
            return;
        }

        const activeSummary = ensurePlayerReactionSummary(currentDetailPlayer);
        if (activeSummary.cooldown_seconds <= 1) {
            currentDetailPlayer.reaction_summary = {
                ...activeSummary,
                cooldown_seconds: 0,
                can_react: true,
                next_available_at: null,
            };
            renderPlayerReactionControls(currentDetailPlayer);
            clearPlayerReactionCooldownTimer();
            return;
        }

        currentDetailPlayer.reaction_summary = {
            ...activeSummary,
            cooldown_seconds: activeSummary.cooldown_seconds - 1,
            can_react: false,
        };
        renderPlayerReactionControls(currentDetailPlayer);
    }, 1000);
}

async function submitPlayerReaction(reactionType) {
    if (!currentDetailPlayer || playerReactionSubmitting) return;

    const summary = ensurePlayerReactionSummary(currentDetailPlayer);
    if (summary.cooldown_seconds > 0) {
        showDetailExportToast(`请等待 ${summary.cooldown_seconds} 秒后再互动`, 'warning');
        renderPlayerReactionControls(currentDetailPlayer);
        return;
    }

    triggerPlayerReactionBounce(reactionType);
    playerReactionSubmitting = true;
    renderPlayerReactionControls(currentDetailPlayer);

    try {
        const response = await fetch(buildAttributeVersionedPath(`/api/attributes/${currentDetailPlayer.uid}/reactions/${reactionType}`, getPlayerDataVersion(currentDetailPlayer)), {
            method: 'POST',
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload?.detail || payload?.message || '互动请求失败');
        }

        currentDetailPlayer.reaction_summary = normalizeReactionSummary(payload.summary);
        renderPlayerReactionControls(currentDetailPlayer);
        startPlayerReactionCooldownTimer();
        showDetailExportToast(payload.message || (reactionType === 'flower' ? '已送花' : '已踩鸡蛋'), payload.accepted ? 'success' : 'warning');
    } catch (error) {
        console.error('Failed to submit player reaction:', error);
        showModal('互动失败', '当前互动没有提交成功，请稍后重试。');
    } finally {
        playerReactionSubmitting = false;
        if (currentDetailPlayer) {
            renderPlayerReactionControls(currentDetailPlayer);
        }
    }
}

function ensureDetailExportToast() {
    let toast = document.getElementById('detailExportToast');
    if (toast) return toast;

    toast = document.createElement('div');
    toast.id = 'detailExportToast';
    toast.className = 'detail-export-toast';
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    document.body.appendChild(toast);
    return toast;
}

function showDetailExportToast(message, tone = 'success') {
    const toast = ensureDetailExportToast();
    toast.textContent = message;
    toast.className = `detail-export-toast is-visible is-${tone}`;
    window.clearTimeout(detailExportToastTimer);
    detailExportToastTimer = window.setTimeout(() => {
        toast.classList.remove('is-visible');
    }, 2400);
}

function buildPlayerCaptureFileName(player) {
    const safeName = String(player?.name || 'player')
        .trim()
        .replace(/[\\/:*?"<>|]+/g, '_')
        .replace(/\s+/g, '_')
        .replace(/^_+|_+$/g, '') || 'player';
    const versionSuffix = getPlayerDataVersion(player) ? `_${getPlayerDataVersion(player)}` : '';
    return `${safeName}_${player?.uid || 'detail'}${versionSuffix}.png`;
}

function buildPlayerShareCard(player) {
    const previewPlayer = buildPreviewPlayer(player, currentGrowthPreviewStep);
    const collections = getPlayerFieldCollections(previewPlayer);
    const technicalItems = collections.technical.concat(collections.setPieces);
    const mentalItems = collections.mental;
    const physicalItems = collections.physical;
    const hiddenItems = collections.hidden;
    const infoRows = buildPlayerInfoRows(player, previewPlayer);
    const positionMapMarkup = buildPositionMap(player, {
        cardClassName: 'position-map-card player-export-position-map',
    });
    const radarMarkup = buildRadarSvg(buildRadarProfile(previewPlayer), {
        cardClassName: 'player-radar-card player-export-radar-card',
        figureClassName: 'player-radar-figure player-export-radar-figure',
        size: 264,
        radius: 72,
        labelRadius: 116,
        labelInset: 10,
    });
    const previewHeader = currentGrowthPreviewStep > 0
        ? `成长预览 +${currentGrowthPreviewStep}${previewPlayer.preview_weak_foot ? ` · ${previewPlayer.preview_weak_foot.label}逆足 +1` : ''}`
        : '当前属性';

    return `
        <article class="player-export-card">
            <div class="player-export-head">
                <div class="player-export-kicker">HEIGO 球员详情图</div>
                <div class="player-export-preview">${escapeHtml(previewHeader)}${getPlayerDataVersion(player) ? ` · ${escapeHtml(getAttributeVersionLabel(getPlayerDataVersion(player)))}` : ''}</div>
            </div>
            <div class="player-detail-layout player-detail-layout-export">
                <section class="detail-section detail-section-overview">
                    <div class="player-info-panel player-info-panel-export">
                        <div class="player-identity-block">
                            <div class="player-identity-head">
                                <div class="player-name">${escapeHtml(player.name)}</div>
                            </div>
                            <div class="player-uid">UID: ${escapeHtml(player.uid)}${getPlayerDataVersion(player) ? ` · ${escapeHtml(getPlayerDataVersion(player))}` : ''}</div>
                        </div>
                        ${infoRows.map(([label, value, isHtml]) => `
                            <div class="info-row">
                                <span class="info-label">${escapeHtml(label)}</span>
                                <span class="info-value">${isHtml ? value : escapeHtml(value)}</span>
                            </div>
                        `).join('')}
                        <div class="detail-overview-map detail-overview-map-export">
                            ${positionMapMarkup}
                        </div>
                        ${player.player_habits ? `
                            <div class="detail-note-block detail-note-block-export">
                                <div class="detail-note-title">球员习惯</div>
                                <div class="detail-note-copy">${escapeHtml(player.player_habits)}</div>
                            </div>
                        ` : ''}
                    </div>
                </section>
                <section class="detail-section detail-section-skills">
                    <div class="detail-skills-grid detail-skills-grid-export">
                        <div class="attribute-group attribute-group-export">
                            <h3>${collections.isGoalkeeper ? '门将属性' : '技术'}</h3>
                            <div class="attribute-list">${renderAttributeList(technicalItems)}</div>
                        </div>
                        <div class="attribute-group attribute-group-export">
                            <h3>精神</h3>
                            <div class="attribute-list">${renderAttributeList(mentalItems)}</div>
                        </div>
                        <div class="attribute-group attribute-group-physical attribute-group-export">
                            <h3>身体</h3>
                            <div class="attribute-list">${renderAttributeList(physicalItems)}</div>
                            ${radarMarkup}
                        </div>
                    </div>
                    <div class="attribute-group attribute-group-wide detail-hidden-panel detail-hidden-panel-export">
                        <h3>隐藏</h3>
                        <div class="attribute-list attribute-list-grid">${renderAttributeList(hiddenItems)}</div>
                    </div>
                </section>
            </div>
        </article>
    `;
}

function buildPlayerShareCaptureSurface(player) {
    const captureRoot = document.createElement('div');
    captureRoot.className = 'capture-export-root';

    const captureFrame = document.createElement('div');
    captureFrame.className = 'player-share-capture-frame';
    captureFrame.innerHTML = buildPlayerShareCard(player);
    captureRoot.appendChild(captureFrame);
    document.body.appendChild(captureRoot);

    return {captureRoot, captureFrame};
}

async function copyBlobToClipboard(blob) {
    if (!navigator.clipboard || typeof ClipboardItem === 'undefined') {
        throw new Error('clipboard-unavailable');
    }
    await navigator.clipboard.write([
        new ClipboardItem({
            [blob.type]: blob,
        }),
    ]);
}

function downloadBlob(blob, fileName) {
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1200);
}

async function copyCurrentPlayerDetailImage() {
    if (playerDetailExportBusy) return;
    if (!currentDetailPlayer) {
        showModal('暂时无法复制', '当前没有可导出的球员详情。');
        return;
    }
    if (!window.htmlToImage || typeof window.htmlToImage.toBlob !== 'function') {
        showModal('导出组件未就绪', '页面截图组件加载失败，请刷新页面后重试。');
        return;
    }

    playerDetailExportBusy = true;
    renderGrowthPreviewToolbar(currentDetailPlayer);

    let captureRoot = null;
    try {
        if (document.fonts?.ready) {
            await document.fonts.ready;
        }

        const captureSurface = buildPlayerShareCaptureSurface(currentDetailPlayer);
        captureRoot = captureSurface.captureRoot;

        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));

        const blob = await window.htmlToImage.toBlob(captureSurface.captureFrame, {
            cacheBust: true,
            pixelRatio: Math.max(2, Math.min(3, window.devicePixelRatio || 1)),
        });

        if (!blob) {
            throw new Error('capture-blob-empty');
        }

        const fileName = buildPlayerCaptureFileName(currentDetailPlayer);
        try {
            await copyBlobToClipboard(blob);
            showDetailExportToast('已复制球员分享图到剪贴板');
        } catch (clipboardError) {
            downloadBlob(blob, fileName);
            showDetailExportToast('浏览器未允许写入剪贴板，已自动下载分享图', 'warning');
        }
    } catch (error) {
        console.error('Failed to export player detail image:', error);
        showModal('生成球员图失败', '分享卡生成失败，请刷新页面后重试。');
    } finally {
        if (captureRoot) captureRoot.remove();
        playerDetailExportBusy = false;
        if (currentDetailPlayer) {
            renderGrowthPreviewToolbar(currentDetailPlayer);
        }
    }
}

function renderGrowthPreviewToolbar(player) {
    const detailToolbar = document.getElementById('playerDetailToolbar');
    if (!detailToolbar || !player) return;

    normalizeCompareSlots();
    currentGrowthPreviewStep = clampGrowthPreviewStep(currentGrowthPreviewStep);

    const labels = ['当前', '+1', '+2', '+3', '+4', '+5'];
    const previewCa = (Number(player.ca) || 0) + getPreviewCaGain(currentGrowthPreviewStep);
    const weakFootPreview = getWeakFootPreview(player, currentGrowthPreviewStep);
    const compareSlotIndex = getCompareSlotIndex(player);
    const versionSource = (availableAttributeVersions && availableAttributeVersions.length)
        ? availableAttributeVersions
        : [getPlayerDataVersion(player)].filter(Boolean);
    const versionOptions = versionSource
        .map(version => `<option value="${escapeHtml(version)}" ${version === getPlayerDataVersion(player) ? 'selected' : ''}>${escapeHtml(version)}</option>`)
        .join('');

    detailToolbar.innerHTML = `
        <div class="detail-toolbar-actions">
            <label class="detail-version-picker detail-toolbar-button" for="playerDetailVersionSelect" title="切换球员属性版本">
                <span class="detail-version-value">${escapeHtml(getPlayerDataVersion(player) || (versionSource[0] || ''))}</span>
                <select
                    id="playerDetailVersionSelect"
                    class="detail-version-select"
                    aria-label="切换球员属性版本"
                    onchange="handleAttributeVersionChange(this.value)"
                >
                    ${versionOptions}
                </select>
            </label>
            <button
                id="copyPlayerDetailButton"
                class="btn detail-toolbar-button detail-copy-button"
                type="button"
                onclick="copyCurrentPlayerDetailImage()"
                ${playerDetailExportBusy ? 'disabled' : ''}
            >
                ${playerDetailExportBusy ? '生成中...' : '复制球员图'}
            </button>
            <button
                class="btn detail-toolbar-button detail-compare-button ${compareSlotIndex !== -1 ? 'is-active' : ''}"
                type="button"
                onclick="queueCurrentPlayerForCompare()"
            >
                ${compareSlotIndex !== -1 ? `已加入对比 ${compareSlotIndex + 1}` : '加入对比'}
            </button>
            <div class="detail-growth-control" aria-label="成长预览进度条">
                <div class="detail-growth-scale">
                    ${labels.map((label, index) => `<span class="detail-growth-label ${index === currentGrowthPreviewStep ? 'is-active' : ''}">${label}</span>`).join('')}
                </div>
                <div class="growth-preview-slider-wrap">
                    <input
                        class="growth-preview-slider"
                        type="range"
                        min="0"
                        max="5"
                        step="1"
                        value="${currentGrowthPreviewStep}"
                        aria-label="成长预览"
                        oninput="setGrowthPreviewStep(this.value)"
                    >
                </div>
                <div class="foot-summary">
                    <span class="foot-badge">预览 CA <strong>${previewCa}</strong></span>
                    ${weakFootPreview ? `<span class="foot-badge">${weakFootPreview.label}逆足 <strong>+1</strong></span>` : ''}
                </div>
            </div>
        </div>
    `;
}

async function handleAttributeVersionChange(version) {
    await loadAttributeVersionCatalog();
    const nextVersion = setCurrentAttributeVersion(version);
    refreshAttributeVersionBanner();
    const currentQuery = document.getElementById('dbPlayerSearch')?.value.trim() || '';
    if (document.getElementById('dbListView')?.classList.contains('active')) {
        if (currentQuery) {
            await searchDatabase(currentQuery, {pushHistory: true, historyMode: 'replace'});
        } else if (typeof syncAppHistory === 'function') {
            syncAppHistory('replace');
        }
        return;
    }
    if (!currentDetailPlayer) return;
    if (currentQuery) {
        currentDbPlayers = await fetchDatabaseSearchResults(currentQuery, {version: nextVersion});
        renderDbPlayers(currentDbPlayers);
    }
    await showPlayerDetail(currentDetailPlayer.uid, {
        returnTab: dbDetailReturnState.tab || 'database',
        pushHistory: true,
        historyMode: 'replace',
        version: nextVersion,
        preservePreviewStep: true,
    });
}

function setGrowthPreviewStep(step) {
    currentGrowthPreviewStep = clampGrowthPreviewStep(step);
    if (currentDetailPlayer) {
        renderPlayerDetail(currentDetailPlayer);
    }
}

function normalizeCompareSlots() {
    if (!Array.isArray(playerCompareSlots) || playerCompareSlots.length !== 2) {
        playerCompareSlots = [null, null];
    }
    playerCompareSlots = playerCompareSlots.map(slot => {
        if (!slot || !slot.player) return null;
        const player = {
            ...slot.player,
            data_version: slot.player.data_version || slot.data_version || getCurrentAttributeVersion(),
        };
        return {
            uid: slot.uid ?? player.uid,
            data_version: slot.data_version || getPlayerDataVersion(player),
            version_key: slot.version_key || getPlayerVersionKey(player),
            player,
            step: clampGrowthPreviewStep(slot.step),
        };
    });
    return playerCompareSlots;
}

function getCompareSlotIndex(playerOrUid, dataVersion = '') {
    normalizeCompareSlots();
    const targetKey = getPlayerVersionKey(playerOrUid, dataVersion);
    return playerCompareSlots.findIndex(slot => slot && slot.version_key === targetKey);
}

function syncComparedPlayerState(player) {
    const slotIndex = getCompareSlotIndex(player);
    if (slotIndex === -1) return;
    playerCompareSlots[slotIndex] = {
        ...playerCompareSlots[slotIndex],
        data_version: getPlayerDataVersion(player),
        version_key: getPlayerVersionKey(player),
        player: {...player},
    };
    renderCompareDock();
    if (comparisonModalOpen) {
        renderComparisonWorkspace();
    }
}

function queueCurrentPlayerForCompare() {
    if (!currentDetailPlayer) return;
    queuePlayerForCompare(currentDetailPlayer);
}

function queuePlayerForCompare(player) {
    normalizeCompareSlots();
    const slotIndex = getCompareSlotIndex(player);
    if (slotIndex !== -1) {
        playerCompareSlots[slotIndex] = {
            ...playerCompareSlots[slotIndex],
            data_version: getPlayerDataVersion(player),
            version_key: getPlayerVersionKey(player),
            player: {...player},
        };
        compareDockExpanded = true;
        renderCompareDock();
        if (currentDetailPlayer) renderGrowthPreviewToolbar(currentDetailPlayer);
        if (comparisonModalOpen) renderComparisonWorkspace();
        return;
    }

    const emptyIndex = playerCompareSlots.findIndex(slot => !slot);
    if (emptyIndex === -1) {
        compareDockExpanded = true;
        renderCompareDock();
        showModal('对比夹已满', '最多支持同时对比 2 名球员，请先从右侧对比夹移除一名后再加入。');
        return;
    }

    playerCompareSlots[emptyIndex] = {
        uid: player.uid,
        data_version: getPlayerDataVersion(player),
        version_key: getPlayerVersionKey(player),
        player: {...player},
        step: 0,
    };
    compareDockExpanded = true;
    renderCompareDock();
    if (currentDetailPlayer) renderGrowthPreviewToolbar(currentDetailPlayer);
}

function removePlayerFromCompare(slotIndex) {
    normalizeCompareSlots();
    if (slotIndex < 0 || slotIndex > 1) return;
    playerCompareSlots[slotIndex] = null;
    if (!playerCompareSlots.some(Boolean)) {
        compareDockExpanded = false;
    }
    renderCompareDock();
    if (currentDetailPlayer) renderGrowthPreviewToolbar(currentDetailPlayer);
    if (comparisonModalOpen) {
        if (playerCompareSlots.filter(Boolean).length < 2) {
            closeComparisonWorkspace();
        } else {
            renderComparisonWorkspace();
        }
    }
}

function clearCompareSlots() {
    playerCompareSlots = [null, null];
    compareDockExpanded = false;
    renderCompareDock();
    if (currentDetailPlayer) renderGrowthPreviewToolbar(currentDetailPlayer);
    if (comparisonModalOpen) {
        closeComparisonWorkspace();
    }
}

function toggleCompareDock() {
    compareDockExpanded = !compareDockExpanded;
    renderCompareDock();
}

function renderCompareDock() {
    const dock = document.getElementById('compareDock');
    if (!dock) return;

    normalizeCompareSlots();
    const activeTab = document.body.dataset.activeTab || document.querySelector('.tab-content.active')?.id || 'home';
    const shouldShowDock = activeTab === 'players' || activeTab === 'database';
    dock.classList.toggle('is-hidden', !shouldShowDock);
    if (!shouldShowDock) {
        dock.innerHTML = '';
        return;
    }

    const filledSlots = playerCompareSlots.filter(Boolean);
    const filledCount = filledSlots.length;
    const compareNames = filledSlots.map(slot => `${escapeHtml(slot.player.name)} (${escapeHtml(getPlayerDataVersion(slot.player))})`);
    const detailReturnTab = activeTab === 'players' ? 'players' : 'database';

    dock.innerHTML = `
        <div class="compare-dock-shell ${compareDockExpanded ? 'is-expanded' : 'is-collapsed'} ${filledCount ? 'has-items' : 'is-empty'}">
            ${compareDockExpanded ? `
                <div class="compare-dock-card ${filledCount ? 'has-items' : 'is-empty'}">
                    <div class="compare-dock-head">
                        <div>
                            <span class="panel-kicker">Compare Folder</span>
                            <h4>对比夹</h4>
                            <div class="compare-dock-summary">${compareNames.length ? compareNames.join(' vs ') : '还没有加入对比球员'}</div>
                        </div>
                        ${filledCount ? '<button class="compare-dock-clear" type="button" onclick="clearCompareSlots()">清空</button>' : ''}
                    </div>
                    <div class="compare-slot-list">
                        ${playerCompareSlots.map((slot, index) => {
                            if (!slot) {
                                return `
                                    <div class="compare-slot is-empty">
                                        <span class="compare-slot-index">槽位 ${index + 1}</span>
                                        <p>在球员详情页点击“加入对比”</p>
                                    </div>
                                `;
                            }
                            const previewPlayer = buildPreviewPlayer(slot.player, slot.step);
                            return `
                                <div class="compare-slot is-filled is-${index === 0 ? 'blue' : 'red'}">
                                    <span class="compare-slot-index">槽位 ${index + 1}</span>
                                    <div class="compare-slot-name">${escapeHtml(slot.player.name)}</div>
                                    <div class="compare-slot-meta">${escapeHtml(slot.player.position || '-')} · ${escapeHtml(getPlayerDataVersion(slot.player))} · CA ${escapeHtml(previewPlayer.preview_ca ?? slot.player.ca ?? '-')}</div>
                                    <div class="compare-slot-actions">
                                        <button class="compare-slot-action" type="button" onclick="showPlayerDetail(${slot.player.uid}, {returnTab: '${detailReturnTab}', version: '${escapeHtml(getPlayerDataVersion(slot.player))}'})">查看球员</button>
                                        <button class="compare-slot-action is-danger" type="button" onclick="removePlayerFromCompare(${index})">移除</button>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                    <div class="compare-dock-actions">
                        <button class="btn btn-primary compare-run-button" type="button" onclick="openComparisonWorkspace()" ${filledCount < 2 ? 'disabled' : ''}>查看对比页</button>
                    </div>
                </div>
            ` : ''}
            <button
                class="compare-dock-handle ${filledCount ? 'has-items' : 'is-empty'} ${compareDockExpanded ? 'is-expanded' : ''}"
                type="button"
                onclick="toggleCompareDock()"
                aria-expanded="${compareDockExpanded}"
                aria-label="${compareDockExpanded ? '收起对比夹' : '展开对比夹'}"
            >
                <span class="compare-dock-handle-dot">${filledCount ? filledCount : '+'}</span>
                <span class="compare-dock-handle-label">${compareDockExpanded ? '收起' : '对比夹'}</span>
                <span class="compare-dock-handle-meta">${filledCount}/2</span>
            </button>
        </div>
    `;
}

function buildComparisonSlider(slotIndex, slot) {
    const labels = ['当前', '+1', '+2', '+3', '+4', '+5'];
    const accentClass = slotIndex === 0 ? 'is-blue' : 'is-red';
    return `
        <div class="comparison-slider-box ${accentClass}">
            <div class="comparison-slider-labels">
                ${labels.map((label, index) => `<span class="comparison-slider-label ${index === clampGrowthPreviewStep(slot.step) ? 'is-active' : ''}">${label}</span>`).join('')}
            </div>
            <input
                class="growth-preview-slider comparison-slider ${accentClass}"
                type="range"
                min="0"
                max="5"
                step="1"
                value="${clampGrowthPreviewStep(slot.step)}"
                aria-label="对比成长预览"
                oninput="setCompareSlotGrowthStep(${slotIndex}, this.value)"
            >
        </div>
    `;
}

function buildComparisonPlayerCard(slot, slotIndex) {
    const previewPlayer = buildPreviewPlayer(slot.player, slot.step);
    const accentClass = slotIndex === 0 ? 'is-blue' : 'is-red';
    const weakFootPreview = getWeakFootPreview(slot.player, slot.step);

    return `
        <section class="comparison-player-card ${accentClass}">
            <div class="comparison-player-head">
                <div>
                    <div class="comparison-player-name">${escapeHtml(slot.player.name)}</div>
                    <div class="comparison-player-version">UID ${escapeHtml(slot.player.uid)} · ${escapeHtml(getPlayerDataVersion(slot.player))}</div>
                </div>
                <div class="comparison-player-tag">${escapeHtml(slot.player.position || '-')}</div>
            </div>
            <div class="comparison-player-club">${escapeHtml(slot.player.heigo_club || '-')} / ${escapeHtml(slot.player.club || '-')}</div>
            ${buildComparisonSlider(slotIndex, slot)}
            <div class="comparison-player-badges">
                <span class="foot-badge">CA <strong>${escapeHtml(previewPlayer.preview_ca ?? slot.player.ca ?? '-')}</strong></span>
                <span class="foot-badge">PA <strong>${escapeHtml(slot.player.pa ?? '-')}</strong></span>
                <span class="foot-badge">左脚 <strong>${escapeHtml(previewPlayer.left_foot ?? '-')}</strong></span>
                <span class="foot-badge">右脚 <strong>${escapeHtml(previewPlayer.right_foot ?? '-')}</strong></span>
                ${weakFootPreview ? `<span class="foot-badge">${weakFootPreview.label}逆足 <strong>+1</strong></span>` : ''}
            </div>
        </section>
    `;
}

function buildComparisonMetaCard(leftPreview, rightPreview) {
    const rows = [
        ['UID', leftPreview.uid, rightPreview.uid],
        ['版本', getPlayerDataVersion(leftPreview) || '-', getPlayerDataVersion(rightPreview) || '-'],
        ['国籍', leftPreview.nationality || '-', rightPreview.nationality || '-'],
        ['生日', leftPreview.birth_date || '未知', rightPreview.birth_date || '未知'],
        ['年龄', leftPreview.age ?? '-', rightPreview.age ?? '-'],
        ['位置', leftPreview.position || '-', rightPreview.position || '-'],
        ['CA / PA', `${leftPreview.preview_ca ?? leftPreview.ca ?? '-'} / ${leftPreview.pa ?? '-'}`, `${rightPreview.preview_ca ?? rightPreview.ca ?? '-'} / ${rightPreview.pa ?? '-'}`],
        ['身高', formatHeight(leftPreview.height), formatHeight(rightPreview.height)],
        ['左脚', leftPreview.left_foot ?? '-', rightPreview.left_foot ?? '-'],
        ['右脚', leftPreview.right_foot ?? '-', rightPreview.right_foot ?? '-'],
        ['HEIGO', leftPreview.heigo_club || '-', rightPreview.heigo_club || '-'],
    ];

    return `
        <section class="comparison-meta-card">
            <h4>基础信息</h4>
            <div class="comparison-meta-list">
                ${rows.map(([label, leftValue, rightValue]) => `
                    <div class="comparison-meta-row">
                        <span class="comparison-meta-value is-blue">${escapeHtml(leftValue)}</span>
                        <span class="comparison-meta-label">${escapeHtml(label)}</span>
                        <span class="comparison-meta-value is-red">${escapeHtml(rightValue)}</span>
                    </div>
                `).join('')}
            </div>
        </section>
    `;
}

function mergeCompareItems(leftItems, rightItems) {
    const registry = new Map();
    const merged = [];

    leftItems.forEach(item => {
        const entry = {key: item.key, label: item.label, left: Number(item.value) || 0, right: 0};
        registry.set(item.key, entry);
        merged.push(entry);
    });

    rightItems.forEach(item => {
        const rightValue = Number(item.value) || 0;
        if (registry.has(item.key)) {
            registry.get(item.key).right = rightValue;
            return;
        }
        const entry = {key: item.key, label: item.label, left: 0, right: rightValue};
        registry.set(item.key, entry);
        merged.push(entry);
    });

    return merged;
}

function renderComparisonMetricRow(item) {
    const leftValue = Math.max(0, Number(item.left) || 0);
    const rightValue = Math.max(0, Number(item.right) || 0);
    const delta = Math.abs(leftValue - rightValue);
    const leftLead = leftValue > rightValue;
    const rightLead = rightValue > leftValue;
    const leftWidth = leftLead ? Math.min(50, (delta / 20) * 50) : 0;
    const rightWidth = rightLead ? Math.min(50, (delta / 20) * 50) : 0;
    const leftDisplay = leftLead ? `+${delta}` : '';
    const rightDisplay = rightLead ? `+${delta}` : '';
    const rowState = delta === 0 ? 'is-even' : leftLead ? 'is-blue-win' : 'is-red-win';

    return `
        <div class="compare-row ${rowState}">
            <div class="compare-value is-blue ${leftLead ? 'is-lead' : 'is-muted'}">${leftDisplay || '&nbsp;'}</div>
            <div class="compare-track-wrap">
                <div class="compare-track-label">${escapeHtml(item.label)}</div>
                <div class="compare-track">
                    <span class="compare-track-center"></span>
                    <span class="compare-track-fill compare-track-fill-blue" style="width:${leftWidth}%;"></span>
                    <span class="compare-track-fill compare-track-fill-red" style="width:${rightWidth}%;"></span>
                </div>
            </div>
            <div class="compare-value is-red ${rightLead ? 'is-lead' : 'is-muted'}">${rightDisplay || '&nbsp;'}</div>
        </div>
    `;
}

function renderComparisonMetricPanel(title, leftItems, rightItems, options = {}) {
    const merged = mergeCompareItems(leftItems, rightItems).filter(item => options.includeLowValues || item.left > 0 || item.right > 0);
    if (!merged.length) return '';
    return `
        <section class="comparison-panel ${options.wide ? 'comparison-panel-wide' : ''}">
            <div class="comparison-panel-head">
                <h4>${escapeHtml(title)}</h4>
            </div>
            <div class="comparison-metric-list">
                ${merged.map(renderComparisonMetricRow).join('')}
            </div>
        </section>
    `;
}

function setCompareSlotGrowthStep(slotIndex, step) {
    normalizeCompareSlots();
    if (!playerCompareSlots[slotIndex]) return;
    playerCompareSlots[slotIndex].step = clampGrowthPreviewStep(step);
    renderCompareDock();
    if (comparisonModalOpen) {
        renderComparisonWorkspace();
    }
}

function openComparisonWorkspace() {
    normalizeCompareSlots();
    if (playerCompareSlots.filter(Boolean).length < 2) {
        showModal('无法开始对比', '请先在球员详情页加入两名球员，再打开对比界面。');
        return;
    }
    comparisonModalOpen = true;
    const overlay = document.getElementById('comparisonOverlay');
    overlay.classList.add('active');
    overlay.setAttribute('aria-hidden', 'false');
    renderComparisonWorkspace();
}

function closeComparisonWorkspace() {
    comparisonModalOpen = false;
    const overlay = document.getElementById('comparisonOverlay');
    overlay.classList.remove('active');
    overlay.setAttribute('aria-hidden', 'true');
}

function renderComparisonWorkspace() {
    const content = document.getElementById('comparisonContent');
    if (!content) return;

    normalizeCompareSlots();
    const leftSlot = playerCompareSlots[0];
    const rightSlot = playerCompareSlots[1];
    if (!leftSlot || !rightSlot) {
        content.innerHTML = '<div class="no-data">对比夹中需要同时存在两名球员。</div>';
        return;
    }

    const leftPreview = buildPreviewPlayer(leftSlot.player, leftSlot.step);
    const rightPreview = buildPreviewPlayer(rightSlot.player, rightSlot.step);
    const leftCollections = getPlayerFieldCollections(leftPreview);
    const rightCollections = getPlayerFieldCollections(rightPreview);
    const technicalTitle = leftCollections.isGoalkeeper || rightCollections.isGoalkeeper ? '技术 / 门将' : '技术 / 定位球';
    const positionItemsLeft = leftCollections.positions.filter(item => item.value > 1);
    const positionItemsRight = rightCollections.positions.filter(item => item.value > 1);

    content.innerHTML = `
        <div class="comparison-stage">
            <div class="comparison-hero-grid">
                ${buildComparisonPlayerCard(leftSlot, 0)}
                <div class="comparison-center-stack">
                    ${buildComparisonRadarSvg(leftPreview, rightPreview)}
                    ${buildComparisonMetaCard(leftPreview, rightPreview)}
                </div>
                ${buildComparisonPlayerCard(rightSlot, 1)}
            </div>
            <div class="comparison-grid">
                ${renderComparisonMetricPanel(technicalTitle, leftCollections.technical.concat(leftCollections.setPieces), rightCollections.technical.concat(rightCollections.setPieces))}
                ${renderComparisonMetricPanel('精神', leftCollections.mental, rightCollections.mental)}
                ${renderComparisonMetricPanel('身体', leftCollections.physical, rightCollections.physical)}
                ${renderComparisonMetricPanel('隐藏', leftCollections.hidden, rightCollections.hidden, {wide: true})}
                ${renderComparisonMetricPanel('位置熟练度', positionItemsLeft, positionItemsRight, {wide: true})}
            </div>
        </div>
    `;
}

function renderPlayerDetail(player) {
    const previewPlayer = buildPreviewPlayer(player, currentGrowthPreviewStep);
    const collections = getPlayerFieldCollections(previewPlayer);
    const radarMarkup = buildRadarSvg(buildRadarProfile(previewPlayer));
    const mobileRadarMarkup = buildRadarSvg(buildRadarProfile(previewPlayer), {
        cardClassName: 'player-radar-card player-radar-card-mobile-chart',
    });
    const positionMapMarkup = buildPositionMap(player);
    const mobilePositionMapMarkup = buildPositionMap(player, {
        cardClassName: 'position-map-card position-map-card-mobile-chart',
    });
    const technicalMarkup = renderAttributeList(collections.technical);
    const setPieceMarkup = collections.setPieces.length ? renderAttributeList(collections.setPieces) : '';
    const infoRows = buildPlayerInfoRows(player, previewPlayer);

    const html = `
        <div class="player-detail-shell" data-mobile-section="${normalizeDetailMobileSection(currentDetailMobileSection)}">
            ${buildDetailMobileNav()}
            <div class="player-detail-layout">
                <section class="detail-section detail-section-overview">
                    <div class="player-info-panel">
                        <div class="player-identity-block">
                            <div class="player-identity-head">
                                <div class="player-name">${escapeHtml(player.name)}</div>
                            </div>
                            <div class="player-uid">UID: ${escapeHtml(player.uid)}</div>
                            <div id="playerReactionControls" class="player-reaction-host"></div>
                        </div>
                        ${infoRows.map(([label, value, isHtml]) => `
                            <div class="info-row">
                                <span class="info-label">${escapeHtml(label)}</span>
                                <span class="info-value">${isHtml ? value : escapeHtml(value)}</span>
                            </div>
                        `).join('')}
                        <div class="detail-overview-map">
                            ${positionMapMarkup}
                        </div>
                        ${player.player_habits ? `<div class="detail-note-block"><div class="detail-note-title">球员习惯</div><div class="detail-note-copy">${escapeHtml(player.player_habits)}</div></div>` : ''}
                    </div>
                </section>
                <section class="detail-section detail-section-skills">
                    <div class="detail-skills-grid">
                        <div class="attribute-group">
                            <h3>${collections.isGoalkeeper ? '门将属性' : '技术'}</h3>
                            <div class="attribute-list">${technicalMarkup}</div>
                            ${setPieceMarkup ? `<div class="attribute-subgroup"><h3>定位球</h3><div class="attribute-list">${setPieceMarkup}</div></div>` : ''}
                        </div>
                        <div class="attribute-group">
                            <h3>精神</h3>
                            <div class="attribute-list">${renderAttributeList(collections.mental)}</div>
                        </div>
                        <div class="attribute-group attribute-group-physical">
                            <h3>身体</h3>
                            <div class="attribute-list">${renderAttributeList(collections.physical)}</div>
                            ${radarMarkup}
                        </div>
                    </div>
                    <div class="attribute-group attribute-group-wide detail-hidden-panel">
                        <h3>隐藏</h3>
                        <div class="attribute-list attribute-list-grid">${renderAttributeList(collections.hidden)}</div>
                    </div>
                </section>
                <section class="detail-section detail-section-charts">
                    <div class="detail-chart-grid">
                        <div class="detail-chart-panel detail-chart-panel-map">
                            ${mobilePositionMapMarkup}
                        </div>
                        <div class="detail-chart-panel detail-chart-panel-radar">
                            ${mobileRadarMarkup}
                        </div>
                    </div>
                </section>
            </div>
        </div>
    `;
    document.getElementById('playerDetailContent').innerHTML = html;
    syncDetailMobileSectionUI();
    renderPlayerReactionControls(player);
    startPlayerReactionCooldownTimer();
    renderGrowthPreviewToolbar(player);
    renderCompareDock();
}

function backToList(options = {}) {
    if (options.useBrowserHistory !== false && typeof canUseAppHistoryBack === 'function' && canUseAppHistoryBack()) {
        history.back();
        return;
    }
    clearPlayerReactionCooldownTimer();
    clearPlayerReactionBounce();
    playerReactionSubmitting = false;
    activateDatabaseView('list');
    currentDetailPlayer = null;
    const returnTab = dbDetailReturnState.tab || 'database';
    if (returnTab !== 'database') {
        showTab(returnTab, null, {syncHistory: false});
    } else {
        showTab('database', null, {syncHistory: false});
    }
    if (options.pushHistory !== false && typeof syncAppHistory === 'function') {
        syncAppHistory(options.historyMode || 'replace');
    }
}

document.getElementById('dbPlayerSearch')?.addEventListener('keypress', event => {
    if (event.key === 'Enter') searchDatabase();
});

document.getElementById('comparisonOverlay')?.addEventListener('click', event => {
    if (event.target.id === 'comparisonOverlay') {
        closeComparisonWorkspace();
    }
});

document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && comparisonModalOpen) {
        closeComparisonWorkspace();
    }
});
