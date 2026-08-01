const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = __dirname;
const html = fs.readFileSync(path.join(root, 'static/app.html'), 'utf8');
const core = fs.readFileSync(path.join(root, 'static/js/app.core.js'), 'utf8');
const app = fs.readFileSync(path.join(root, 'static/app.js'), 'utf8');
const competition = fs.readFileSync(path.join(root, 'static/js/app.competition.js'), 'utf8');
const admin = fs.readFileSync(path.join(root, 'static/js/app.admin.js'), 'utf8');
const css = fs.readFileSync(path.join(root, 'static/app.css'), 'utf8');
const competitionCss = fs.readFileSync(path.join(root, 'static/css/pages/competition.css'), 'utf8');

for (const id of ['rosterDataStatus', 'databaseDataStatus', 'competitionDataStatus', 'workspaceDataStatusList']) {
    assert.match(html, new RegExp(`id="${id}"`));
}

assert.match(core, /fetch\('\/api\/data-status'\)/);
assert.match(core, /function renderDataStatusStrip/);
assert.match(core, /function openDataStatusItem/);
assert.match(core, /dataStatusIconSvg/);
assert.match(core, /aria-label=/);
assert.match(core, /loadDataStatus\(\{force:true\}\)/);
assert.match(app, /renderDataStatusStrip\('rosterDataStatus'/);
assert.match(app, /renderDataStatusStrip\('databaseDataStatus'/);

assert.match(competition, /function renderCompetitionDataStatus/);
assert.match(competition, /standings: 'standings'/);
assert.match(competition, /schedule: 'schedule'/);
assert.match(competition, /playerRankings: 'player_rankings'/);
assert.match(competition, /suspensions: 'suspensions'/);
assert.match(competition, /JSON\.stringify\(\{text: payload\.text, round_no: payload\.roundNo\}\)/);
assert.match(competition, /renderCompetitionDataStatus\(\)/);

assert.match(admin, /function renderWorkspaceDataStatuses/);
assert.match(admin, /workspaceDashboardData\?\.data_statuses/);
assert.match(admin, /openDataStatusItem/);

assert.match(css, /\.data-status-strip/);
assert.match(css, /\.data-status-strip\.is-error/);
assert.match(css, /\.workspace-data-status-row/);
assert.match(competitionCss, /\.suspension-round-field/);
assert.match(css, /@media \(max-width: 680px\)/);

console.log('data status frontend structure checks passed');
