const assert = require('node:assert/strict');
const fs = require('node:fs');

const html = fs.readFileSync('static/app.html', 'utf8');
const updatesHtml = fs.readFileSync('static/updates.html', 'utf8');
const feedbackHtml = fs.readFileSync('static/data-feedback.html', 'utf8');
const legacyCss = fs.readFileSync('static/app.css', 'utf8');
const shellCss = fs.readFileSync('static/css/shell.css', 'utf8');
const databaseCss = fs.readFileSync('static/css/pages/database.css', 'utf8');
const competitionCss = fs.readFileSync('static/css/pages/competition.css', 'utf8');
const teamCss = fs.readFileSync('static/css/pages/team.css', 'utf8');
const responsiveCss = fs.readFileSync('static/css/responsive.css', 'utf8');
const appCode = fs.readFileSync('static/app.js', 'utf8');

const orderedStyles = [
    '/static/app.css',
    '/static/css/ui-foundation.css',
    '/static/css/shell.css',
    '/static/css/responsive.css',
];

let previousIndex = -1;
for (const stylesheet of orderedStyles) {
    const index = html.indexOf(stylesheet);
    assert(index > previousIndex, `${stylesheet} should load after the preceding CSS layer`);
    previousIndex = index;
}

for (const stylesheet of orderedStyles.slice(1)) {
    assert(html.includes(`${stylesheet}?v=__STATIC_ASSET_VERSION__`), `${stylesheet} should use the release cache key`);
}

for (const stylesheet of [
    '/static/css/pages/database.css',
    '/static/css/pages/competition.css',
    '/static/css/pages/team.css',
]) {
    assert(!html.includes(stylesheet), `${stylesheet} should be loaded only when its module opens`);
}
assert.match(appCode, /const APP_MODULE_STYLES = \{[\s\S]*overview: \['\/static\/css\/pages\/team\.css'\][\s\S]*team: \['\/static\/css\/pages\/team\.css'\][\s\S]*competition: \['\/static\/css\/pages\/competition\.css'\][\s\S]*database: \['\/static\/css\/pages\/database\.css'\]/, 'page styles should be mapped to their owning modules');
assert.match(appCode, /function loadAppStyle\(path\)[\s\S]*document\.head\.insertBefore\(link, responsiveStyle \|\| null\)/, 'lazy page styles should retain their position before responsive overrides');

for (const subpage of [updatesHtml, feedbackHtml]) {
    assert(subpage.indexOf('/static/css/shell.css') > subpage.indexOf('/static/css/ui-foundation.css'), 'subpages should load shell ownership after the foundation');
    assert(subpage.indexOf('/static/css/responsive.css') > subpage.indexOf('/static/css/shell.css'), 'subpages should load responsive ownership after shell');
    assert(subpage.indexOf('/static/subpages.css') > subpage.indexOf('/static/css/responsive.css'), 'subpage-specific rules should remain the final local layer');
}

for (const forbidden of [
    'header.shell-header',
    '.shell-topbar',
    '.shell-actions',
    '.global-coach-account',
    '.global-coach-login',
    '.global-coach-trigger',
    '.nav-tabs',
    '.nav-tab',
    '.mobile-bottom-nav',
    '.mobile-more-menu',
    '.site-footer',
    '#competition',
    '.competition-',
    '.standings-',
    '.schedule-',
    '.match-event',
    '.suspension-',
    '.player-ranking',
    '.mobile-standings',
    '.mobile-schedule',
    '#overview',
    '#team',
    '.overview-',
    '.teams-table',
    '.team-center-',
    '.team-detail-',
    '.team-hero',
    '.team-panel',
    '.team-stat-strip',
    '.team-spine-',
    '.team-match-',
    '.team-next-',
    '.team-journey-',
    '.team-cup-',
    '.team-discipline-',
    '.team-power-',
    '.team-roster-',
    '.team-lineup-',
    '.team-skeleton-',
    '.team-wage-',
    '.team-debug-',
    '.team-logo-upload-',
    '.info-grid',
    '.info-card',
    'body:not([data-active-tab="home"]) .shell-topbar',
    'body:not([data-active-tab="home"]) .header-logo',
    '.database-module-hero',
    '.database-module-marks',
    '#database',
    '#dbDetailView',
    '#playerDetailContent',
    '.database-',
    '.db-',
    '.candidate-',
    '.compare-',
    '.comparison-',
    '.power-ranking-',
    '.weighted-power-',
    '.reaction-',
    '.mobile-reaction-',
    '#dbTacticsView',
    '#dbPowerRankingView',
    '#dbReactionLeaderboardView',
    '#dbListView',
    '#candidateListsBoard',
    '#candidateAdminItems',
    '.power-player-link',
    '.power-growth-badge',
    '.mobile-power-ranking',
    '.power-card-',
    '.detail-compare-button',
    '.heigo-power-relative',
    '.heigo-power-percent',
    '.position-map-card',
    '.attributes-panel',
    '.growth-indicator',
    '.growth-positive',
    '.growth-negative',
    '.player-detail-',
    '.player-identity-',
    '.player-radar-',
    '.attribute-',
    '.growth-preview-',
    '.match-event-own-goal-note',
    '.schedule-event-own-goal',
]) {
    assert(!legacyCss.includes(forbidden), `${forbidden} should not be reintroduced into legacy app.css`);
}
assert.doesNotMatch(legacyCss, /(^|[,\s])\.[\w-]*cup-/m, 'cup selectors should not be reintroduced into legacy app.css');
assert.doesNotMatch(legacyCss, /(^|[\s>+~,(])\.team-name(?=$|[\s>+~.:,#[])/m, 'overview team-name selector should not be reintroduced into legacy app.css');

assert.match(shellCss, /HEIGO shell ownership/, 'shell.css should declare its selector ownership');
assert.match(shellCss, /\.global-coach-menu/, 'coach account menu should belong to the shell layer');
assert.match(shellCss, /\.nav-tabs\.glass-card/, 'desktop primary navigation should belong to the shell layer');
assert.match(shellCss, /\.site-footer/, 'the global footer should belong to the shell layer');
assert.match(responsiveCss, /\.mobile-bottom-nav/, 'mobile primary navigation should belong to the responsive layer');
assert.match(responsiveCss, /\.mobile-more-menu/, 'mobile overflow navigation should belong to the responsive layer');
assert.match(databaseCss, /Player database page ownership/, 'database.css should declare its selector ownership');
assert.match(databaseCss, /\.candidate-public-search-section/, 'candidate lists should belong to the database page layer');
assert.match(databaseCss, /\.player-detail-shell/, 'player details should belong to the database page layer');
assert.match(databaseCss, /\.comparison-table/, 'player comparison should belong to the database page layer');
assert.match(databaseCss, /\.db-tactics-pitch/, 'database tactics should belong to the database page layer');
assert.match(databaseCss, /\.power-ranking-hero/, 'power rankings should belong to the database page layer');
assert.match(databaseCss + responsiveCss, /\.reaction-ranking-results/, 'reaction rankings should belong to the database page or responsive layer');
assert.match(competitionCss, /Competition page ownership/, 'competition.css should declare its selector ownership');
assert.match(teamCss, /Team center and league overview page ownership/, 'team.css should declare its selector ownership');
assert.match(teamCss, /\.team-center-landing/, 'team center landing should belong to the team page layer');
assert.match(teamCss, /\.team-detail-primary-grid/, 'team detail layout should belong to the team page layer');
assert.match(teamCss, /\.team-cup-opponent-row/, 'team cup outlook should belong to the team page layer');
assert.match(teamCss, /\.overview-summary-card/, 'league overview should belong to the team page layer');
assert.match(competitionCss, /\.standings-table/, 'standings should belong to the competition page layer');
assert.match(competitionCss, /\.schedule-match-row/, 'schedule rows should belong to the competition page layer');
assert.match(competitionCss, /\.player-ranking-table/, 'player rankings should belong to the competition page layer');
assert.match(competitionCss, /\.suspension-team-card/, 'suspensions should belong to the competition page layer');
assert.match(competitionCss, /\.cup-group-stage-shell/, 'cup group stages should belong to the competition page layer');
assert.match(responsiveCss, /Cross-module responsive ownership/, 'responsive.css should declare its breakpoint ownership');
assert.doesNotMatch(legacyCss, /Final cascade: compact database headings/, 'legacy CSS should not rely on the removed final override patch');
assert.doesNotMatch(legacyCss, /Function pages use a compact application shell/, 'the obsolete compact-shell override should stay removed');

console.log('frontend CSS layer ownership checks passed');
