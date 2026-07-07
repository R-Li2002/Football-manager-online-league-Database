const AppModules = {
    home: {onEnter: () => { if (typeof updateHeroBadgeState === 'function') updateHeroBadgeState(); }},
    overview: {onEnter: () => { if (typeof renderOverview === 'function') renderOverview(); }},
    players: {onEnter: () => { if (typeof renderPlayerQueryState === 'function') renderPlayerQueryState(); }},
    competition: {onEnter: () => { if (typeof loadCompetitionData === 'function') loadCompetitionData(); }},
    coaches: {onEnter: () => { if (typeof loadCoaches === 'function') loadCoaches(); }},
    database: {onEnter: async () => {
        if (typeof loadAttributeVersionCatalog === 'function') {
            await loadAttributeVersionCatalog();
        }
        if (typeof refreshAttributeVersionBanner === 'function') {
            refreshAttributeVersionBanner();
        }
        if (typeof renderAdvancedSearchTriggerState === 'function') {
            renderAdvancedSearchTriggerState();
        }
        if (typeof renderDatabaseSearchSummary === 'function') {
            renderDatabaseSearchSummary();
        }
        if (typeof syncDatabaseSubtabUI === 'function') {
            syncDatabaseSubtabUI();
        }
        if (typeof populateReactionLeaderboardTeamSelect === 'function') {
            populateReactionLeaderboardTeamSelect();
        }
        if (typeof renderCompareDock === 'function') renderCompareDock();
        if (typeof renderCandidateDock === 'function') renderCandidateDock();
    }},
    admin: {onEnter: () => {
        if (typeof syncAdminTabVisibility === 'function') {
            syncAdminTabVisibility();
        }
        if (isAdmin) {
            if (typeof syncAdminPanelVisibility === 'function') {
                syncAdminPanelVisibility();
            }
            if (typeof renderOperationsAuditCard === 'function') renderOperationsAuditCard();
            if (typeof renderDataFeedbackReportsCard === 'function') renderDataFeedbackReportsCard();
            return;
        }
        if (typeof showAdminLoginPanel === 'function') {
            showAdminLoginPanel({reveal: false, focusLogin: true});
        }
    }},
};

const APP_HISTORY_MARKER = 'heigo-spa';
const APP_TAB_NAMES = new Set(['home', 'overview', 'players', 'competition', 'coaches', 'database', 'admin']);
let appHistoryReady = false;
let appHistoryRestoring = false;
let appHistoryIndex = 0;

function normalizeAppTabName(tabName) {
    return APP_TAB_NAMES.has(tabName) ? tabName : 'home';
}

function getActiveTabName() {
    const bodyTab = document.body.dataset.activeTab;
    if (APP_TAB_NAMES.has(bodyTab)) {
        return bodyTab;
    }
    const activeTab = document.querySelector('.tab-content.active')?.id;
    return normalizeAppTabName(activeTab);
}

const MOBILE_PRIMARY_TABS = new Set(['home', 'players', 'competition', 'database']);

function isMobileViewport() {
    return window.matchMedia ? window.matchMedia('(max-width: 780px)').matches : window.innerWidth <= 780;
}

function closeMobileMoreMenu() {
    const menu = document.getElementById('mobileMoreMenu');
    const toggle = document.querySelector('[data-mobile-more-toggle]');
    if (menu) {
        menu.hidden = true;
    }
    if (toggle) {
        toggle.setAttribute('aria-expanded', 'false');
        toggle.classList.remove('is-open');
    }
}

function toggleMobileMoreMenu(forceOpen) {
    const menu = document.getElementById('mobileMoreMenu');
    const toggle = document.querySelector('[data-mobile-more-toggle]');
    if (!menu || !toggle) return;
    const shouldOpen = typeof forceOpen === 'boolean' ? forceOpen : menu.hidden;
    menu.hidden = !shouldOpen;
    toggle.setAttribute('aria-expanded', shouldOpen ? 'true' : 'false');
    toggle.classList.toggle('is-open', shouldOpen);
}

function syncMobileNavState(options = {}) {
    const activeTab = getActiveTabName();
    document.querySelectorAll('[data-mobile-tab]').forEach(button => {
        button.classList.toggle('active', button.dataset.mobileTab === activeTab);
    });

    const moreToggle = document.querySelector('[data-mobile-more-toggle]');
    if (moreToggle) {
        moreToggle.classList.toggle('active', APP_TAB_NAMES.has(activeTab) && !MOBILE_PRIMARY_TABS.has(activeTab));
    }

    const mobileAdminTab = document.getElementById('mobileAdminTab');
    if (mobileAdminTab) {
        mobileAdminTab.classList.toggle('hidden-tab', !(isAdmin || adminEntryUnlocked));
    }

    if (options.closeMenu !== false) {
        closeMobileMoreMenu();
    }
}

function initializeMobileNavigation() {
    const menu = document.getElementById('mobileMoreMenu');
    const toggle = document.querySelector('[data-mobile-more-toggle]');
    if (!menu || !toggle) return;

    document.addEventListener('click', event => {
        if (menu.hidden) return;
        if (menu.contains(event.target) || toggle.contains(event.target)) return;
        closeMobileMoreMenu();
    });

    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') {
            closeMobileMoreMenu();
        }
    });

    window.addEventListener('resize', () => {
        if (!isMobileViewport()) {
            closeMobileMoreMenu();
        }
    });

    syncMobileNavState({closeMenu: false});
}

function buildAppHistoryUrl(state) {
    const normalized = normalizeHistoryState(state);
    const url = new URL(window.location.href);
    const params = url.searchParams;
    ['tab', 'databaseSubtab', 'candidateList', 'q', 'version'].forEach(key => params.delete(key));

    if (normalized.tab !== 'home') {
        params.set('tab', normalized.tab);
    }
    if (normalized.tab === 'database') {
        const database = normalized.database || {};
        if (database.scopeType === 'candidate_list' && database.scopeId) {
            params.set('candidateList', String(database.scopeId));
        } else if (database.view === 'candidates' || database.subtab === 'candidates') {
            params.set('databaseSubtab', 'candidates');
        } else if (database.view === 'leaderboard' || database.subtab === 'leaderboard') {
            params.set('databaseSubtab', 'leaderboard');
        }
        if (database.query) {
            params.set('q', database.query);
        }
        if (database.attributeVersion) {
            params.set('version', database.attributeVersion);
        }
    }

    const query = params.toString();
    return `${url.pathname}${query ? `?${query}` : ''}${url.hash}`;
}

function applyInitialUrlState(rawState) {
    const state = normalizeHistoryState(rawState);
    const params = new URLSearchParams(window.location.search);
    const tabParam = params.get('tab');
    const candidateListId = Number(params.get('candidateList'));
    const databaseSubtab = params.get('databaseSubtab');
    const query = params.get('q');
    const version = params.get('version');

    if (tabParam) {
        state.tab = normalizeAppTabName(tabParam);
    }

    if (Number.isFinite(candidateListId) && candidateListId > 0) {
        state.tab = 'database';
        state.database.subtab = 'search';
        state.database.view = 'list';
        state.database.scopeType = 'candidate_list';
        state.database.scopeId = candidateListId;
    } else if (state.tab === 'database' && databaseSubtab === 'candidates') {
        state.database.subtab = 'candidates';
        state.database.view = 'candidates';
        state.database.scopeType = 'none';
        state.database.scopeId = null;
    } else if (state.tab === 'database' && databaseSubtab === 'leaderboard') {
        state.database.subtab = 'leaderboard';
        state.database.view = 'leaderboard';
        state.database.scopeType = 'none';
        state.database.scopeId = null;
    }

    if (state.tab === 'database') {
        if (query !== null) {
            state.database.query = query;
        }
        if (version !== null) {
            state.database.attributeVersion = version;
        }
    }

    return normalizeHistoryState(state, state.__appHistoryIndex);
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
    const isLeaderboardView = document.getElementById('dbReactionLeaderboardView')?.classList.contains('active');
    const isCandidateView = document.getElementById('dbCandidateListsView')?.classList.contains('active');
    return {
        query: document.getElementById('dbPlayerSearch')?.value.trim() || '',
        batch: typeof getDatabaseBatchRawValue === 'function'
            ? getDatabaseBatchRawValue()
            : (document.getElementById('dbBatchSearch')?.value || ''),
        attributeVersion: typeof getCurrentAttributeVersion === 'function' ? getCurrentAttributeVersion() : '',
        advancedFilters: typeof captureAdvancedDatabaseFilters === 'function' ? captureAdvancedDatabaseFilters() : {},
        sort: normalizeSortState(currentDbSort, 'number'),
        subtab: currentDatabaseSubtab === 'leaderboard' ? 'leaderboard' : currentDatabaseSubtab === 'candidates' ? 'candidates' : 'search',
        scopeType: databaseSearchScope?.type || 'none',
        scopeId: databaseSearchScope?.id || null,
        leaderboardMetric: document.getElementById('dbReactionMetricSelect')?.value || 'flowers',
        leaderboardLimit: document.getElementById('dbReactionLimitSelect')?.value || '20',
        leaderboardTeam: document.getElementById('dbReactionTeamSelect')?.value || '',
        view: isDetailView && currentDetailPlayer ? 'detail' : isLeaderboardView ? 'leaderboard' : isCandidateView ? 'candidates' : 'list',
        detailUid: isDetailView && currentDetailPlayer ? Number(currentDetailPlayer.uid) || null : null,
        returnTab: normalizeAppTabName(dbDetailReturnState?.tab || 'database'),
        returnSubtab: dbDetailReturnState?.subtab === 'leaderboard' ? 'leaderboard' : dbDetailReturnState?.subtab === 'candidates' ? 'candidates' : 'search',
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
            batch: typeof baseState.database?.batch === 'string' ? baseState.database.batch : '',
            attributeVersion: typeof baseState.database?.attributeVersion === 'string' ? baseState.database.attributeVersion : '',
            advancedFilters: baseState.database?.advancedFilters && typeof baseState.database.advancedFilters === 'object'
                ? baseState.database.advancedFilters
                : {},
            sort: normalizeSortState(baseState.database?.sort, 'number'),
            subtab: baseState.database?.subtab === 'leaderboard' ? 'leaderboard' : baseState.database?.subtab === 'candidates' ? 'candidates' : 'search',
            scopeType: baseState.database?.scopeType === 'candidate_list' ? 'candidate_list' : baseState.database?.scopeType === 'batch' ? 'batch' : 'none',
            scopeId: Number.isFinite(Number(baseState.database?.scopeId)) ? Number(baseState.database.scopeId) : null,
            leaderboardMetric: typeof baseState.database?.leaderboardMetric === 'string' ? baseState.database.leaderboardMetric : 'flowers',
            leaderboardLimit: typeof baseState.database?.leaderboardLimit === 'string' ? baseState.database.leaderboardLimit : '20',
            leaderboardTeam: typeof baseState.database?.leaderboardTeam === 'string' ? baseState.database.leaderboardTeam : '',
            view: baseState.database?.view === 'detail' ? 'detail' : baseState.database?.view === 'leaderboard' ? 'leaderboard' : baseState.database?.view === 'candidates' ? 'candidates' : 'list',
            detailUid: Number.isFinite(Number(baseState.database?.detailUid))
                ? Number(baseState.database.detailUid)
                : null,
            returnTab: normalizeAppTabName(baseState.database?.returnTab || 'database'),
            returnSubtab: baseState.database?.returnSubtab === 'leaderboard' ? 'leaderboard' : baseState.database?.returnSubtab === 'candidates' ? 'candidates' : 'search',
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
        history.replaceState(nextState, '', buildAppHistoryUrl(nextState));
        return;
    }

    appHistoryIndex = nextState.__appHistoryIndex;
    history.pushState(nextState, '', buildAppHistoryUrl(nextState));
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
    if (typeof setDatabaseBatchRawValue === 'function') {
        setDatabaseBatchRawValue(databaseState.batch || '');
    }

    if (typeof loadAttributeVersionCatalog === 'function') {
        await loadAttributeVersionCatalog();
    }
    if (typeof setCurrentAttributeVersion === 'function') {
        setCurrentAttributeVersion(databaseState.attributeVersion);
    }
    if (typeof applyAdvancedDatabaseFiltersState === 'function') {
        applyAdvancedDatabaseFiltersState(databaseState.advancedFilters, {renderPanel: false});
    }
    currentDbSort = normalizeSortState(databaseState.sort, 'number');
    currentDatabaseSubtab = databaseState.subtab === 'leaderboard' ? 'leaderboard' : databaseState.subtab === 'candidates' ? 'candidates' : 'search';
    dbDetailReturnState = {
        tab: normalizeAppTabName(databaseState.returnTab || 'database'),
        subtab: databaseState.returnSubtab === 'leaderboard' ? 'leaderboard' : databaseState.returnSubtab === 'candidates' ? 'candidates' : 'search',
    };
    if (typeof syncDatabaseSubtabUI === 'function') {
        syncDatabaseSubtabUI();
    }
    const leaderboardMetricSelect = document.getElementById('dbReactionMetricSelect');
    const leaderboardLimitSelect = document.getElementById('dbReactionLimitSelect');
    const leaderboardTeamSelect = document.getElementById('dbReactionTeamSelect');
    if (leaderboardMetricSelect) leaderboardMetricSelect.value = databaseState.leaderboardMetric || 'flowers';
    if (leaderboardLimitSelect) leaderboardLimitSelect.value = databaseState.leaderboardLimit || '20';
    if (typeof populateReactionLeaderboardTeamSelect === 'function') {
        populateReactionLeaderboardTeamSelect();
    }
    if (leaderboardTeamSelect) leaderboardTeamSelect.value = databaseState.leaderboardTeam || '';

    if (databaseState.view === 'detail' && databaseState.detailUid && typeof showPlayerDetail === 'function') {
        await showPlayerDetail(databaseState.detailUid, {
            returnTab: dbDetailReturnState.tab,
            returnSubtab: dbDetailReturnState.subtab,
            pushHistory: false,
        });
        return;
    }

    if (databaseState.view === 'leaderboard' && typeof loadReactionLeaderboard === 'function') {
        await loadReactionLeaderboard({pushHistory: false});
        return;
    }

    if (databaseState.view === 'candidates' && typeof loadCandidateLists === 'function') {
        if (typeof activateDatabaseView === 'function') {
            activateDatabaseView('candidates');
        }
        await loadCandidateLists({pushHistory: false});
        return;
    }

    if (databaseState.scopeType === 'candidate_list' && databaseState.scopeId && typeof enterCandidateListScope === 'function') {
        await enterCandidateListScope(databaseState.scopeId, {pushHistory: false, query: databaseState.query || ''});
        return;
    }

    if (typeof activateDatabaseView === 'function') {
        activateDatabaseView('list');
    }
    currentDetailPlayer = null;

    if ((databaseState.query || databaseState.batch || (typeof hasActiveAdvancedFilters === 'function' && hasActiveAdvancedFilters())) && typeof searchDatabase === 'function') {
        await searchDatabase(databaseState.query, {pushHistory: false});
        return;
    }

    currentDbPlayers = [];
    if (typeof renderDatabaseSearchPlaceholder === 'function') {
        renderDatabaseSearchPlaceholder('请输入球员姓名或 UID，或打开高级搜索配置筛选条件。');
    } else {
        const dbTableTitle = document.getElementById('dbTableTitle');
        const dbPlayersTable = document.getElementById('dbPlayersTable');
        if (dbTableTitle) {
            dbTableTitle.textContent = '\u7403\u5458\u5e93\u641c\u7d22\u7ed3\u679c';
        }
        if (dbPlayersTable) {
            dbPlayersTable.innerHTML = '<div class="no-data">\u8bf7\u8f93\u5165\u7403\u5458\u59d3\u540d\u6216 UID \u8fdb\u884c\u641c\u7d22</div>';
        }
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
    const initialState = applyInitialUrlState(normalizeHistoryState(history.state, initialIndex));
    appHistoryIndex = initialState.__appHistoryIndex;
    history.replaceState(initialState, '', buildAppHistoryUrl(initialState));
    appHistoryReady = true;
    await restoreAppHistoryState(initialState);
}

async function init() {
    const savedTheme = localStorage.getItem('themeMode');
    isDarkMode = savedTheme === 'dark';
    document.body.classList.toggle('light-mode', !isDarkMode);
    syncThemeToggleState();
    initializeMobileNavigation();
    try {
        const [teamsRes, playersRes, infoRes, adminRes] = await Promise.all([
            fetch('/api/teams'),
            fetch('/api/players'),
            fetch('/api/league/info'),
            fetch('/api/admin/check'),
        ]);
        if (typeof loadAttributeVersionCatalog === 'function') {
            await loadAttributeVersionCatalog({force: true});
        }
        teams = await teamsRes.json();
        allPlayers = await playersRes.json();
        currentPlayers = [...allPlayers];
        leagueInfo = await infoRes.json();
        const adminData = await adminRes.json();
        currentAdminRole = adminData.role || '';
        isAdmin = Boolean(adminData.authenticated && adminData.can_manage_admin);
        canManageSchedule = Boolean(adminData.authenticated && adminData.can_manage_schedule);
        canManageSuspensions = Boolean(adminData.authenticated && adminData.can_manage_suspensions);
        canManageCandidateLists = Boolean(adminData.authenticated && adminData.can_manage_candidate_lists);
        if (typeof syncCoachAuthStatus === 'function') {
            await syncCoachAuthStatus();
        }

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
        } else {
            if (typeof syncAdminTabVisibility === 'function') {
                syncAdminTabVisibility();
            }
            if (typeof syncAdminPanelVisibility === 'function') {
                syncAdminPanelVisibility({focusLogin: false});
            }
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
    if (typeof loadCoaches === 'function') {
        coachesLoaded = false;
        if (document.body.dataset.activeTab === 'coaches') {
            await loadCoaches({force: true});
        }
    }
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
    if (typeof renderCandidateDock === 'function') {
        renderCandidateDock();
    }
    syncMobileNavState();
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

const HEIGO_QQ_GROUPS = ['796068353'];
const HEIGO_QQ_JOIN_URL = 'https://qm.qq.com/q/iJlazr0QSI';

function buildQqGroupCard(groupNumber, index) {
    const label = HEIGO_QQ_GROUPS.length > 1 ? `QQ群 ${index + 1}` : '官方 QQ 群';
    return `
        <div class="join-heigo-group-card">
            <div class="join-heigo-group-main">
                <div class="join-heigo-group-label">${label}</div>
                <div class="join-heigo-group-number">${groupNumber}</div>
            </div>
            <div class="join-heigo-group-actions">
                <a class="btn btn-primary join-heigo-action join-heigo-primary-action" href="${HEIGO_QQ_JOIN_URL}" target="_blank" rel="noopener noreferrer">申请加入</a>
                <button class="btn btn-secondary join-heigo-action" type="button" onclick="copyHeigoGroupNumber('${groupNumber}')">复制群号</button>
            </div>
        </div>
    `;
}

function showJoinHeigoModal() {
    showModal('加入 Heigo', `
        <div class="join-heigo-modal">
            <div class="join-heigo-hero">
                <div class="join-heigo-icon" aria-hidden="true">H</div>
                <div class="join-heigo-copy">
                    <div class="join-heigo-title">Heigo联机FM群</div>
                    <p class="join-heigo-intro">加入历史悠久的FM联机联赛群，与众多教练一起纵横联机。</p>
                </div>
            </div>
            <div class="join-heigo-group-list">
                ${HEIGO_QQ_GROUPS.map(buildQqGroupCard).join('')}
            </div>
        </div>
    `);
}

async function copyHeigoGroupNumber(groupNumber) {
    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(groupNumber);
        } else {
            const input = document.createElement('textarea');
            input.value = groupNumber;
            input.setAttribute('readonly', '');
            input.style.position = 'fixed';
            input.style.left = '-9999px';
            document.body.appendChild(input);
            input.select();
            document.execCommand('copy');
            document.body.removeChild(input);
        }
        showModal('已复制群号', `QQ群号 ${groupNumber} 已复制。`);
    } catch (error) {
        console.error('复制群号失败:', error);
        showModal('复制失败', `请手动复制 QQ 群号：${groupNumber}`);
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
