const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const workspaceRoot = __dirname;
const coreCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/app.core.js'), 'utf8');
const homeCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/app.home.js'), 'utf8');
const adminCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/app.admin.js'), 'utf8');
const playersCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/app.players.js'), 'utf8');
const appCode = fs
    .readFileSync(path.join(workspaceRoot, 'static/app.js'), 'utf8')
    .replace(/\ninit\(\);\s*$/, '\n');

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
        focused: false,
        appendChild() {},
        removeChild() {},
        addEventListener() {},
        focus() {
            this.focused = true;
        },
    };
}

const elements = new Map();

function registerElement(element) {
    elements.set(element.id, element);
    return element;
}

const body = createElement('body');

const tabContents = ['home', 'overview', 'players', 'database', 'admin'].map(id =>
    registerElement(createElement(id, ['tab-content', id === 'home' ? 'active' : '']))
);

const navTabs = ['home', 'overview', 'players', 'database'].map(tabName => {
    const element = registerElement(createElement(`${tabName}Tab`, ['nav-tab', tabName === 'home' ? 'active' : '']));
    element.dataset.tab = tabName;
    return element;
});

const adminTab = registerElement(createElement('adminTab', ['nav-tab', 'hidden-tab']));
adminTab.dataset.tab = 'admin';
navTabs.push(adminTab);

const heroPlayerSearch = registerElement(createElement('heroPlayerSearch'));
const heroSearchResults = registerElement(createElement('heroSearchResults'));
const playerSearch = registerElement(createElement('playerSearch'));
const teamSelect = registerElement(createElement('teamSelect'));
const tableTitle = registerElement(createElement('tableTitle'));
const adminLogin = registerElement(createElement('adminLogin'));
const adminPanel = registerElement(createElement('adminPanel'));
const adminUsername = registerElement(createElement('adminUsername'));

adminLogin.style.display = 'none';
adminPanel.style.display = 'block';
body.dataset.activeTab = 'home';

const document = {
    body,
    getElementById(id) {
        return elements.get(id) || null;
    },
    querySelectorAll(selector) {
        if (selector === '.tab-content') {
            return tabContents;
        }
        if (selector === '.nav-tab') {
            return navTabs;
        }
        return [];
    },
    querySelector(selector) {
        const navTabMatch = selector.match(/^\.nav-tab\[data-tab="([^"]+)"\]$/);
        if (navTabMatch) {
            return navTabs.find(tab => tab.dataset.tab === navTabMatch[1]) || null;
        }
        return null;
    },
    createElement(tagName) {
        return createElement(tagName);
    },
};

const history = {
    state: null,
    pushState(state) {
        this.state = state;
    },
    replaceState(state) {
        this.state = state;
    },
};

const localStorageState = new Map();
const localStorage = {
    getItem(key) {
        return localStorageState.get(key) || '';
    },
    setItem(key, value) {
        localStorageState.set(key, String(value));
    },
};

const context = {
    console,
    document,
    history,
    localStorage,
    URLSearchParams,
    window: {
        document,
        history,
        localStorage,
        location: {href: 'http://localhost/'},
        addEventListener() {},
        setTimeout(callback) {
            callback();
            return 1;
        },
        URL: {
            createObjectURL() {
                return 'blob:test';
            },
            revokeObjectURL() {},
        },
    },
    fetch: async url => {
        if (url === '/api/admin/logout') {
            return {ok: true, json: async () => ({success: true})};
        }
        throw new Error(`Unexpected fetch in frontend admin regression test: ${url}`);
    },
};

vm.createContext(context);
vm.runInContext(coreCode, context, {filename: 'app.core.js'});
vm.runInContext(homeCode, context, {filename: 'app.home.js'});
vm.runInContext(adminCode, context, {filename: 'app.admin.js'});
vm.runInContext(playersCode, context, {filename: 'app.players.js'});
vm.runInContext(appCode, context, {filename: 'app.js'});

assert.equal(context.normalizeAppTabName('admin'), 'admin');
assert.equal(context.isAdminEntryQuery(' heigomanage '), true);

function resetAdminState() {
    context.isAdmin = false;
    context.adminEntryUnlocked = false;
    document.body.dataset.activeTab = 'home';
    tabContents.forEach(tab => {
        tab.classList.toggle('active', tab.id === 'home');
    });
    navTabs.forEach(tab => tab.classList.remove('active'));
    navTabs.find(tab => tab.dataset.tab === 'home')?.classList.add('active');
    adminTab.classList.add('hidden-tab');
    adminLogin.style.display = 'none';
    adminPanel.style.display = 'block';
    adminUsername.focused = false;
    heroPlayerSearch.value = '';
    heroSearchResults.innerHTML = '';
    playerSearch.value = '';
    teamSelect.value = '';
    tableTitle.textContent = '';
}

async function assertAdminEntryFromPlayerSearch() {
    resetAdminState();
    playerSearch.value = 'heigomanage';
    await context.searchPlayers({pushHistory: false});

    assert.equal(playerSearch.value, '');
    assert.equal(document.body.dataset.activeTab, 'admin');
    assert.equal(adminTab.classList.contains('active'), true);
    assert.equal(adminTab.classList.contains('hidden-tab'), false);
    assert.equal(adminLogin.style.display, 'block');
    assert.equal(adminPanel.style.display, 'none');
    assert.equal(tabContents.find(tab => tab.id === 'admin').classList.contains('active'), true);
    assert.equal(tabContents.find(tab => tab.id === 'home').classList.contains('active'), false);
    assert.equal(adminUsername.focused, true);
    assert.equal(context.adminEntryUnlocked, true);
    assert.equal(tableTitle.textContent, '');
}

async function assertAdminEntryFromHeroSearch() {
    resetAdminState();
    heroPlayerSearch.value = 'heigomanage';
    heroSearchResults.innerHTML = 'stale';
    await context.runHeroSearch({pushHistory: false});

    assert.equal(heroPlayerSearch.value, '');
    assert.equal(heroSearchResults.innerHTML, '');
    assert.equal(document.body.dataset.activeTab, 'admin');
    assert.equal(adminTab.classList.contains('active'), true);
    assert.equal(adminTab.classList.contains('hidden-tab'), false);
    assert.equal(adminLogin.style.display, 'block');
    assert.equal(adminPanel.style.display, 'none');
    assert.equal(tabContents.find(tab => tab.id === 'admin').classList.contains('active'), true);
    assert.equal(tabContents.find(tab => tab.id === 'home').classList.contains('active'), false);
    assert.equal(adminUsername.focused, true);
    assert.equal(context.adminEntryUnlocked, true);
    assert.equal(tableTitle.textContent, '');
}

(async () => {
    await assertAdminEntryFromPlayerSearch();
    await assertAdminEntryFromHeroSearch();
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
