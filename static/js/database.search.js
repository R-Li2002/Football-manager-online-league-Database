async function searchDatabase(nameOverride = null, options = {}) {
    const shouldSyncHistory = options.pushHistory !== false;
    const historyMode = options.historyMode || 'push';
    currentDatabaseSubtab = 'search';
    syncDatabaseSubtabUI();
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
            returnSubtab: 'search',
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
    if (options.pushHistory !== false && typeof syncAppHistory === 'function') {
        syncAppHistory(options.historyMode || 'push');
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

