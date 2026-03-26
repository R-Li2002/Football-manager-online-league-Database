const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const workspaceRoot = __dirname;
const coreCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/app.core.js'), 'utf8');
const databaseCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/app.database.js'), 'utf8');
const databaseSearchCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/database.search.js'), 'utf8');
const databaseCompareCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/database.compare.js'), 'utf8');

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
        classList: createClassList(initialClasses),
        appendChild(child) {
            this.options = this.options || [];
            this.options.push(child);
        },
        addEventListener() {},
        setAttribute(name, value) {
            this.attributes = this.attributes || {};
            this.attributes[name] = String(value);
        },
        getAttribute(name) {
            return this.attributes?.[name] || null;
        },
    };
}

const elements = new Map();

function registerElement(element) {
    elements.set(element.id, element);
    return element;
}

registerElement(createElement('dbPlayerSearch'));
registerElement(createElement('dbPlayersTable'));
registerElement(createElement('dbTableTitle'));
registerElement(createElement('playerDetailToolbar'));
registerElement(createElement('playerDetailContent'));
registerElement(createElement('dbSubtabSearch', ['database-subtab', 'active']));
registerElement(createElement('dbSubtabLeaderboard', ['database-subtab']));
registerElement(createElement('dbListView', ['list-view', 'active']));
registerElement(createElement('dbReactionLeaderboardView', ['list-view']));
registerElement(createElement('dbDetailView', ['detail-view']));
registerElement(createElement('dbReactionMetricSelect'));
registerElement(createElement('dbReactionLimitSelect'));
registerElement(createElement('dbReactionTeamSelect'));
registerElement(createElement('dbReactionLeaderboardTitle'));
registerElement(createElement('dbReactionLeaderboardTable'));

elements.get('dbReactionMetricSelect').value = 'flowers';
elements.get('dbReactionLimitSelect').value = '20';
elements.get('dbReactionTeamSelect').value = '';

const document = {
    body: {dataset: {}},
    addEventListener() {},
    getElementById(id) {
        return elements.get(id) || null;
    },
    createElement(tagName) {
        return createElement(tagName);
    },
};

let fetchPayload = {metric: 'flowers', limit: 20, data_version: '2620', items: []};
let fetchOk = true;
let fetchStatus = 200;
let fetchRejectError = null;
let fetchedUrls = [];
let loadCalls = [];
let shownTabs = [];

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
    URLSearchParams,
    fetch: async url => {
        fetchedUrls.push(url);
        if (fetchRejectError) {
            throw fetchRejectError;
        }
        return {
            ok: fetchOk,
            status: fetchStatus,
            json: async () => fetchPayload,
        };
    },
    history: {back() {}},
    setTimeout,
    clearTimeout,
};

vm.createContext(context);
vm.runInContext(coreCode, context, {filename: 'app.core.js'});
vm.runInContext(databaseCode, context, {filename: 'app.database.js'});
vm.runInContext(databaseSearchCode, context, {filename: 'database.search.js'});
vm.runInContext(databaseCompareCode, context, {filename: 'database.compare.js'});

context.teams = [
    {name: 'Alpha FC', level: '超级'},
    {name: 'Beta FC', level: '甲级'},
];
context.availableAttributeVersions = ['2620'];
context.currentAttributeVersion = '2620';
context.loadAttributeVersionCatalog = async () => ({available_versions: ['2620'], default_version: '2620'});
context.refreshAttributeVersionBanner = () => {};
context.syncAppHistory = () => {};
context.showTab = tabName => {
    shownTabs.push(tabName);
};
context.clearPlayerReactionCooldownTimer = () => {};
context.clearPlayerReactionBounce = () => {};
context.canUseAppHistoryBack = () => false;

async function flushMicrotasks() {
    await Promise.resolve();
    await Promise.resolve();
}

async function assertLeaderboardSubtabSwitchesAndLoads() {
    fetchPayload = {metric: 'flowers', limit: 20, data_version: '2620', items: []};
    fetchOk = true;
    fetchStatus = 200;
    fetchRejectError = null;
    fetchedUrls = [];
    context.showDatabaseSubtab('leaderboard', {pushHistory: false});
    await flushMicrotasks();

    assert.equal(context.currentDatabaseSubtab, 'leaderboard');
    assert.equal(elements.get('dbSubtabLeaderboard').classList.contains('active'), true);
    assert.equal(elements.get('dbSubtabSearch').classList.contains('active'), false);
    assert.equal(elements.get('dbReactionLeaderboardView').classList.contains('active'), true);
    assert.equal(elements.get('dbListView').classList.contains('active'), false);
    assert.equal(fetchedUrls.length, 1);
    assert.ok(fetchedUrls[0].includes('/api/reactions/leaderboard?'));
    assert.ok(fetchedUrls[0].includes('metric=flowers'));
    assert.ok(fetchedUrls[0].includes('limit=20'));
    assert.ok(fetchedUrls[0].includes('version=2620'));
}

async function assertEmptyLeaderboardRendersFallback() {
    fetchPayload = {metric: 'eggs', limit: 10, data_version: '2620', items: []};
    fetchOk = true;
    fetchStatus = 200;
    fetchRejectError = null;
    elements.get('dbReactionMetricSelect').value = 'eggs';
    elements.get('dbReactionLimitSelect').value = '10';

    await context.loadReactionLeaderboard({pushHistory: false});

    assert.equal(elements.get('dbReactionLeaderboardTitle').textContent, '鸡蛋榜 (10) · 2620');
    assert.ok(elements.get('dbReactionLeaderboardTable').innerHTML.includes('当前筛选条件下还没有互动数据'));
}

async function assertLeaderboardLoadFailureShowsInlineMessage() {
    fetchPayload = {detail: 'service-unavailable'};
    fetchOk = false;
    fetchStatus = 503;
    fetchRejectError = null;
    elements.get('dbReactionMetricSelect').value = 'flowers';
    elements.get('dbReactionLimitSelect').value = '20';

    await context.loadReactionLeaderboard({pushHistory: false});

    assert.equal(
        elements.get('dbReactionLeaderboardTitle').textContent,
        `${context.getDatabaseLeaderboardMetricLabel('flowers')} (20) · 2620`
    );
    assert.ok(elements.get('dbReactionLeaderboardTable').innerHTML.includes('service-unavailable'));
}

function assertRenderedRowsLinkBackToLeaderboard() {
    context.renderReactionLeaderboard({
        metric: 'net',
        limit: 5,
        data_version: '2620',
        items: [
            {
                uid: 99,
                name: 'Gamma',
                data_version: '2620',
                heigo_club: 'Alpha FC',
                position: 'MC',
                ca: 140,
                pa: 160,
                flowers: 9,
                eggs: 1,
                net_score: 8,
            },
        ],
    });

    assert.ok(elements.get('dbReactionLeaderboardTable').innerHTML.includes("returnSubtab: 'leaderboard'"));
}

function assertBackToListReturnsToLeaderboard() {
    loadCalls = [];
    shownTabs = [];
    context.loadReactionLeaderboard = options => {
        loadCalls.push(options);
    };
    context.dbDetailReturnState = {tab: 'database', subtab: 'leaderboard'};
    context.currentDatabaseSubtab = 'search';
    context.currentDetailPlayer = {uid: 99};

    context.backToList({useBrowserHistory: false, pushHistory: false});

    assert.equal(context.currentDatabaseSubtab, 'leaderboard');
    assert.equal(elements.get('dbReactionLeaderboardView').classList.contains('active'), true);
    assert.deepEqual(shownTabs, ['database']);
    assert.equal(loadCalls.length, 1);
    assert.equal(loadCalls[0].pushHistory, false);
}

(async () => {
    await assertLeaderboardSubtabSwitchesAndLoads();
    await assertEmptyLeaderboardRendersFallback();
    await assertLeaderboardLoadFailureShowsInlineMessage();
    assertRenderedRowsLinkBackToLeaderboard();
    assertBackToListReturnsToLeaderboard();
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
