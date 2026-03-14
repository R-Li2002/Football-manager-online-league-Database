const AppModules = {
    home: {onEnter: () => { if (typeof updateHeroBadgeState === 'function') updateHeroBadgeState(); }},
    overview: {onEnter: () => { if (typeof renderOverview === 'function') renderOverview(); }},
    players: {onEnter: () => { if (typeof renderPlayerQueryState === 'function') renderPlayerQueryState(); }},
    database: {onEnter: () => { if (typeof renderCompareDock === 'function') renderCompareDock(); }},
    admin: {onEnter: () => { if (isAdmin && typeof renderOperationsAuditCard === 'function') renderOperationsAuditCard(); }},
};

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

function showTab(tabName, triggerElement = null) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    const activeButton = triggerElement || document.querySelector(`.nav-tab[data-tab="${tabName}"]`);
    if (activeButton) {
        activeButton.classList.add('active');
    }
    document.body.dataset.activeTab = tabName;
    const module = AppModules[tabName];
    if (module && typeof module.onEnter === 'function') {
        module.onEnter();
    }
    if (typeof renderCompareDock === 'function') {
        renderCompareDock();
    }
}

function updateStats() {
    const teamCount = document.getElementById('teamCount');
    const playerCount = document.getElementById('playerCount');
    if (teamCount) teamCount.textContent = teams.length;
    if (playerCount) playerCount.textContent = allPlayers.length;
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
