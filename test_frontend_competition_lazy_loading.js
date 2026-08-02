const assert = require('node:assert/strict');
const fs = require('node:fs');

const code = fs.readFileSync('static/js/app.competition.js', 'utf8');

assert.match(code, /var competitionLoadedSections = new Set\(\)/, 'competition sections should track independent load state');
assert.match(code, /var competitionSectionLoadPromises = new Map\(\)/, 'duplicate requests for one section should share an in-flight promise');
assert.match(code, /async function loadCompetitionSection\(section = currentCompetitionSubtab/, 'competition should expose a section loader');
assert.match(code, /competitionSectionLoadPromises\.has\(normalizedSection\)/, 'the section loader should reuse in-flight requests');
assert.match(code, /function renderCompetitionSectionError\(section\)/, 'a section should own its failure state');
assert.match(code, /其他统计模块不受影响/, 'failure copy should make isolation explicit');

const ratingBranch = code.match(/if \(section === 'rating'\) \{([\s\S]*?)\n    \}/)?.[1] || '';
assert.match(ratingBranch, /\/api\/rankings/, 'rating should load its own endpoint');
assert.doesNotMatch(ratingBranch, /\/api\/matches|\/api\/standings|\/api\/suspensions/, 'rating should not load unrelated competition data');

const playerBranch = code.match(/if \(section === 'playerRankings'\) \{([\s\S]*?)\n    \}/)?.[1] || '';
assert.match(playerBranch, /\/api\/player-rankings/, 'player rankings should load its own endpoint');
assert.doesNotMatch(playerBranch, /\/api\/matches|\/api\/standings|\/api\/rankings'/, 'player rankings should not load unrelated competition data');

assert.match(code, /showCompetitionSubtab[\s\S]*loadCompetitionSection\(currentCompetitionSubtab\)/, 'switching tabs should load only the selected section');
assert.match(code, /function invalidateCompetitionSections\(/, 'writes should invalidate cached sections explicitly');

console.log('frontend competition lazy-loading checks passed');
