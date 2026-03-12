function updateHeroBadgeState() {
    const heroTeamCount = document.getElementById('heroTeamCount');
    const heroPlayerCount = document.getElementById('heroPlayerCount');
    const heroModeBadge = document.getElementById('heroModeBadge');
    if (heroTeamCount) {
        heroTeamCount.textContent = teams.length;
    }
    if (heroPlayerCount) {
        heroPlayerCount.textContent = allPlayers.length;
    }
    if (heroModeBadge) {
        heroModeBadge.textContent = isAdmin ? '管理员维护已启用' : '公开查询模式';
    }
}

function clearHeroSearchResults() {
    const container = document.getElementById('heroSearchResults');
    if (container) {
        container.innerHTML = '';
    }
}

function isExactDatabaseMatch(player, query) {
    const normalizedQuery = String(query || '').trim().toLowerCase();
    if (!normalizedQuery) return false;
    return String(player.name || '').trim().toLowerCase() === normalizedQuery;
}

function renderHeroSearchResults(query, players) {
    const container = document.getElementById('heroSearchResults');
    if (!container) return;
    if (!players.length) {
        container.innerHTML = `<div class="home-search-empty">没有找到和 “${escapeHtml(query)}” 相关的球员。</div>`;
        return;
    }
    const preview = players.slice(0, 6);
    const moreCount = Math.max(0, players.length - preview.length);
    container.innerHTML = `
        <div class="home-results-card surface-card">
            <div class="home-results-head">
                <div>
                    <span class="panel-kicker">Fuzzy Matches</span>
                    <h3>找到 ${players.length} 条相关结果</h3>
                </div>
                <button class="btn btn-secondary" onclick="openDatabaseResultsFromHero(decodeURIComponent('${encodeURIComponent(query)}'))">查看全部结果</button>
            </div>
            <div class="home-results-list">
                ${preview.map(player => `
                    <button class="home-result-item" onclick="openDatabaseDetailFromHero(${player.uid})">
                        <span class="home-result-main">
                            <strong>${escapeHtml(player.name)}</strong>
                            <span>${escapeHtml(player.position || '-')} · ${escapeHtml(String(player.age ?? '-'))} 岁</span>
                        </span>
                        <span class="home-result-meta">${escapeHtml(player.heigo_club || '-')}</span>
                    </button>
                `).join('')}
            </div>
            ${moreCount > 0 ? `<div class="home-search-more">还有 ${moreCount} 条结果未展开。</div>` : ''}
        </div>
    `;
}

async function runHeroSearch() {
    const heroSearch = document.getElementById('heroPlayerSearch');
    const query = heroSearch ? heroSearch.value.trim() : '';
    const resultContainer = document.getElementById('heroSearchResults');

    if (!query) {
        clearHeroSearchResults();
        if (heroSearch) heroSearch.focus();
        return;
    }

    if (resultContainer) {
        resultContainer.innerHTML = '<div class="home-search-empty">搜索中...</div>';
    }

    if (/^\d+$/.test(query)) {
        await openDatabaseDetailFromHero(query);
        return;
    }

    const results = await fetchDatabaseSearchResults(query);
    const exactMatches = results.filter(player => isExactDatabaseMatch(player, query));
    if (exactMatches.length === 1) {
        await openDatabaseDetailFromHero(exactMatches[0].uid);
        return;
    }

    renderHeroSearchResults(query, results);
}

async function openDatabaseDetailFromHero(uid) {
    clearHeroSearchResults();
    await showPlayerDetail(uid, {returnTab: 'home'});
}

async function openDatabaseResultsFromHero(query = '') {
    showTab('database');
    document.getElementById('dbDetailView').classList.remove('active');
    document.getElementById('dbListView').classList.add('active');
    const detailToolbar = document.getElementById('playerDetailToolbar');
    if (detailToolbar) detailToolbar.innerHTML = '';
    const dbSearch = document.getElementById('dbPlayerSearch');
    if (dbSearch) {
        dbSearch.value = query;
    }
    if (query) {
        await searchDatabase(query);
    }
}

function goToTeamDirectory() {
    showTab('overview');
    window.setTimeout(() => {
        document.getElementById('teamsTable')?.scrollIntoView({behavior: 'smooth', block: 'start'});
    }, 60);
}

document.getElementById('heroPlayerSearch')?.addEventListener('keypress', e => {
    if (e.key === 'Enter') runHeroSearch();
});