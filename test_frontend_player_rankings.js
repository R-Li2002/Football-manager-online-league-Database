const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const competitionCode = fs.readFileSync(path.join(__dirname, 'static/js/app.competition.js'), 'utf8');
const playerRankingsBoard = {innerHTML: ''};
let mobileViewport = false;

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

const document = {
    addEventListener() {},
    getElementById(id) {
        return id === 'playerRankingsBoard' ? playerRankingsBoard : null;
    },
};

const context = {
    console,
    document,
    window: {
        innerWidth: 1280,
        matchMedia() {
            return {matches: mobileViewport};
        },
    },
    escapeHtml,
    htmlJsString(value) {
        return escapeHtml(JSON.stringify(String(value ?? '')));
    },
};

vm.createContext(context);
vm.runInContext(competitionCode, context, {filename: 'app.competition.js'});

context.playerRankingData = {
    levels: ['超级'],
    rows: [{
        level: '超级',
        player_uid: 83320135,
        player_name: 'António Silva',
        team_name: 'A. Bilbao',
        goals: 3,
        assists: 1,
        mvps: 2,
        appearances: 4,
    }],
    coverage: [{level: '超级', played_matches: 4, matches_with_events: 4}],
};
context.currentCompetitionLevel = '超级';
context.currentPlayerRankingType = 'goals';

function assertDesktopRankingPlayerNameLinksToAttributeDetail() {
    mobileViewport = false;
    context.renderPlayerRankingsBoard();

    assert.match(playerRankingsBoard.innerHTML, /class="player-ranking-player-link /);
    assert.match(playerRankingsBoard.innerHTML, /openCompetitionPlayerAttributeDetail\(83320135, 'playerRankings'\)/);
    assert.match(playerRankingsBoard.innerHTML, />António Silva<\/button>/);
}

function assertMobileRankingPlayerNameLinksToAttributeDetail() {
    mobileViewport = true;
    context.renderPlayerRankingsBoard();

    assert.match(playerRankingsBoard.innerHTML, /player-ranking-player-link mobile-player-ranking-name/);
    assert.match(playerRankingsBoard.innerHTML, /openCompetitionPlayerAttributeDetail\(83320135, 'playerRankings'\)/);
}

function assertMissingUidRemainsPlainText() {
    const markup = context.renderPlayerRankingPlayerName({player_uid: null, player_name: 'Legacy Player'});

    assert.match(markup, /<span/);
    assert.doesNotMatch(markup, /onclick=/);
}

assertDesktopRankingPlayerNameLinksToAttributeDetail();
assertMobileRankingPlayerNameLinksToAttributeDetail();
assertMissingUidRemainsPlainText();
