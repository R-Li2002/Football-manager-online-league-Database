const assert = require('node:assert/strict');
const fs = require('node:fs');

const code = fs.readFileSync('static/js/app.competition.js', 'utf8');

assert.match(code, /var competitionLoadedSections = new Set\(\)/, 'competition sections should track independent load state');
assert.match(code, /var competitionSectionLoadPromises = new Map\(\)/, 'duplicate requests for one section should share an in-flight promise');
assert.match(code, /var competitionSectionDataCache = new Map\(\)/, 'competition responses should be cached by section and competition');
assert.match(code, /function getCompetitionSectionCacheKey\(section, level = currentCompetitionLevel\)/, 'cache keys should include the active competition');
assert.match(code, /async function loadCompetitionSection\(section = currentCompetitionSubtab/, 'competition should expose a section loader');
assert.match(code, /competitionSectionLoadPromises\.has\(cacheKey\)/, 'the section loader should reuse in-flight requests for one competition');
assert.match(code, /function renderCompetitionSectionError\(section, failureType = 'request'\)/, 'a section should own request and render failure states');
assert.match(code, /其他统计模块不受影响/, 'failure copy should make isolation explicit');
assert.match(code, /function applyAndRenderCompetitionSectionPayload\(/, 'section rendering should have its own guarded boundary');
assert.match(code, /Failed to request competition section/, 'request failures should be reported separately');
assert.match(code, /Failed to render competition section/, 'render failures should be reported separately');
assert.match(code, /failureType === 'render'/, 'render errors should not be mislabeled as data loading failures');
assert.match(code, /\/api\/matches\?level=\$\{encodeURIComponent\(level\)\}/, 'league schedules should request only the current level');
assert.match(code, /\/api\/standings\?level=\$\{encodeURIComponent\(level\)\}/, 'league standings should request only the current level');
assert.match(code, /\/api\/suspensions\?level=\$\{encodeURIComponent\(level\)\}/, 'suspensions should request only the current level');
assert.match(code, /\/api\/player-rankings\?level=\$\{encodeURIComponent\(level\)\}/, 'player rankings should request only the current level');
assert.doesNotMatch(code, /fetchCompetitionJson\('\/api\/matches'\)/, 'league schedules should not fall back to the full schedule');
assert.doesNotMatch(code, /fetchCompetitionJson\('\/api\/standings'\)/, 'standings should not fetch all levels');
assert.doesNotMatch(code, /\/api\/cups\/champions_cup\/(?:groups|bracket)'/, 'cup loading should not hard-code unrelated champions cup requests');
assert.doesNotMatch(code, /\/api\/cups\/league_cup\/(?:groups|bracket)'/, 'cup loading should not hard-code unrelated league cup requests');

const requestBlock = code.match(/async function requestCompetitionSection\([\s\S]*?\n\}\n\nasync function loadCompetitionSection/)?.[0] || '';
const ratingBranch = requestBlock.match(/if \(section === 'rating'\) \{([\s\S]*?)\n    \}/)?.[1] || '';
assert.match(ratingBranch, /\/api\/rankings/, 'rating should load its own endpoint');
assert.doesNotMatch(ratingBranch, /\/api\/matches|\/api\/standings|\/api\/suspensions/, 'rating should not load unrelated competition data');

const playerBranch = requestBlock.match(/if \(section === 'playerRankings'\) \{([\s\S]*?)\n    \}/)?.[1] || '';
assert.match(playerBranch, /\/api\/player-rankings/, 'player rankings should load its own endpoint');
assert.doesNotMatch(playerBranch, /\/api\/matches|\/api\/standings|\/api\/rankings'/, 'player rankings should not load unrelated competition data');

assert.match(code, /showCompetitionSubtab[\s\S]*loadCompetitionSection\(currentCompetitionSubtab\)/, 'switching tabs should load only the selected section');
assert.match(code, /setCompetitionLevel[\s\S]*getCompetitionSectionCacheKey\(currentCompetitionSubtab\)[\s\S]*loadCompetitionSection\(currentCompetitionSubtab\)/, 'switching competitions should restore or load that competition scope');
assert.match(code, /function invalidateCompetitionSections\(/, 'writes should invalidate cached sections explicitly');

console.log('frontend competition lazy-loading checks passed');
