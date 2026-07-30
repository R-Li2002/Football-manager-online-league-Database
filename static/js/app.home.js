const HOME_PROMOTION_DISMISSED_STORAGE_KEY = 'heigoHomePromotionsDismissed';
const HOME_PROMOTION_ICONS = {
    megaphone: '◖',
    trophy: '♛',
    list: '≡',
    star: '✦',
    whistle: '◉',
    info: 'i',
};
let homePromotions = [];
let homePromotionsLoaded = false;
let homePromotionsLoading = null;

function updateHeroBadgeState() {
    const heroTeamCount = document.getElementById('heroTeamCount');
    const heroPlayerCount = document.getElementById('heroPlayerCount');
    const heroDbPlayerCount = document.getElementById('heroDbPlayerCount');
    const heroModeBadge = document.getElementById('heroModeBadge');
    if (heroTeamCount) {
        heroTeamCount.textContent = teams.length || Number(homeSummary.team_count || 0);
    }
    if (heroPlayerCount) {
        heroPlayerCount.textContent = allPlayers.length || Number(homeSummary.player_count || 0);
    }
    if (heroDbPlayerCount) {
        heroDbPlayerCount.textContent = Number(defaultAttributeVersionPlayerCount || 0).toLocaleString();
    }
    if (heroModeBadge) {
        heroModeBadge.textContent = isAdmin ? '管理员维护已启用' : '公开查询模式';
    }
    loadHomePromotions();
}

function homePromotionStorageGet(key) {
    try {
        return window.localStorage?.getItem(key) || '';
    } catch (error) {
        return '';
    }
}

function homePromotionStorageSet(key, value) {
    try {
        window.localStorage?.setItem(key, value);
    } catch (error) {
        // Home promotions remain usable when storage is unavailable.
    }
}

function getDismissedHomePromotionVersions() {
    try {
        const payload = JSON.parse(homePromotionStorageGet(HOME_PROMOTION_DISMISSED_STORAGE_KEY) || '{}');
        return payload && typeof payload === 'object' ? payload : {};
    } catch (error) {
        return {};
    }
}

function getHomePromotionVersion(promotion) {
    return String(promotion.updated_at || promotion.updatedAt || promotion.id);
}

function getHomePromotionMedia(promotion) {
    if (promotion.image_url) {
        return `<span class="home-promotion-media"><img src="${escapeHtml(promotion.image_url)}" alt=""></span>`;
    }
    return `<span class="home-promotion-media is-symbol" aria-hidden="true">${escapeHtml(HOME_PROMOTION_ICONS[promotion.icon] || HOME_PROMOTION_ICONS.megaphone)}</span>`;
}

function renderHomePromotions() {
    const board = document.getElementById('homePromotionBoard');
    if (!board) return;
    const dismissed = getDismissedHomePromotionVersions();
    const visible = homePromotions.filter(item => dismissed[item.id] !== getHomePromotionVersion(item));
    board.classList.remove('is-loading');
    board.removeAttribute('aria-busy');
    if (!visible.length) {
        board.hidden = true;
        board.innerHTML = '';
        return;
    }
    board.hidden = false;
    board.className = `home-promotion-board${visible.length === 1 ? ' has-single' : ''}`;
    board.innerHTML = `
        <div class="home-promotion-board-head">
            <div><span>HEIGO BROADCAST</span><strong>联赛播报</strong></div>
            <p>重要荣誉、名单与联赛动态</p>
        </div>
        <div class="home-promotion-grid">
            ${visible.map((promotion, index) => `
                <article class="home-promotion-card is-${escapeHtml(promotion.theme || 'violet')} ${index === 0 ? 'is-featured' : ''}">
                    ${getHomePromotionMedia(promotion)}
                    <div class="home-promotion-copy">
                        <span>${escapeHtml(promotion.eyebrow || 'HEIGO Broadcast')}</span>
                        <h2>${escapeHtml(promotion.title || '')}</h2>
                        ${promotion.body ? `<p>${escapeHtml(promotion.body)}</p>` : ''}
                    </div>
                    <div class="home-promotion-actions">
                        ${promotion.action_kind !== 'none' && promotion.action_label ? `<button class="btn home-promotion-action" type="button" onclick="openHomePromotionAction(${Number(promotion.id)})">${escapeHtml(promotion.action_label)}</button>` : ''}
                    </div>
                    ${promotion.is_dismissible ? `<button class="home-promotion-dismiss" type="button" onclick="dismissHomePromotion(${Number(promotion.id)})" aria-label="关闭${escapeHtml(promotion.title || '宣传')}">&times;</button>` : ''}
                </article>
            `).join('')}
        </div>
    `;
}

function dismissHomePromotion(promotionId) {
    const promotion = homePromotions.find(item => Number(item.id) === Number(promotionId));
    if (!promotion) return;
    const dismissed = getDismissedHomePromotionVersions();
    dismissed[promotion.id] = getHomePromotionVersion(promotion);
    homePromotionStorageSet(HOME_PROMOTION_DISMISSED_STORAGE_KEY, JSON.stringify(dismissed));
    renderHomePromotions();
}

async function openHomePromotionAction(promotionId) {
    const promotion = homePromotions.find(item => Number(item.id) === Number(promotionId));
    if (!promotion || !promotion.action_target) return;
    if (promotion.action_kind === 'url') {
        window.location.assign(promotion.action_target);
        return;
    }
    const [tabName, subtab, level] = String(promotion.action_target).split(':');
    if (tabName === 'team' && typeof openTeamCenter === 'function') {
        await openTeamCenter();
        return;
    }
    await showTab(tabName || 'home', null, {syncHistory: false});
    if (tabName === 'database' && subtab && typeof showDatabaseSubtab === 'function') showDatabaseSubtab(subtab);
    if (tabName === 'competition' && subtab && typeof showCompetitionSubtab === 'function') showCompetitionSubtab(subtab);
    if (level && typeof setCompetitionLevel === 'function') setCompetitionLevel(level);
    if (typeof syncAppHistory === 'function') syncAppHistory('push');
}

async function loadHomePromotions(options = {}) {
    if (homePromotionsLoaded && options.force !== true) {
        renderHomePromotions();
        return homePromotions;
    }
    if (homePromotionsLoading) return homePromotionsLoading;
    homePromotionsLoading = (async () => {
        try {
            const response = await fetch('/api/home-promotions');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            homePromotions = await response.json();
            homePromotionsLoaded = true;
            renderHomePromotions();
            return homePromotions;
        } catch (error) {
            console.warn('主页宣传加载失败:', error);
            const board = document.getElementById('homePromotionBoard');
            if (board) board.hidden = true;
            return [];
        } finally {
            homePromotionsLoading = null;
        }
    })();
    return homePromotionsLoading;
}

const loadHomeChampionPromotions = loadHomePromotions;

function clearHeroSearchResults() {
    const container = document.getElementById('heroSearchResults');
    if (container) {
        container.innerHTML = '';
    }
}

function heroJsString(value) {
    return escapeHtml(JSON.stringify(String(value ?? '')));
}

function buildHeroSearchHaystack(values) {
    return values
        .map(value => [
            normalizeSearchText(value || ''),
            normalizeSearchTextLoose(value || ''),
            String(value || '').toLowerCase(),
        ])
        .flat()
        .filter(Boolean)
        .join(' ');
}

function heroMatchesQuery(values, query) {
    const queryKeys = buildSearchNormalizedKeys(query);
    const needles = [
        ...queryKeys.strictKeys,
        ...queryKeys.looseKeys,
        String(query || '').toLowerCase(),
    ].filter(Boolean);
    if (!needles.length) return false;
    const haystack = buildHeroSearchHaystack(values);
    return needles.some(needle => haystack.includes(needle));
}

function getHeroLocalSearchGroups(query, options = {}) {
    const leaguePlayers = Array.isArray(options.leaguePlayers) ? options.leaguePlayers : allPlayers;
    const teamMatches = (teams || [])
        .filter(team => heroMatchesQuery([team.name, team.manager, team.level], query))
        .slice(0, 5);
    const leaguePlayerMatches = (leaguePlayers || [])
        .filter(player => heroMatchesQuery([player.name, player.uid, player.team_name, player.position, player.nationality], query))
        .slice(0, 5);
    const coachMatches = ((window.coachesData && Array.isArray(window.coachesData.coaches)) ? window.coachesData.coaches : [])
        .filter(coach => heroMatchesQuery([coach.nickname, coach.team_name, coach.level, coach.title], query))
        .slice(0, 5);
    return {teamMatches, leaguePlayerMatches, coachMatches};
}

function isExactDatabaseMatch(player, query) {
    const queryKeys = buildSearchNormalizedKeys(query);
    const playerKeys = buildSearchNormalizedKeys(player.name || '');
    const allQueryKeys = [...queryKeys.strictKeys, ...queryKeys.looseKeys];
    const playerKeySet = new Set([...playerKeys.strictKeys, ...playerKeys.looseKeys]);
    if (!allQueryKeys.length) return false;
    return allQueryKeys.some(key => playerKeySet.has(key));
}

function renderHeroResultGroup(title, subtitle, itemsHtml, count, actionHtml = '') {
    if (!count) return '';
    return `
        <section class="home-result-group">
            <div class="home-result-group-head">
                <div>
                    <span>${escapeHtml(title)}</span>
                    <em>${escapeHtml(subtitle)}</em>
                </div>
                ${actionHtml}
            </div>
            <div class="home-results-list">${itemsHtml}</div>
        </section>
    `;
}

function renderHeroSearchResults(query, players, localGroups = getHeroLocalSearchGroups(query)) {
    const container = document.getElementById('heroSearchResults');
    if (!container) return;
    const databasePreview = players.slice(0, 6);
    const databaseMoreCount = Math.max(0, players.length - databasePreview.length);
    const teamMatches = localGroups.teamMatches || [];
    const leaguePlayerMatches = localGroups.leaguePlayerMatches || [];
    const coachMatches = localGroups.coachMatches || [];
    const totalLocalCount = teamMatches.length + leaguePlayerMatches.length + coachMatches.length;
    if (!players.length && !totalLocalCount) {
        container.innerHTML = `<div class="home-search-empty">没有找到和 “${escapeHtml(query)}” 相关的球队、球员或教练。</div>`;
        return;
    }
    container.innerHTML = `
        <div class="home-results-card surface-card">
            <div class="home-results-head">
                <div>
                    <span class="panel-kicker">Search Results</span>
                    <h3>找到 ${players.length + totalLocalCount} 条相关结果</h3>
                </div>
            </div>
            ${renderHeroResultGroup('球队', `${teamMatches.length} 条联赛球队`, teamMatches.map(team => `
                <button class="home-result-item home-result-team" onclick="viewTeamPlayers(${heroJsString(team.name || '')})">
                    <span class="home-result-main">
                        <strong>${escapeHtml(team.name || '-')}</strong>
                        <span>${escapeHtml(team.level || '-')} · 主教练 ${escapeHtml(team.manager || '-')}</span>
                    </span>
                    <span class="home-result-meta">联赛球队</span>
                </button>
            `).join(''), teamMatches.length)}
            ${renderHeroResultGroup('联赛球员', `${leaguePlayerMatches.length} 条当前名单`, leaguePlayerMatches.map(player => `
                <button class="home-result-item home-result-league-player" onclick="openDatabaseDetailFromHero(${Number(player.uid)})">
                    <span class="home-result-main">
                        <strong>${escapeHtml(player.name || '-')}</strong>
                        <span>${escapeHtml(player.position || '-')} · ${escapeHtml(String(player.age ?? '-'))} 岁 · ${escapeHtml(player.team_name || '-')}</span>
                    </span>
                    <span class="home-result-meta">球队中心</span>
                </button>
            `).join(''), leaguePlayerMatches.length)}
            ${renderHeroResultGroup('教练', `${coachMatches.length} 条教练主页`, coachMatches.map(coach => `
                <button class="home-result-item home-result-coach" onclick="openCoachProfileByName(${heroJsString(coach.nickname || '')})">
                    <span class="home-result-main">
                        <strong>${escapeHtml(coach.nickname || '-')}</strong>
                        <span>${escapeHtml(coach.team_name || '-')} · ${escapeHtml(coach.level || '-')}</span>
                    </span>
                    <span class="home-result-meta">教练主页</span>
                </button>
            `).join(''), coachMatches.length)}
            ${renderHeroResultGroup(
                '球员库',
                `${players.length} 条全库结果`,
                databasePreview.map(player => `
                    <button class="home-result-item" onclick="openDatabaseDetailFromHero(${player.uid}, {version: '${escapeHtml(player.data_version)}'})">
                        <span class="home-result-main">
                            <strong>${escapeHtml(player.name)}</strong>
                            <span>${escapeHtml(player.position || '-')} · ${escapeHtml(String(player.age ?? '-'))} 岁</span>
                        </span>
                        <span class="home-result-meta">${escapeHtml(player.heigo_club || '-')}</span>
                    </button>
                `).join(''),
                players.length,
                `<button class="btn btn-secondary home-result-group-action" onclick="openDatabaseResultsFromHero(decodeURIComponent('${encodeURIComponent(query)}'))">查看全部</button>`
            )}
            ${databaseMoreCount > 0 ? `<div class="home-search-more">球员库还有 ${databaseMoreCount} 条结果未展开。</div>` : ''}
        </div>
    `;
}

async function runHeroSearch(options = {}) {
    const heroSearch = document.getElementById('heroPlayerSearch');
    const query = heroSearch ? heroSearch.value.trim() : '';
    const shouldSyncHistory = options.pushHistory !== false;
    const historyMode = options.historyMode || 'push';

    if (!query) {
        clearHeroSearchResults();
        if (heroSearch) heroSearch.focus();
        return;
    }

    if (isAdminEntryQuery(query)) {
        clearHeroSearchResults();
        if (heroSearch) {
            heroSearch.value = '';
        }
        if (typeof openAdminEntry === 'function') {
            await openAdminEntry();
        } else {
            showAdminLoginPanel({reveal: true, focusLogin: false});
            showTab('admin', null, {syncHistory: false});
        }
        if (shouldSyncHistory && typeof syncAppHistory === 'function') {
            syncAppHistory(historyMode);
        }
        return;
    }

    const resultContainer = document.getElementById('heroSearchResults');
    if (resultContainer) {
        resultContainer.innerHTML = '<div class="home-search-empty">搜索中...</div>';
    }

    if (/^\d+$/.test(query)) {
        await openDatabaseDetailFromHero(query);
        return;
    }

    let leaguePlayers = [];
    try {
        const [, playerMatches] = await Promise.all([
            typeof ensureTeamsLoaded === 'function' ? ensureTeamsLoaded() : Promise.resolve(teams),
            fetchJsonOrThrow(`/api/players/search/${encodeURIComponent(query)}`),
            typeof ensureAppModule === 'function'
                ? ensureAppModule('coaches').then(() => ensureCoachesDataLoaded())
                : Promise.resolve(),
        ]);
        leaguePlayers = Array.isArray(playerMatches) ? playerMatches : [];
    } catch (error) {
        console.warn('首页搜索加载联赛数据失败:', error);
        if (typeof ensureCoachesDataLoaded === 'function') {
            try {
            await ensureCoachesDataLoaded();
            } catch (coachError) {
                console.warn('首页搜索加载教练数据失败:', coachError);
            }
        }
    }
    const localGroups = getHeroLocalSearchGroups(query, {leaguePlayers});
    const results = await fetchDatabaseSearchResults(query);
    const exactMatches = results.filter(player => isExactDatabaseMatch(player, query));
    const localMatchCount = localGroups.teamMatches.length + localGroups.leaguePlayerMatches.length + localGroups.coachMatches.length;
    if (exactMatches.length === 1 && !localMatchCount) {
        await openDatabaseDetailFromHero(exactMatches[0].uid, {version: exactMatches[0].data_version});
        return;
    }

    renderHeroSearchResults(query, results, localGroups);
}

async function openDatabaseDetailFromHero(uid, options = {}) {
    clearHeroSearchResults();
    await showTab('database', null, {syncHistory: false});
    if (typeof showPlayerDetail === 'function') {
        await showPlayerDetail(uid, {returnTab: 'home', ...options});
    }
}

async function openDatabaseResultsFromHero(query = '', options = {}) {
    const shouldSyncHistory = options.pushHistory !== false;
    const historyMode = options.historyMode || 'push';
    await showTab('database', null, {syncHistory: false});
    if (typeof activateDatabaseView === 'function') {
        activateDatabaseView('list');
    }
    const dbSearch = document.getElementById('dbPlayerSearch');
    if (dbSearch) {
        dbSearch.value = query;
    }
    if (query) {
        await searchDatabase(query, {pushHistory: shouldSyncHistory, historyMode});
        return;
    }
    if (shouldSyncHistory && typeof syncAppHistory === 'function') {
        syncAppHistory(historyMode);
    }
}

async function openAdvancedDatabaseSearchFromHero(options = {}) {
    const heroSearch = document.getElementById('heroPlayerSearch');
    const query = heroSearch ? heroSearch.value.trim() : '';
    const shouldSyncHistory = options.pushHistory !== false;
    const historyMode = options.historyMode || 'push';
    await showTab('database', null, {syncHistory: false});
    if (typeof activateDatabaseView === 'function') {
        activateDatabaseView('list');
    }
    if (typeof showDatabaseSubtab === 'function') {
        showDatabaseSubtab('search');
    }
    const dbSearch = document.getElementById('dbPlayerSearch');
    if (dbSearch) {
        dbSearch.value = query;
    }
    if (typeof toggleAdvancedSearchPanel === 'function') {
        await loadAttributeVersionCatalog();
        toggleAdvancedSearchPanel(true);
    }
    if (shouldSyncHistory && typeof syncAppHistory === 'function') {
        syncAppHistory(historyMode);
    }
}

async function goToTeamDirectory(options = {}) {
    await showTab('overview', null, {
        syncHistory: options.pushHistory !== false,
        historyMode: options.historyMode || 'push',
    });
    if (options.scroll === false) {
        return;
    }
    window.setTimeout(() => {
        document.getElementById('teamsTable')?.scrollIntoView({behavior: 'smooth', block: 'start'});
    }, 60);
}

document.getElementById('heroPlayerSearch')?.addEventListener('keypress', e => {
    if (e.key === 'Enter') runHeroSearch();
});
