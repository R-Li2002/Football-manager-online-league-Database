const APP_STATIC_ASSET_VERSION = (() => {
    try {
        return new URL(document.currentScript?.src || '', window.location.href).searchParams.get('v') || '';
    } catch (error) {
        return '';
    }
})();
const APP_ASSET_LOAD_PROMISES = new Map();
const APP_MODULE_LOAD_PROMISES = new Map();
const APP_MODULE_ASSETS = {
    coaches: ['/static/js/app.coaches.js'],
    overview: ['/static/js/app.coaches.js', '/static/js/app.overview.js'],
    team: ['/static/js/app.coaches.js', '/static/vendor/html-to-image.js', '/static/js/app.players.js', '/static/js/app.team.js'],
    players: ['/static/js/app.coaches.js', '/static/js/app.players.js'],
    competition: ['/static/js/app.coaches.js', '/static/vendor/html-to-image.js', '/static/js/app.admin.js', '/static/js/app.competition.js'],
    database: [
        '/static/vendor/html-to-image.js',
        '/static/js/app.database.js',
        '/static/js/database.search.js',
        '/static/js/database.tactics.js',
        '/static/js/database.compare.js',
    ],
    admin: ['/static/js/app.admin.js'],
};
const APP_MODULE_READY_CHECKS = {
    coaches: () => typeof loadCoaches === 'function',
    overview: () => typeof renderOverview === 'function',
    team: () => typeof renderTeamDetail === 'function',
    players: () => typeof searchPlayers === 'function',
    competition: () => typeof loadCompetitionData === 'function',
    database: () => typeof searchDatabase === 'function' && typeof showPlayerDetail === 'function',
    admin: () => typeof showAdminLoginPanel === 'function',
};
let globalCoachMenuOpen = false;
let teamsLoadPromise = null;
let playersLoadPromise = null;
let leagueInfoLoadPromise = null;
let tabActivationSequence = 0;

function buildVersionedAssetUrl(path) {
    if (!APP_STATIC_ASSET_VERSION) return path;
    const separator = path.includes('?') ? '&' : '?';
    return `${path}${separator}v=${encodeURIComponent(APP_STATIC_ASSET_VERSION)}`;
}

function loadAppScript(path) {
    if (APP_ASSET_LOAD_PROMISES.has(path)) {
        return APP_ASSET_LOAD_PROMISES.get(path);
    }
    const promise = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = buildVersionedAssetUrl(path);
        script.async = false;
        script.dataset.appLazyAsset = path;
        script.addEventListener('load', () => resolve(path), {once: true});
        script.addEventListener('error', () => reject(new Error(`模块资源加载失败: ${path}`)), {once: true});
        document.body.appendChild(script);
    }).catch(error => {
        APP_ASSET_LOAD_PROMISES.delete(path);
        throw error;
    });
    APP_ASSET_LOAD_PROMISES.set(path, promise);
    return promise;
}

function ensureAppModule(moduleName) {
    if (APP_MODULE_READY_CHECKS[moduleName]?.()) {
        return Promise.resolve(moduleName);
    }
    if (APP_MODULE_LOAD_PROMISES.has(moduleName)) {
        return APP_MODULE_LOAD_PROMISES.get(moduleName);
    }
    const assets = APP_MODULE_ASSETS[moduleName] || [];
    const promise = (async () => {
        for (const asset of assets) {
            await loadAppScript(asset);
        }
        return moduleName;
    })().catch(error => {
        APP_MODULE_LOAD_PROMISES.delete(moduleName);
        throw error;
    });
    APP_MODULE_LOAD_PROMISES.set(moduleName, promise);
    return promise;
}

function getGlobalCoachInitials(name) {
    const normalized = String(name || '教练').trim();
    return normalized.slice(0, 2).toUpperCase();
}

function renderGlobalCoachAccount() {
    const host = document.getElementById('globalCoachAccount');
    if (!host) return;
    const account = currentCoachAccount || {authenticated: false};
    if (!account.authenticated) {
        globalCoachMenuOpen = false;
        host.classList.remove('is-open');
        host.innerHTML = '<button class="global-coach-login" type="button" onclick="openGlobalCoachLogin()"><span class="global-coach-login-mark" aria-hidden="true"><svg class="ui-icon" viewBox="0 0 24 24" focusable="false"><circle cx="12" cy="8" r="3.5"/><path d="M5.5 20c.5-4 2.7-6 6.5-6s6 2 6.5 6"/></svg></span><span>教练登录</span></button>';
        if (typeof syncHomeDashboardAccount === 'function') syncHomeDashboardAccount();
        return;
    }
    const avatar = account.avatar_path
        ? `<img src="${escapeHtml(account.avatar_path)}" alt="${escapeHtml(account.nickname || '教练')}头像">`
        : `<span class="global-coach-avatar-fallback">${escapeHtml(getGlobalCoachInitials(account.nickname || account.username))}</span>`;
    const hasWork = Boolean(!account.must_change_password && account.qq_number && (account.can_manage_schedule || account.can_manage_suspensions || account.can_manage_candidate_lists));
    const identityMeta = account.team_name || (account.qq_number ? `QQ ${account.qq_number}` : '教练账号');
    host.classList.toggle('is-open', globalCoachMenuOpen);
    host.innerHTML = `
        <button class="global-coach-trigger" type="button" aria-haspopup="menu" aria-expanded="${globalCoachMenuOpen ? 'true' : 'false'}" onclick="toggleGlobalCoachMenu(event)">
            <span class="global-coach-avatar">${avatar}</span>
            <span class="global-coach-copy"><strong>${escapeHtml(account.nickname || account.username || '教练')}</strong><small>${escapeHtml(identityMeta)}</small></span>
            <span class="global-coach-chevron" aria-hidden="true">⌄</span>
        </button>
        <div class="global-coach-menu" role="menu" ${globalCoachMenuOpen ? '' : 'hidden'}>
            <div class="global-coach-menu-head">
                <span class="global-coach-avatar is-large">${avatar}</span>
                <div><strong>${escapeHtml(account.nickname || account.username || '教练')}</strong><span>${escapeHtml(account.team_name || '未关联球队')}</span>${account.qq_number ? `<small>QQ ${escapeHtml(account.qq_number)}</small>` : '<small>QQ 尚未绑定</small>'}</div>
            </div>
            ${(account.must_change_password || !account.qq_number) ? `<button class="global-coach-menu-alert" type="button" role="menuitem" onclick="openGlobalCoachSecurity()"><span>!</span><div><strong>${account.must_change_password ? '请先修改默认密码' : '请先绑定 QQ 号'}</strong><small>完成登录安全设置后才能使用个人功能</small></div></button>` : ''}
            <div class="global-coach-menu-actions">
                <button type="button" role="menuitem" onclick="openGlobalCoachTeam()"><span aria-hidden="true">⌂</span><div><strong>我的球队</strong><small>${escapeHtml(account.team_name || '查看球队关联')}</small></div></button>
                <button type="button" role="menuitem" onclick="openGlobalCoachProfile()"><span aria-hidden="true">◎</span><div><strong>个人主页</strong><small>资料、头像与荣誉</small></div></button>
                <button type="button" role="menuitem" onclick="openGlobalCoachSecurity()"><span aria-hidden="true">◇</span><div><strong>QQ 与登录安全</strong><small>${account.qq_number ? `已绑定 ${escapeHtml(account.qq_number)}` : '绑定主要登录凭证'}</small></div></button>
                ${hasWork ? '<button type="button" role="menuitem" onclick="openGlobalCoachWorkspace()"><span aria-hidden="true">⚙</span><div><strong>联赛工作台</strong><small>进入已授权工作模块</small></div></button>' : ''}
            </div>
            <button class="global-coach-logout" type="button" role="menuitem" onclick="globalCoachLogout()">退出教练账号</button>
        </div>
    `;
    if (typeof syncHomeDashboardAccount === 'function') syncHomeDashboardAccount();
}

function toggleGlobalCoachMenu(event) {
    event?.stopPropagation();
    globalCoachMenuOpen = !globalCoachMenuOpen;
    renderGlobalCoachAccount();
}

function closeGlobalCoachMenu() {
    if (!globalCoachMenuOpen) return;
    globalCoachMenuOpen = false;
    renderGlobalCoachAccount();
}

async function openGlobalCoachLogin() {
    await ensureAppModule('coaches');
    showCoachLoginPanel();
}

async function ensureGlobalCoachSecurityReady() {
    if (!currentCoachAccount.authenticated) return false;
    if (!currentCoachAccount.must_change_password && currentCoachAccount.qq_number) return true;
    await ensureAppModule('coaches');
    beginCoachSecuritySetup();
    return false;
}

async function openGlobalCoachTeam() {
    closeGlobalCoachMenu();
    if (!await ensureGlobalCoachSecurityReady()) return;
    await Promise.all([ensureAppModule('team'), ensureTeamsLoaded()]);
    const linkedTeam = teams.find(team => (
        (Number(currentCoachAccount.team_id) > 0 && Number(team.id) === Number(currentCoachAccount.team_id))
        || (currentCoachAccount.team_name && team.name === currentCoachAccount.team_name)
    ));
    if (!linkedTeam) {
        showModal('未关联球队', '当前教练账号没有关联到有效球队，请联系管理员检查账号资料。');
        return;
    }
    await openTeamDetail(linkedTeam.name, {historyMode: 'push', smooth: false});
}

async function openGlobalCoachProfile() {
    closeGlobalCoachMenu();
    if (!await ensureGlobalCoachSecurityReady()) return;
    await ensureAppModule('coaches');
    await showTab('coaches', null, {historyMode: 'push'});
    await loadCoaches();
    await openCoachDetail(currentCoachAccount.coach_uid);
}

async function openGlobalCoachSecurity() {
    closeGlobalCoachMenu();
    await ensureAppModule('coaches');
    if (currentCoachAccount.must_change_password || !currentCoachAccount.qq_number) beginCoachSecuritySetup();
    else showCoachQqModal();
}

async function openGlobalCoachWorkspace() {
    closeGlobalCoachMenu();
    if (!await ensureGlobalCoachSecurityReady()) return;
    await showTab('admin', null, {historyMode: 'push'});
}

async function globalCoachLogout() {
    closeGlobalCoachMenu();
    await ensureAppModule('coaches');
    await coachLogout();
}

async function openPlayerAttributeDetail(uid, options = {}) {
    try {
        await ensureAppModule('database');
        if (typeof showPlayerDetail !== 'function') {
            throw new Error('球员详情模块未就绪');
        }
        await showPlayerDetail(uid, options);
    } catch (error) {
        console.error('球员属性页面加载失败:', error);
        showModal('加载失败', '球员属性页面暂时无法加载，请稍后重试。');
    }
}

async function openRosterPlayerAttributeDetail(uid) {
    if (typeof selectRosterPlayer === 'function') {
        selectRosterPlayer(uid);
    }
    await openPlayerAttributeDetail(uid, {
        returnTab: 'players',
        returnSubtab: 'search',
    });
}

async function openCompetitionPlayerAttributeDetail(uid, returnSubtab = 'playerRankings') {
    await openPlayerAttributeDetail(uid, {
        returnTab: 'competition',
        returnSubtab,
    });
}

async function fetchJsonOrThrow(url, options) {
    const response = await fetch(url, options);
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${url}`);
    return response.json();
}

function ensureTeamsLoaded(options = {}) {
    if (teams.length && options.force !== true) return Promise.resolve(teams);
    if (teamsLoadPromise && options.force !== true) return teamsLoadPromise;
    teamsLoadPromise = fetchJsonOrThrow('/api/teams')
        .then(data => {
            teams = Array.isArray(data) ? data : [];
            return teams;
        })
        .finally(() => {
            teamsLoadPromise = null;
        });
    return teamsLoadPromise;
}

function ensurePlayersLoaded(options = {}) {
    if (allPlayers.length && options.force !== true) return Promise.resolve(allPlayers);
    if (playersLoadPromise && options.force !== true) return playersLoadPromise;
    playersLoadPromise = fetchJsonOrThrow('/api/players')
        .then(data => {
            allPlayers = Array.isArray(data) ? data : [];
            currentPlayers = [...allPlayers];
            if (typeof invalidateCompetitionPlayerCaches === 'function') invalidateCompetitionPlayerCaches();
            return allPlayers;
        })
        .finally(() => {
            playersLoadPromise = null;
        });
    return playersLoadPromise;
}

function ensureLeagueInfoLoaded(options = {}) {
    if (leagueInfo.length && options.force !== true) return Promise.resolve(leagueInfo);
    if (leagueInfoLoadPromise && options.force !== true) return leagueInfoLoadPromise;
    leagueInfoLoadPromise = fetchJsonOrThrow('/api/league/info')
        .then(data => {
            leagueInfo = Array.isArray(data) ? data : [];
            return leagueInfo;
        })
        .finally(() => {
            leagueInfoLoadPromise = null;
        });
    return leagueInfoLoadPromise;
}

function syncLightweightAdminTabVisibility() {
    const hasWorkspaceAccess = Boolean(
        workspaceSessionState?.authenticated
        && workspaceSessionState.identity
        && (workspaceSessionState.identity.is_full_admin || (workspaceSessionState.identity.capabilities || []).some(item => item !== 'coach_profile.write_self'))
    );
    document.getElementById('adminTab')?.classList.toggle('hidden-tab', !(isAdmin || adminEntryUnlocked || hasWorkspaceAccess));
    syncMobileNavState({closeMenu: false});
}

async function prepareAppTab(tabName) {
    if (tabName === 'home') return;
    if (tabName === 'overview') {
        await Promise.all([ensureAppModule('overview'), ensureTeamsLoaded(), ensureLeagueInfoLoaded()]);
    } else if (tabName === 'team') {
        await Promise.all([ensureAppModule('team'), ensureTeamsLoaded(), ensureLeagueInfoLoaded()]);
    } else if (tabName === 'players') {
        await Promise.all([ensureAppModule('players'), ensureTeamsLoaded(), ensurePlayersLoaded()]);
    } else if (tabName === 'competition') {
        await Promise.all([ensureAppModule('competition'), ensureTeamsLoaded(), ensurePlayersLoaded()]);
    } else if (tabName === 'coaches') {
        await ensureAppModule('coaches');
    } else if (tabName === 'database') {
        await ensureAppModule('database');
    } else if (tabName === 'admin') {
        if (isAdmin) {
            await Promise.all([
                ensureAppModule('overview'),
                ensureAppModule('players'),
                ensureAppModule('competition'),
                ensureAppModule('coaches'),
                ensureAppModule('database'),
                ensureTeamsLoaded(),
                ensurePlayersLoaded(),
                ensureLeagueInfoLoaded(),
            ]);
        }
    }
    if (isAdmin || tabName === 'admin') {
        await ensureAppModule('admin');
    }
}

const AppModules = {
    home: {onEnter: () => { if (typeof updateHeroBadgeState === 'function') updateHeroBadgeState(); }},
    overview: {onEnter: () => { if (typeof renderOverview === 'function') renderOverview(); }},
    team: {onEnter: () => { if (typeof renderTeamDetail === 'function') renderTeamDetail(); }},
    players: {onEnter: async () => {
        if (typeof populateTeamSelect === 'function') {
            populateTeamSelect();
        }
        if (typeof ensureRosterRendered === 'function') {
            ensureRosterRendered();
        } else if (typeof renderPlayerQueryState === 'function') {
            renderPlayerQueryState();
        }
        if (typeof loadDataStatus === 'function') await loadDataStatus();
        if (typeof renderDataStatusStrip === 'function') renderDataStatusStrip('rosterDataStatus', 'roster', 'all');
    }},
    competition: {onEnter: async () => { if (typeof loadCompetitionData === 'function') await loadCompetitionData(); }},
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
        if (typeof populatePowerRankingTeamSelect === 'function') {
            populatePowerRankingTeamSelect();
        }
        if (typeof renderCompareDock === 'function') renderCompareDock();
        if (typeof renderCandidateDock === 'function') renderCandidateDock();
        if (typeof loadDataStatus === 'function') await loadDataStatus();
        if (typeof renderDataStatusStrip === 'function') renderDataStatusStrip('databaseDataStatus', 'attributes', 'all');
    }},
    admin: {onEnter: async () => {
        if (typeof openWorkspace === 'function') {
            await openWorkspace();
        }
    }},
};

const APP_HISTORY_MARKER = 'heigo-spa';
const APP_TAB_NAMES = new Set(['home', 'overview', 'team', 'players', 'competition', 'coaches', 'database', 'admin']);
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

const MOBILE_PRIMARY_TABS = new Set(['home', 'team', 'competition', 'database']);

function isMobileViewport() {
    return window.matchMedia ? window.matchMedia('(max-width: 780px)').matches : window.innerWidth <= 780;
}

function closeMobileMoreMenu(options = {}) {
    const menu = document.getElementById('mobileMoreMenu');
    const toggle = document.querySelector('[data-mobile-more-toggle]');
    if (menu) {
        menu.hidden = true;
    }
    if (toggle) {
        toggle.setAttribute('aria-expanded', 'false');
        toggle.classList.remove('is-open');
        if (options.restoreFocus === true) toggle.focus();
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
    if (shouldOpen) {
        window.requestAnimationFrame(() => {
            const target = menu.querySelector('.mobile-more-menu-item.active:not(.hidden-tab)')
                || menu.querySelector('.mobile-more-menu-item:not(.hidden-tab)');
            target?.focus();
        });
    } else {
        toggle.focus();
    }
}

function syncMobileNavState(options = {}) {
    const activeTab = getActiveTabName();
    document.querySelectorAll('[data-mobile-tab]').forEach(button => {
        const isActive = button.dataset.mobileTab === activeTab;
        button.classList.toggle('active', isActive);
        if (isActive) button.setAttribute('aria-current', 'page');
        else button.removeAttribute('aria-current');
    });

    const moreToggle = document.querySelector('[data-mobile-more-toggle]');
    if (moreToggle) {
        const representsActivePage = APP_TAB_NAMES.has(activeTab) && !MOBILE_PRIMARY_TABS.has(activeTab);
        moreToggle.classList.toggle('active', representsActivePage);
        if (representsActivePage) moreToggle.setAttribute('aria-current', 'page');
        else moreToggle.removeAttribute('aria-current');
    }

    const mobileAdminTab = document.getElementById('mobileAdminTab');
    if (mobileAdminTab) {
        const hasWorkspaceAccess = Boolean(
            workspaceSessionState?.authenticated
            && workspaceSessionState.identity
            && (workspaceSessionState.identity.is_full_admin || (workspaceSessionState.identity.capabilities || []).some(item => item !== 'coach_profile.write_self'))
        );
        mobileAdminTab.classList.toggle('hidden-tab', !(isAdmin || adminEntryUnlocked || hasWorkspaceAccess));
    }

    if (options.closeMenu !== false) {
        closeMobileMoreMenu();
    }
    const workspaceReturnButton = document.getElementById('workspaceReturnButton');
    if (workspaceReturnButton) {
        const hasWorkspaceAccess = Boolean(
            workspaceSessionState?.authenticated
            && workspaceSessionState.identity
            && (workspaceSessionState.identity.is_full_admin || (workspaceSessionState.identity.capabilities || []).some(item => item !== 'coach_profile.write_self'))
        );
        const showWorkspaceReturn = hasWorkspaceAccess && activeTab !== 'admin';
        workspaceReturnButton.hidden = !showWorkspaceReturn;
        const mobileMoreButton = document.querySelector('[data-mobile-more-toggle]');
        if (mobileMoreButton) mobileMoreButton.hidden = showWorkspaceReturn;
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
            closeMobileMoreMenu({restoreFocus: true});
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
    ['tab', 'team', 'databaseSubtab', 'candidateList', 'q', 'version', 'competitionSubtab', 'level', 'cupPhase', 'cupView', 'round', 'workFilter', 'rankingType'].forEach(key => params.delete(key));

    if (normalized.tab !== 'home') {
        params.set('tab', normalized.tab);
    }
    if (normalized.tab === 'team' && normalized.team?.name) {
        params.set('team', normalized.team.name);
    }
    if (normalized.tab === 'database') {
        const database = normalized.database || {};
        if (database.scopeType === 'candidate_list' && database.scopeId) {
            params.set('candidateList', String(database.scopeId));
        } else if (database.view === 'candidates' || database.subtab === 'candidates') {
            params.set('databaseSubtab', 'candidates');
        } else if (database.view === 'leaderboard' || database.subtab === 'leaderboard') {
            params.set('databaseSubtab', 'leaderboard');
        } else if (database.view === 'power' || database.subtab === 'power') {
            params.set('databaseSubtab', 'power');
        } else if (database.view === 'tactics' || database.subtab === 'tactics') {
            params.set('databaseSubtab', 'tactics');
        }
        if (database.query) {
            params.set('q', database.query);
        }
        if (database.attributeVersion) {
            params.set('version', database.attributeVersion);
        }
    }
    if (normalized.tab === 'competition') {
        const competition = normalized.competition || {};
        if (competition.subtab !== 'standings') params.set('competitionSubtab', competition.subtab);
        if (competition.level !== '超级') params.set('level', competition.level);
        if (competition.cupPhase === 'group') params.set('cupPhase', competition.cupPhase);
        if (competition.cupView === 'results') params.set('cupView', competition.cupView);
        if (competition.round) params.set('round', String(competition.round));
        if (competition.workFilter !== 'all') params.set('workFilter', competition.workFilter);
        if (competition.rankingType !== 'goals') params.set('rankingType', competition.rankingType);
    }

    const query = params.toString();
    return `${url.pathname}${query ? `?${query}` : ''}${url.hash}`;
}

function applyInitialUrlState(rawState) {
    const state = normalizeHistoryState(rawState);
    const params = new URLSearchParams(window.location.search);
    const tabParam = params.get('tab');
    const teamParam = params.get('team');
    const candidateListId = Number(params.get('candidateList'));
    const databaseSubtab = params.get('databaseSubtab');
    const query = params.get('q');
    const version = params.get('version');
    const competitionSubtab = params.get('competitionSubtab');
    const competitionLevel = params.get('level');
    const competitionCupPhase = params.get('cupPhase');
    const competitionCupView = params.get('cupView');
    const competitionRound = Number(params.get('round'));
    const workFilter = params.get('workFilter');
    const rankingType = params.get('rankingType');

    if (tabParam) {
        state.tab = normalizeAppTabName(tabParam);
    }
    if (state.tab === 'team' && teamParam) {
        state.team.name = teamParam;
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
    } else if (state.tab === 'database' && databaseSubtab === 'power') {
        state.database.subtab = 'power';
        state.database.view = 'power';
        state.database.scopeType = 'none';
        state.database.scopeId = null;
    } else if (state.tab === 'database' && databaseSubtab === 'tactics') {
        state.database.subtab = 'tactics';
        state.database.view = 'tactics';
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
    if (state.tab === 'competition') {
        if (['standings', 'schedule', 'playerRankings', 'suspensions'].includes(competitionSubtab)) {
            state.competition.subtab = competitionSubtab;
        }
        if (['超级', '甲级', '乙级', '冠军杯', '联盟杯', '无铭剑杯'].includes(competitionLevel)) {
            state.competition.level = competitionLevel;
        }
        if (['group', 'knockout'].includes(competitionCupPhase)) {
            state.competition.cupPhase = competitionCupPhase;
        }
        if (['groups', 'results'].includes(competitionCupView)) {
            state.competition.cupView = competitionCupView;
        }
        if (Number.isFinite(competitionRound) && competitionRound > 0) {
            state.competition.round = competitionRound;
        }
        if (['all', 'missing_result', 'missing_events', 'invalid'].includes(workFilter)) {
            state.competition.workFilter = workFilter;
        }
        if (['goals', 'assists', 'mvps'].includes(rankingType)) {
            state.competition.rankingType = rankingType;
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
    const isPowerView = document.getElementById('dbPowerRankingView')?.classList.contains('active');
    const isTacticsView = document.getElementById('dbTacticsView')?.classList.contains('active');
    const isCandidateView = document.getElementById('dbCandidateListsView')?.classList.contains('active');
    return {
        query: document.getElementById('dbPlayerSearch')?.value.trim() || '',
        batch: typeof getDatabaseBatchRawValue === 'function'
            ? getDatabaseBatchRawValue()
            : (document.getElementById('dbBatchSearch')?.value || ''),
        attributeVersion: typeof getCurrentAttributeVersion === 'function' ? getCurrentAttributeVersion() : '',
        advancedFilters: typeof captureAdvancedDatabaseFilters === 'function' ? captureAdvancedDatabaseFilters() : {},
        sort: normalizeSortState(currentDbSort, 'number'),
        subtab: currentDatabaseSubtab === 'tactics' ? 'tactics' : currentDatabaseSubtab === 'power' ? 'power' : currentDatabaseSubtab === 'leaderboard' ? 'leaderboard' : currentDatabaseSubtab === 'candidates' ? 'candidates' : 'search',
        scopeType: databaseSearchScope?.type || 'none',
        scopeId: databaseSearchScope?.id || null,
        leaderboardMetric: document.getElementById('dbReactionMetricSelect')?.value || 'flowers',
        leaderboardLimit: document.getElementById('dbReactionLimitSelect')?.value || '20',
        leaderboardTeam: document.getElementById('dbReactionTeamSelect')?.value || '',
        powerShape: document.getElementById('dbPowerShapeSelect')?.value || 'all',
        powerLimit: document.getElementById('dbPowerLimitSelect')?.value || '50',
        powerTeam: document.getElementById('dbPowerTeamSelect')?.value || '',
        view: isDetailView && currentDetailPlayer ? 'detail' : isTacticsView ? 'tactics' : isPowerView ? 'power' : isLeaderboardView ? 'leaderboard' : isCandidateView ? 'candidates' : 'list',
        detailUid: isDetailView && currentDetailPlayer ? Number(currentDetailPlayer.uid) || null : null,
        returnTab: normalizeAppTabName(dbDetailReturnState?.tab || 'database'),
        returnSubtab: dbDetailReturnState?.subtab === 'tactics' ? 'tactics' : dbDetailReturnState?.subtab === 'power' ? 'power' : dbDetailReturnState?.subtab === 'leaderboard' ? 'leaderboard' : dbDetailReturnState?.subtab === 'candidates' ? 'candidates' : 'search',
    };
}

function captureCompetitionHistoryState() {
    const subtab = typeof currentCompetitionSubtab === 'string' ? currentCompetitionSubtab : 'standings';
    const level = typeof currentCompetitionLevel === 'string' ? currentCompetitionLevel : '超级';
    const workFilter = typeof currentCompetitionWorkFilter === 'string' ? currentCompetitionWorkFilter : 'all';
    const rankingType = typeof currentPlayerRankingType === 'string' ? currentPlayerRankingType : 'goals';
    const cupPhase = typeof currentCupPhase === 'string' ? currentCupPhase : 'knockout';
    const cupView = typeof currentCupGroupScheduleView === 'string' ? currentCupGroupScheduleView : 'groups';
    return {
        subtab: ['schedule', 'playerRankings', 'suspensions'].includes(subtab)
            ? subtab
            : 'standings',
        level: ['超级', '甲级', '乙级', '冠军杯', '联盟杯', '无铭剑杯'].includes(level)
            ? level
            : '超级',
        cupPhase: cupPhase === 'group' ? 'group' : 'knockout',
        cupView: cupView === 'results' ? 'results' : 'groups',
        round: Number(document.getElementById('scheduleRoundSelect')?.value || 0) || null,
        workFilter: ['missing_result', 'missing_events', 'invalid'].includes(workFilter)
            ? workFilter
            : 'all',
        rankingType: ['assists', 'mvps'].includes(rankingType) ? rankingType : 'goals',
    };
}

function captureAppHistoryState() {
    return {
        tab: getActiveTabName(),
        team: {
            name: typeof currentTeamDetailName === 'string' ? currentTeamDetailName : '',
        },
        overview: captureOverviewHistoryState(),
        players: capturePlayersHistoryState(),
        competition: captureCompetitionHistoryState(),
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
        team: {
            name: typeof baseState.team?.name === 'string' ? baseState.team.name : '',
        },
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
        competition: {
            subtab: ['schedule', 'playerRankings', 'suspensions'].includes(baseState.competition?.subtab)
                ? baseState.competition.subtab
                : 'standings',
            level: ['超级', '甲级', '乙级', '冠军杯', '联盟杯', '无铭剑杯'].includes(baseState.competition?.level)
                ? baseState.competition.level
                : '超级',
            cupPhase: baseState.competition?.cupPhase === 'group' ? 'group' : 'knockout',
            cupView: baseState.competition?.cupView === 'results' ? 'results' : 'groups',
            round: Number.isFinite(Number(baseState.competition?.round)) && Number(baseState.competition.round) > 0
                ? Number(baseState.competition.round)
                : null,
            workFilter: ['missing_result', 'missing_events', 'invalid'].includes(baseState.competition?.workFilter)
                ? baseState.competition.workFilter
                : 'all',
            rankingType: ['assists', 'mvps'].includes(baseState.competition?.rankingType)
                ? baseState.competition.rankingType
                : 'goals',
        },
        database: {
            query: typeof baseState.database?.query === 'string' ? baseState.database.query : '',
            batch: typeof baseState.database?.batch === 'string' ? baseState.database.batch : '',
            attributeVersion: typeof baseState.database?.attributeVersion === 'string' ? baseState.database.attributeVersion : '',
            advancedFilters: baseState.database?.advancedFilters && typeof baseState.database.advancedFilters === 'object'
                ? baseState.database.advancedFilters
                : {},
            sort: normalizeSortState(baseState.database?.sort, 'number'),
            subtab: baseState.database?.subtab === 'tactics' ? 'tactics' : baseState.database?.subtab === 'power' ? 'power' : baseState.database?.subtab === 'leaderboard' ? 'leaderboard' : baseState.database?.subtab === 'candidates' ? 'candidates' : 'search',
            scopeType: baseState.database?.scopeType === 'candidate_list' ? 'candidate_list' : baseState.database?.scopeType === 'batch' ? 'batch' : 'none',
            scopeId: Number.isFinite(Number(baseState.database?.scopeId)) ? Number(baseState.database.scopeId) : null,
            leaderboardMetric: typeof baseState.database?.leaderboardMetric === 'string' ? baseState.database.leaderboardMetric : 'flowers',
            leaderboardLimit: typeof baseState.database?.leaderboardLimit === 'string' ? baseState.database.leaderboardLimit : '20',
            leaderboardTeam: typeof baseState.database?.leaderboardTeam === 'string' ? baseState.database.leaderboardTeam : '',
            powerShape: typeof baseState.database?.powerShape === 'string' ? baseState.database.powerShape : 'all',
            powerLimit: typeof baseState.database?.powerLimit === 'string' ? baseState.database.powerLimit : '50',
            powerTeam: typeof baseState.database?.powerTeam === 'string' ? baseState.database.powerTeam : '',
            view: baseState.database?.view === 'detail' ? 'detail' : baseState.database?.view === 'tactics' ? 'tactics' : baseState.database?.view === 'power' ? 'power' : baseState.database?.view === 'leaderboard' ? 'leaderboard' : baseState.database?.view === 'candidates' ? 'candidates' : 'list',
            detailUid: Number.isFinite(Number(baseState.database?.detailUid))
                ? Number(baseState.database.detailUid)
                : null,
            returnTab: normalizeAppTabName(baseState.database?.returnTab || 'database'),
            returnSubtab: baseState.database?.returnSubtab === 'tactics' ? 'tactics' : baseState.database?.returnSubtab === 'power' ? 'power' : baseState.database?.returnSubtab === 'leaderboard' ? 'leaderboard' : baseState.database?.returnSubtab === 'candidates' ? 'candidates' : 'search',
        },
    };
}

function getComparableHistoryState(state) {
    const normalized = normalizeHistoryState(state);
    return JSON.stringify({
        tab: normalized.tab,
        team: normalized.team,
        overview: normalized.overview,
        players: normalized.players,
        competition: normalized.competition,
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

async function restoreTeamHistoryState(teamState) {
    if (typeof currentTeamDetailName !== 'undefined') {
        currentTeamDetailName = typeof teamState?.name === 'string' ? teamState.name : '';
    }
}

async function restoreCompetitionHistoryState(competitionState) {
    if (typeof showCompetitionSubtab !== 'function') return;
    currentCompetitionLevel = competitionState.level || '超级';
    currentCupPhase = competitionState.cupPhase === 'group' ? 'group' : 'knockout';
    currentCupGroupScheduleView = competitionState.cupView === 'results' ? 'results' : 'groups';
    currentPlayerRankingType = competitionState.rankingType || 'goals';
    currentCompetitionWorkFilter = competitionState.workFilter || 'all';
    showCompetitionSubtab(competitionState.subtab || 'standings');
    if (competitionState.round) {
        const roundSelect = document.getElementById('scheduleRoundSelect');
        if (roundSelect) roundSelect.value = String(competitionState.round);
    }
    if (currentCompetitionSubtab === 'schedule' && typeof renderScheduleBoard === 'function') {
        renderScheduleBoard();
    } else if (currentCompetitionSubtab === 'playerRankings' && typeof setPlayerRankingType === 'function') {
        setPlayerRankingType(currentPlayerRankingType);
    }
    if (typeof renderCompetitionWorkPanel === 'function') renderCompetitionWorkPanel();
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
    currentDatabaseSubtab = databaseState.subtab === 'tactics' ? 'tactics' : databaseState.subtab === 'power' ? 'power' : databaseState.subtab === 'leaderboard' ? 'leaderboard' : databaseState.subtab === 'candidates' ? 'candidates' : 'search';
    dbDetailReturnState = {
        tab: normalizeAppTabName(databaseState.returnTab || 'database'),
        subtab: databaseState.returnSubtab === 'tactics' ? 'tactics' : databaseState.returnSubtab === 'power' ? 'power' : databaseState.returnSubtab === 'leaderboard' ? 'leaderboard' : databaseState.returnSubtab === 'candidates' ? 'candidates' : 'search',
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
    const powerShapeSelect = document.getElementById('dbPowerShapeSelect');
    const powerLimitSelect = document.getElementById('dbPowerLimitSelect');
    const powerTeamSelect = document.getElementById('dbPowerTeamSelect');
    if (powerShapeSelect) powerShapeSelect.value = databaseState.powerShape || 'all';
    if (powerLimitSelect) powerLimitSelect.value = databaseState.powerLimit || '50';
    if (typeof populatePowerRankingTeamSelect === 'function') populatePowerRankingTeamSelect();
    if (powerTeamSelect) powerTeamSelect.value = databaseState.powerTeam || '';

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

    if (databaseState.view === 'power' && typeof loadPowerRanking === 'function') {
        await loadPowerRanking({pushHistory: false});
        return;
    }

    if (databaseState.view === 'tactics' && typeof loadDatabaseTacticsBoard === 'function') {
        await loadDatabaseTacticsBoard({pushHistory: false});
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
        await prepareAppTab(state.tab);
        if (state.tab === 'overview') {
            await restoreOverviewHistoryState(state.overview);
        } else if (state.tab === 'team') {
            await restoreTeamHistoryState(state.team);
        } else if (state.tab === 'players') {
            await restorePlayersHistoryState(state.players);
        } else if (state.tab === 'database') {
            await restoreDatabaseHistoryState(state.database);
        }
        await showTab(state.tab, null, {syncHistory: false, prepared: true});
        if (state.tab === 'competition') {
            await restoreCompetitionHistoryState(state.competition);
        }
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
    loadSiteVisitStats();
    try {
        const [summary, adminData, workspaceSession, coachAccount] = await Promise.all([
            fetchJsonOrThrow('/api/home/summary'),
            fetchJsonOrThrow('/api/admin/check'),
            fetchJsonOrThrow('/api/workspace/session'),
            fetchJsonOrThrow('/api/coach/check'),
        ]);
        homeSummary = summary || homeSummary;
        defaultAttributeVersionPlayerCount = Number(homeSummary.database_player_count || 0);
        currentAttributeVersion = String(homeSummary.default_attribute_version || '');
        currentAdminRole = adminData.role || '';
        isAdmin = Boolean(adminData.authenticated && adminData.can_manage_admin);
        canManageSchedule = Boolean(adminData.authenticated && adminData.can_manage_schedule);
        canManageSuspensions = Boolean(adminData.authenticated && adminData.can_manage_suspensions);
        canManageCandidateLists = Boolean(adminData.authenticated && adminData.can_manage_candidate_lists);
        workspaceSessionState = workspaceSession || workspaceSessionState;
        currentCoachAccount = coachAccount || {authenticated: false};
        renderGlobalCoachAccount();
        if (!adminData.authenticated && workspaceSessionState.authenticated && workspaceSessionState.identity) {
            const capabilities = new Set(workspaceSessionState.identity.capabilities || []);
            canManageSchedule = capabilities.has('schedule.write');
            canManageSuspensions = capabilities.has('suspensions.write');
            canManageCandidateLists = capabilities.has('candidate_lists.write');
        }
        syncLightweightAdminTabVisibility();
        updateAttributeVersionPlayerCountLabels();
        await initializeAppHistory();
        if (currentCoachAccount.authenticated && (currentCoachAccount.must_change_password || !currentCoachAccount.qq_number)) {
            await ensureAppModule('coaches');
            beginCoachSecuritySetup();
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

document.addEventListener('click', event => {
    if (!event.target.closest('.global-coach-account')) closeGlobalCoachMenu();
});

document.addEventListener('keydown', event => {
    if (event.key === 'Escape') closeGlobalCoachMenu();
});

async function loadSiteVisitStats() {
    const statsElement = document.getElementById('footerVisitStats');
    const totalElement = document.getElementById('footerTotalVisits');
    const todayElement = document.getElementById('footerTodayVisits');
    if (!statsElement || !totalElement || !todayElement) return;

    try {
        const response = await fetch('/api/site-visits', {method: 'POST'});
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const stats = await response.json();
        totalElement.textContent = Number(stats.total_count || 0).toLocaleString('zh-CN');
        todayElement.textContent = Number(stats.today_count || 0).toLocaleString('zh-CN');
        statsElement.hidden = false;
    } catch (error) {
        console.warn('访问统计加载失败:', error);
    }
}

async function refreshTeamDataset() {
    const teamsRes = await fetch('/api/teams');
    teams = await teamsRes.json();
    teamsLoadPromise = null;
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
    playersLoadPromise = null;
    if (typeof invalidateCompetitionPlayerCaches === 'function') invalidateCompetitionPlayerCaches();
    if (typeof markRosterRenderStale === 'function') {
        markRosterRenderStale();
    }
    if (document.body.dataset.activeTab === 'players' && typeof ensureRosterRendered === 'function') {
        ensureRosterRendered();
    }
    updateStats();
}

async function refreshLeagueInfoDataset() {
    const infoRes = await fetch('/api/league/info');
    leagueInfo = await infoRes.json();
    leagueInfoLoadPromise = null;
    renderOverview();
}

async function showTab(tabName, triggerElement = null, options = {}) {
    const normalizedTab = normalizeAppTabName(tabName);
    const activationId = ++tabActivationSequence;
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(el => {
        el.classList.remove('active');
        el.removeAttribute?.('aria-current');
    });
    document.getElementById(normalizedTab).classList.add('active');
    const activeButton = triggerElement || document.querySelector(`.nav-tab[data-tab="${normalizedTab}"]`);
    if (activeButton) {
        activeButton.classList.add('active');
        activeButton.setAttribute?.('aria-current', 'page');
    }
    document.body.dataset.activeTab = normalizedTab;
    syncMobileNavState();
    try {
        if (options.prepared !== true) {
            await prepareAppTab(normalizedTab);
        }
    } catch (error) {
        console.error(`页面模块加载失败: ${normalizedTab}`, error);
        if (activationId === tabActivationSequence) {
            showModal('页面加载失败', '相关功能暂时无法加载，请刷新页面后重试。');
        }
        return;
    }
    if (activationId !== tabActivationSequence || getActiveTabName() !== normalizedTab) return;
    const module = AppModules[normalizedTab];
    if (module && typeof module.onEnter === 'function') {
        await module.onEnter();
    }
    if (typeof renderCompareDock === 'function') {
        renderCompareDock();
    }
    if (typeof renderCandidateDock === 'function') {
        renderCandidateDock();
    }
    if (options.syncHistory !== false) {
        syncAppHistory(options.historyMode || 'push');
    }
}

function populateTeamSelect() {
    const select = document.getElementById('teamSelect');
    if (!select) return;
    const previousValue = select.value;
    select.innerHTML = '<option value="">-- 全部球队 --</option>';
    teams.forEach(team => {
        const option = document.createElement('option');
        option.value = team.name;
        option.textContent = `${team.name} (${team.level})`;
        select.appendChild(option);
    });
    if (teams.some(team => team.name === previousValue)) {
        select.value = previousValue;
    }
}

async function openTeamRoster(teamName, options = {}) {
    await showTab('players', null, {syncHistory: false});
    const teamSelect = document.getElementById('teamSelect');
    const playerSearch = document.getElementById('playerSearch');
    if (teamSelect) teamSelect.value = teamName;
    if (playerSearch) playerSearch.value = '';
    if (typeof searchPlayers === 'function') {
        await searchPlayers({...options, pushHistory: false});
    }
    if (options.pushHistory !== false) {
        syncAppHistory(options.historyMode || 'push');
    }
}

async function openFullLeagueRoster(options = {}) {
    await showTab('players', null, {syncHistory: false});
    const teamSelect = document.getElementById('teamSelect');
    const playerSearch = document.getElementById('playerSearch');
    if (teamSelect) teamSelect.value = '';
    if (playerSearch) playerSearch.value = '';
    if (typeof resetPlayers === 'function') {
        resetPlayers({pushHistory: false});
    }
    window.scrollTo({top: 0, behavior: options.smooth === false ? 'auto' : 'smooth'});
    if (options.pushHistory !== false) {
        syncAppHistory(options.historyMode || 'push');
    }
}

async function viewTeamPlayers(teamName, options = {}) {
    if (typeof openTeamDetail !== 'function') {
        await ensureAppModule('team');
    }
    return openTeamDetail(teamName, options);
}

async function openTeamCenter(options = {}) {
    await Promise.all([ensureAppModule('team'), ensureTeamsLoaded()]);
    currentTeamDetailName = '';
    await showTab('team', options.triggerElement || null, {
        historyMode: options.historyMode || 'push',
    });
    window.scrollTo({top: 0, behavior: options.smooth === false ? 'auto' : 'smooth'});
}

async function openAdminEntry() {
    adminEntryUnlocked = true;
    syncLightweightAdminTabVisibility();
    await showTab('admin', null, {syncHistory: false});
}

function updateStats() {
    const teamCount = document.getElementById('teamCount');
    const playerCount = document.getElementById('playerCount');
    if (teamCount) teamCount.textContent = teams.length || Number(homeSummary.team_count || 0);
    if (playerCount) playerCount.textContent = allPlayers.length || Number(homeSummary.player_count || 0);
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
    const exportButton = document.getElementById('homeRosterExportButton');
    setUiButtonBusy(exportButton, true, '正在整理');
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
        const disposition = response.headers.get('Content-Disposition') || '';
        const serverFilename = disposition.match(/filename="?([^";]+)"?/i)?.[1];
        a.download = serverFilename || `heigo_roster_export_${timestamp}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        showUiToast('联赛名单 Excel 已开始下载', 'success');
    } catch (error) {
        console.error('导出错误:', error);
        showModal('错误', `导出失败：${error.message}`);
    } finally {
        setUiButtonBusy(exportButton, false);
    }
}

init();
