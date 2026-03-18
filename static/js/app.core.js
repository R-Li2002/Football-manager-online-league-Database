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
var currentAttributeVersion = localStorage.getItem('attributeDataVersion') || '';
var isAdmin = false;
var isDarkMode = false;
var currentDetailPlayer = null;
var currentGrowthPreviewStep = 0;
var currentSelectedRosterUid = null;
var currentRosterSort = {field: '', order: 'desc'};
var dbDetailReturnState = {tab: 'database'};
var playerCompareSlots = [null, null];
var comparisonModalOpen = false;
var currentDetailMobileSection = 'overview';

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
    isAdmin: {enumerable: true, get: () => isAdmin, set: value => { isAdmin = value; }},
    isDarkMode: {enumerable: true, get: () => isDarkMode, set: value => { isDarkMode = value; }},
    currentDetailPlayer: {enumerable: true, get: () => currentDetailPlayer, set: value => { currentDetailPlayer = value; }},
    currentGrowthPreviewStep: {enumerable: true, get: () => currentGrowthPreviewStep, set: value => { currentGrowthPreviewStep = value; }},
    currentSelectedRosterUid: {enumerable: true, get: () => currentSelectedRosterUid, set: value => { currentSelectedRosterUid = value; }},
    currentRosterSort: {enumerable: true, get: () => currentRosterSort, set: value => { currentRosterSort = value; }},
    dbDetailReturnState: {enumerable: true, get: () => dbDetailReturnState, set: value => { dbDetailReturnState = value; }},
    playerCompareSlots: {enumerable: true, get: () => playerCompareSlots, set: value => { playerCompareSlots = value; }},
    comparisonModalOpen: {enumerable: true, get: () => comparisonModalOpen, set: value => { comparisonModalOpen = value; }},
    currentDetailMobileSection: {enumerable: true, get: () => currentDetailMobileSection, set: value => { currentDetailMobileSection = value; }},
});

function syncThemeToggleState() {
    const themeIcon = document.getElementById('themeIcon');
    const themeText = document.getElementById('themeText');
    if (!themeIcon || !themeText) return;
    if (isDarkMode) {
        themeIcon.textContent = '☀';
        themeText.textContent = '切换白天';
    } else {
        themeIcon.textContent = '🌙';
        themeText.textContent = '切换夜间';
    }
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
    if (options.persist !== false) {
        localStorage.setItem('attributeDataVersion', currentAttributeVersion || '');
    }
    return currentAttributeVersion;
}

async function loadAttributeVersionCatalog(options = {}) {
    if (availableAttributeVersions.length && options.force !== true) {
        return {
            available_versions: [...availableAttributeVersions],
            default_version: getCurrentAttributeVersion() || availableAttributeVersions[0] || '',
        };
    }

    const response = await fetch('/api/attributes/versions');
    const payload = await response.json();
    availableAttributeVersions = Array.isArray(payload.available_versions) ? payload.available_versions : [];
    const savedVersion = normalizeAttributeVersion(localStorage.getItem('attributeDataVersion'));
    setCurrentAttributeVersion(savedVersion || payload.default_version, {persist: true});
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

function showModal(title, body) {
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalBody').innerHTML = body;
    document.getElementById('resultModal').classList.add('active');
}

function closeModal() {
    document.getElementById('resultModal').classList.remove('active');
}

window.AppCore = {
    fetchDatabaseSearchResults,
    loadAttributeVersionCatalog,
    getCurrentAttributeVersion,
    setCurrentAttributeVersion,
    buildAttributeVersionedPath,
    toggleTheme,
    updateThemeStyles,
    syncThemeToggleState,
    escapeHtml,
    showModal,
    closeModal,
};
