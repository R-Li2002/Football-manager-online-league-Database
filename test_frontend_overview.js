const assert = require('assert');
const fs = require('fs');

const app = fs.readFileSync('static/app.js', 'utf8');
const html = fs.readFileSync('static/app.html', 'utf8');
const css = [
    fs.readFileSync('static/app.css', 'utf8'),
    fs.readFileSync('static/css/pages/team.css', 'utf8'),
    fs.readFileSync('static/css/responsive.css', 'utf8'),
].join('\n');
const core = fs.readFileSync('static/js/app.core.js', 'utf8');
const overview = fs.readFileSync('static/js/app.overview.js', 'utf8');
const players = fs.readFileSync('static/js/app.players.js', 'utf8');

assert.match(overview, /function renderOverview\(\)[\s\S]*renderTeamsTable\(\);\n}/, 'overview rendering should always replace the initial team-table loading state');
assert(overview.includes("allPlayers.length || Number(homeSummary?.player_count || 0)"), 'overview should keep the lightweight home player count before the full roster is loaded');
assert(app.includes('async function openFullLeagueRoster(options = {})'), 'overview should expose a complete league roster entry');
assert(app.includes("await showTab('players', null, {syncHistory: false})"), 'complete roster entry should reuse the existing league roster module');
assert(app.includes('resetPlayers({pushHistory: false})'), 'complete roster entry should clear team and player filters');
assert.strictEqual((html.match(/完整联赛名单/g) || []).length >= 2, true, 'overview and roster headers should expose the complete league roster label');
assert(html.includes('onclick="openFullLeagueRoster()"'), 'team list header should switch to the complete league roster');
assert(html.includes("onclick=\"showTab('overview')\""), 'complete roster header should switch back to team overview');
assert(players.includes("buildRosterHeader('UID', 'uid'"), 'complete roster should retain UID');
assert(players.includes("buildRosterHeader('初始CA', 'initial_ca'"), 'complete roster should retain initial CA');
assert(players.includes("buildRosterHeader('当前CA', 'ca'"), 'complete roster should retain current CA');
assert(players.includes("buildRosterHeader('PA', 'pa'"), 'complete roster should retain PA');
assert(players.includes("buildRosterHeader('位置', 'position'"), 'complete roster should retain position');
assert(players.includes("buildRosterHeader('国籍', 'nationality'"), 'complete roster should retain nationality');
assert(players.includes("buildRosterHeader('所属球队', 'team_name'"), 'complete roster should retain team');
assert(players.includes("buildRosterHeader('工资', 'wage'"), 'complete roster should retain wage');
assert(css.includes('.league-data-switch-button.is-active'), 'league data switch should have a clear active state');
assert(overview.includes('return renderLeagueLevelBadge(level);'), 'overview should reuse the shared league signature');
assert(core.includes("'超级': {className: 'level-super', character: '超', english: 'SUPER'}"), 'super league signature should use the Chinese super mark');
assert(core.includes("'甲级': {className: 'level-a', character: '甲', english: 'FIRST'}"), 'first division signature should use the Chinese first mark');
assert(core.includes("'乙级': {className: 'level-b', character: '乙', english: 'SECOND'}"), 'second division signature should use the Chinese second mark');
assert(!core.includes('league-tier-shield') && !core.includes('league-tier-wings'), 'rejected shield and ribbon markup should be removed');
assert(css.includes('font: 900 .82rem/1 var(--font-data);'), 'league monograms should use the crisp data typeface');
assert(css.includes('.league-level-mark {\n    font-family: var(--font-cn-display);'), 'Chinese league marks should use the same display font as the website');
assert(css.includes('.league-level-signature.is-compact { min-height: 27px; padding: 0; border: 0;'), 'compact monograms should not carry a redundant outer frame');
assert(css.includes('.league-level-signature.level-super { --league-level-color: #9c82ff;'), 'super league signature should use the violet palette');
assert(css.includes('.league-level-signature.level-a { --league-level-color: #55aeff;'), 'first division signature should use the blue palette');
assert(css.includes('.league-level-signature.level-b { --league-level-color: #45cf9a;'), 'second division signature should use the mint palette');
assert(overview.includes("'wage_cap', this.value"), 'admin team overview should allow direct wage-cap editing');
assert(overview.includes('const hasWageCapOverride = Number.isFinite(wageCapOverride) && wageCapOverride > 0;'), 'team wage-cap override should take priority over the level default');
assert(css.includes('.editable-input.team-wage-cap-input'), 'team wage-cap editor should use a dedicated compact style');

console.log('frontend overview checks passed');
