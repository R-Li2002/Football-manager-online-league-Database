const AppModules = {
    home: {onEnter: () => { if (typeof updateHeroBadgeState === 'function') updateHeroBadgeState(); }},
    overview: {onEnter: () => { if (typeof renderOverview === 'function') renderOverview(); }},
    players: {onEnter: () => { if (typeof renderPlayerQueryState === 'function') renderPlayerQueryState(); }},
    database: {onEnter: () => { if (typeof renderCompareDock === 'function') renderCompareDock(); }},
    admin: {onEnter: () => { if (isAdmin && typeof renderOperationsAuditCard === 'function') renderOperationsAuditCard(); }},
};

const APP_HISTORY_MARKER = 'heigo-spa';
const APP_TAB_NAMES = new Set(['home', 'overview', 'players', 'database', 'admin']);
let appHistoryReady = false;
let appHistoryRestoring = false;
let appHistoryIndex = 0;

function normalizeAppTabName(tabName) {
    const normalized = APP_TAB_NAMES.has(tabName) ? tabName : 'home';
    if (normalized === 'admin' && !isAdmin) {
        return 'home';
    }
    return normalized;
}

function getActiveTabName() {
    const bodyTab = document.body.dataset.activeTab;
    if (APP_TAB_NAMES.has(bodyTab)) {
        return bodyTab;
    }
    const activeTab = document.querySelector('.tab-content.active')?.id;
    return normalizeAppTabName(activeTab);
}

function normalizeSortState(sortState, defaultType = 'number') {
    const field = typeof sortState?.field === 'string' ? sortState.field : '';
    const type = sortState?.type === 'text' ? 'text' : defaultType;
    const defaultOrder = type === 'text' ? 'asc' : 'desc';
    const order = sortState?.order === 'asc' || sortState?.order === 'desc'
        ? sortState.order
        : defaultOrder;
    return {field, order, type};
}

function captureOverviewHistoryState() {
    return {
        expanded: Boolean(overviewMetaExpanded),
        sort: normalizeSortState(currentOverviewSort, 'number'),
    };
}

function capturePlayersHistoryState() {
    return {
        team: document.getElementById('teamSelect')?.value || '',
        query: document.getElementById('playerSearch')?.value.trim() || '',
        sort: normalizeSortState(currentRosterSort, 'number'),
        selectedUid: currentSelectedRosterUid ? Number(currentSelectedRosterUid) : null,
    };
}

function captureDatabaseHistoryState() {
    const isDetailView = document.getElementById('dbDetailView')?.classList.contains('active');
    return {
        query: document.getElementById('dbPlayerSearch')?.value.trim() || '',
        sort: normalizeSortState(currentDbSort, 'number'),
        view: isDetailView && currentDetailPlayer ? 'detail' : 'list',
        detailUid: isDetailView && currentDetailPlayer ? Number(currentDetailPlayer.uid) || null : null,
        returnTab: normalizeAppTabName(dbDetailReturnState?.tab || 'database'),
    };
}

function captureAppHistoryState() {
    return {
        tab: getActiveTabName(),
        overview: captureOverviewHistoryState(),
        players: capturePlayersHistoryState(),
        database: captureDatabaseHistoryState(),
    };
}

function normalizeHistoryState(rawState, index = appHistoryIndex) {
    const baseState = rawState?.__appHistory === APP_HISTORY_MARKER
        ? rawState
        : captureAppHistoryState();

    return {
        __appHistory: APP_HISTORY_MARKER,
        __appHistoryIndex: Number.isFinite(Number(baseState.__appHistoryIndex))
            ? Number(baseState.__appHistoryIndex)
            : index,
        tab: normalizeAppTabName(baseState.tab),
        overview: {
            expanded: Boolean(baseState.overview?.expanded),
            sort: normalizeSortState(baseState.overview?.sort, 'number'),
        },
        players: {
            team: typeof baseState.players?.team === 'string' ? baseState.players.team : '',
            query: typeof baseState.players?.query === 'string' ? baseState.players.query : '',
            sort: normalizeSortState(baseState.players?.sort, 'number'),
            selectedUid: Number.isFinite(Number(baseState.players?.selectedUid))
                ? Number(baseState.players.selectedUid)
                : null,
        },
        database: {
            query: typeof baseState.database?.query === 'string' ? baseState.database.query : '',
            sort: normalizeSortState(baseState.database?.sort, 'number'),
            view: baseState.database?.view === 'detail' ? 'detail' : 'list',
            detailUid: Number.isFinite(Number(baseState.database?.detailUid))
                ? Number(baseState.database.detailUid)
                : null,
            returnTab: normalizeAppTabName(baseState.database?.returnTab || 'database'),
        },
    };
}

function getComparableHistoryState(state) {
    const normalized = normalizeHistoryState(state);
    return JSON.stringify({
        tab: normalized.tab,
        overview: normalized.overview,
        players: normalized.players,
        database: normalized.database,
    });
}

function syncAppHistory(mode = 'push') {
    if (!appHistoryReady || appHistoryRestoring) return;

    const nextIndex = mode === 'push' ? appHistoryIndex + 1 : appHistoryIndex;
    const nextState = normalizeHistoryState(captureAppHistoryState(), nextIndex);
    const currentState = history.state?.__appHistory === APP_HISTORY_MARKER
        ? normalizeHistoryState(history.state)
        : null;

    if (currentState && getComparableHistoryState(currentState) === getComparableHistoryState(nextState)) {
        appHistoryIndex = currentState.__appHistoryIndex || appHistoryIndex;
        return;
    }

    if (mode === 'replace') {
        appHistoryIndex = nextState.__appHistoryIndex;
        history.replaceState(nextState, '', window.location.href);
        return;
    }

    appHistoryIndex = nextState.__appHistoryIndex;
    history.pushState(nextState, '', window.location.href);
}

function canUseAppHistoryBack() {
    return history.state?.__appHistory === APP_HISTORY_MARKER
        && Number(history.state.__appHistoryIndex) > 0;
}

async function restoreOverviewHistoryState(overviewState) {
    overviewMetaExpanded = Boolean(overviewState.expanded);
    currentOverviewSort = normalizeSortState(overviewState.sort, 'number');
    if (typeof renderOverview === 'function') {
        renderOverview();
    }
    if (typeof renderTeamsTable === 'function') {
        renderTeamsTable();
    }
}

async function restorePlayersHistoryState(playersState) {
    const teamSelect = document.getElementById('teamSelect');
    const playerSearch = document.getElementById('playerSearch');
    const normalizedTeam = teams.some(team => team.name === playersState.team) ? playersState.team : '';

    if (teamSelect) {
        teamSelect.value = normalizedTeam;
    }
    if (playerSearch) {
        playerSearch.value = playersState.query || '';
    }

    currentRosterSort = normalizeSortState(playersState.sort, 'number');
    currentSelectedRosterUid = Number.isFinite(Number(playersState.selectedUid))
        ? Number(playersState.selectedUid)
        : null;

    if (typeof searchPlayers === 'function') {
        await searchPlayers({pushHistory: false});
    }

    if (currentSelectedRosterUid && typeof selectRosterPlayer === 'function') {
        selectRosterPlayer(currentSelectedRosterUid);
    }
}

async function restoreDatabaseHistoryState(databaseState) {
    const searchInput = document.getElementById('dbPlayerSearch');
    if (searchInput) {
        searchInput.value = databaseState.query || '';
    }

    currentDbSort = normalizeSortState(databaseState.sort, 'number');
    dbDetailReturnState = {tab: normalizeAppTabName(databaseState.returnTab || 'database')};

    if (databaseState.view === 'detail' && databaseState.detailUid && typeof showPlayerDetail === 'function') {
        await showPlayerDetail(databaseState.detailUid, {
            returnTab: dbDetailReturnState.tab,
            pushHistory: false,
        });
        return;
    }

    if (typeof activateDatabaseView === 'function') {
        activateDatabaseView('list');
    }
    currentDetailPlayer = null;

    if (databaseState.query && typeof searchDatabase === 'function') {
        await searchDatabase(databaseState.query, {pushHistory: false});
        return;
    }

    currentDbPlayers = [];
    const dbTableTitle = document.getElementById('dbTableTitle');
    const dbPlayersTable = document.getElementById('dbPlayersTable');
    if (dbTableTitle) {
        dbTableTitle.textContent = '\u7403\u5458\u5e93\u641c\u7d22\u7ed3\u679c';
    }
    if (dbPlayersTable) {
        dbPlayersTable.innerHTML = '<div class="no-data">\u8bf7\u8f93\u5165\u7403\u5458\u59d3\u540d\u6216 UID \u8fdb\u884c\u641c\u7d22</div>';
    }
}

async function restoreAppHistoryState(rawState) {
    const state = normalizeHistoryState(rawState, appHistoryIndex);
    appHistoryRestoring = true;

    try {
        await restoreOverviewHistoryState(state.overview);
        await restorePlayersHistoryState(state.players);
        await restoreDatabaseHistoryState(state.database);
        showTab(state.tab, null, {syncHistory: false});
    } finally {
        appHistoryRestoring = false;
    }
}

async function handleAppPopState(event) {
    if (event.state?.__appHistory !== APP_HISTORY_MARKER) {
        return;
    }
    appHistoryIndex = Number(event.state.__appHistoryIndex) || 0;
    await restoreAppHistoryState(event.state);
}

async function initializeAppHistory() {
    window.addEventListener('popstate', handleAppPopState);
    const initialIndex = history.state?.__appHistory === APP_HISTORY_MARKER
        ? Number(history.state.__appHistoryIndex) || 0
        : 0;
    const initialState = normalizeHistoryState(history.state, initialIndex);
    appHistoryIndex = initialState.__appHistoryIndex;
    history.replaceState(initialState, '', window.location.href);
    appHistoryReady = true;
    await restoreAppHistoryState(initialState);
}

async function init() {
    const savedTheme = localStorage.getItem('themeMode');
    isDarkMode = savedTheme === 'dark';
    document.body.classList.toggle('light-mode', !isDarkMode);
    syncThemeToggleState();
    try {
        const [teamsRes, playersRes, infoRes, adminRes] = await Promise.all([
            fetch('/api/teams'),
            fetch('/api/players'),
            fetch('/api/league/info'),
            fetch('/api/admin/check'),
        ]);
        teams = await teamsRes.json();
        allPlayers = await playersRes.json();
        currentPlayers = [...allPlayers];
        leagueInfo = await infoRes.json();
        const adminData = await adminRes.json();
        isAdmin = adminData.authenticated;

        renderOverview();
        renderTeamsTable();
        renderTeamStatSourceDebugView();
        populateTeamSelect();
        updateStats();
        renderPlayers(currentPlayers);
        if (typeof renderCompareDock === 'function') {
            renderCompareDock();
        }

        if (isAdmin) {
            showAdminTab();
        }

        await initializeAppHistory();
    } catch (error) {
        console.error('Error:', error);
    }
}

async function refreshTeamDataset() {
    const teamsRes = await fetch('/api/teams');
    teams = await teamsRes.json();
    renderTeamsTable();
    renderTeamStatSourceDebugView();
    populateTeamSelect();
    if (isAdmin) {
        populateAdminSelects();
    }
}

async function refreshPlayerDataset() {
    const playersRes = await fetch('/api/players');
    allPlayers = await playersRes.json();
    currentPlayers = [...allPlayers];
    renderPlayers(currentPlayers);
    updateStats();
}

async function refreshLeagueInfoDataset() {
    const infoRes = await fetch('/api/league/info');
    leagueInfo = await infoRes.json();
    renderOverview();
}

function showTab(tabName, triggerElement = null, options = {}) {
    const normalizedTab = normalizeAppTabName(tabName);
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));
    document.getElementById(normalizedTab).classList.add('active');
    const activeButton = triggerElement || document.querySelector(`.nav-tab[data-tab="${normalizedTab}"]`);
    if (activeButton) {
        activeButton.classList.add('active');
    }
    document.body.dataset.activeTab = normalizedTab;
    const module = AppModules[normalizedTab];
    if (module && typeof module.onEnter === 'function') {
        module.onEnter();
    }
    if (typeof renderCompareDock === 'function') {
        renderCompareDock();
    }
    if (options.syncHistory !== false) {
        syncAppHistory(options.historyMode || 'push');
    }
}

function updateStats() {
    const teamCount = document.getElementById('teamCount');
    const playerCount = document.getElementById('playerCount');
    if (teamCount) teamCount.textContent = teams.length;
    if (playerCount) playerCount.textContent = allPlayers.length;
    if (typeof renderOverview === 'function') {
        renderOverview();
    }
    if (typeof updateHeroBadgeState === 'function') {
        updateHeroBadgeState();
    }
}

async function exportData() {
    try {
        const response = await fetch('/api/export/excel');
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText || '导出失败'}`);
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const now = new Date();
        const timestamp = `${now.getFullYear()}${(now.getMonth() + 1).toString().padStart(2, '0')}${now.getDate().toString().padStart(2, '0')}_${now.getHours().toString().padStart(2, '0')}${now.getMinutes().toString().padStart(2, '0')}${now.getSeconds().toString().padStart(2, '0')}`;
        a.download = `heigo_export_${timestamp}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        console.error('导出错误:', error);
        showModal('错误', `导出失败：${error.message}`);
    }
}

init();
