const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, 'static/app.html'), 'utf8');
const css = [
    fs.readFileSync(path.join(__dirname, 'static/app.css'), 'utf8'),
    fs.readFileSync(path.join(__dirname, 'static/css/pages/database.css'), 'utf8'),
    fs.readFileSync(path.join(__dirname, 'static/css/responsive.css'), 'utf8'),
].join('\n');
const app = fs.readFileSync(path.join(__dirname, 'static/app.js'), 'utf8');
const tactics = fs.readFileSync(path.join(__dirname, 'static/js/database.tactics.js'), 'utf8');

assert.match(html, /id="dbSubtabTactics"[\s\S]*?>战术板</);
assert.match(html, /id="dbTacticsView"/);
assert.match(app, /database\.tactics\.js/);
assert.match(app, /databaseSubtab', 'tactics'/);
assert.match(tactics, /heigo_database_tactics_board_v1/);
assert.match(tactics, /buildPreviewPlayer\(player, growthStep\)/);
assert.match(tactics, /calculateWeightedPower\(preview\)/);
assert.match(tactics, /onpointerdown="startDatabaseTacticsDrag/);
assert.match(tactics, /function moveDatabaseTacticsDrag/);
assert.match(tactics, /场上 11 人都可以用鼠标或手指拖到任意位置/);
assert.match(tactics, /x: Number\.isFinite\(rawX\)/);
assert.match(tactics, /function setDatabaseTacticsDropPoint/);
assert.match(css, /#dbTacticsView \.db-tactics-pitch/);
assert.match(css, /@media \(max-width: 640px\)[\s\S]*db-tactics-player-card/);
assert.match(css, /touch-action: none/);
assert.match(css, /white-space:\s*normal;\s*overflow-wrap:\s*break-word;\s*word-break:\s*normal/);
assert.match(css, /db-tactics-player-card strong\s*\{[^}]*grid-column:\s*2 \/ 4/s);

const storage = new Map();
const context = {
    console,
    localStorage: {
        getItem(key) { return storage.get(key) || null; },
        setItem(key, value) { storage.set(key, String(value)); },
    },
};
vm.createContext(context);
vm.runInContext(tactics, context, {filename: 'database.tactics.js'});

assert.deepEqual(
    Array.from(context.getDatabaseTacticsEligibleSteps({ca: 120, pa: 190})),
    [0, 1, 2, 3, 4],
    'growth states should follow the same CA-space thresholds as the power ranking',
);
assert.deepEqual(
    Array.from(context.getDatabaseTacticsEligibleSteps({ca: 100, pa: 190})),
    [0, 1, 2, 3, 4, 5],
);

context.databaseTacticsState.players = {7: {uid: 7, ca: 120, pa: 190}};
context.databaseTacticsState.picks = {st: {uid: 7, growth_step: 4, x: 73.5, y: 34.25}};
context.normalizeDatabaseTacticsPicks();
assert.equal(context.databaseTacticsState.picks.st.x, 73.5);
assert.equal(context.databaseTacticsState.picks.st.y, 34.25);

console.log('database tactics frontend checks passed');
