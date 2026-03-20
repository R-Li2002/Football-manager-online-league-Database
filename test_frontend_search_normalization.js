const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const workspaceRoot = __dirname;
const coreCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/app.core.js'), 'utf8');
const homeCode = fs.readFileSync(path.join(workspaceRoot, 'static/js/app.home.js'), 'utf8');

const context = {
    console,
    fetch: async () => {
        throw new Error('fetch should not be called in search normalization tests');
    },
    localStorage: {
        getItem() {
            return '';
        },
        setItem() {},
    },
    window: {},
    document: {
        getElementById() {
            return null;
        },
    },
};

vm.createContext(context);
vm.runInContext(coreCode, context, {filename: 'app.core.js'});
vm.runInContext(homeCode, context, {filename: 'app.home.js'});

assert.equal(context.normalizeSearchText('\u0391\u03bb\u03ad\u03be\u03b1\u03bd\u03b4\u03c1\u03bf\u03c2'), 'alexandros');
assert.equal(context.normalizeSearchTextLoose('G\u00fcndo\u011fan'), 'guendogan');

const gundoganKeys = context.buildSearchNormalizedKeys('guendogan');
assert.deepEqual([...gundoganKeys.strictKeys], ['guendogan', 'gundogan']);
assert.deepEqual([...gundoganKeys.looseKeys], ['guendogan']);

assert.equal(context.isExactDatabaseMatch({name: '\u0130lkay G\u00fcndo\u011fan'}, 'Ilkay guendogan'), true);
assert.equal(context.isExactDatabaseMatch({name: '\u0391\u03bb\u03ad\u03be\u03b1\u03bd\u03b4\u03c1\u03bf\u03c2'}, 'alexandros'), true);
assert.equal(context.isExactDatabaseMatch({name: 'Jo\u00e3o F\u00e9lix'}, 'Joao Felix'), true);
