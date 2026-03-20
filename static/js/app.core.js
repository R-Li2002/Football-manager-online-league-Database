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
var adminEntryUnlocked = false;
var isDarkMode = false;
const ADMIN_ENTRY_QUERY = 'heigomanage';
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
    adminEntryUnlocked: {enumerable: true, get: () => adminEntryUnlocked, set: value => { adminEntryUnlocked = value; }},
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
    normalizeSearchText,
    normalizeSearchTextLoose,
    buildSearchNormalizedKeys,
    formatCompactNationality,
    showModal,
    closeModal,
};
