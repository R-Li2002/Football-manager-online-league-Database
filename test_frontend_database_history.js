const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const workspaceRoot = __dirname;
const coreCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/app.core.js'), 'utf8');
const databaseCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/app.database.js'), 'utf8');
const databaseSearchCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/database.search.js'), 'utf8');
const appCode = fs.readFileSync(path.join(workspaceRoot, 'static/app.js'), 'utf8');

function createClassList(initialClasses = []) {
    const classes = new Set(initialClasses);
    return {
        add(...tokens) {
            tokens.filter(Boolean).forEach(token => classes.add(token));
        },
        remove(...tokens) {
            tokens.filter(Boolean).forEach(token => classes.delete(token));
        },
        toggle(token, force) {
            if (force === true) {
                classes.add(token);
                return true;
            }
            if (force === false) {
                classes.delete(token);
                return false;
            }
            if (classes.has(token)) {
                classes.delete(token);
                return false;
            }
            classes.add(token);
            return true;
        },
        contains(token) {
            return classes.has(token);
        },
    };
}

function createElement(id = '', initialClasses = []) {
    return {
        id,
        value: '',
        innerHTML: '',
        textContent: '',
        dataset: {},
        hidden: false,
        style: {},
        classList: createClassList(initialClasses),
        appendChild() {},
        removeChild() {},
        addEventListener() {},
        click() {},
        setAttribute(name, value) {
            this.attributes = this.attributes || {};
            this.attributes[name] = String(value);
        },
        getAttribute(name) {
            return this.attributes?.[name] || null;
        },
        contains(target) {
            return target === this;
        },
    };
}

const elements = new Map();
function registerElement(element) {
    elements.set(element.id, element);
    return element;
}

[
    'home', 'overview', 'players', 'database', 'admin',
    'teamSelect', 'playerSearch', 'dbPlayerSearch', 'dbPlayersTable', 'dbTableTitle', 'dbTableMeta', 'dbQueryChips',
    'dbAdvancedSearchToggle', 'dbAdvancedSearchCount', 'dbAdvancedSearchPanel', 'dbAdvancedSearchOverlay',
    'dbReactionMetricSelect', 'dbReactionLimitSelect', 'dbReactionTeamSelect', 'dbReactionLeaderboardTitle', 'dbReactionLeaderboardTable',
    'dbSubtabSearch', 'dbSubtabLeaderboard', 'dbListView', 'dbReactionLeaderboardView', 'dbDetailView',
    'dbAttributeVersionSelect', 'comparisonOverlay', 'themeIcon', 'themeText',
].forEach(id => registerElement(createElement(id)));

elements.get('home').classList.add('tab-content', 'active');
elements.get('overview').classList.add('tab-content');
elements.get('players').classList.add('tab-content');
elements.get('database').classList.add('tab-content');
elements.get('admin').classList.add('tab-content');
elements.get('dbSubtabSearch').classList.add('database-subtab', 'active');
elements.get('dbSubtabLeaderboard').classList.add('database-subtab');
elements.get('dbListView').classList.add('list-view', 'active');
elements.get('dbReactionLeaderboardView').classList.add('list-view');
elements.get('dbDetailView').classList.add('detail-view');
elements.get('dbReactionMetricSelect').value = 'flowers';
elements.get('dbReactionLimitSelect').value = '20';
elements.get('dbReactionTeamSelect').value = '';

const navButtons = ['home', 'overview', 'players', 'database', 'admin'].map(tab => {
    const button = createElement(`nav-${tab}`, ['nav-tab']);
    button.dataset.tab = tab;
    return button;
});

const document = {
    body: {
        dataset: {},
        classList: createClassList([]),
        appendChild() {},
        removeChild() {},
    },
    getElementById(id) {
        return elements.get(id) || null;
    },
    createElement(tagName) {
        return createElement(tagName);
    },
    querySelectorAll(selector) {
        if (selector === '.tab-content') {
            return ['home', 'overview', 'players', 'database', 'admin'].map(id => elements.get(id));
        }
        if (selector === '.nav-tab') {
            return navButtons;
        }
        return [];
    },
    querySelector(selector) {
        const match = selector.match(/\.nav-tab\[data-tab="(.+)"\]/);
        if (match) {
            return navButtons.find(button => button.dataset.tab === match[1]) || null;
        }
        return null;
    },
    addEventListener() {},
};

const history = {
    state: null,
    replaceState(state) {
        this.state = state;
    },
    pushState(state) {
        this.state = state;
    },
    back() {},
};

const fetchPayloads = {
    '/api/teams': [],
    '/api/players': [],
    '/api/league/info': [],
    '/api/admin/check': {authenticated: false},
    '/api/attributes/versions': {available_versions: ['2620'], default_version: '2620'},
};

const context = {
    console,
    document,
    window: {
        document,
        addEventListener() {},
        location: {href: 'http://localhost/'},
        URL: {
            createObjectURL() { return 'blob:test'; },
            revokeObjectURL() {},
        },
    },
    history,
    fetch: async url => ({
        ok: true,
        status: 200,
        json: async () => fetchPayloads[url] || {},
        blob: async () => Buffer.from(''),
    }),
    localStorage: {
        getItem() {
            return '';
        },
        setItem() {},
    },
    renderOverview() {},
    renderTeamsTable() {},
    renderTeamStatSourceDebugView() {},
    populateTeamSelect() {},
    updateStats() {},
    renderPlayers() {},
    syncAdminTabVisibility() {},
    syncAdminPanelVisibility() {},
    renderCompareDock() {},
    overviewMetaExpanded: false,
    currentOverviewSort: {field: '', order: 'desc', type: 'number'},
    currentPlayers: [],
    currentRosterSort: {field: '', order: 'desc', type: 'number'},
    currentSelectedRosterUid: null,
    setTimeout,
    clearTimeout,
};

vm.createContext(context);
vm.runInContext(coreCode, context, {filename: 'app.core.js'});
vm.runInContext(databaseCode, context, {filename: 'app.database.js'});
vm.runInContext(databaseSearchCode, context, {filename: 'database.search.js'});
vm.runInContext(appCode, context, {filename: 'app.js'});

async function flushMicrotasks() {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
}

(async () => {
    await flushMicrotasks();

    context.applyAdvancedDatabaseFiltersState({
        ca: {min: '120'},
        positions: {ST: 15},
    });
    elements.get('dbPlayerSearch').value = '';
    const captured = context.captureDatabaseHistoryState();
    assert.equal(captured.advancedFilters.ca.min, '120');
    assert.equal(captured.advancedFilters.positions.ST, 15);

    let restoredSearch = null;
    context.searchDatabase = async (query, options) => {
        restoredSearch = {
            query,
            options,
            filters: context.captureAdvancedDatabaseFilters(),
        };
    };
    await context.restoreDatabaseHistoryState({
        query: '',
        attributeVersion: '2620',
        advancedFilters: {positions: {ST: 15}, ca: {min: '120'}},
        sort: {field: '', order: 'desc', type: 'number'},
        subtab: 'search',
        leaderboardMetric: 'flowers',
        leaderboardLimit: '20',
        leaderboardTeam: '',
        view: 'list',
        detailUid: null,
        returnTab: 'database',
        returnSubtab: 'search',
    });

    assert.equal(restoredSearch.query, '');
    assert.equal(restoredSearch.options.pushHistory, false);
    assert.equal(restoredSearch.filters.positions.ST, 15);
    assert.equal(restoredSearch.filters.ca.min, '120');
})().catch(error => {
    console.error(error);
    process.exit(1);
});
