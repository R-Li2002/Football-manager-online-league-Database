const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const workspaceRoot = __dirname;
const coreCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/app.core.js'), 'utf8');
const databaseCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/app.database.js'), 'utf8');
const databaseSearchCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/database.search.js'), 'utf8');

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
        style: {display: ''},
        hidden: false,
        classList: createClassList(initialClasses),
        appendChild() {},
        addEventListener() {},
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
    'dbPlayerSearch',
    'dbPlayersTable',
    'dbTableTitle',
    'dbTableMeta',
    'dbQueryChips',
    'dbAdvancedSearchToggle',
    'dbAdvancedSearchCount',
    'dbAdvancedSearchPanel',
    'dbAdvancedSearchOverlay',
    'dbAttributeVersionSelect',
    'playerDetailToolbar',
    'playerDetailContent',
    'dbReactionMetricSelect',
    'dbReactionLimitSelect',
    'dbReactionTeamSelect',
    'dbReactionLeaderboardTitle',
    'dbReactionLeaderboardTable',
    'comparisonOverlay',
].forEach(id => registerElement(createElement(id)));

registerElement(createElement('dbSubtabSearch', ['database-subtab', 'active']));
registerElement(createElement('dbSubtabLeaderboard', ['database-subtab']));
registerElement(createElement('dbListView', ['list-view', 'active']));
registerElement(createElement('dbReactionLeaderboardView', ['list-view']));
registerElement(createElement('dbDetailView', ['detail-view']));

elements.get('dbReactionMetricSelect').value = 'flowers';
elements.get('dbReactionLimitSelect').value = '20';
elements.get('dbReactionTeamSelect').value = '';

const documentListeners = {};
const document = {
    body: {
        dataset: {},
        classList: createClassList([]),
    },
    addEventListener(type, handler) {
        documentListeners[type] = documentListeners[type] || [];
        documentListeners[type].push(handler);
    },
    getElementById(id) {
        return elements.get(id) || null;
    },
    createElement(tagName) {
        return createElement(tagName);
    },
};

let advancedSearchResponse = {
    items: [
        {uid: 1, name: 'Filter One', data_version: '2620', position: 'ST', age: 22, ca: 150, pa: 170, nationality: 'ES', club: 'Real', heigo_club: 'Alpha'},
    ],
    data_version: '2620',
    limit: 200,
    truncated: false,
    applied_filters_summary: ['CA ≥ 120', 'ST ≥ 15'],
};
let advancedSearchBodies = [];

const context = {
    console,
    document,
    window: {document},
    localStorage: {
        getItem() {
            return '';
        },
        setItem() {},
    },
    fetch: async (url, options = {}) => {
        if (url === '/api/attributes/advanced-search') {
            advancedSearchBodies.push(JSON.parse(options.body));
            return {
                ok: true,
                status: 200,
                json: async () => advancedSearchResponse,
            };
        }
        throw new Error(`Unexpected fetch: ${url}`);
    },
    history: {back() {}},
    setTimeout,
    clearTimeout,
};

vm.createContext(context);
vm.runInContext(coreCode, context, {filename: 'app.core.js'});
vm.runInContext(databaseCode, context, {filename: 'app.database.js'});
vm.runInContext(databaseSearchCode, context, {filename: 'database.search.js'});

context.availableAttributeVersions = ['2620', '2630'];
context.currentAttributeVersion = '2620';
context.loadAttributeVersionCatalog = async () => ({available_versions: ['2620', '2630'], default_version: '2620'});
context.refreshAttributeVersionBanner = () => {};
context.syncAppHistory = () => {};
context.showTab = () => {};
context.clearPlayerReactionCooldownTimer = () => {};
context.clearPlayerReactionBounce = () => {};
context.canUseAppHistoryBack = () => false;
context.populateReactionLeaderboardTeamSelect = () => {};

async function flushMicrotasks() {
    await Promise.resolve();
    await Promise.resolve();
}

async function assertAdvancedTriggerReflectsActiveCount() {
    context.applyAdvancedDatabaseFiltersState({
        ca: {min: '120'},
        attributes: {passing: {min: '14'}},
        positions: {ST: 15},
    });
    assert.equal(elements.get('dbAdvancedSearchToggle').classList.contains('is-active'), true);
    assert.equal(elements.get('dbAdvancedSearchCount').hidden, false);
    assert.equal(elements.get('dbAdvancedSearchCount').textContent, '3');
}

async function assertPositionCycleFollowsConfiguredSteps() {
    context.clearAdvancedDatabaseFilters({});
    context.cycleAdvancedPositionFilter('ST');
    assert.equal(context.currentDbAdvancedFilters.positions.ST, 10);
    context.cycleAdvancedPositionFilter('ST');
    assert.equal(context.currentDbAdvancedFilters.positions.ST, 15);
    context.cycleAdvancedPositionFilter('ST');
    assert.equal(context.currentDbAdvancedFilters.positions.ST, 18);
    context.cycleAdvancedPositionFilter('ST');
    assert.equal('ST' in context.currentDbAdvancedFilters.positions, false);
}

async function assertPositionMapHidesInlineScoreBadge() {
    context.applyAdvancedDatabaseFiltersState({positions: {ST: 15, AMC: 18}}, {renderPanel: true});
    context.renderDatabaseAdvancedSearchPanel();
    assert.equal(elements.get('dbAdvancedSearchPanel').innerHTML.includes('advanced-search-position-state'), false);
}

async function assertAdvancedSearchSupportsBlankKeyword() {
    advancedSearchBodies = [];
    context.applyAdvancedDatabaseFiltersState({ca: {min: '120'}, positions: {ST: 15}});
    elements.get('dbPlayerSearch').value = '';
    await context.searchDatabase('', {pushHistory: false});
    await flushMicrotasks();

    assert.equal(advancedSearchBodies.length, 1);
    assert.equal(advancedSearchBodies[0].query, '');
    assert.equal(advancedSearchBodies[0].version, '2620');
    assert.equal(advancedSearchBodies[0].ca.min, 120);
    assert.equal(advancedSearchBodies[0].positions[0].position, 'ST');
    assert.ok(elements.get('dbQueryChips').innerHTML.includes('CA ≥ 120'));
}

async function assertVersionSwitchRerunsAdvancedSearch() {
    advancedSearchBodies = [];
    advancedSearchResponse = {
        ...advancedSearchResponse,
        data_version: '2630',
        applied_filters_summary: ['CA ≥ 120', 'ST ≥ 15'],
    };
    context.applyAdvancedDatabaseFiltersState({ca: {min: '120'}, positions: {ST: 15}});
    elements.get('dbPlayerSearch').value = '';
    await context.handleAttributeVersionChange('2630');
    await flushMicrotasks();

    assert.equal(advancedSearchBodies.length, 1);
    assert.equal(advancedSearchBodies[0].version, '2630');
    assert.equal(context.currentDbSearchMeta.data_version, '2630');
}

async function assertClearAdvancedFiltersResetsState() {
    context.applyAdvancedDatabaseFiltersState({ca: {min: '120'}, positions: {ST: 15}});
    elements.get('dbPlayerSearch').value = '';
    context.clearAdvancedFiltersFromResults();
    assert.equal(context.countActiveAdvancedFilters(), 0);
    assert.equal(elements.get('dbAdvancedSearchCount').hidden, true);
    assert.ok(elements.get('dbPlayersTable').innerHTML.includes('高级搜索配置筛选条件'));
}

(async () => {
    await assertAdvancedTriggerReflectsActiveCount();
    await assertPositionCycleFollowsConfiguredSteps();
    await assertPositionMapHidesInlineScoreBadge();
    await assertAdvancedSearchSupportsBlankKeyword();
    await assertVersionSwitchRerunsAdvancedSearch();
    await assertClearAdvancedFiltersResetsState();
})().catch(error => {
    console.error(error);
    process.exit(1);
});
