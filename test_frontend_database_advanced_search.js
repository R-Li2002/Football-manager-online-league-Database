const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const workspaceRoot = __dirname;
const coreCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/app.core.js'), 'utf8');
const databaseCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/app.database.js'), 'utf8');
const databaseSearchCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/database.search.js'), 'utf8');
const databaseCss = fs.readFileSync(path.join(workspaceRoot, 'static/css/pages/database.css'), 'utf8');

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
    querySelector() {
        return null;
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

async function assertPositionClickCyclesWithoutPanelRerender() {
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

async function assertPositionMapUsesDirectTouchFriendlyCycle() {
    context.applyAdvancedDatabaseFiltersState({positions: {ST: 15, AMC: 18}}, {renderPanel: true});
    context.renderDatabaseAdvancedSearchPanel();
    const markup = elements.get('dbAdvancedSearchPanel').innerHTML;
    assert.equal((databaseSearchCode.match(/function buildAdvancedSearchPositionMap/g) || []).length, 1);
    assert.equal(markup.includes('database-position-score-options'), false);
    assert.ok(markup.includes("onclick=\"cycleAdvancedPositionFilter('ST')\""));
    assert.ok(markup.includes('advanced-search-position-state'));
    assert.ok(markup.includes('15+'));
    assert.equal(markup.includes('pitch-marker-tooltip'), false);
    assert.ok(markup.includes('不限 → ≥10 → ≥15 → ≥18 → 不限'));
    assert.ok(markup.includes('多个位置需要同时满足'));
    assert.ok(markup.includes('database-advanced-base-panel'));
    assert.ok(markup.includes('database-advanced-base-column'));
    assert.ok(markup.includes('database-advanced-position-column'));
    assert.ok(markup.includes('left:50%;top:8%'));
    assert.ok(markup.includes('left:50%;top:25%'));
    assert.match(
        databaseCss,
        /button\.advanced-search-position-marker:not\(:disabled\):active\s*\{[^}]*transform:\s*translate\(-50%,\s*-50%\)\s*scale\(0\.98\)/s,
    );
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

async function assertBaseProfileAndSeaFiltersReachAdvancedSearch() {
    advancedSearchBodies = [];
    context.applyAdvancedDatabaseFiltersState({
        height: {min: '185', max: '195'},
        left_foot: {min: '12'},
        right_foot: {min: '15'},
        sea_status: 'not_in_sea',
    });
    await context.searchDatabase('', {pushHistory: false});
    await flushMicrotasks();

    assert.equal(advancedSearchBodies.length, 1);
    assert.equal(advancedSearchBodies[0].attributes.height.min, 185);
    assert.equal(advancedSearchBodies[0].attributes.height.max, 195);
    assert.equal(advancedSearchBodies[0].attributes.left_foot.min, 12);
    assert.equal(advancedSearchBodies[0].attributes.right_foot.min, 15);
    assert.equal(advancedSearchBodies[0].sea_status, 'not_in_sea');
    assert.ok(context.buildAppliedAdvancedFilterSummary().includes('排除大海球员'));
}

async function assertWeightedPowerRangeReachesAdvancedSearch() {
    advancedSearchBodies = [];
    context.applyAdvancedDatabaseFiltersState({weighted_power: {min: '60', max: '75'}});
    context.renderDatabaseAdvancedSearchPanel();
    assert.ok(elements.get('dbAdvancedSearchPanel').innerHTML.includes('加权战力值'));

    await context.searchDatabase('', {pushHistory: false});
    await flushMicrotasks();

    assert.equal(advancedSearchBodies.length, 1);
    assert.equal(advancedSearchBodies[0].weighted_power.min, 60);
    assert.equal(advancedSearchBodies[0].weighted_power.max, 75);
    assert.ok(context.buildAppliedAdvancedFilterSummary().includes('加权战力值 60-75'));
}

async function assertCandidateScopeUsesServerSideAdvancedSearch() {
    advancedSearchBodies = [];
    context.setDatabaseSearchScope({
        type: 'candidate_list',
        id: 7,
        name: '测试名单',
        dataVersion: '2620',
        uids: [1, 2],
        players: [
            {uid: 1, name: 'Filter One', data_version: '2620', ca: 150},
            {uid: 2, name: 'Filter Two', data_version: '2620', ca: 145},
        ],
    });
    context.applyAdvancedDatabaseFiltersState({height: {min: '185'}});
    await context.searchDatabase('', {pushHistory: false});
    await flushMicrotasks();

    assert.equal(advancedSearchBodies.length, 1);
    assert.equal(advancedSearchBodies[0].attributes.height.min, 185);
    assert.equal(advancedSearchBodies[0].uids.join(','), '1,2');
    context.resetDatabaseSearchScope();
}

async function assertLatestAdvancedSearchRequestWins() {
    const originalFetcher = context.fetchDatabaseAdvancedSearchResults;
    const pending = [];
    context.fetchDatabaseAdvancedSearchResults = payload => new Promise(resolve => pending.push({payload, resolve}));
    context.applyAdvancedDatabaseFiltersState({ca: {min: '120'}});
    const firstSearch = context.searchDatabase('', {pushHistory: false});
    await flushMicrotasks();
    context.applyAdvancedDatabaseFiltersState({ca: {min: '160'}});
    const secondSearch = context.searchDatabase('', {pushHistory: false});
    await flushMicrotasks();

    pending[1].resolve({...advancedSearchResponse, items: [{uid: 2, name: 'New Result'}], applied_filters_summary: ['CA ≥ 160']});
    await secondSearch;
    pending[0].resolve({...advancedSearchResponse, items: [{uid: 1, name: 'Old Result'}], applied_filters_summary: ['CA ≥ 120']});
    await firstSearch;

    assert.equal(context.currentDbPlayers[0].uid, 2);
    assert.ok(elements.get('dbQueryChips').innerHTML.includes('CA ≥ 160'));
    context.fetchDatabaseAdvancedSearchResults = originalFetcher;
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

function assertMobileSearchCardPrioritizesPowerMetrics() {
    const markup = context.renderMobileDbPlayerCard({
        uid: 1,
        name: 'Power Player',
        data_version: '2630',
        position: 'MC',
        age: 23,
        ca: 155,
        pa: 175,
        nationality: 'ES',
        club: 'Club',
        heigo_club: 'HEIGO Club',
        weighted_power: 72.34,
        heigo_power: 81.23,
        top_percent: 4.2,
    });
    assert.match(markup, /加权战力值/);
    assert.match(markup, /72\.34/);
    assert.match(markup, /HEIGO战力/);
    assert.match(markup, /81\.23/);
    assert.match(markup, /前 5%/);
    assert.doesNotMatch(markup, /mobile-db-metric-strip/);
}

function assertCandidateAddedAtIsVisibleAndSortable() {
    context.setDatabaseSearchScope({
        type: 'candidate_list',
        id: 9,
        name: '测试名单',
        dataVersion: '2630',
        players: [
            {uid: 1, added_at: '2026-08-12T03:00:00'},
            {uid: 2, added_at: '2026-08-13T03:22:00'},
        ],
    });
    const players = [
        {uid: 1, name: 'Older Player', data_version: '2630', position: 'MC', ca: 140, pa: 160, added_at: '2026-08-12T03:00:00'},
        {uid: 2, name: 'Newer Player', data_version: '2630', position: 'ST', ca: 150, pa: 170, added_at: '2026-08-13T03:22:00'},
    ];
    context.currentDbSort = {field: 'added_at', order: 'desc', type: 'date'};
    context.currentDbPlayers = players;
    context.renderDbPlayers(players);
    const markup = elements.get('dbPlayersTable').innerHTML;
    assert.match(markup, /加入时间/);
    assert.match(markup, /2026-08-13 11:22/);
    assert.ok(markup.indexOf('Newer Player') < markup.indexOf('Older Player'));
    assert.match(markup, /value="added_at_desc"[^>]*selected[^>]*>最新加入/);
    context.currentDbSort = {field: 'added_at', order: 'asc', type: 'date'};
    const ascending = context.getSortedDbPlayers(players);
    assert.equal(ascending.map(player => player.uid).join(','), '1,2');
    context.candidateAdminPlayerSort = {field: 'added_at', order: 'desc'};
    const adminHeader = context.buildCandidateAdminSortButton('added_at', '加入时间');
    assert.match(adminHeader, /candidate-admin-sort[\s\S]*?sortable-label[\s\S]*?sort-indicator is-active[\s\S]*?↓/);
    context.resetDatabaseSearchScope();
    context.currentDbSort = {field: '', order: '', type: 'number'};
}

(async () => {
    await assertAdvancedTriggerReflectsActiveCount();
    await assertPositionClickCyclesWithoutPanelRerender();
    await assertPositionMapUsesDirectTouchFriendlyCycle();
    await assertAdvancedSearchSupportsBlankKeyword();
    await assertBaseProfileAndSeaFiltersReachAdvancedSearch();
    await assertWeightedPowerRangeReachesAdvancedSearch();
    await assertCandidateScopeUsesServerSideAdvancedSearch();
    await assertLatestAdvancedSearchRequestWins();
    await assertVersionSwitchRerunsAdvancedSearch();
    await assertClearAdvancedFiltersResetsState();
    assertMobileSearchCardPrioritizesPowerMetrics();
    assertCandidateAddedAtIsVisibleAndSortable();
})().catch(error => {
    console.error(error);
    process.exit(1);
});
