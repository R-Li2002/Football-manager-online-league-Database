const ROSTER_SORT_FIELD_CONFIG = {
    uid: {label: 'UID', type: 'number', align: 'center'},
    name: {label: '姓名', type: 'text', align: 'left'},
    age: {label: '年龄', type: 'number', align: 'center'},
    initial_ca: {label: '初始 CA', type: 'number', align: 'center'},
    ca: {label: '当前 CA', type: 'number', align: 'center'},
    pa: {label: 'PA', type: 'number', align: 'center'},
    position: {label: '位置', type: 'text', align: 'center'},
    nationality: {label: '国籍', type: 'text', align: 'center'},
    team_name: {label: '所属球队', type: 'text', align: 'left'},
    wage: {label: '工资', type: 'number', align: 'center'},
    slot_type: {label: '名额', type: 'text', align: 'center'},
};

var rosterStandingsData = {levels: [], rows: []};
var rosterStandingsLoading = false;
var rosterStandingsLoaded = false;
var rosterMobileViewMode = 'cards';
var rosterDesktopViewMode = 'table';
var rosterRendered = false;
var rosterPage = 1;
var rosterRenderFrameId = null;
const ROSTER_DESKTOP_PAGE_SIZE = 50;
const ROSTER_MOBILE_PAGE_SIZE = 20;

const ROSTER_FORMATIONS = {
    '4-3-3': [
        {key: 'gk', label: 'GK', x: 50, y: 90, roles: ['GK']},
        {key: 'lb', label: 'LB', x: 18, y: 72, roles: ['DL', 'LWB', 'WBL', 'LB']},
        {key: 'lcb', label: 'CB', x: 38, y: 74, roles: ['DC', 'CB']},
        {key: 'rcb', label: 'CB', x: 62, y: 74, roles: ['DC', 'CB']},
        {key: 'rb', label: 'RB', x: 82, y: 72, roles: ['DR', 'RWB', 'WBR', 'RB']},
        {key: 'lcm', label: 'CM', x: 32, y: 52, roles: ['MC', 'DM', 'AMC', 'CM']},
        {key: 'cm', label: 'CM', x: 50, y: 56, roles: ['MC', 'DM', 'CM']},
        {key: 'rcm', label: 'CM', x: 68, y: 52, roles: ['MC', 'DM', 'AMC', 'CM']},
        {key: 'lw', label: 'LW', x: 20, y: 30, roles: ['AML', 'ML', 'ST', 'LW']},
        {key: 'st', label: 'ST', x: 50, y: 24, roles: ['ST', 'AM', 'CF']},
        {key: 'rw', label: 'RW', x: 80, y: 30, roles: ['AMR', 'MR', 'ST', 'RW']},
    ],
    '4-2-3-1': [
        {key: 'gk', label: 'GK', x: 50, y: 90, roles: ['GK']},
        {key: 'lb', label: 'LB', x: 18, y: 72, roles: ['DL', 'LWB', 'WBL', 'LB']},
        {key: 'lcb', label: 'CB', x: 38, y: 75, roles: ['DC', 'CB']},
        {key: 'rcb', label: 'CB', x: 62, y: 75, roles: ['DC', 'CB']},
        {key: 'rb', label: 'RB', x: 82, y: 72, roles: ['DR', 'RWB', 'WBR', 'RB']},
        {key: 'ldm', label: 'DM', x: 40, y: 58, roles: ['DM', 'MC', 'CM']},
        {key: 'rdm', label: 'DM', x: 60, y: 58, roles: ['DM', 'MC', 'CM']},
        {key: 'lam', label: 'AM', x: 24, y: 40, roles: ['AML', 'ML', 'AMC', 'AM']},
        {key: 'amc', label: 'AM', x: 50, y: 38, roles: ['AMC', 'MC', 'ST', 'AM']},
        {key: 'ram', label: 'AM', x: 76, y: 40, roles: ['AMR', 'MR', 'AMC', 'AM']},
        {key: 'st', label: 'ST', x: 50, y: 22, roles: ['ST', 'CF']},
    ],
    '3-4-3': [
        {key: 'gk', label: 'GK', x: 50, y: 90, roles: ['GK']},
        {key: 'lcb', label: 'CB', x: 30, y: 73, roles: ['DC', 'CB']},
        {key: 'cb', label: 'CB', x: 50, y: 76, roles: ['DC', 'CB']},
        {key: 'rcb', label: 'CB', x: 70, y: 73, roles: ['DC', 'CB']},
        {key: 'lm', label: 'LM', x: 18, y: 52, roles: ['ML', 'AML', 'DL', 'LWB']},
        {key: 'lcm', label: 'CM', x: 40, y: 56, roles: ['MC', 'DM', 'CM']},
        {key: 'rcm', label: 'CM', x: 60, y: 56, roles: ['MC', 'DM', 'CM']},
        {key: 'rm', label: 'RM', x: 82, y: 52, roles: ['MR', 'AMR', 'DR', 'RWB']},
        {key: 'lw', label: 'LW', x: 22, y: 30, roles: ['AML', 'ML', 'ST']},
        {key: 'st', label: 'ST', x: 50, y: 22, roles: ['ST', 'CF']},
        {key: 'rw', label: 'RW', x: 78, y: 30, roles: ['AMR', 'MR', 'ST']},
    ],
    '3-5-2': [
        {key: 'gk', label: 'GK', x: 50, y: 90, roles: ['GK']},
        {key: 'lcb', label: 'CB', x: 30, y: 73, roles: ['DC', 'CB']},
        {key: 'cb', label: 'CB', x: 50, y: 76, roles: ['DC', 'CB']},
        {key: 'rcb', label: 'CB', x: 70, y: 73, roles: ['DC', 'CB']},
        {key: 'lwb', label: 'WB', x: 16, y: 52, roles: ['LWB', 'WBL', 'DL', 'ML']},
        {key: 'ldm', label: 'CM', x: 38, y: 58, roles: ['MC', 'DM', 'CM']},
        {key: 'cm', label: 'CM', x: 50, y: 48, roles: ['MC', 'DM', 'AMC', 'CM']},
        {key: 'rdm', label: 'CM', x: 62, y: 58, roles: ['MC', 'DM', 'CM']},
        {key: 'rwb', label: 'WB', x: 84, y: 52, roles: ['RWB', 'WBR', 'DR', 'MR']},
        {key: 'lst', label: 'ST', x: 40, y: 24, roles: ['ST', 'CF']},
        {key: 'rst', label: 'ST', x: 60, y: 24, roles: ['ST', 'CF']},
    ],
    '4-4-2': [
        {key: 'gk', label: 'GK', x: 50, y: 90, roles: ['GK']},
        {key: 'lb', label: 'LB', x: 18, y: 72, roles: ['DL', 'LWB', 'WBL']},
        {key: 'lcb', label: 'CB', x: 38, y: 75, roles: ['DC', 'CB']},
        {key: 'rcb', label: 'CB', x: 62, y: 75, roles: ['DC', 'CB']},
        {key: 'rb', label: 'RB', x: 82, y: 72, roles: ['DR', 'RWB', 'WBR']},
        {key: 'lm', label: 'LM', x: 20, y: 50, roles: ['ML', 'AML', 'DL']},
        {key: 'lcm', label: 'CM', x: 40, y: 54, roles: ['MC', 'DM', 'CM']},
        {key: 'rcm', label: 'CM', x: 60, y: 54, roles: ['MC', 'DM', 'CM']},
        {key: 'rm', label: 'RM', x: 80, y: 50, roles: ['MR', 'AMR', 'DR']},
        {key: 'lst', label: 'ST', x: 40, y: 24, roles: ['ST', 'CF']},
        {key: 'rst', label: 'ST', x: 60, y: 24, roles: ['ST', 'CF']},
    ],
};

var rosterFormationState = {
    teamName: '',
    teamId: null,
    formation: '4-3-3',
    picks: {},
    players: [],
    canEdit: null,
    saveBusy: false,
    saveMessage: '',
    saveState: 'idle',
    exportBusy: false,
    selectedMove: null,
};

const ROSTER_TACTICAL_SLOTS = [
    {key: 'fw_l', label: 'IF', line: 'forward', x: 25, y: 15, roles: ['ST', 'AML', 'LW']},
    {key: 'fw_c', label: 'ST', line: 'forward', x: 50, y: 14, roles: ['ST', 'CF']},
    {key: 'fw_r', label: 'IF', line: 'forward', x: 75, y: 15, roles: ['ST', 'AMR', 'RW']},
    {key: 'am_wl', label: 'W', line: 'attack', x: 14, y: 27, roles: ['AML', 'ML', 'LW']},
    {key: 'am_l', label: 'IF', line: 'attack', x: 32, y: 28, roles: ['AML', 'AMC', 'ST']},
    {key: 'am_c', label: 'AM', line: 'attack', x: 50, y: 29, roles: ['AMC', 'AM', 'MC']},
    {key: 'am_r', label: 'IF', line: 'attack', x: 68, y: 28, roles: ['AMR', 'AMC', 'ST']},
    {key: 'am_wr', label: 'W', line: 'attack', x: 86, y: 27, roles: ['AMR', 'MR', 'RW']},
    {key: 'mc_wl', label: 'AWB', line: 'mid', x: 14, y: 40, roles: ['ML', 'AML', 'LWB', 'DL']},
    {key: 'mc_l', label: 'BBM', line: 'mid', x: 32, y: 41, roles: ['MC', 'DM', 'AMC']},
    {key: 'mc_c', label: 'CM', line: 'mid', x: 50, y: 42, roles: ['MC', 'DM']},
    {key: 'mc_r', label: 'BBM', line: 'mid', x: 68, y: 41, roles: ['MC', 'DM', 'AMC']},
    {key: 'mc_wr', label: 'AWB', line: 'mid', x: 86, y: 40, roles: ['MR', 'AMR', 'RWB', 'DR']},
    {key: 'dm_wl', label: 'WB', line: 'dm', x: 14, y: 55, roles: ['LWB', 'WBL', 'DL', 'ML']},
    {key: 'dm_l', label: 'DM', line: 'dm', x: 32, y: 56, roles: ['DM', 'MC']},
    {key: 'dm_c', label: 'HB', line: 'dm', x: 50, y: 57, roles: ['DM', 'MC', 'DC']},
    {key: 'dm_r', label: 'DM', line: 'dm', x: 68, y: 56, roles: ['DM', 'MC']},
    {key: 'dm_wr', label: 'WB', line: 'dm', x: 86, y: 55, roles: ['RWB', 'WBR', 'DR', 'MR']},
    {key: 'def_l', label: 'AWB', line: 'defense', x: 14, y: 70, roles: ['DL', 'LWB', 'WBL']},
    {key: 'def_lc', label: 'OCB', line: 'defense', x: 32, y: 71, roles: ['DC', 'CB', 'DL']},
    {key: 'def_c', label: 'BCB', line: 'defense', x: 50, y: 72, roles: ['DC', 'CB']},
    {key: 'def_rc', label: 'OCB', line: 'defense', x: 68, y: 71, roles: ['DC', 'CB', 'DR']},
    {key: 'def_r', label: 'AWB', line: 'defense', x: 86, y: 70, roles: ['DR', 'RWB', 'WBR']},
    {key: 'gk', label: 'BGK', line: 'keeper', x: 50, y: 85, roles: ['GK']},
];

const ROSTER_FORMATION_SLOT_KEYS = {
    '4-3-3': ['gk', 'def_l', 'def_lc', 'def_rc', 'def_r', 'mc_l', 'mc_c', 'mc_r', 'am_wl', 'fw_c', 'am_wr'],
    '4-2-3-1': ['gk', 'def_l', 'def_lc', 'def_rc', 'def_r', 'dm_l', 'dm_r', 'am_wl', 'am_c', 'am_wr', 'fw_c'],
    '3-4-3': ['gk', 'def_lc', 'def_c', 'def_rc', 'mc_wl', 'mc_l', 'mc_r', 'mc_wr', 'fw_l', 'fw_c', 'fw_r'],
    '3-5-2': ['gk', 'def_lc', 'def_c', 'def_rc', 'dm_wl', 'mc_l', 'mc_c', 'mc_r', 'dm_wr', 'fw_l', 'fw_r'],
    '4-4-2': ['gk', 'def_l', 'def_lc', 'def_rc', 'def_r', 'mc_wl', 'mc_l', 'mc_r', 'mc_wr', 'fw_l', 'fw_r'],
};

function escapeQueryText(value) {
    return escapeHtml(value ?? '');
}

function normalizeRosterLookupText(value) {
    return String(value || '').trim().toLowerCase().replace(/\s+/g, ' ');
}

function getRosterSearchBasePlayers() {
    return [...(allPlayers || [])];
}

function filterRosterPlayersLocally(players, {teamName = '', playerName = ''} = {}) {
    const normalizedName = normalizeRosterLookupText(playerName);
    return (players || []).filter(player => {
        if (teamName && player.team_name !== teamName) return false;
        if (normalizedName && !normalizeRosterLookupText(player.name).includes(normalizedName) && !String(player.uid || '').includes(normalizedName)) return false;
        return true;
    });
}

function getDefaultRosterSortOrder(type) {
    return type === 'text' ? 'asc' : 'desc';
}

function compareRosterValues(left, right, type, order) {
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

function getSortedRosterPlayers(players) {
    if (!currentRosterSort.field) return [...players];
    const sorted = [...players];
    sorted.sort((left, right) => compareRosterValues(
        left[currentRosterSort.field],
        right[currentRosterSort.field],
        currentRosterSort.type || 'number',
        currentRosterSort.order || 'desc'
    ));
    return sorted;
}

function toggleRosterSort(field) {
    const config = ROSTER_SORT_FIELD_CONFIG[field] || {type: 'text', label: field};
    if (currentRosterSort.field === field) {
        currentRosterSort.order = currentRosterSort.order === 'asc' ? 'desc' : 'asc';
    } else {
        currentRosterSort = {
            field,
            type: config.type,
            order: getDefaultRosterSortOrder(config.type),
        };
    }
    rosterPage = 1;
    renderPlayers(currentPlayers);
    if (typeof syncAppHistory === 'function') {
        syncAppHistory('replace');
    }
}

function getRosterSortIndicator(field) {
    if (currentRosterSort.field !== field) return '<span class="sort-indicator">↕</span>';
    return `<span class="sort-indicator is-active">${currentRosterSort.order === 'asc' ? '↑' : '↓'}</span>`;
}

function buildRosterHeader(label, field, numeric = false) {
    const config = ROSTER_SORT_FIELD_CONFIG[field] || {align: 'left'};
    const className = numeric ? `sortable-header numeric-column header-align-${config.align}` : `sortable-header header-align-${config.align}`;
    return `<th class="${className}" role="button" tabindex="0" onclick="toggleRosterSort('${field}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();toggleRosterSort('${field}');}"><span class="sortable-heading"><span class="sortable-label">${label}</span>${getRosterSortIndicator(field)}</span></th>`;
}

function isRosterMobileViewport() {
    if (typeof isMobileViewport === 'function') return isMobileViewport();
    return window.matchMedia?.('(max-width: 780px)').matches || window.innerWidth <= 780;
}

function getRosterViewMode() {
    return isRosterMobileViewport() ? rosterMobileViewMode : rosterDesktopViewMode;
}

function isRosterCardMode() {
    return getRosterViewMode() === 'cards';
}

function setRosterViewMode(mode) {
    const nextMode = mode === 'cards' ? 'cards' : 'table';
    if (isRosterMobileViewport()) {
        rosterMobileViewMode = nextMode;
    } else {
        rosterDesktopViewMode = nextMode;
    }
    rosterPage = 1;
    renderPlayers(currentPlayers);
}

function handleRosterViewportChange() {
    if (!document.getElementById('players')?.classList.contains('active')) return;
    if (!Array.isArray(currentPlayers)) return;
    rosterPage = 1;
    renderPlayers(currentPlayers);
}

window.addEventListener('resize', () => {
    window.clearTimeout(window.rosterViewportResizeTimer);
    window.rosterViewportResizeTimer = window.setTimeout(handleRosterViewportChange, 120);
});

function renderRosterViewToggle() {
    const toggleEl = document.getElementById('rosterViewToggle');
    if (!toggleEl) return;
    toggleEl.hidden = false;
    const mode = getRosterViewMode();
    toggleEl.innerHTML = `
        <button type="button" class="roster-view-button ${mode === 'cards' ? 'active' : ''}" onclick="setRosterViewMode('cards')" aria-pressed="${mode === 'cards'}">卡片</button>
        <button type="button" class="roster-view-button ${mode === 'table' ? 'active' : ''}" onclick="setRosterViewMode('table')" aria-pressed="${mode === 'table'}">表格</button>
    `;
}

function renderPlayerQueryState() {
    const titleEl = document.getElementById('playerQueryTitle');
    const metaEl = document.getElementById('playerQueryMeta');
    const chipsEl = document.getElementById('playerQueryChips');
    const actionsEl = document.getElementById('playerRosterActions');
    const teamBadgeEl = document.getElementById('playerRosterTeamBadge');
    if (!titleEl || !metaEl || !chipsEl) return;

    const teamName = document.getElementById('teamSelect')?.value || '';
    const playerName = document.getElementById('playerSearch')?.value.trim() || '';
    const sortField = currentRosterSort.field || '';
    const sortOrder = currentRosterSort.order || 'desc';
    const hasFilters = Boolean(teamName || playerName || sortField);
    const count = Array.isArray(currentPlayers) ? currentPlayers.length : 0;
    const team = findRosterTeamByName(teamName);
    const ranking = getRosterTeamRanking(teamName);

    if (teamName) {
        titleEl.innerHTML = renderRosterTeamSummary(teamName, team, ranking);
        metaEl.innerHTML = playerName ? `<span><strong>姓名筛选</strong>${escapeQueryText(playerName)}</span>` : '';
        ensureRosterStandingsLoaded();
    } else if (playerName) {
        titleEl.textContent = `联赛球员搜索`;
        metaEl.innerHTML = `<span><strong>姓名</strong>${escapeQueryText(playerName)}</span>`;
    } else {
        titleEl.textContent = '全部联赛名单';
        metaEl.innerHTML = `<span><strong>范围</strong>全部联赛球队</span>`;
    }

    if (teamBadgeEl) {
        teamBadgeEl.innerHTML = renderRosterTeamBadge(teamName);
        teamBadgeEl.classList.toggle('is-visible', Boolean(teamName));
    }

    const chips = [];
    chips.push(`<span class="query-chip"><strong>${count}</strong>&nbsp;名结果</span>`);

    if (playerName) {
        chips.push(`<span class="query-chip">姓名&nbsp;<strong>${escapeQueryText(playerName)}</strong></span>`);
    }
    if (sortField) {
        const fieldMeta = ROSTER_SORT_FIELD_CONFIG[sortField];
        const orderLabel = sortOrder === 'asc' ? '升序' : '降序';
        chips.push(`<span class="query-chip is-muted">排序&nbsp;<strong>${fieldMeta?.label || escapeQueryText(sortField)}</strong>&nbsp;${orderLabel}</span>`);
    }
    if (!hasFilters) {
        chips.push('<span class="query-chip is-muted">未应用额外筛选</span>');
    }

    chipsEl.innerHTML = chips.join('');
    if (actionsEl) {
        const canPlan = Boolean(teamName && currentPlayers.some(player => player.team_name === teamName));
        actionsEl.innerHTML = canPlan
            ? `<button class="btn btn-secondary roster-formation-trigger" type="button" onclick="openRosterFormationModal(${htmlJsString(teamName)})">编辑阵容预览</button>`
            : '';
    }
}

function renderRosterTeamSummary(teamName, team, ranking) {
    const manager = String(team?.manager || '').trim();
    const level = String(team?.level || ranking?.level || '').trim();
    const rankText = ranking ? `第 ${Number(ranking.rank)} 名` : '排名待更新';
    return `
        <span class="roster-team-summary">
            <span class="query-chip roster-team-name-chip">球队&nbsp;<strong>${escapeQueryText(teamName)}</strong></span>
            <span class="roster-summary-item">
                <span>主教练</span>
                ${manager
                    ? `<button class="roster-summary-link" type="button" onclick="openRosterCoachProfile(${htmlJsString(manager)})">${escapeQueryText(manager)}</button>`
                    : '<em>-</em>'}
            </span>
            <span class="roster-summary-item">
                <span>级别</span><strong>${escapeQueryText(level || '-')}</strong>
            </span>
            <span class="roster-summary-item">
                <span>排名</span>
                ${ranking
                    ? `<button class="roster-summary-link" type="button" onclick="openRosterStandingsRank(${htmlJsString(ranking.level || level || '超级')})">${escapeQueryText(rankText)}</button>`
                    : `<strong>${escapeQueryText(rankText)}</strong>`}
            </span>
        </span>
    `;
}

function openRosterCoachProfile(managerName) {
    if (typeof openCoachProfileByName === 'function') {
        openCoachProfileByName(managerName);
    }
}

function openRosterStandingsRank(level) {
    const targetLevel = String(level || '超级').trim() || '超级';
    if (typeof showTab === 'function') {
        showTab('competition');
    }
    if (typeof showCompetitionSubtab === 'function') {
        showCompetitionSubtab('standings');
    }
    if (typeof setCompetitionLevel === 'function') {
        setCompetitionLevel(targetLevel);
    }
}

function findRosterTeamByName(teamName) {
    const normalized = String(teamName || '').trim();
    if (!normalized || !Array.isArray(teams)) return null;
    return teams.find(team => String(team?.name || '').trim() === normalized) || null;
}

function getRosterTeamRanking(teamName) {
    const normalized = String(teamName || '').trim();
    if (!normalized) return null;
    const rows = Array.isArray(rosterStandingsData?.rows) ? rosterStandingsData.rows : [];
    return rows.find(row => String(row?.team_name || row?.team || '').trim() === normalized) || null;
}

async function ensureRosterStandingsLoaded() {
    if (rosterStandingsLoaded || rosterStandingsLoading) return;
    rosterStandingsLoading = true;
    try {
        const response = await fetch('/api/standings');
        if (!response.ok) throw new Error('standings-load-failed');
        rosterStandingsData = await response.json();
        rosterStandingsLoaded = true;
        renderPlayerQueryState();
    } catch (error) {
        console.warn('Failed to load roster standings:', error);
    } finally {
        rosterStandingsLoading = false;
    }
}

function getRosterTeamLogoFallback(teamName) {
    const clean = String(teamName || '').trim();
    if (!clean) return 'HE';
    const compact = clean.replace(/[^A-Za-z0-9\u4e00-\u9fa5]/g, '');
    return (compact || clean).slice(0, 2).toUpperCase();
}

function renderRosterTeamBadge(teamName) {
    const team = findRosterTeamByName(teamName);
    if (!teamName) return '';
    if (team?.logo_path) {
        return `
            <div class="roster-team-badge has-logo" aria-hidden="true">
                <img src="${escapeQueryText(team.logo_path)}" alt="${escapeQueryText(teamName)}队徽" width="512" height="512" loading="lazy" decoding="async">
            </div>
        `;
    }
    return `
        <div class="roster-team-badge" aria-hidden="true">
            <span>${escapeQueryText(getRosterTeamLogoFallback(teamName))}</span>
        </div>
    `;
}

function canEditRosterFormation(team) {
    if (typeof rosterFormationState.canEdit === 'boolean') return rosterFormationState.canEdit;
    return Boolean(team);
}

function getRosterTeamPlayers(teamName) {
    const source = rosterFormationState.teamName === teamName && rosterFormationState.players.length
        ? rosterFormationState.players
        : (allPlayers || []);
    return source
        .filter(player => player.team_name === teamName)
        .sort((left, right) => {
            const caDiff = Number(right.ca || 0) - Number(left.ca || 0);
            if (caDiff) return caDiff;
            return String(left.name || '').localeCompare(String(right.name || ''), ['en', 'zh-CN'], {numeric: true});
        });
}

function getRosterFormationSlots() {
    const keys = ROSTER_FORMATION_SLOT_KEYS[rosterFormationState.formation] || ROSTER_FORMATION_SLOT_KEYS['4-3-3'];
    return keys.map(key => ROSTER_TACTICAL_SLOTS.find(slot => slot.key === key)).filter(Boolean);
}

function getRosterBoardSlots() {
    return ROSTER_TACTICAL_SLOTS;
}

function normalizeRosterPosition(value) {
    return String(value || '').toUpperCase().replace(/[()]/g, ' ').replace(/[,\-/]+/g, ' ');
}

function getRosterPositionTokens(value) {
    return normalizeRosterPosition(value).split(/\s+/).filter(Boolean);
}

function getRosterPositionCompact(value) {
    return String(value || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
}

function rosterPositionHasLineSide(tokens, compact, line, side = '') {
    if (side && (compact.includes(`${line}${side}`) || compact.includes(`${line} ${side}`))) return true;
    if (!side && (tokens.includes(line) || compact.includes(line))) return true;
    return tokens.includes(line) && (!side || tokens.includes(side));
}

function rosterPositionMatchesRole(position, rawRole) {
    const role = String(rawRole || '').toUpperCase();
    const tokens = getRosterPositionTokens(position);
    const compact = getRosterPositionCompact(position);
    if (!role) return false;
    if (tokens.includes(role) || compact.includes(role)) return true;
    if (role === 'CB' || role === 'DC') return rosterPositionHasLineSide(tokens, compact, 'D', 'C');
    if (role === 'LB' || role === 'DL') return rosterPositionHasLineSide(tokens, compact, 'D', 'L');
    if (role === 'RB' || role === 'DR') return rosterPositionHasLineSide(tokens, compact, 'D', 'R');
    if (role === 'LWB' || role === 'WBL') return rosterPositionHasLineSide(tokens, compact, 'WB', 'L');
    if (role === 'RWB' || role === 'WBR') return rosterPositionHasLineSide(tokens, compact, 'WB', 'R');
    if (role === 'CM' || role === 'MC') return rosterPositionHasLineSide(tokens, compact, 'M', 'C');
    if (role === 'DM') return compact.includes('DM') || tokens.includes('DM');
    if (role === 'AM' || role === 'AMC') return compact.includes('AMC') || rosterPositionHasLineSide(tokens, compact, 'AM', 'C');
    if (role === 'LW' || role === 'AML') return rosterPositionHasLineSide(tokens, compact, 'AM', 'L') || rosterPositionHasLineSide(tokens, compact, 'M', 'L');
    if (role === 'RW' || role === 'AMR') return rosterPositionHasLineSide(tokens, compact, 'AM', 'R') || rosterPositionHasLineSide(tokens, compact, 'M', 'R');
    if (role === 'ML') return rosterPositionHasLineSide(tokens, compact, 'M', 'L');
    if (role === 'MR') return rosterPositionHasLineSide(tokens, compact, 'M', 'R');
    if (role === 'ST' || role === 'CF') return tokens.includes('ST') || compact.includes('ST');
    if (role === 'GK') return tokens.includes('GK') || compact.includes('GK');
    return false;
}

function rosterPlayerMatchesSlot(player, slot) {
    return (slot.roles || []).some(role => rosterPositionMatchesRole(player.position, role));
}

function autoPickRosterFormation(teamName, formation = rosterFormationState.formation) {
    rosterFormationState.formation = formation;
    const players = getRosterTeamPlayers(teamName);
    rosterFormationState.picks = buildAutoRosterFormationPicks(players, formation);
}

function buildAutoRosterFormationPicks(players, formation = '4-3-3') {
    const keys = ROSTER_FORMATION_SLOT_KEYS[formation] || ROSTER_FORMATION_SLOT_KEYS['4-3-3'];
    const slots = keys.map(key => ROSTER_TACTICAL_SLOTS.find(slot => slot.key === key)).filter(Boolean);
    const used = new Set();
    const picks = {};
    for (const slot of slots) {
        let candidate = players.find(player => !used.has(Number(player.uid)) && rosterPlayerMatchesSlot(player, slot));
        if (!candidate) {
            candidate = players.find(player => !used.has(Number(player.uid)));
        }
        if (candidate) {
            picks[slot.key] = Number(candidate.uid);
            used.add(Number(candidate.uid));
        }
    }
    return picks;
}

function getFormationPickedPlayer(slotKey) {
    const uid = Number(rosterFormationState.picks?.[slotKey] || 0);
    if (!uid) return null;
    return getRosterTeamPlayers(rosterFormationState.teamName).find(player => Number(player.uid) === uid) || null;
}

function getRosterBenchPlayers() {
    const pickedUids = new Set(Object.values(rosterFormationState.picks || {}).map(uid => Number(uid)).filter(Boolean));
    return getRosterTeamPlayers(rosterFormationState.teamName).filter(player => !pickedUids.has(Number(player.uid)));
}

function getRosterPlayerCardRole(player, slot = null) {
    if (slot?.label) return slot.label;
    const position = String(player?.position || '');
    if (rosterPositionMatchesRole(position, 'GK')) return 'BGK';
    if (rosterPositionMatchesRole(position, 'ST')) return 'ST';
    if (rosterPositionMatchesRole(position, 'AML') || rosterPositionMatchesRole(position, 'AMR')) return 'IF';
    if (rosterPositionMatchesRole(position, 'AMC')) return 'AM';
    if (rosterPositionMatchesRole(position, 'MC') || rosterPositionMatchesRole(position, 'DM')) return 'BBM';
    if (rosterPositionMatchesRole(position, 'DL') || rosterPositionMatchesRole(position, 'DR') || rosterPositionMatchesRole(position, 'LWB') || rosterPositionMatchesRole(position, 'RWB')) return 'AWB';
    if (rosterPositionMatchesRole(position, 'DC')) return 'BCB';
    return 'HEI';
}

function getRosterPlayerCardTone(player, slot = null) {
    const line = slot?.line || '';
    const position = String(player?.position || '');
    if (line === 'keeper') return 'keeper';
    if (line === 'forward') return 'forward';
    if (line === 'attack') return 'attack';
    if (line === 'mid' || line === 'dm') return 'midfield';
    if (line === 'defense') return 'defense';
    if (rosterPositionMatchesRole(position, 'GK')) return 'keeper';
    if (rosterPositionMatchesRole(position, 'ST')) return 'forward';
    if (rosterPositionMatchesRole(position, 'AML') || rosterPositionMatchesRole(position, 'AMR') || rosterPositionMatchesRole(position, 'AMC')) return 'attack';
    if (rosterPositionMatchesRole(position, 'DC')) return 'defense';
    return 'midfield';
}

function getRosterPlayerShortName(name) {
    const clean = String(name || '').trim().replace(/\s+/g, ' ');
    if (!clean) return '-';
    const parts = clean.split(' ').filter(Boolean);
    if (parts.length > 1) return parts[parts.length - 1];
    return clean;
}

function buildRosterFormationCard(player, options = {}) {
    if (!player) return '';
    const slot = options.slot || null;
    const source = options.source || 'bench';
    const sourceValue = source === 'slot' ? slot?.key : Number(player.uid);
    const selectedMove = rosterFormationState.selectedMove;
    const isSelected = selectedMove
        && selectedMove.type === source
        && String(selectedMove.value) === String(sourceValue);
    const cardClass = `formation-player-card tone-${getRosterPlayerCardTone(player, slot)}${isSelected ? ' is-selected' : ''}`;
    const role = getRosterPlayerCardRole(player, slot);
    const interactive = options.interactive !== false;
    const hasHeigoPower = player.heigo_power !== null && player.heigo_power !== undefined && player.heigo_power !== '';
    const heigoPower = hasHeigoPower ? Number(player.heigo_power) : Number.NaN;
    const interactionAttrs = interactive
        ? `draggable="true" data-source="${escapeHtml(source)}" data-source-value="${escapeHtml(sourceValue)}" onclick="handleRosterFormationCardTap(event, ${htmlJsString(source)}, ${htmlJsString(sourceValue)})" ondragstart="handleRosterFormationDragStart(event, ${htmlJsString(source)}, ${htmlJsString(sourceValue)})" ondragend="handleRosterFormationDragEnd(event)" title="拖拽或点击更换球员"`
        : 'draggable="false"';
    return `
        <div class="${cardClass}${interactive ? '' : ' is-static'}" ${interactionAttrs}>
            <span class="formation-shirt-icon" aria-hidden="true"></span>
            <span class="formation-card-role">${escapeHtml(role)}</span>
            <strong data-short-name="${escapeHtml(getRosterPlayerShortName(player.name))}">${escapeHtml(player.name || '-')}</strong>
            <span class="formation-card-meta">${escapeHtml(player.position || '-')}</span>
            <span class="formation-card-power">HEIGO ${Number.isFinite(heigoPower) ? heigoPower.toFixed(2) : '--'}</span>
        </div>
    `;
}

function renderRosterFormationPreview(options = {}) {
    const teamName = String(options.teamName || '').trim();
    const players = Array.isArray(options.players) ? options.players : [];
    const formation = ROSTER_FORMATION_SLOT_KEYS[options.formation] ? options.formation : '4-3-3';
    const rawPicks = options.picks && typeof options.picks === 'object' ? options.picks : {};
    const picks = Object.keys(rawPicks).length ? rawPicks : buildAutoRosterFormationPicks(players, formation);
    const playersByUid = new Map(players.map(player => [Number(player.uid), player]));
    const slotKeys = [...new Set([...(ROSTER_FORMATION_SLOT_KEYS[formation] || []), ...Object.keys(picks)])];
    const slots = slotKeys.map(key => ROSTER_TACTICAL_SLOTS.find(slot => slot.key === key)).filter(Boolean);
    const pitchSlots = slots.map(slot => {
        const player = playersByUid.get(Number(picks[slot.key] || 0));
        return `<div class="formation-slot ${player ? 'has-player' : ''}" style="left:${slot.x}%;top:${slot.y}%;">${player ? buildRosterFormationCard(player, {source: 'slot', slot, interactive: false}) : '<span class="formation-slot-plus">+</span>'}</div>`;
    }).join('');
    return `<section class="formation-capture team-center-lineup-capture surface-card">
        <div class="formation-capture-head"><div><span class="panel-kicker">Starting XI</span><h3>${escapeHtml(teamName)}</h3></div><strong>${escapeHtml(formation)}</strong></div>
        <div class="formation-pitch" aria-label="${escapeHtml(teamName)}首发阵容">
            <div class="formation-pitch-line formation-pitch-center"></div><div class="formation-pitch-box formation-pitch-box-top"></div><div class="formation-pitch-box formation-pitch-box-bottom"></div><div class="formation-goal-box formation-goal-box-top"></div><div class="formation-goal-box formation-goal-box-bottom"></div>
            <span class="formation-corner corner-tl"></span><span class="formation-corner corner-tr"></span><span class="formation-corner corner-bl"></span><span class="formation-corner corner-br"></span>${pitchSlots}
        </div>
    </section>`;
}

function swapRosterFormationSlots(sourceSlotKey, targetSlotKey) {
    if (!sourceSlotKey || !targetSlotKey || sourceSlotKey === targetSlotKey) return;
    const sourceUid = rosterFormationState.picks?.[sourceSlotKey] || '';
    const targetUid = rosterFormationState.picks?.[targetSlotKey] || '';
    if (targetUid) {
        rosterFormationState.picks[sourceSlotKey] = Number(targetUid);
    } else {
        delete rosterFormationState.picks[sourceSlotKey];
    }
    if (sourceUid) {
        rosterFormationState.picks[targetSlotKey] = Number(sourceUid);
    } else {
        delete rosterFormationState.picks[targetSlotKey];
    }
    refreshRosterFormationModal();
}

function moveRosterBenchPlayerToSlot(playerUid, targetSlotKey) {
    if (!playerUid || !targetSlotKey) return;
    const normalizedUid = Number(playerUid);
    for (const [slotKey, uid] of Object.entries(rosterFormationState.picks || {})) {
        if (Number(uid) === normalizedUid) {
            delete rosterFormationState.picks[slotKey];
        }
    }
    rosterFormationState.picks[targetSlotKey] = normalizedUid;
    refreshRosterFormationModal();
}

function moveRosterSlotPlayerToBench(sourceSlotKey) {
    if (!sourceSlotKey) return;
    delete rosterFormationState.picks[sourceSlotKey];
    refreshRosterFormationModal();
}

function clearRosterFormationSelection(options = {}) {
    rosterFormationState.selectedMove = null;
    if (options.render !== false) refreshRosterFormationModal();
}

function setRosterFormationSelection(type, value) {
    const next = {type, value: String(value || '')};
    const current = rosterFormationState.selectedMove;
    if (current && current.type === next.type && String(current.value) === next.value) {
        clearRosterFormationSelection();
        return;
    }
    rosterFormationState.selectedMove = next;
    refreshRosterFormationModal();
}

function applyRosterFormationMoveToSlot(move, targetSlotKey) {
    if (!move || !targetSlotKey) return;
    rosterFormationState.selectedMove = null;
    if (move.type === 'slot') {
        swapRosterFormationSlots(move.value, targetSlotKey);
    } else if (move.type === 'bench') {
        moveRosterBenchPlayerToSlot(move.value, targetSlotKey);
    }
}

function applyRosterFormationMoveToBench(move) {
    rosterFormationState.selectedMove = null;
    if (move?.type === 'slot') {
        moveRosterSlotPlayerToBench(move.value);
    } else {
        refreshRosterFormationModal();
    }
}

function handleRosterFormationCardTap(event, sourceType, sourceValue) {
    event?.preventDefault();
    event?.stopPropagation();
    setRosterFormationSelection(sourceType, sourceValue);
}

function handleRosterFormationSlotTap(event, targetSlotKey) {
    event?.preventDefault();
    event?.stopPropagation();
    const move = rosterFormationState.selectedMove;
    if (!move) return;
    applyRosterFormationMoveToSlot(move, targetSlotKey);
}

function handleRosterFormationBenchTap(event) {
    event?.preventDefault();
    event?.stopPropagation();
    const move = rosterFormationState.selectedMove;
    if (!move) return;
    applyRosterFormationMoveToBench(move);
}

function parseRosterFormationDragData(event) {
    const raw = event?.dataTransfer?.getData('application/json') || event?.dataTransfer?.getData('text/plain') || '';
    if (!raw) return null;
    try {
        const parsed = JSON.parse(raw);
        if (parsed && parsed.type) return parsed;
    } catch (error) {
        return {type: 'slot', value: raw};
    }
    return null;
}

function handleRosterFormationDragStart(event, sourceType, sourceValue) {
    if (!event?.dataTransfer) return;
    const payload = JSON.stringify({type: sourceType, value: String(sourceValue || '')});
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('application/json', payload);
    event.dataTransfer.setData('text/plain', payload);
    event.currentTarget?.classList?.add('is-dragging');
    document.querySelector('.formation-board')?.classList?.add('is-drag-active');
}

function handleRosterFormationDragEnd(event) {
    event?.currentTarget?.classList?.remove('is-dragging');
    document.querySelector('.formation-board')?.classList?.remove('is-drag-active');
}

function handleRosterFormationDragOver(event) {
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
    event.currentTarget?.classList?.add('is-drop-target');
}

function handleRosterFormationDragLeave(event) {
    event.currentTarget?.classList?.remove('is-drop-target');
}

function handleRosterFormationDrop(event, targetSlotKey) {
    event.preventDefault();
    event.currentTarget?.classList?.remove('is-drop-target');
    document.querySelector('.formation-board')?.classList?.remove('is-drag-active');
    rosterFormationState.selectedMove = null;
    const data = parseRosterFormationDragData(event);
    if (!data) return;
    if (data.type === 'slot') {
        swapRosterFormationSlots(data.value, targetSlotKey);
    } else if (data.type === 'bench') {
        moveRosterBenchPlayerToSlot(data.value, targetSlotKey);
    }
}

function handleRosterFormationBenchDrop(event) {
    event.preventDefault();
    event.currentTarget?.classList?.remove('is-drop-target');
    document.querySelector('.formation-board')?.classList?.remove('is-drag-active');
    rosterFormationState.selectedMove = null;
    const data = parseRosterFormationDragData(event);
    if (data?.type === 'slot') {
        moveRosterSlotPlayerToBench(data.value);
    }
}

function buildFormationPlayerOptions(players, selectedUid, slot) {
    const selected = Number(selectedUid || 0);
    const usedByOtherSlots = new Set(Object.entries(rosterFormationState.picks || {})
        .filter(([key, uid]) => key !== slot.key && Number(uid))
        .map(([, uid]) => Number(uid)));
    const sorted = [...players].sort((left, right) => {
        const leftFit = rosterPlayerMatchesSlot(left, slot) ? 1 : 0;
        const rightFit = rosterPlayerMatchesSlot(right, slot) ? 1 : 0;
        if (leftFit !== rightFit) return rightFit - leftFit;
        return Number(right.ca || 0) - Number(left.ca || 0);
    });
    return [
        '<option value="">空位</option>',
        ...sorted.map(player => {
            const uid = Number(player.uid);
            const disabled = usedByOtherSlots.has(uid) ? ' disabled' : '';
            const label = `${player.name} · ${player.position || '-'} · CA ${player.ca || '-'}`;
            return `<option value="${uid}"${uid === selected ? ' selected' : ''}${disabled}>${escapeHtml(label)}</option>`;
        }),
    ].join('');
}

function renderRosterFormationModal() {
    const teamName = rosterFormationState.teamName;
    const team = teams.find(item => item.name === teamName);
    const players = getRosterTeamPlayers(teamName);
    const slots = getRosterBoardSlots();
    const benchPlayers = getRosterBenchPlayers();
    const canEdit = canEditRosterFormation(team);
    const formationOptions = Object.keys(ROSTER_FORMATIONS)
        .map(key => `<option value="${escapeHtml(key)}"${key === rosterFormationState.formation ? ' selected' : ''}>${escapeHtml(key)}</option>`)
        .join('');
    const pitchSlots = slots.map(slot => {
        const player = getFormationPickedPlayer(slot.key);
        return `
            <div class="formation-slot ${player ? 'has-player' : ''}" style="left:${slot.x}%;top:${slot.y}%;" data-slot-key="${escapeHtml(slot.key)}" onclick="handleRosterFormationSlotTap(event, ${htmlJsString(slot.key)})" ondragover="handleRosterFormationDragOver(event)" ondragleave="handleRosterFormationDragLeave(event)" ondrop="handleRosterFormationDrop(event, ${htmlJsString(slot.key)})">
                <span class="formation-slot-plus">+</span>
                ${player ? buildRosterFormationCard(player, {source: 'slot', slot}) : ''}
            </div>
        `;
    }).join('');
    const benchCards = benchPlayers.map(player => buildRosterFormationCard(player, {source: 'bench'})).join('');

    return `
        <div class="formation-modal formation-board ${rosterFormationState.selectedMove ? 'is-tap-active' : ''}">
            <div class="formation-toolbar capture-exclude">
                <label>
                    <span>阵型</span>
                    <select onchange="changeRosterFormation(this.value)" ${canEdit ? '' : 'disabled'}>${formationOptions}</select>
                </label>
                ${canEdit ? '<button class="btn btn-secondary" type="button" onclick="autoFillRosterFormation()">自动填入</button><button class="btn btn-secondary" type="button" onclick="clearRosterFormation()">清空</button>' : ''}
                ${canEdit && rosterFormationState.teamId ? `<button class="btn btn-primary" type="button" onclick="saveRosterFormation()" ${rosterFormationState.saveBusy ? 'disabled aria-busy="true"' : ''}>${rosterFormationState.saveBusy ? '<span class="ui-button-spinner" aria-hidden="true"></span><span>保存中...</span>' : '保存阵容'}</button>` : ''}
                ${rosterFormationState.saveMessage ? `<span class="formation-save-message is-${escapeHtml(rosterFormationState.saveState || 'idle')}" role="${rosterFormationState.saveState === 'error' ? 'alert' : 'status'}" aria-live="${rosterFormationState.saveState === 'error' ? 'assertive' : 'polite'}">${escapeHtml(rosterFormationState.saveMessage)}</span>` : ''}
            </div>
            ${canEdit ? '' : '<div class="formation-readonly-note capture-exclude">当前为公开预览；只有本队主教练或完整管理员可以调整并保存阵容。</div>'}
            <section id="rosterFormationCapture" class="formation-capture surface-card" data-team-name="${escapeHtml(teamName)}" onclick="clearRosterFormationSelection()">
                <div class="formation-capture-head">
                    <div>
                        <span class="panel-kicker">Lineup Preview</span>
                        <h3>${escapeHtml(teamName)}</h3>
                    </div>
                    <strong>${escapeHtml(rosterFormationState.formation)}</strong>
                </div>
                <div class="formation-pitch" aria-label="${escapeHtml(teamName)}阵容预览">
                    <div class="formation-pitch-line formation-pitch-center"></div>
                    <div class="formation-pitch-box formation-pitch-box-top"></div>
                    <div class="formation-pitch-box formation-pitch-box-bottom"></div>
                    <div class="formation-goal-box formation-goal-box-top"></div>
                    <div class="formation-goal-box formation-goal-box-bottom"></div>
                    <span class="formation-corner corner-tl"></span>
                    <span class="formation-corner corner-tr"></span>
                    <span class="formation-corner corner-bl"></span>
                    <span class="formation-corner corner-br"></span>
                    ${pitchSlots}
                </div>
                <div class="formation-bench" onclick="handleRosterFormationBenchTap(event)" ondragover="handleRosterFormationDragOver(event)" ondragleave="handleRosterFormationDragLeave(event)" ondrop="handleRosterFormationBenchDrop(event)">
                    <div class="formation-bench-title">替补席</div>
                    <div class="formation-bench-grid">${benchCards || '<span class="formation-bench-empty">暂无替补球员</span>'}</div>
                </div>
            </section>
        </div>
    `;
}

function openRosterFormationModal(teamName, options = {}) {
    const normalizedTeamName = String(teamName || '').trim();
    const team = teams.find(item => item.name === normalizedTeamName);
    if (!team) {
        showModal('阵容预览', '请先选择一个有效球队。');
        return;
    }
    rosterFormationState.teamName = normalizedTeamName;
    rosterFormationState.teamId = Number(options.teamId || team.id || 0) || null;
    rosterFormationState.players = Array.isArray(options.players)
        ? options.players.map(player => ({...player, team_name: player.team_name || normalizedTeamName}))
        : [];
    rosterFormationState.canEdit = typeof options.canEdit === 'boolean' ? options.canEdit : null;
    rosterFormationState.saveMessage = '';
    rosterFormationState.saveState = 'idle';
    rosterFormationState.formation = ROSTER_FORMATION_SLOT_KEYS[options.formation] ? options.formation : (rosterFormationState.formation || '4-3-3');
    const savedPicks = options.picks && typeof options.picks === 'object' ? options.picks : {};
    rosterFormationState.picks = Object.keys(savedPicks).length
        ? Object.fromEntries(Object.entries(savedPicks).map(([key, uid]) => [key, Number(uid)]))
        : buildAutoRosterFormationPicks(getRosterTeamPlayers(normalizedTeamName), rosterFormationState.formation);
    showModal(`${normalizedTeamName} 阵容预览`, renderRosterFormationModal());
}

function refreshRosterFormationModal() {
    const body = document.getElementById('modalBody');
    if (body) body.innerHTML = renderRosterFormationModal();
}

function changeRosterFormation(formation) {
    if (!ROSTER_FORMATIONS[formation]) return;
    autoPickRosterFormation(rosterFormationState.teamName, formation);
    refreshRosterFormationModal();
}

function setRosterFormationPick(slotKey, value) {
    const uid = Number(value || 0);
    if (!uid) {
        delete rosterFormationState.picks[slotKey];
    } else {
        rosterFormationState.picks[slotKey] = uid;
    }
    refreshRosterFormationModal();
}

function autoFillRosterFormation() {
    autoPickRosterFormation(rosterFormationState.teamName, rosterFormationState.formation);
    refreshRosterFormationModal();
}

function clearRosterFormation() {
    rosterFormationState.picks = {};
    refreshRosterFormationModal();
}

async function saveRosterFormation() {
    if (rosterFormationState.saveBusy || !rosterFormationState.teamId || !canEditRosterFormation(teams.find(item => item.name === rosterFormationState.teamName))) return;
    const pickedUids = Object.values(rosterFormationState.picks || {}).map(uid => Number(uid)).filter(Boolean);
    if (pickedUids.length !== 11 || new Set(pickedUids).size !== 11) {
        rosterFormationState.saveMessage = '请先在场上安排恰好 11 名不同球员';
        rosterFormationState.saveState = 'warning';
        refreshRosterFormationModal();
        return;
    }
    rosterFormationState.saveBusy = true;
    rosterFormationState.saveMessage = '正在保存阵容';
    rosterFormationState.saveState = 'saving';
    refreshRosterFormationModal();
    try {
        const response = await fetch(`/api/teams/${rosterFormationState.teamId}/lineup`, {
            method: 'PATCH',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({formation: rosterFormationState.formation, picks: rosterFormationState.picks}),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
        rosterFormationState.formation = payload.formation || rosterFormationState.formation;
        rosterFormationState.picks = payload.picks || rosterFormationState.picks;
        rosterFormationState.saveMessage = '阵容已保存并同步到球队中心';
        rosterFormationState.saveState = 'saved';
        if (typeof teamDetailHandleLineupSaved === 'function') teamDetailHandleLineupSaved(payload);
    } catch (error) {
        console.error('Failed to save roster formation:', error);
        rosterFormationState.saveMessage = `保存失败：${error.message || '请稍后重试'}`;
        rosterFormationState.saveState = 'error';
    } finally {
        rosterFormationState.saveBusy = false;
        refreshRosterFormationModal();
    }
}

function buildRosterFormationImageFileName() {
    const date = new Date();
    const stamp = [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, '0'),
        String(date.getDate()).padStart(2, '0'),
    ].join('');
    const cleanTeam = String(rosterFormationState.teamName || '球队').replace(/[\\/:*?"<>|\s]+/g, '_');
    const cleanFormation = String(rosterFormationState.formation || '阵型').replace(/[\\/:*?"<>|\s]+/g, '_');
    return `HEIGO_${cleanTeam}_${cleanFormation}_阵容预览_${stamp}.png`;
}

async function saveRosterFormationImage() {
    if (rosterFormationState.exportBusy) return;
    if (!window.htmlToImage || typeof window.htmlToImage.toBlob !== 'function') {
        showModal('导出组件未就绪', '页面截图组件加载失败，请刷新页面后重试。');
        return;
    }
    const target = document.getElementById('rosterFormationCapture');
    if (!target) {
        showModal('暂时无法保存', '当前没有可导出的阵容预览。');
        return;
    }
    rosterFormationState.exportBusy = true;
    target.classList.add('is-exporting');
    try {
        if (document.fonts?.ready) await document.fonts.ready;
        await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
        const blob = await window.htmlToImage.toBlob(target, {
            cacheBust: true,
            pixelRatio: Math.max(2, Math.min(3, window.devicePixelRatio || 1)),
            filter: node => !(node?.classList && node.classList.contains('capture-exclude')),
        });
        if (!blob) throw new Error('capture-blob-empty');
        downloadRosterFormationBlob(blob, buildRosterFormationImageFileName());
    } catch (error) {
        console.error('Failed to export roster formation image:', error);
        showModal('生成图片失败', '阵容预览图片生成失败，请刷新页面后重试。');
    } finally {
        target.classList.remove('is-exporting');
        rosterFormationState.exportBusy = false;
    }
}

function downloadRosterFormationBlob(blob, fileName) {
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1200);
}

function getSlotBadge(slot) {
    if (!slot) return '';
    const badges = {'7M': 'slot-7m', '8M': 'slot-8m', '伪名': 'slot-fake'};
    return `<span class="slot-badge ${badges[slot] || ''}">${slot}</span>`;
}

function sortPlayers() {
    renderPlayers(currentPlayers);
}

function formatRosterPlayerValue(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return '';
    return `${numeric.toFixed(1)}M`;
}

async function getRosterPlayerWageDetail(uid) {
    const normalizedUid = Number(uid);
    if (playerDetailCache[normalizedUid]) {
        return playerDetailCache[normalizedUid];
    }
    const res = await fetch(`/api/player/wage-detail/${normalizedUid}`);
    if (!res.ok) {
        throw new Error(`wage-detail-${res.status}`);
    }
    const data = await res.json();
    playerDetailCache[normalizedUid] = data;
    return data;
}

function buildRosterPlayerCopyText(player, wageDetail = null) {
    const values = [
        player.uid,
        player.name,
        player.age,
        player.initial_ca,
        player.ca,
        player.pa,
        player.position,
    ];
    const finalValue = formatRosterPlayerValue(wageDetail?.final_value);
    if (finalValue) {
        values.push('身价', finalValue);
    }
    return values.map(value => String(value ?? '').trim()).join(' ');
}

function findRosterPlayerByUid(uid) {
    const normalizedUid = Number(uid);
    return [...(currentPlayers || []), ...(allPlayers || [])]
        .find(player => Number(player.uid) === normalizedUid);
}

function fallbackCopyRosterText(text) {
    if (typeof document.execCommand !== 'function') {
        return false;
    }
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.top = '-1000px';
    textarea.style.left = '-1000px';
    document.body.appendChild(textarea);
    textarea.select();
    try {
        return document.execCommand('copy');
    } catch (error) {
        return false;
    } finally {
        document.body.removeChild(textarea);
    }
}

function showRosterCopyStatus(message, tone = 'success') {
    if (typeof showDetailExportToast === 'function') {
        showDetailExportToast(message, tone);
        return;
    }
    if (typeof showUiToast === 'function') {
        showUiToast(message, tone === 'warning' ? 'warning' : 'success');
        return;
    }
    showModal(tone === 'warning' ? '操作未完成' : '操作完成', escapeHtml(message));
}

async function copyRosterPlayerInfo(event, uid) {
    event?.preventDefault();
    event?.stopPropagation();
    const player = findRosterPlayerByUid(uid);
    if (!player) {
        showRosterCopyStatus('未找到球员数据，无法复制', 'warning');
        return;
    }

    let wageDetail = null;
    try {
        wageDetail = await getRosterPlayerWageDetail(uid);
    } catch (error) {
        console.warn(`Failed to load wage detail for roster copy ${uid}:`, error);
    }
    const text = buildRosterPlayerCopyText(player, wageDetail);
    try {
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(text);
        } else if (!fallbackCopyRosterText(text)) {
            throw new Error('copy-failed');
        }
        showRosterCopyStatus('已复制球员信息');
    } catch (error) {
        if (fallbackCopyRosterText(text)) {
            showRosterCopyStatus('已复制球员信息');
            return;
        }
        showRosterCopyStatus('浏览器未允许写入剪贴板，请手动复制', 'warning');
    }
}

function renderPlayers(players) {
    rosterRendered = true;
    renderPlayerQueryState();
    renderRosterViewToggle();
    if (players.length === 0) {
        document.getElementById('playersTable').innerHTML = '<div class="no-data">没有找到符合条件的球员</div>';
        return;
    }

    const sortedPlayers = getSortedRosterPlayers(players);
    const pageSize = isRosterMobileViewport() ? ROSTER_MOBILE_PAGE_SIZE : ROSTER_DESKTOP_PAGE_SIZE;
    const totalPages = Math.max(1, Math.ceil(sortedPlayers.length / pageSize));
    rosterPage = Math.max(1, Math.min(rosterPage, totalPages));
    const pageStart = (rosterPage - 1) * pageSize;
    const visiblePlayers = sortedPlayers.slice(pageStart, pageStart + pageSize);
    const paginationHtml = renderRosterPagination(sortedPlayers.length, pageSize, rosterPage, totalPages);
    if (isRosterCardMode()) {
        document.getElementById('playersTable').innerHTML = `${renderRosterMobileCards(visiblePlayers)}${paginationHtml}`;
        return;
    }
    renderRosterTable(visiblePlayers, paginationHtml);
}

function markRosterRenderStale() {
    if (rosterRenderFrameId !== null && typeof cancelAnimationFrame === 'function') {
        cancelAnimationFrame(rosterRenderFrameId);
    }
    rosterRenderFrameId = null;
    rosterRendered = false;
    rosterPage = 1;
    const container = document.getElementById('playersTable');
    if (container && !document.getElementById('players')?.classList.contains('active')) {
        container.innerHTML = '<div class="loading">进入联赛名单后加载...</div>';
    }
}

function ensureRosterRendered() {
    if (!rosterRendered) {
        const container = document.getElementById('playersTable');
        if (container) {
            container.innerHTML = '<div class="loading">正在加载联赛名单...</div>';
        }
        if (rosterRenderFrameId !== null) return;
        const render = () => {
            rosterRenderFrameId = null;
            if (!document.getElementById('players')?.classList.contains('active')) return;
            renderPlayers(currentPlayers || []);
        };
        if (typeof requestAnimationFrame === 'function') {
            rosterRenderFrameId = requestAnimationFrame(() => {
                rosterRenderFrameId = requestAnimationFrame(render);
            });
        } else {
            rosterRenderFrameId = -1;
            window.setTimeout(render, 0);
        }
        return;
    }
    renderPlayerQueryState();
    renderRosterViewToggle();
}

function renderRosterPagination(totalCount, pageSize, currentPage, totalPages) {
    if (totalCount <= pageSize) return '';
    const start = (currentPage - 1) * pageSize + 1;
    const end = Math.min(totalCount, currentPage * pageSize);
    return `
        <nav class="roster-pagination" aria-label="联赛名单分页">
            <span class="roster-pagination-summary">显示 ${start}-${end}，共 ${totalCount} 人</span>
            <div class="roster-pagination-controls">
                <button type="button" class="roster-page-button" onclick="setRosterPage(${currentPage - 1})" ${currentPage <= 1 ? 'disabled' : ''} aria-label="上一页">‹</button>
                <select class="roster-page-select" aria-label="选择名单页码" onchange="setRosterPage(this.value)">
                    ${Array.from({length: totalPages}, (_item, index) => {
                        const page = index + 1;
                        return `<option value="${page}" ${page === currentPage ? 'selected' : ''}>第 ${page} / ${totalPages} 页</option>`;
                    }).join('')}
                </select>
                <button type="button" class="roster-page-button" onclick="setRosterPage(${currentPage + 1})" ${currentPage >= totalPages ? 'disabled' : ''} aria-label="下一页">›</button>
            </div>
        </nav>
    `;
}

function setRosterPage(page) {
    rosterPage = Math.max(1, Number(page) || 1);
    renderPlayers(currentPlayers || []);
    document.querySelector('.player-results-panel')?.scrollIntoView({behavior: 'smooth', block: 'start'});
}

function getRosterPlayerGrowth(player) {
    const current = Number(player.ca || 0);
    const initial = Number(player.initial_ca || 0);
    return current - initial;
}

function getRosterPositionClass(position) {
    const text = String(position || '').toUpperCase();
    if (text.includes('GK')) return 'is-gk';
    if (/\b(ST|CF|FW)\b/.test(text)) return 'is-forward';
    if (/\b(AM|AML|AMR|AMC|IF|W|MR|ML)\b/.test(text)) return 'is-attacker';
    if (/\b(DM|MC|CM|M)\b/.test(text)) return 'is-midfielder';
    if (/\b(DR|DL|DC|CB|WB|FB)\b/.test(text)) return 'is-defender';
    return 'is-midfielder';
}

function renderRosterMobileCards(players) {
    return `<div class="mobile-roster-list" aria-label="联赛名单卡片视图">${players.map(player => {
        const uid = Number(player.uid);
        const playerName = escapeHtml(player.name || '');
        const teamName = escapeHtml(player.team_name || '');
        const teamArg = htmlJsString(player.team_name || '');
        const position = escapeHtml(player.position || '-');
        const nationality = escapeHtml(formatCompactNationality(player.nationality || '-', {maxLength: 18}));
        const wage = Number(player.wage || 0).toFixed(3);
        const growth = getRosterPlayerGrowth(player);
        const growthText = growth > 0 ? `+${growth}` : String(growth);
        const growthClass = growth > 0 ? 'is-positive' : growth < 0 ? 'is-negative' : 'is-flat';
        const selectedClass = Number(currentSelectedRosterUid) === uid ? ' is-selected' : '';
        return `
            <article class="mobile-roster-card${selectedClass}" id="player-card-${uid}" data-player-uid="${uid}" tabindex="0" onclick="openRosterPlayerCard(event, ${uid})" onkeydown="handleRosterCardKeydown(event, ${uid})">
                <div class="mobile-roster-card-main">
                    <div class="mobile-roster-player">
                        <button type="button" class="mobile-roster-name" onclick="event.stopPropagation(); openRosterPlayerAttributeDetail(${uid})">${playerName}</button>
                        <span class="mobile-roster-subline">UID ${uid} · ${nationality}</span>
                    </div>
                    <span class="mobile-roster-position ${getRosterPositionClass(player.position)}">${position}</span>
                </div>
                <div class="mobile-roster-team-row">
                    <button type="button" class="mobile-roster-team" onclick="event.stopPropagation(); viewTeamPlayers(${teamArg})">${teamName || '-'}</button>
                    <span class="mobile-roster-slot">${getSlotBadge(player.slot_type)}</span>
                </div>
                <div class="mobile-roster-stats">
                    <span><strong>${Number(player.age || 0)}</strong><em>年龄</em></span>
                    <span><strong>${Number(player.initial_ca || 0)}</strong><em>初始 CA</em></span>
                    <span><strong>${Number(player.ca || 0)}</strong><em>当前 CA</em></span>
                    <span><strong>${Number(player.pa || 0)}</strong><em>PA</em></span>
                    <span class="${growthClass}"><strong>${growthText}</strong><em>成长</em></span>
                    <span><strong>${wage}M</strong><em>工资</em></span>
                </div>
                <div class="mobile-roster-card-actions">
                    <button type="button" class="roster-copy-button mobile-roster-copy" onclick="copyRosterPlayerInfo(event, ${uid})">复制</button>
                </div>
            </article>
        `;
    }).join('')}</div>`;
}

function renderRosterTable(sortedPlayers, paginationHtml = '') {
    const html = `<table class="players-list-table" aria-label="联赛名单数据表">
        <colgroup>
            <col class="uid-column">
            <col class="name-column">
            <col class="age-column">
            <col class="ca-column">
            <col class="ca-column">
            <col class="ca-column">
            <col class="position-column">
            <col class="nation-column">
            <col class="team-column">
            <col class="wage-column">
            <col class="table-slot-col">
            ${isAdmin ? '<col class="detail-column">' : ''}
            <col class="copy-column">
        </colgroup>
        <thead><tr>${buildRosterHeader('UID', 'uid', true)}${buildRosterHeader('姓名', 'name')}${buildRosterHeader('年龄', 'age', true)}${buildRosterHeader('初始CA', 'initial_ca', true)}${buildRosterHeader('当前CA', 'ca', true)}${buildRosterHeader('PA', 'pa', true)}${buildRosterHeader('位置', 'position')}${buildRosterHeader('国籍', 'nationality')}${buildRosterHeader('所属球队', 'team_name')}${buildRosterHeader('工资', 'wage', true)}${buildRosterHeader('名额', 'slot_type')}${isAdmin ? '<th class="detail-column">详情</th>' : ''}<th class="copy-column">复制</th></tr></thead><tbody>${sortedPlayers.map(player => {
            const uidCell = isAdmin
                ? `<td class="numeric-cell"><input type="number" class="editable-input" value="${player.uid}" onchange="updatePlayerUidConfirm(${player.uid}, this.value, this)" style="background:rgba(0,0,0,0.2);border:2px solid #e74c3c;padding:4px 6px;border-radius:4px;color:#fff;width:50px;font-weight:bold;" title="修改 UID 需要谨慎，请确认无误！"></td>`
                : `<td class="numeric-cell">${player.uid}</td>`;

            const nameCell = isAdmin
                ? `<td class="name-cell"><input type="text" class="editable-input" value="${player.name.replace(/"/g, '&quot;')}" onchange="updatePlayerField(${player.uid}, 'name', this.value)" style="background:rgba(0,0,0,0.2);border:1px solid rgba(0,217,255,0.3);padding:4px 8px;border-radius:4px;color:#fff;width:118px;"></td>`
                : `<td class="name-cell" title="${player.name.replace(/"/g, '&quot;')}"><span class="player-link roster-player-link" onclick="openRosterPlayerAttributeDetail(${player.uid})">${player.name}</span></td>`;

            const ageCell = isAdmin
                ? `<td class="numeric-cell"><input type="number" class="editable-input" value="${player.age}" onchange="updatePlayerField(${player.uid}, 'age', this.value)" style="background:rgba(0,0,0,0.2);border:1px solid rgba(0,217,255,0.3);padding:4px 8px;border-radius:4px;color:#fff;width:50px;"></td>`
                : `<td class="numeric-cell">${player.age}</td>`;

            const caCell = isAdmin
                ? `<td class="numeric-cell"><input type="number" class="editable-input player-rating-input" min="1" max="200" value="${player.ca}" onchange="updatePlayerField(${player.uid}, 'ca', this.value)" aria-label="编辑 ${player.name.replace(/"/g, '&quot;')} 当前 CA" title="修改后自动重算工资与球队统计"></td>`
                : `<td class="numeric-cell"><strong>${player.ca}</strong></td>`;

            const paCell = isAdmin
                ? `<td class="numeric-cell"><input type="number" class="editable-input player-rating-input" min="-10" max="200" value="${player.pa}" onchange="updatePlayerField(${player.uid}, 'pa', this.value)" aria-label="编辑 ${player.name.replace(/"/g, '&quot;')} PA" title="支持 -10 至 200，修改后自动重算工资与球队统计"></td>`
                : `<td class="numeric-cell">${player.pa}</td>`;

            const positionCell = isAdmin
                ? `<td class="position-cell"><input type="text" class="editable-input" value="${player.position.replace(/"/g, '&quot;')}" onchange="updatePlayerField(${player.uid}, 'position', this.value)" style="background:rgba(0,0,0,0.2);border:1px solid rgba(0,217,255,0.3);padding:4px 8px;border-radius:4px;color:#fff;width:80px;"></td>`
                : `<td class="position-cell">${player.position}</td>`;

            const nationalityCell = isAdmin
                ? `<td class="nationality-cell" title="${player.nationality.replace(/"/g, '&quot;')}"><input type="text" class="editable-input" value="${player.nationality.replace(/"/g, '&quot;')}" onchange="updatePlayerField(${player.uid}, 'nationality', this.value)" style="background:rgba(0,0,0,0.2);border:1px solid rgba(0,217,255,0.3);padding:4px 8px;border-radius:4px;color:#fff;width:88px;"></td>`
                : `<td class="nationality-cell" title="${player.nationality.replace(/"/g, '&quot;')}">${escapeHtml(formatCompactNationality(player.nationality, {maxLength: 14}))}</td>`;

            const detailCell = isAdmin
                ? `<td><button class="btn btn-secondary" style="padding:4px 8px;font-size:0.8rem;" onclick="togglePlayerDetail(${player.uid})">📊</button></td>`
                : '';
            const copyCell = `<td class="copy-cell"><button type="button" class="roster-copy-button" onclick="copyRosterPlayerInfo(event, ${player.uid})" title="复制 UID 姓名 年龄 初始CA 当前CA PA 位置 身价">复制</button></td>`;

            const isSelected = Number(currentSelectedRosterUid) === Number(player.uid);
            const mainRow = `<tr id="player-row-${player.uid}" class="${isSelected ? 'row-selected' : ''}" data-player-uid="${player.uid}" tabindex="0" onclick="selectRosterPlayer(${player.uid})" onkeydown="handleRosterRowKeydown(event, ${player.uid})">${uidCell}${nameCell}${ageCell}<td class="numeric-cell">${player.initial_ca}</td>${caCell}${paCell}${positionCell}${nationalityCell}<td class="team-name-cell"><span class="player-link roster-player-link" onclick="viewTeamPlayers('${player.team_name.replace(/'/g, "\\'")}')">${player.team_name}</span></td><td class="numeric-cell">${player.wage.toFixed(3)}M</td><td class="slot-cell">${getSlotBadge(player.slot_type)}</td>${detailCell}${copyCell}</tr>`;

            const detailRow = isAdmin
                ? `<tr id="player-detail-${player.uid}" class="player-detail-row" style="display:none;background:var(--bg-tertiary);"><td colspan="13"><div style="padding:15px;display:grid;grid-template-columns:repeat(4,1fr);gap:10px;">
                    <div><strong>初始身价:</strong> <span id="detail-initial-value-${player.uid}">加载中...</span></div>
                    <div><strong>当前身价:</strong> <span id="detail-current-value-${player.uid}">加载中...</span></div>
                    <div><strong>潜力身价:</strong> <span id="detail-potential-value-${player.uid}">加载中...</span></div>
                    <div><strong>最终身价:</strong> <span id="detail-final-value-${player.uid}">加载中...</span></div>
                    <div><strong>初始字段:</strong> <span id="detail-initial-field-${player.uid}">加载中...</span></div>
                    <div><strong>系数:</strong> <span id="detail-coefficient-${player.uid}">加载中...</span></div>
                    <div><strong>名额类型:</strong> <span id="detail-slot-type-${player.uid}">加载中...</span></div>
                    <div><strong>工资计算:</strong> <span id="detail-wage-calc-${player.uid}">加载中...</span></div>
                </div></td></tr>`
                : '';

            return mainRow + detailRow;
        }).join('')}</tbody></table>${paginationHtml}`;
    document.getElementById('playersTable').innerHTML = html;
    bindRosterKeyboardNavigation();
}

function selectRosterPlayer(uid) {
    currentSelectedRosterUid = Number(uid);
    document.querySelectorAll('#playersTable tr.row-selected').forEach(row => row.classList.remove('row-selected'));
    document.querySelectorAll('#playersTable .mobile-roster-card.is-selected').forEach(card => card.classList.remove('is-selected'));
    const row = document.getElementById(`player-row-${uid}`);
    if (row) {
        row.classList.add('row-selected');
    }
    const card = document.getElementById(`player-card-${uid}`);
    if (card) {
        card.classList.add('is-selected');
    }
}

function handleRosterRowKeydown(event, uid) {
    if (event.target?.closest?.('button,input,select,textarea,a')) return;
    if (event.key === 'Enter') {
        event.preventDefault();
        openRosterPlayerAttributeDetail(uid);
    }
}

function handleRosterCardKeydown(event, uid) {
    if (event.target?.closest?.('button,input,select,textarea,a')) return;
    if (event.key === 'Enter') {
        event.preventDefault();
        openRosterPlayerAttributeDetail(uid);
    }
}

function openRosterPlayerCard(event, uid) {
    if (event.target?.closest?.('button,input,select,textarea,a')) return;
    selectRosterPlayer(uid);
    openRosterPlayerAttributeDetail(uid);
}

function bindRosterKeyboardNavigation() {
    const rows = Array.from(document.querySelectorAll('#playersTable tr[data-player-uid]'));
    if (!rows.length) return;
    rows.forEach((row, index) => {
        row.addEventListener('keydown', event => {
            if (event.key === 'ArrowDown') {
                event.preventDefault();
                const next = rows[Math.min(index + 1, rows.length - 1)];
                next?.focus();
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                const prev = rows[Math.max(index - 1, 0)];
                prev?.focus();
            }
        });
    });
}

const playerDetailCache = {};

async function togglePlayerDetail(uid) {
    const detailRow = document.getElementById(`player-detail-${uid}`);
    if (detailRow.style.display === 'none') {
        detailRow.style.display = 'table-row';
        if (playerDetailCache[uid]) {
            updateDetailDisplay(uid, playerDetailCache[uid]);
        } else {
            try {
                const res = await fetch(`/api/player/wage-detail/${uid}`);
                const data = await res.json();
                playerDetailCache[uid] = data;
                updateDetailDisplay(uid, data);
            } catch (error) {
                document.getElementById(`detail-initial-value-${uid}`).textContent = '加载失败';
                document.getElementById(`detail-current-value-${uid}`).textContent = '加载失败';
                console.error(`Failed to load detail for player ${uid}:`, error);
            }
        }
    } else {
        detailRow.style.display = 'none';
    }
}

function updateDetailDisplay(uid, data) {
    document.getElementById(`detail-initial-value-${uid}`).textContent = data.initial_value;
    document.getElementById(`detail-current-value-${uid}`).textContent = data.current_value;
    document.getElementById(`detail-potential-value-${uid}`).textContent = data.potential_value;
    document.getElementById(`detail-final-value-${uid}`).textContent = data.final_value.toFixed(3);
    document.getElementById(`detail-initial-field-${uid}`).textContent = data.initial_field.toFixed(3);
    document.getElementById(`detail-coefficient-${uid}`).textContent = data.coefficient;
    document.getElementById(`detail-slot-type-${uid}`).textContent = data.slot_type || '-';
    document.getElementById(`detail-wage-calc-${uid}`).textContent = `${data.final_value.toFixed(3)} × ${data.coefficient} = ${data.wage.toFixed(3)}M`;
}

async function searchPlayers(options = {}) {
    const shouldSyncHistory = options.pushHistory !== false;
    const historyMode = options.historyMode || 'push';
    const teamName = document.getElementById('teamSelect').value;
    const playerName = document.getElementById('playerSearch').value.trim();

    if (isAdminEntryQuery(playerName)) {
        if (typeof openAdminEntry === 'function') {
            await openAdminEntry();
        } else {
            if (typeof showAdminLoginPanel === 'function') {
                showAdminLoginPanel({reveal: true, focusLogin: false});
            }
            await showTab('admin', null, {syncHistory: false});
        }
        document.getElementById('playerSearch').value = '';
        if (shouldSyncHistory && typeof syncAppHistory === 'function') {
            syncAppHistory(historyMode);
        }
        return;
    }

    const basePlayers = getRosterSearchBasePlayers();
    rosterPage = 1;
    if (playerName || teamName) {
        document.getElementById('tableTitle').textContent = teamName
            ? `${teamName} 筛选结果`
            : `搜索结果: "${playerName}"`;
        currentPlayers = filterRosterPlayersLocally(basePlayers, {teamName, playerName});
    } else {
        document.getElementById('tableTitle').textContent = '全部联赛名单';
        currentPlayers = [...allPlayers];
    }

    renderPlayers(currentPlayers);
    if (shouldSyncHistory && typeof syncAppHistory === 'function') {
        syncAppHistory(historyMode);
    }
}

function resetPlayers(options = {}) {
    const shouldSyncHistory = options.pushHistory !== false;
    const historyMode = options.historyMode || 'push';
    document.getElementById('teamSelect').value = '';
    document.getElementById('playerSearch').value = '';
    document.getElementById('tableTitle').textContent = '全部联赛名单';
    currentRosterSort = {field: '', order: 'desc', type: 'number'};
    currentSelectedRosterUid = null;
    rosterPage = 1;
    currentPlayers = [...allPlayers];
    renderPlayers(currentPlayers);
    if (shouldSyncHistory && typeof syncAppHistory === 'function') {
        syncAppHistory(historyMode);
    }
}

document.getElementById('playerSearch')?.addEventListener('keypress', event => {
    if (event.key === 'Enter') searchPlayers();
});
document.getElementById('teamSelect')?.addEventListener('change', () => {
    searchPlayers();
});
