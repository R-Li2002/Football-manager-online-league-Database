const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const workspaceRoot = __dirname;
const coreCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/app.core.js'), 'utf8');
const playersCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/app.players.js'), 'utf8');

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

function createElement(id = '') {
    return {
        id,
        value: '',
        innerHTML: '',
        textContent: '',
        dataset: {},
        style: {},
        classList: createClassList(),
        appendChild(child) {
            this.children = this.children || [];
            this.children.push(child);
        },
        removeChild(child) {
            this.children = (this.children || []).filter(item => item !== child);
        },
        addEventListener() {},
        setAttribute(name, value) {
            this.attributes = this.attributes || {};
            this.attributes[name] = String(value);
        },
        select() {
            this.selected = true;
        },
        focus() {
            this.focused = true;
        },
    };
}

const elements = new Map();
function registerElement(id) {
    const element = createElement(id);
    elements.set(id, element);
    return element;
}

[
    'playersTable',
    'playerQueryTitle',
    'playerQueryMeta',
    'playerQueryChips',
    'teamSelect',
    'playerSearch',
].forEach(registerElement);

const body = createElement('body');
const document = {
    body,
    getElementById(id) {
        return elements.get(id) || null;
    },
    createElement(tagName) {
        return createElement(tagName);
    },
    querySelectorAll(selector) {
        if (selector === '#playersTable tr.row-selected') return [];
        if (selector === '#playersTable tr[data-player-uid]') return [];
        return [];
    },
};

const clipboardWrites = [];
const toastMessages = [];
let execCommandCalls = 0;

const context = {
    console,
    document,
    window: {document},
    navigator: {
        clipboard: {
            writeText: async text => {
                clipboardWrites.push(text);
            },
        },
    },
    documentCommandSucceeded: true,
    isAdmin: false,
    allPlayers: [],
    currentPlayers: [],
    currentRosterSort: {field: '', order: 'desc', type: 'number'},
    currentSelectedRosterUid: null,
    showDetailExportToast(message, tone = 'success') {
        toastMessages.push({message, tone});
    },
    document: {
        ...document,
        execCommand(command) {
            execCommandCalls += 1;
            assert.equal(command, 'copy');
            return context.documentCommandSucceeded;
        },
    },
};
context.window.navigator = context.navigator;
context.window.document = context.document;

vm.createContext(context);
vm.runInContext(coreCode, context, {filename: 'app.core.js'});
vm.runInContext(playersCode, context, {filename: 'app.players.js'});

const samplePlayer = {
    uid: 1001,
    name: 'Copy Target',
    age: 22,
    initial_ca: 120,
    ca: 133,
    pa: 158,
    position: 'AMC',
    nationality: 'Portugal',
    team_name: 'Alpha FC',
    wage: 1.25,
    slot_type: '7M',
};

function createCopyEvent() {
    return {
        prevented: false,
        stopped: false,
        preventDefault() {
            this.prevented = true;
        },
        stopPropagation() {
            this.stopped = true;
        },
    };
}

async function assertCopyTextUsesExpectedRosterFields() {
    assert.equal(
        context.buildRosterPlayerCopyText(samplePlayer),
        '1001 Copy Target 22 120 133 158 AMC'
    );
}

async function assertClipboardCopyStopsRowInteraction() {
    context.currentPlayers = [samplePlayer];
    context.allPlayers = [];
    clipboardWrites.length = 0;
    toastMessages.length = 0;

    const event = createCopyEvent();
    await context.copyRosterPlayerInfo(event, 1001);

    assert.equal(event.prevented, true);
    assert.equal(event.stopped, true);
    assert.deepEqual(clipboardWrites, ['1001 Copy Target 22 120 133 158 AMC']);
    assert.equal(toastMessages.at(-1).tone, 'success');
}

async function assertFallbackCopyIsUsedWhenClipboardIsUnavailable() {
    const originalClipboard = context.navigator.clipboard;
    context.navigator.clipboard = null;
    context.documentCommandSucceeded = true;
    execCommandCalls = 0;
    toastMessages.length = 0;

    await context.copyRosterPlayerInfo(createCopyEvent(), 1001);

    assert.equal(execCommandCalls, 1);
    assert.equal(toastMessages.at(-1).tone, 'success');
    context.navigator.clipboard = originalClipboard;
}

async function assertWarningIsShownWhenAllCopyMethodsFail() {
    const originalClipboard = context.navigator.clipboard;
    const originalExecCommand = context.document.execCommand;
    context.navigator.clipboard = null;
    delete context.document.execCommand;
    toastMessages.length = 0;

    await context.copyRosterPlayerInfo(createCopyEvent(), 1001);

    assert.equal(toastMessages.at(-1).tone, 'warning');
    context.navigator.clipboard = originalClipboard;
    context.document.execCommand = originalExecCommand;
}

async function assertRenderPlayersAddsCopyColumnWithoutAdminDetailColumn() {
    context.isAdmin = false;
    context.currentPlayers = [samplePlayer];
    context.renderPlayers([samplePlayer]);

    const html = elements.get('playersTable').innerHTML;
    assert.match(html, /copy-column/);
    assert.match(html, /roster-copy-button/);
    assert.match(html, /copyRosterPlayerInfo\(event, 1001\)/);
    assert.doesNotMatch(html, /colspan="13"/);
}

async function assertRenderPlayersUsesWiderDetailColspanForAdminRows() {
    context.isAdmin = true;
    context.renderPlayers([samplePlayer]);

    const html = elements.get('playersTable').innerHTML;
    assert.match(html, /colspan="13"/);
    assert.match(html, /roster-copy-button/);
}

(async () => {
    await assertCopyTextUsesExpectedRosterFields();
    await assertClipboardCopyStopsRowInteraction();
    await assertFallbackCopyIsUsedWhenClipboardIsUnavailable();
    await assertWarningIsShownWhenAllCopyMethodsFail();
    await assertRenderPlayersAddsCopyColumnWithoutAdminDetailColumn();
    await assertRenderPlayersUsesWiderDetailColspanForAdminRows();
})().catch(error => {
    console.error(error);
    process.exit(1);
});
