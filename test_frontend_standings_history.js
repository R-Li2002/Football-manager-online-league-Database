const assert = require('node:assert/strict');
const fs = require('node:fs');

const competition = fs.readFileSync('static/js/app.competition.js', 'utf8');
const competitionCss = fs.readFileSync('static/css/pages/competition.css', 'utf8');
const responsiveCss = fs.readFileSync('static/css/responsive.css', 'utf8');
const core = fs.readFileSync('static/js/app.core.js', 'utf8');

assert.match(competition, /openStandingsHistory\(/, 'standings should expose the history modal entry');
assert.match(competition, /\/api\/standings\/history\?level=/, 'history modal should load the per-round standings endpoint');
assert.match(competition, /class="standings-history-modal-overlay"/, 'history should open as a modal instead of a secondary page');
assert.match(competition, /buildStandingHistoryPath\(/, 'history should render team trajectories');
assert.match(competition, /data-history-node=/, 'history should use moving team crest nodes');
assert.match(competition, /toggleStandingHistoryPlayback\(/, 'history should support play and pause');
assert.match(competitionCss, /prefers-reduced-motion: reduce[\s\S]*standings-history-node/, 'history should respect reduced motion');
assert.match(competition, /本轮录入中/, 'incomplete rounds should be clearly labeled');
assert.match(competitionCss, /\.standings-history-node\s*\{[\s\S]*transition:\s*transform/, 'crest nodes should animate with compositor-friendly transforms');
assert.match(competitionCss, /\.standings-history-modal-overlay/, 'desktop history modal should be styled');
assert.match(responsiveCss, /\.standings-history-modal-overlay[\s\S]*place-items:\s*end stretch/, 'mobile history should use a bottom-sheet modal');
assert.doesNotMatch(responsiveCss, /\.standings-history-speeds button\s*\{[\s\S]*?\}\s*\}\s*\.standings-zone-legend/, 'history rules must not close the mobile standings media query early');
assert.match(core, /play:\s*'<path/, 'shared icon vocabulary should include play');
assert.match(core, /pause:\s*'<path/, 'shared icon vocabulary should include pause');

console.log('standings history frontend checks passed');
