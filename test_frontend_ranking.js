const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const code = fs.readFileSync(path.join(__dirname, 'static/js/app.competition.js'), 'utf8');
const ratingBoard = {innerHTML: ''};
const context = {
    console,
    Intl,
    canManageRankings: true,
    document: {
        addEventListener() {},
        getElementById(id) { return id === 'ratingBoard' ? ratingBoard : null; },
    },
    window: {innerWidth: 1280, matchMedia() { return {matches: false}; }},
    escapeHtml(value) { return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;'); },
    renderUiState() { return '<div>empty</div>'; },
};
vm.createContext(context);
vm.runInContext(code, context, {filename: 'app.competition.js'});

context.rankingData = {
    initial_points: 1000,
    appearance_bonus: 20,
    transfer_rate: 0.1,
    total_matches: 1,
    rows: [{rank: 1, team_id: 1, team_name: 'Alpha FC', level: '超级', logo_path: '', base_points: 1100, total_points: 1120, matches: 1, wins: 1, draws: 0, losses: 0}],
    matches: [{id: 8, home_team_name: 'Alpha FC', away_team_name: 'Beta FC', home_score: 2, away_score: 1}],
};
context.renderRankingBoard();

assert.match(ratingBoard.innerHTML, /排位积分榜/);
assert.match(ratingBoard.innerHTML, /基础分/);
assert.match(ratingBoard.innerHTML, /总分/);
assert.match(ratingBoard.innerHTML, /Alpha FC/);
assert.match(ratingBoard.innerHTML, /添加排位比赛/);
assert.match(ratingBoard.innerHTML, /2<\/b><i>:\s*<\/i><b>1/);
assert.match(ratingBoard.innerHTML, /deleteRankingMatch\(8\)/);

context.canManageRankings = false;
context.renderRankingBoard();
assert.match(ratingBoard.innerHTML, /拥有“排位统计”权限/);
assert.doesNotMatch(ratingBoard.innerHTML, /deleteRankingMatch\(8\)/);
