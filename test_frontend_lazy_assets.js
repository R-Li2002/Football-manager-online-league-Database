const assert = require('node:assert/strict');
const fs = require('node:fs');

const html = fs.readFileSync('static/app.html', 'utf8');
const app = fs.readFileSync('static/app.js', 'utf8');
const admin = fs.readFileSync('static/js/app.admin.js', 'utf8');
const coaches = fs.readFileSync('static/js/app.coaches.js', 'utf8');
const competition = fs.readFileSync('static/js/app.competition.js', 'utf8');
const database = fs.readFileSync('static/js/app.database.js', 'utf8');
const databaseSearch = fs.readFileSync('static/js/database.search.js', 'utf8');

assert.doesNotMatch(
    html,
    /static\/css\/pages\/(?:database|competition|team)\.css/,
    'page CSS should stay out of the initial document',
);
assert.match(app, /const APP_STYLE_LOAD_PROMISES = new Map\(\)/, 'lazy styles should deduplicate concurrent requests');
assert.match(app, /const APP_MODULE_STYLES = \{[\s\S]*competition:[\s\S]*database:/, 'module CSS should have an explicit ownership map');
assert.match(app, /document\.head\.insertBefore\(link, responsiveStyle \|\| null\)/, 'lazy styles should load before responsive overrides');

assert.match(app, /competition:\s*\['\/static\/js\/app\.competition\.js'\]/, 'competition should load one feature script');
assert.doesNotMatch(app, /competition:\s*\[[^\]]*(?:app\.admin|html-to-image)/, 'competition should not preload admin or screenshot code');
assert.match(app, /function renderCoachProfileLink\(/, 'coach profile links should be available before feature modules load');
assert.match(app, /function openCoachProfileLinkByName\([\s\S]*ensureAppModule\('coaches'\)/, 'coach profile clicks should lazy-load the full coach module');
assert.doesNotMatch(coaches, /function renderCoachProfileLink\(/, 'the coach module should not own the shared link renderer');
assert.match(app, /tabName === 'competition'[\s\S]{0,180}ensureTeamsLoaded\(\)/, 'competition should load its team directory');
assert.doesNotMatch(app, /tabName === 'competition'[\s\S]{0,220}ensurePlayersLoaded\(\)/, 'competition should not load all players on entry');
assert.match(competition, /async function ensureCompetitionPlayersLoaded\(\)/, 'competition should load players at editor boundaries');
assert.match(competition, /await ensureCompetitionPlayersLoaded\(\)/, 'player-dependent competition actions should use the boundary loader');

assert.match(app, /'database-tactics': \['\/static\/js\/database\.tactics\.js'\]/, 'tactics should be a separate database submodule');
assert.doesNotMatch(app, /database:\s*\[[^\]]*database\.tactics\.js/, 'database entry should not preload tactics');
assert.match(databaseSearch, /async function showDatabaseSubtab\(subtab[\s\S]*ensureAppModule\('database-tactics'\)/, 'opening tactics should load its submodule');
assert.doesNotMatch(database, /database\.tactics\.js/, 'the main database implementation should remain independent of tactics assets');

assert.match(admin, /let workspaceAdminOperationsLoadPromise = null;/, 'admin operations dependencies should be deduplicated');
assert.match(admin, /if \(normalized === 'imports'\) loadWorkspaceAdminOperations\(\)/, 'import tools should load operational dependencies on demand');
assert.match(admin, /if \(normalized === 'operations'\) loadWorkspaceAdminOperations\(\)/, 'maintenance tools should load operational dependencies on demand');
assert.match(admin, /function loadWorkspaceAdminOperations\(\)[\s\S]*ensureAppModule\('overview'\)[\s\S]*ensurePlayersLoaded\(\)/, 'heavy admin datasets should be isolated behind the operations loader');

assert.match(app, /function ensureHtmlToImage\(\)/, 'screenshot rendering should have an on-demand loader');
assert.doesNotMatch(app, /(?:team|database|competition):\s*\[[^\]]*html-to-image/, 'feature modules should not preload screenshot rendering');
assert.match(app, /function refreshHorizontalScrollAffordances/, 'mobile horizontal navigation should expose a shared overflow affordance');

console.log('frontend lazy asset checks passed');
