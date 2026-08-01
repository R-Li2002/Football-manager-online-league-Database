var teams = [];
var allPlayers = [];
var leagueInfo = [];
var currentPlayers = [];
var currentDbPlayers = [];
var lastFormalImportSummary = null;
var lastSchemaBootstrapStatus = null;
var recentOperationAudits = [];
var currentOperationAuditCategory = '';
var availableAttributeVersions = [];
var currentAttributeVersion = '';
var defaultAttributeVersionPlayerCount = 0;
var isAdmin = false;
var currentAdminRole = '';
var canManageSchedule = false;
var canManageCupStandings = false;
var canManageRankings = false;
var canManageSuspensions = false;
var canManageCandidateLists = false;
var adminEntryUnlocked = false;
var isDarkMode = false;
const ADMIN_ENTRY_QUERY = 'heigomanage';
var currentDetailPlayer = null;
var currentGrowthPreviewStep = 0;
var currentSelectedRosterUid = null;
var currentRosterSort = {field: '', order: 'desc'};
var currentDatabaseSubtab = 'search';
var dbDetailReturnState = {tab: 'database'};
var playerCompareSlots = [null, null, null, null];
var comparisonModalOpen = false;
var currentDetailMobileSection = 'overview';
var currentDbAdvancedFilters = null;
var currentDbSearchMeta = {
    mode: 'basic',
    query: '',
    truncated: false,
    limit: 200,
    applied_filters_summary: [],
    data_version: '',
    batch_scope_count: 0,
    batch_unmatched_count: 0,
    scope_type: 'none',
    scope_label: '',
};
var databaseSearchScope = {
    type: 'none',
    id: null,
    name: '',
    dataVersion: '',
    uids: [],
    players: [],
    missingUids: [],
    raw: '',
    unmatched: [],
};
var candidateLists = [];
var adminCandidateLists = [];
var currentCandidateListId = null;
var activeCandidateList = null;
var activeCandidateListPlayers = [];
var candidateDockExpanded = false;
var candidateDockBusy = false;
var currentCoachAccount = {authenticated: false};
var workspaceSessionState = {authenticated: false, identity: null};
var homeSummary = {
    team_count: 0,
    player_count: 0,
    database_player_count: 0,
    default_attribute_version: '',
};
var currentOverviewSort = {field: '', order: '', type: 'number'};
var overviewMetaExpanded = false;
var currentDbSort = {field: '', order: '', type: 'number'};
var dataStatusData = {generated_at: null, items: []};
var dataStatusLoadPromise = null;
var dataStatusLoadError = '';

window.AppState = window.AppState || {};
Object.defineProperties(window.AppState, {
    teams: {enumerable: true, get: () => teams, set: value => { teams = value; }},
    allPlayers: {enumerable: true, get: () => allPlayers, set: value => { allPlayers = value; }},
    leagueInfo: {enumerable: true, get: () => leagueInfo, set: value => { leagueInfo = value; }},
    currentPlayers: {enumerable: true, get: () => currentPlayers, set: value => { currentPlayers = value; }},
    currentDbPlayers: {enumerable: true, get: () => currentDbPlayers, set: value => { currentDbPlayers = value; }},
    lastFormalImportSummary: {enumerable: true, get: () => lastFormalImportSummary, set: value => { lastFormalImportSummary = value; }},
    lastSchemaBootstrapStatus: {enumerable: true, get: () => lastSchemaBootstrapStatus, set: value => { lastSchemaBootstrapStatus = value; }},
    recentOperationAudits: {enumerable: true, get: () => recentOperationAudits, set: value => { recentOperationAudits = value; }},
    currentOperationAuditCategory: {enumerable: true, get: () => currentOperationAuditCategory, set: value => { currentOperationAuditCategory = value; }},
    availableAttributeVersions: {enumerable: true, get: () => availableAttributeVersions, set: value => { availableAttributeVersions = value; }},
    currentAttributeVersion: {enumerable: true, get: () => currentAttributeVersion, set: value => { currentAttributeVersion = value; }},
    defaultAttributeVersionPlayerCount: {enumerable: true, get: () => defaultAttributeVersionPlayerCount, set: value => { defaultAttributeVersionPlayerCount = value; }},
    isAdmin: {enumerable: true, get: () => isAdmin, set: value => { isAdmin = value; }},
    currentAdminRole: {enumerable: true, get: () => currentAdminRole, set: value => { currentAdminRole = value; }},
    canManageSchedule: {enumerable: true, get: () => canManageSchedule, set: value => { canManageSchedule = value; }},
    canManageCupStandings: {enumerable: true, get: () => canManageCupStandings, set: value => { canManageCupStandings = value; }},
    canManageRankings: {enumerable: true, get: () => canManageRankings, set: value => { canManageRankings = value; }},
    canManageSuspensions: {enumerable: true, get: () => canManageSuspensions, set: value => { canManageSuspensions = value; }},
    canManageCandidateLists: {enumerable: true, get: () => canManageCandidateLists, set: value => { canManageCandidateLists = value; }},
    adminEntryUnlocked: {enumerable: true, get: () => adminEntryUnlocked, set: value => { adminEntryUnlocked = value; }},
    isDarkMode: {enumerable: true, get: () => isDarkMode, set: value => { isDarkMode = value; }},
    currentDetailPlayer: {enumerable: true, get: () => currentDetailPlayer, set: value => { currentDetailPlayer = value; }},
    currentGrowthPreviewStep: {enumerable: true, get: () => currentGrowthPreviewStep, set: value => { currentGrowthPreviewStep = value; }},
    currentSelectedRosterUid: {enumerable: true, get: () => currentSelectedRosterUid, set: value => { currentSelectedRosterUid = value; }},
    currentRosterSort: {enumerable: true, get: () => currentRosterSort, set: value => { currentRosterSort = value; }},
    currentDatabaseSubtab: {enumerable: true, get: () => currentDatabaseSubtab, set: value => { currentDatabaseSubtab = value; }},
    dbDetailReturnState: {enumerable: true, get: () => dbDetailReturnState, set: value => { dbDetailReturnState = value; }},
    playerCompareSlots: {enumerable: true, get: () => playerCompareSlots, set: value => { playerCompareSlots = value; }},
    comparisonModalOpen: {enumerable: true, get: () => comparisonModalOpen, set: value => { comparisonModalOpen = value; }},
    currentDetailMobileSection: {enumerable: true, get: () => currentDetailMobileSection, set: value => { currentDetailMobileSection = value; }},
    currentDbAdvancedFilters: {enumerable: true, get: () => currentDbAdvancedFilters, set: value => { currentDbAdvancedFilters = value; }},
    currentDbSearchMeta: {enumerable: true, get: () => currentDbSearchMeta, set: value => { currentDbSearchMeta = value; }},
    databaseSearchScope: {enumerable: true, get: () => databaseSearchScope, set: value => { databaseSearchScope = value; }},
    candidateLists: {enumerable: true, get: () => candidateLists, set: value => { candidateLists = value; }},
    adminCandidateLists: {enumerable: true, get: () => adminCandidateLists, set: value => { adminCandidateLists = value; }},
    currentCandidateListId: {enumerable: true, get: () => currentCandidateListId, set: value => { currentCandidateListId = value; }},
    activeCandidateList: {enumerable: true, get: () => activeCandidateList, set: value => { activeCandidateList = value; }},
    activeCandidateListPlayers: {enumerable: true, get: () => activeCandidateListPlayers, set: value => { activeCandidateListPlayers = value; }},
    candidateDockExpanded: {enumerable: true, get: () => candidateDockExpanded, set: value => { candidateDockExpanded = value; }},
    candidateDockBusy: {enumerable: true, get: () => candidateDockBusy, set: value => { candidateDockBusy = value; }},
    homeSummary: {enumerable: true, get: () => homeSummary, set: value => { homeSummary = value; }},
    currentCoachAccount: {enumerable: true, get: () => currentCoachAccount, set: value => { currentCoachAccount = value; }},
    workspaceSessionState: {enumerable: true, get: () => workspaceSessionState, set: value => { workspaceSessionState = value; }},
});

function syncThemeToggleState() {
    const themeIcon = document.getElementById('themeIcon');
    const themeText = document.getElementById('themeText');
    if (!themeIcon || !themeText) return;
    themeIcon.classList.toggle('is-dark-mode', isDarkMode);
    if (isDarkMode) {
        themeText.textContent = '切换白天';
    } else {
        themeText.textContent = '切换夜间';
    }
}

function dataStatusIconSvg(status) {
    const paths = {
        normal: '<path d="M5 12.5 9.2 16.5 19 6.5"/>',
        pending: '<path d="M12 7v5l3 2"/><circle cx="12" cy="12" r="8.5"/>',
        stale: '<path d="M4.5 12a7.5 7.5 0 1 0 2.2-5.3L4.5 9"/><path d="M4.5 4.5V9H9"/>',
        error: '<path d="M12 8v5"/><path d="M12 16.5h.01"/><path d="M10.2 4.7 3.7 16a2 2 0 0 0 1.7 3h13.2a2 2 0 0 0 1.7-3L13.8 4.7a2 2 0 0 0-3.6 0Z"/>',
        unknown: '<circle cx="12" cy="12" r="8.5"/><path d="M9.8 9.5a2.3 2.3 0 1 1 3.2 2.1c-.7.3-1 .8-1 1.5"/><path d="M12 16.5h.01"/>',
    };
    return `<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${paths[status] || paths.unknown}</svg>`;
}

function uiStateIconSvg(tone = 'info') {
    const paths = {
        success: '<path d="M5 12.5 9.2 16.5 19 6.5"/><circle cx="12" cy="12" r="9"/>',
        warning: '<path d="M12 8v5M12 16.5h.01"/><path d="M10.2 4.7 3.7 16a2 2 0 0 0 1.7 3h13.2a2 2 0 0 0 1.7-3L13.8 4.7a2 2 0 0 0-3.6 0Z"/>',
        danger: '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6m0-6-6 6"/>',
        empty: '<path d="M4 8.5h16v10H4zM8 8.5V6h8v2.5M9 13h6"/>',
        loading: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3 2"/>',
        info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    };
    return `<svg class="ui-icon" viewBox="0 0 24 24" focusable="false" aria-hidden="true">${paths[tone] || paths.info}</svg>`;
}

function uiIconSvg(name, className = 'ui-icon') {
    const paths = {
        close: '<path d="m7 7 10 10M17 7 7 17"/>',
        'arrow-right': '<path d="M5 12h14m-5-5 5 5-5 5"/>',
        'arrow-left': '<path d="M19 12H5m5-5-5 5 5 5"/>',
        download: '<path d="M12 4v11m0 0 4-4m-4 4-4-4M5 19h14"/>',
        return: '<path d="m9 7-5 5 5 5M5 12h9a5 5 0 0 1 5 5v2"/>',
        check: '<path d="M5 12.5 9.2 16.5 19 6.5"/>',
        minus: '<path d="M5 12h14"/>',
        'chevron-down': '<path d="m7 10 5 5 5-5"/>',
        alert: '<path d="M12 8v5M12 16.5h.01"/><path d="M10.2 4.7 3.7 16a2 2 0 0 0 1.7 3h13.2a2 2 0 0 0 1.7-3L13.8 4.7a2 2 0 0 0-3.6 0Z"/>',
    };
    return `<svg class="${escapeHtml(className)}" viewBox="0 0 24 24" focusable="false" aria-hidden="true">${paths[name] || paths.alert}</svg>`;
}

function renderUiState(options = {}) {
    const allowedTones = new Set(['success', 'warning', 'danger', 'empty', 'loading', 'info']);
    const tone = allowedTones.has(options.tone) ? options.tone : 'info';
    const title = escapeHtml(options.title || (tone === 'empty' ? '暂无数据' : '状态提示'));
    const message = options.message ? `<p>${escapeHtml(options.message)}</p>` : '';
    const action = options.actionLabel && options.actionOnclick
        ? `<button class="btn ${escapeHtml(options.actionClass || 'btn-secondary')} ui-state-action" type="button" onclick="${escapeHtml(options.actionOnclick)}">${escapeHtml(options.actionLabel)}</button>`
        : '';
    const role = tone === 'danger' ? 'alert' : 'status';
    return `<div class="ui-state-panel is-${tone}${options.compact ? ' is-compact' : ''}" role="${role}" aria-live="${tone === 'danger' ? 'assertive' : 'polite'}"><span class="ui-state-icon">${uiStateIconSvg(tone)}</span><div class="ui-state-copy"><strong>${title}</strong>${message}</div>${action}</div>`;
}

let uiToastTimer = null;

function showUiToast(message, tone = 'success', options = {}) {
    const allowedTones = new Set(['success', 'warning', 'danger', 'info']);
    const normalizedTone = allowedTones.has(tone) ? tone : 'info';
    let toast = document.getElementById('uiToast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'uiToast';
        toast.className = 'ui-toast';
        document.body.appendChild(toast);
    }
    toast.className = `ui-toast is-${normalizedTone}`;
    toast.setAttribute('role', normalizedTone === 'danger' ? 'alert' : 'status');
    toast.setAttribute('aria-live', normalizedTone === 'danger' ? 'assertive' : 'polite');
    toast.innerHTML = `<span class="ui-toast-icon">${uiStateIconSvg(normalizedTone)}</span><span>${escapeHtml(message || '')}</span>`;
    window.clearTimeout(uiToastTimer);
    requestAnimationFrame(() => toast.classList.add('is-visible'));
    uiToastTimer = window.setTimeout(() => toast.classList.remove('is-visible'), Number(options.duration || 3200));
    return toast;
}

function setUiButtonBusy(buttonOrId, busy, label = '处理中...') {
    const button = typeof buttonOrId === 'string' ? document.getElementById(buttonOrId) : buttonOrId;
    if (!button) return;
    if (busy) {
        if (!button.dataset.uiOriginalHtml) button.dataset.uiOriginalHtml = button.innerHTML;
        button.disabled = true;
        button.setAttribute('aria-busy', 'true');
        button.innerHTML = `<span class="ui-button-spinner" aria-hidden="true"></span><span>${escapeHtml(label)}</span>`;
        return;
    }
    button.disabled = false;
    button.removeAttribute('aria-busy');
    if (button.dataset.uiOriginalHtml) {
        button.innerHTML = button.dataset.uiOriginalHtml;
        delete button.dataset.uiOriginalHtml;
    }
}

let uiFieldIdSeed = 0;

function setUiFieldError(inputOrId, message = '') {
    const input = typeof inputOrId === 'string' ? document.getElementById(inputOrId) : inputOrId;
    if (!input) return;
    if (!input.id) input.id = `uiField${++uiFieldIdSeed}`;
    const errorId = input.dataset.uiErrorId || `${input.id}Error`;
    input.dataset.uiErrorId = errorId;
    let error = document.getElementById(errorId);
    if (!error) {
        error = document.createElement('small');
        error.id = errorId;
        error.className = 'ui-field-error';
        input.insertAdjacentElement('afterend', error);
    }
    const describedBy = new Set(String(input.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean));
    describedBy.add(errorId);
    input.setAttribute('aria-describedby', [...describedBy].join(' '));
    if (message) {
        input.setAttribute('aria-invalid', 'true');
        error.textContent = message;
        error.hidden = false;
    } else {
        input.removeAttribute('aria-invalid');
        error.textContent = '';
        error.hidden = true;
    }
}

function setUiInlineFeedback(containerOrId, message = '', tone = 'info') {
    const container = typeof containerOrId === 'string' ? document.getElementById(containerOrId) : containerOrId;
    if (!container) return;
    if (!message) {
        container.hidden = true;
        container.innerHTML = '';
        return;
    }
    const normalizedTone = ['success', 'warning', 'danger', 'info'].includes(tone) ? tone : 'info';
    container.hidden = false;
    container.className = `ui-inline-feedback is-${normalizedTone}`;
    container.setAttribute('role', normalizedTone === 'danger' ? 'alert' : 'status');
    container.setAttribute('aria-live', normalizedTone === 'danger' ? 'assertive' : 'polite');
    container.innerHTML = `<span>${uiStateIconSvg(normalizedTone)}</span><span>${escapeHtml(message)}</span>`;
}

function dataStatusJsString(value) {
    return escapeHtml(JSON.stringify(String(value ?? '')));
}

function getDataStatusItem(key, scope = 'all') {
    return (dataStatusData.items || []).find(item => item.key === key && String(item.scope || 'all') === String(scope || 'all')) || null;
}

function formatDataStatusTime(value) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleString('zh-CN', {month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit'});
}

function dataStatusMeta(item) {
    const parts = [];
    if (Number(item.updated_round || 0) > 0) parts.push(`更新至第 ${Number(item.updated_round)} 轮`);
    if (Number(item.issue_count || 0) > 0) parts.push(`${Number(item.issue_count)} 项待处理`);
    if (item.data_version) parts.push(`版本 ${item.data_version}`);
    const updateTime = formatDataStatusTime(item.updated_at);
    if (updateTime) parts.push(`${updateTime} 更新`);
    return parts;
}

function renderDataStatusStrip(containerId, key, scope = 'all') {
    const container = document.getElementById(containerId);
    if (!container) return;
    if (dataStatusLoadError) {
        container.hidden = false;
        container.innerHTML = `<button class="data-status-strip is-unknown" type="button" onclick="loadDataStatus({force:true})" aria-label="数据状态读取失败，点击重试"><span class="data-status-icon">${dataStatusIconSvg('unknown')}</span><span class="data-status-state">读取失败</span><span class="data-status-copy"><strong>状态暂不可用</strong><small>点击重新读取，不影响当前页面数据</small></span><span class="data-status-action">重试</span></button>`;
        return;
    }
    const item = getDataStatusItem(key, scope);
    if (!item) {
        container.hidden = true;
        container.innerHTML = '';
        return;
    }
    const meta = dataStatusMeta(item);
    const ariaLabel = `${item.scope !== 'all' ? `${item.scope}` : ''}${item.label}，${item.status_label}，${item.message}`;
    container.hidden = false;
    container.innerHTML = `
        <button class="data-status-strip is-${escapeHtml(item.status || 'unknown')}" type="button" onclick="openDataStatusItem(${dataStatusJsString(item.key)}, ${dataStatusJsString(item.scope || 'all')})" aria-label="${escapeHtml(ariaLabel)}">
            <span class="data-status-icon">${dataStatusIconSvg(item.status)}</span>
            <span class="data-status-state">${escapeHtml(item.status_label || '状态未知')}</span>
            <span class="data-status-copy"><strong>${escapeHtml(item.message || item.label)}</strong>${meta.length ? `<small>${meta.map(value => escapeHtml(value)).join('<i>·</i>')}</small>` : ''}</span>
            <span class="data-status-action">查看</span>
        </button>
    `;
}

function refreshVisibleDataStatus() {
    renderDataStatusStrip('rosterDataStatus', 'roster', 'all');
    renderDataStatusStrip('databaseDataStatus', 'attributes', 'all');
    if (typeof renderCompetitionDataStatus === 'function') renderCompetitionDataStatus();
}

async function loadDataStatus(options = {}) {
    if ((dataStatusData.items || []).length && options.force !== true) {
        refreshVisibleDataStatus();
        return dataStatusData;
    }
    if (dataStatusLoadPromise && options.force !== true) return dataStatusLoadPromise;
    dataStatusLoadError = '';
    dataStatusLoadPromise = fetch('/api/data-status')
        .then(async response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            dataStatusData = await response.json();
            return dataStatusData;
        })
        .catch(error => {
            dataStatusLoadError = error?.message || '数据状态读取失败';
            return dataStatusData;
        })
        .finally(() => {
            dataStatusLoadPromise = null;
            refreshVisibleDataStatus();
        });
    return dataStatusLoadPromise;
}

async function openDataStatusItem(key, scope = 'all') {
    const item = getDataStatusItem(key, scope);
    if (!item?.target_tab) return;
    await showTab(item.target_tab, null, {syncHistory: false});
    if (item.target_tab === 'competition' && typeof showCompetitionSubtab === 'function') {
        if (item.target_level) currentCompetitionLevel = item.target_level;
        showCompetitionSubtab(item.target_subtab || 'standings');
        if (item.target_level && typeof setCompetitionLevel === 'function') setCompetitionLevel(item.target_level);
    } else if (item.target_tab === 'database' && typeof showDatabaseSubtab === 'function') {
        showDatabaseSubtab(item.target_subtab || 'search');
    }
    if (typeof syncAppHistory === 'function') syncAppHistory('push');
}

function isAdminEntryQuery(value) {
    return String(value || '').trim().toLowerCase() === ADMIN_ENTRY_QUERY;
}

function normalizeAttributeVersion(version) {
    const normalized = String(version || '').trim();
    return normalized || '';
}

function getCurrentAttributeVersion() {
    return normalizeAttributeVersion(currentAttributeVersion);
}

function setCurrentAttributeVersion(version, options = {}) {
    const normalized = normalizeAttributeVersion(version);
    const fallbackVersion = availableAttributeVersions[0] || normalized;
    currentAttributeVersion = availableAttributeVersions.includes(normalized) ? normalized : fallbackVersion;
    return currentAttributeVersion;
}

function updateAttributeVersionPlayerCountLabels() {
    const text = defaultAttributeVersionPlayerCount
        ? Number(defaultAttributeVersionPlayerCount).toLocaleString()
        : '-';
    const heroDbPlayerCount = document.getElementById('heroDbPlayerCount');
    const dbPlayerSearchCount = document.getElementById('dbPlayerSearchCount');
    if (heroDbPlayerCount) {
        heroDbPlayerCount.textContent = text;
    }
    if (dbPlayerSearchCount) {
        dbPlayerSearchCount.textContent = text;
    }
}

async function loadAttributeVersionCatalog(options = {}) {
    if (availableAttributeVersions.length && options.force !== true) {
        updateAttributeVersionPlayerCountLabels();
        return {
            available_versions: [...availableAttributeVersions],
            default_version: getCurrentAttributeVersion() || availableAttributeVersions[0] || '',
            default_version_player_count: defaultAttributeVersionPlayerCount,
        };
    }

    const response = await fetch('/api/attributes/versions');
    const payload = await response.json();
    availableAttributeVersions = Array.isArray(payload.available_versions) ? payload.available_versions : [];
    defaultAttributeVersionPlayerCount = Number(payload.default_version_player_count || 0);
    const activeVersion = normalizeAttributeVersion(currentAttributeVersion);
    setCurrentAttributeVersion(activeVersion || payload.default_version, {persist: false});
    updateAttributeVersionPlayerCountLabels();
    return payload;
}

function buildAttributeVersionedPath(path, version) {
    const normalizedVersion = normalizeAttributeVersion(version);
    if (!normalizedVersion) return path;
    const separator = path.includes('?') ? '&' : '?';
    return `${path}${separator}version=${encodeURIComponent(normalizedVersion)}`;
}

async function fetchDatabaseSearchResults(name, options = {}) {
    const version = normalizeAttributeVersion(options.version || getCurrentAttributeVersion());
    const res = await fetch(buildAttributeVersionedPath(`/api/attributes/search/${encodeURIComponent(name)}`, version));
    return await res.json();
}

async function fetchDatabaseAdvancedSearchResults(payload) {
    const response = await fetch('/api/attributes/advanced-search', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    });
    let data = null;
    try {
        data = await response.json();
    } catch (error) {
        data = null;
    }
    if (!response.ok) {
        throw new Error(data?.detail || data?.message || `HTTP ${response.status}`);
    }
    return data;
}

function toggleTheme() {
    isDarkMode = !isDarkMode;
    document.body.classList.toggle('light-mode', !isDarkMode);
    localStorage.setItem('themeMode', isDarkMode ? 'dark' : 'light');
    updateThemeStyles();
}

function updateThemeStyles() {
    document.body.classList.toggle('light-mode', !isDarkMode);
    syncThemeToggleState();
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function renderLeagueLevelSignature(level, options = {}) {
    const config = {
        '超级': {className: 'level-super', character: '超', english: 'SUPER'},
        '甲级': {className: 'level-a', character: '甲', english: 'FIRST'},
        '乙级': {className: 'level-b', character: '乙', english: 'SECOND'},
    }[level] || {className: '', character: '?', english: 'LEAGUE'};
    const safeLevel = escapeHtml(level || '未知');
    const compactClass = options.compact ? ' is-compact' : '';
    const copy = options.compact ? '' : `<span class="league-level-copy"><strong>${safeLevel}</strong><small>${config.english}</small></span>`;
    return `<span class="league-level-signature ${config.className}${compactClass}" title="${safeLevel}联赛"${options.compact ? ` aria-label="${safeLevel}联赛"` : ''}><span class="league-level-mark" aria-hidden="true">${config.character}</span>${copy}</span>`;
}

function renderLeagueLevelBadge(level) {
    return renderLeagueLevelSignature(level);
}

function renderLeagueTierSet() {
    return `<span class="league-tier-set" aria-label="超级、甲级、乙级联赛">${['超级', '甲级', '乙级'].map(level => renderLeagueLevelSignature(level, {compact: true})).join('')}</span>`;
}

function htmlJsString(value) {
    return escapeHtml(JSON.stringify(String(value ?? '')));
}

const NATIONALITY_SHORT_NAME_MAP = {
    'Bosnia and Herzegovina': 'Bosnia',
    'Central African Republic': 'CAR',
    'Cape Verde Islands': 'Cape Verde',
    'Czechia': 'Czech Rep.',
    'Democratic Republic of Congo': 'DR Congo',
    'Dominican Republic': 'D. Republic',
    'Equatorial Guinea': 'Eq. Guinea',
    'Guinea-Bissau': 'Guinea-B.',
    'North Macedonia': 'Macedonia',
    'Northern Ireland': 'N. Ireland',
    'Pays Basque': 'Basque',
    'Republic of Ireland': 'Ireland',
    'Saint Kitts and Nevis': 'St Kitts',
    'South Korea': 'Korea',
    'South Sudan': 'S. Sudan',
    'United States': 'USA',
};

const BASE_SEARCH_CHAR_REPLACEMENTS = {
    'ß': 'ss',
    'Æ': 'ae',
    'æ': 'ae',
    'Œ': 'oe',
    'œ': 'oe',
    'Ø': 'o',
    'ø': 'o',
    'Ł': 'l',
    'ł': 'l',
    'Đ': 'd',
    'đ': 'd',
    'Ð': 'd',
    'ð': 'd',
    'Þ': 'th',
    'þ': 'th',
    'Ħ': 'h',
    'ħ': 'h',
    'ı': 'i',
    'Ĳ': 'ij',
    'ĳ': 'ij',
    'Ə': 'e',
    'ə': 'e',
    'Α': 'a',
    'α': 'a',
    'Β': 'b',
    'β': 'b',
    'Γ': 'g',
    'γ': 'g',
    'Δ': 'd',
    'δ': 'd',
    'Ε': 'e',
    'ε': 'e',
    'Ζ': 'z',
    'ζ': 'z',
    'Η': 'i',
    'η': 'i',
    'Θ': 'th',
    'θ': 'th',
    'Ι': 'i',
    'ι': 'i',
    'Κ': 'k',
    'κ': 'k',
    'Λ': 'l',
    'λ': 'l',
    'Μ': 'm',
    'μ': 'm',
    'Ν': 'n',
    'ν': 'n',
    'Ξ': 'x',
    'ξ': 'x',
    'Ο': 'o',
    'ο': 'o',
    'Π': 'p',
    'π': 'p',
    'Ρ': 'r',
    'ρ': 'r',
    'Σ': 's',
    'σ': 's',
    'ς': 's',
    'Τ': 't',
    'τ': 't',
    'Υ': 'y',
    'υ': 'y',
    'Φ': 'f',
    'φ': 'f',
    'Χ': 'ch',
    'χ': 'ch',
    'Ψ': 'ps',
    'ψ': 'ps',
    'Ω': 'o',
    'ω': 'o',
};

const LOOSE_SEARCH_PRE_REPLACEMENTS = {
    'Ä': 'ae',
    'ä': 'ae',
    'Ö': 'oe',
    'ö': 'oe',
    'Ü': 'ue',
    'ü': 'ue',
};

const LOOSE_DIGRAPH_COLLAPSE_REPLACEMENTS = [
    ['ae', 'a'],
    ['oe', 'o'],
    ['ue', 'u'],
];

const SEARCH_SEPARATOR_RE = /[\s'’`.\-_/]+/g;

function clampCompactText(text, maxLength) {
    const normalized = String(text || '').trim();
    if (!normalized) return '';
    if (normalized.length <= maxLength) return normalized;
    if (maxLength <= 1) return normalized.slice(0, maxLength);
    return `${normalized.slice(0, maxLength - 1).trimEnd()}…`;
}

function shortenNationalityToken(token) {
    const normalized = String(token || '').trim();
    if (!normalized) return '';
    return NATIONALITY_SHORT_NAME_MAP[normalized] || normalized;
}

function formatCompactNationality(value, options = {}) {
    const raw = String(value || '').trim();
    if (!raw) return '-';

    const maxLength = Math.max(8, Number(options.maxLength) || 16);
    const parts = raw
        .split(',')
        .map(shortenNationalityToken)
        .filter(Boolean);

    if (!parts.length) return '-';
    return clampCompactText(parts[0], maxLength);
}

function applySearchReplacementMap(value, replacements) {
    if (!replacements) return value;
    return Array.from(value, character => replacements[character] ?? character).join('');
}

function normalizeSearchTextInternal(value, options = {}) {
    const raw = String(value ?? '');
    if (!raw.trim()) return '';

    let text = raw.normalize('NFKC');
    if (options.preReplacements) {
        text = applySearchReplacementMap(text, options.preReplacements);
    }
    text = text.normalize('NFKD');
    if (options.charReplacements) {
        text = applySearchReplacementMap(text, options.charReplacements);
    }
    text = text
        .replace(/[\u0300-\u036f]/g, '')
        .normalize('NFKC')
        .toLowerCase()
        .replace(SEARCH_SEPARATOR_RE, '')
        .trim();
    return text;
}

function normalizeSearchText(value) {
    return normalizeSearchTextInternal(value, {charReplacements: BASE_SEARCH_CHAR_REPLACEMENTS});
}

function normalizeSearchTextLoose(value) {
    return normalizeSearchTextInternal(value, {
        preReplacements: LOOSE_SEARCH_PRE_REPLACEMENTS,
        charReplacements: BASE_SEARCH_CHAR_REPLACEMENTS,
    });
}

function collapseLooseSearchText(value) {
    let collapsed = String(value || '');
    for (const [source, target] of LOOSE_DIGRAPH_COLLAPSE_REPLACEMENTS) {
        collapsed = collapsed.replaceAll(source, target);
    }
    return collapsed;
}

function buildSearchNormalizedKeys(value) {
    const strictKeys = [];
    const looseKeys = [];

    const baseKey = normalizeSearchText(value);
    const looseKey = normalizeSearchTextLoose(value);
    const collapsedLooseKey = collapseLooseSearchText(looseKey);

    for (const key of [baseKey, collapsedLooseKey]) {
        if (key && !strictKeys.includes(key)) {
            strictKeys.push(key);
        }
    }

    if (looseKey && !looseKeys.includes(looseKey)) {
        looseKeys.push(looseKey);
    }

    return {strictKeys, looseKeys};
}

let resultModalReturnFocus = null;

function handleResultModalKeydown(event) {
    const modal = document.getElementById('resultModal');
    if (!modal?.classList.contains('active')) return;
    if (event.key === 'Escape') {
        event.preventDefault();
        closeModal();
        return;
    }
    if (event.key !== 'Tab') return;
    const focusable = [...modal.querySelectorAll('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])')]
        .filter(element => !element.hidden && element.getClientRects().length);
    if (!focusable.length) {
        event.preventDefault();
        modal.querySelector('.modal-content')?.focus();
        return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
    }
}

function showModal(title, body, options = {}) {
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalBody').innerHTML = body;
    const modal = document.getElementById('resultModal');
    resultModalReturnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    modal.classList.toggle('is-locked', options.locked === true);
    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
    modal.removeEventListener('keydown', handleResultModalKeydown);
    modal.addEventListener('keydown', handleResultModalKeydown);
    requestAnimationFrame(() => {
        const focusTarget = modal.querySelector('[autofocus], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), button:not(:disabled), a[href]') || modal.querySelector('.modal-content');
        focusTarget?.focus();
    });
}

function closeModal(options = {}) {
    const modal = document.getElementById('resultModal');
    if (modal.classList.contains('is-locked') && options.force !== true) return;
    modal.classList.remove('active', 'is-locked');
    modal.setAttribute('aria-hidden', 'true');
    const returnFocus = resultModalReturnFocus;
    resultModalReturnFocus = null;
    if (returnFocus?.isConnected) requestAnimationFrame(() => returnFocus.focus());
}

window.AppCore = {
    fetchDatabaseSearchResults,
    fetchDatabaseAdvancedSearchResults,
    loadAttributeVersionCatalog,
    getCurrentAttributeVersion,
    setCurrentAttributeVersion,
    buildAttributeVersionedPath,
    toggleTheme,
    updateThemeStyles,
    syncThemeToggleState,
    escapeHtml,
    normalizeSearchText,
    normalizeSearchTextLoose,
    buildSearchNormalizedKeys,
    formatCompactNationality,
    showModal,
    closeModal,
    renderUiState,
    showUiToast,
    setUiButtonBusy,
    setUiFieldError,
    setUiInlineFeedback,
    uiIconSvg,
};
