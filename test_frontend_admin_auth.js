const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const workspaceRoot = __dirname;
const adminCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/app.admin.js'), 'utf8');

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
const adminTab = registerElement(createElement('adminTab', ['nav-tab', 'hidden-tab']));
adminTab.dataset.tab = 'admin';
const adminLogin = registerElement(createElement('adminLogin'));
const adminPanel = registerElement(createElement('adminPanel'));
const adminUsername = registerElement(createElement('adminUsername'));
const adminPassword = registerElement(createElement('adminPassword'));
const transferUid = registerElement(createElement('transferUid'));
const transferTeam = registerElement(createElement('transferTeam'));
const transferNotes = registerElement(createElement('transferNotes'));
const modalTitle = registerElement(createElement('modalTitle'));
const modalBody = registerElement(createElement('modalBody'));
const resultModal = registerElement(createElement('resultModal'));

adminLogin.style.display = 'block';
adminPanel.style.display = 'none';
body.dataset.activeTab = 'admin';

const document = {
    body,
    getElementById(id) {
        return elements.get(id) || null;
    },
};

let fetchQueue = [];
function queueFetch(...responses) {
    fetchQueue = responses.slice();
}

const context = {
    console,
    document,
    Date,
    currentPlayers: [],
    currentOperationAuditCategory: '',
    lastFormalImportSummary: null,
    lastSchemaBootstrapStatus: null,
    recentOperationAudits: [],
    teams: [],
    isAdmin: false,
    adminEntryUnlocked: false,
    fetch: async (url, options = {}) => {
        const next = fetchQueue.shift();
        if (!next) {
            throw new Error(`Unexpected fetch: ${url}`);
        }
        return {
            status: next.status ?? (next.ok === false ? 500 : 200),
            ok: next.ok ?? ((next.status ?? 200) >= 200 && (next.status ?? 200) < 300),
            json: async () => next.json ?? {},
            blob: async () => next.blob ?? Buffer.from(''),
            headers: {get: () => null},
        };
    },
    window: {
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
    showModal(title, bodyHtml) {
        modalTitle.textContent = title;
        modalBody.innerHTML = bodyHtml;
        resultModal.classList.add('active');
    },
    closeModal() {
        resultModal.classList.remove('active');
    },
    showTab(tabName) {
        body.dataset.activeTab = tabName;
        adminTab.classList.toggle('active', tabName === 'admin');
    },
    hideTeamStatSourceDebugView() {},
    renderTeamsTable() {},
    renderPlayers() {},
    updateStats() {},
    renderFormalImportSummaryCard() {},
    renderSchemaBootstrapStatusCard() {},
    renderOperationsAuditCard() {},
    renderTeamStatSourceDebugView() {},
    populateAdminSelects() {},
    loadSchemaBootstrapStatus() {},
    loadLatestFormalImportSummary() {},
    loadOperationsAudit() {},
    loadSeaPlayers() {},
    loadTransferLogs() {},
    loadLogFile() {},
    refreshPlayerDataset: async () => {},
    refreshTeamDataset: async () => {},
    refreshLeagueInfoDataset: async () => {},
    loadAttributeVersionCatalog: async () => {},
    refreshAttributeVersionBanner() {},
    escapeHtml(value) {
        return String(value ?? '');
    },
    formatCompactNationality(value) {
        return String(value ?? '');
    },
    confirm() {
        return true;
    },
};

vm.createContext(context);
vm.runInContext(adminCode, context, {filename: 'app.admin.js'});

async function testLoginRequiresConfirmedSession() {
    queueFetch(
        {ok: true, status: 200, json: {success: true, username: 'HEIGO01'}},
        {ok: true, status: 200, json: {authenticated: false}},
    );
    adminUsername.value = 'HEIGO01';
    adminPassword.value = 'StrongPassword1!';

    await context.adminLogin();

    assert.equal(context.isAdmin, false);
    assert.equal(adminLogin.style.display, 'block');
    assert.equal(adminPanel.style.display, 'none');
    assert.equal(body.dataset.activeTab, 'admin');
    assert.equal(adminUsername.focused, true);
    assert.equal(modalTitle.textContent, '错误');
    assert.match(modalBody.innerHTML, /登录态未生效/);
}

async function testUnauthorizedMutationFallsBackToLogin() {
    context.isAdmin = true;
    context.adminEntryUnlocked = true;
    adminLogin.style.display = 'none';
    adminPanel.style.display = 'block';
    transferUid.value = '123';
    transferTeam.value = '测试球队';
    transferNotes.value = 'test';
    queueFetch({ok: false, status: 401, json: {detail: '未授权'}});

    await context.transferPlayer();

    assert.equal(context.isAdmin, false);
    assert.equal(adminLogin.style.display, 'block');
    assert.equal(adminPanel.style.display, 'none');
    assert.equal(body.dataset.activeTab, 'admin');
    assert.equal(adminUsername.focused, true);
    assert.equal(modalTitle.textContent, '未授权');
    assert.match(modalBody.innerHTML, /管理员登录已失效/);
}

(async () => {
    await testLoginRequiresConfirmedSession();
    await testUnauthorizedMutationFallsBackToLogin();
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
