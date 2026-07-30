const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = __dirname;
const html = fs.readFileSync(path.join(root, 'static/app.html'), 'utf8');
const competition = fs.readFileSync(path.join(root, 'static/js/app.competition.js'), 'utf8');
const app = fs.readFileSync(path.join(root, 'static/app.js'), 'utf8');

assert.match(html, /id="cupPhaseTabs"/);
assert.match(html, /id="cupPhaseGroupTab"/);
assert.match(html, /id="cupPhaseKnockoutTab"/);
assert.match(html, /id="cupGroupStageBoard"/);
assert.match(html, />小组赛阶段</);
assert.match(html, />淘汰赛阶段</);

assert.match(competition, /var currentCupPhase = 'knockout'/);
assert.match(competition, /function setCupPhase\(phase\)/);
assert.match(competition, /function renderCupGroupStageBoard\(\)/);
assert.match(competition, /currentCupPhase === 'knockout'/);
assert.match(competition, /本届尚未录入/);
assert.match(competition, /cupConfig && currentCupPhase === 'knockout'/);

assert.match(app, /params\.set\('cupPhase', competition\.cupPhase\)/);
assert.match(app, /currentCupPhase = competitionState\.cupPhase === 'group'/);

console.log('cup phase frontend checks passed');
