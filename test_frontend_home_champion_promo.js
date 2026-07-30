const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const homeCode = fs.readFileSync(path.join(__dirname, 'static/js/app.home.js'), 'utf8');

function createElement(id) {
    const classes = new Set();
    return {
        id,
        hidden: true,
        className: '',
        innerHTML: '',
        textContent: '',
        value: '',
        classList: {
            add(...tokens) { tokens.forEach(token => classes.add(token)); },
            remove(...tokens) { tokens.forEach(token => classes.delete(token)); },
            contains(token) { return classes.has(token); },
        },
        setAttribute() {},
        removeAttribute() {},
        addEventListener() {},
        focus() {},
    };
}

const elements = new Map();
[
    'homePromotionBoard',
    'heroTeamCount',
    'heroPlayerCount',
    'heroDbPlayerCount',
    'heroModeBadge',
    'heroPlayerSearch',
].forEach(id => elements.set(id, createElement(id)));

const storageState = new Map();
const localStorage = {
    getItem(key) {
        return storageState.get(key) || '';
    },
    setItem(key, value) {
        storageState.set(key, String(value));
    },
};

const brackets = {
    champions_cup: {
        competition: 'champions_cup',
        title: '冠军杯',
        trophy_url: '/static/images/trophy/champion.png',
        stages: [{
            key: 'final',
            matches: [{
                status: 'played',
                winner_team_id: 7,
                winner_team_name: 'R. Madrid',
                home_score: 4,
                away_score: 2,
                updated_at: '2026-07-16T10:00:00',
            }],
        }],
    },
    league_cup: {
        competition: 'league_cup',
        title: '联盟杯',
        trophy_url: '/league.png',
        stages: [{
            key: 'final',
            matches: [{
                status: 'played',
                winner_team_id: 79,
                winner_team_name: 'Leicester City',
                home_score: 5,
                away_score: 6,
                updated_at: '2026-07-16T15:27:39',
            }],
        }],
    },
    wumingjian_cup: {competition: 'wumingjian_cup', title: '无铭剑杯', trophy_url: '/fa.png', stages: []},
};

const configuredPromotions = [
    {id: 1, content_type: 'honor', theme: 'gold', icon: 'trophy', eyebrow: '冠军杯 · CHAMPION', title: 'R. Madrid 荣膺冠军杯冠军', body: '决赛 4 : 2 · 主教练 HEIGO', image_url: '/logos/rm.png', action_kind: 'tab', action_label: '查看夺冠之路', action_target: 'competition:standings:冠军杯', is_dismissible: true, updated_at: '2026-07-16T10:00:00'},
    {id: 2, content_type: 'announcement', theme: 'blue', icon: 'list', eyebrow: 'CANDIDATE LISTS', title: '87届初期强制名单已发布', body: '进入候选名单查看。', action_kind: 'tab', action_label: '查看名单', action_target: 'database:candidates', is_dismissible: true, updated_at: '2026-07-16T15:27:39'},
];

let modalPayload = null;
const navigationCalls = [];
const context = {
    console,
    document: {
        getElementById(id) {
            return elements.get(id) || null;
        },
    },
    window: {
        localStorage,
        location: {assign(target) { navigationCalls.push(['url', target]); }},
        setTimeout(callback) {
            callback();
            return 1;
        },
    },
    localStorage,
    teams: [
        {id: 7, name: 'R. Madrid', manager: 'HEIGO', logo_path: '/logos/rm.png'},
        {id: 79, name: 'Leicester City', manager: 'Blue Fox', logo_path: '/logos/leicester.png'},
    ],
    allPlayers: [],
    defaultAttributeVersionPlayerCount: 0,
    isAdmin: false,
    escapeHtml(value) {
        return String(value ?? '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#039;');
    },
    fetch: async url => ({ok: url === '/api/home-promotions', json: async () => configuredPromotions}),
    showModal(title, body) {
        modalPayload = {title, body};
    },
    closeModal() {},
    showTab(tabName) {
        navigationCalls.push(['tab', tabName]);
    },
    showCompetitionSubtab(subtab) {
        navigationCalls.push(['subtab', subtab]);
    },
    showDatabaseSubtab(subtab) {
        navigationCalls.push(['database', subtab]);
    },
    setCompetitionLevel(level) {
        navigationCalls.push(['level', level]);
    },
    syncAppHistory(mode) {
        navigationCalls.push(['history', mode]);
    },
};
context.window.document = context.document;

vm.createContext(context);
vm.runInContext(homeCode, context, {filename: 'app.home.js'});

(async () => {
    const promotions = await context.loadHomePromotions({force: true});
    const banner = elements.get('homePromotionBoard');

    assert.equal(promotions.length, 2);
    assert.equal(banner.hidden, false);
    assert.match(banner.innerHTML, /R\. Madrid/);
    assert.match(banner.innerHTML, /87届初期强制名单已发布/);
    assert.match(banner.innerHTML, /主教练 HEIGO/);
    assert.match(banner.innerHTML, /决赛 4 : 2/);
    assert.match(banner.innerHTML, /\/logos\/rm\.png/);

    context.dismissHomePromotion(1);
    assert.doesNotMatch(banner.innerHTML, /R\. Madrid/);
    assert.match(banner.innerHTML, /87届初期强制名单已发布/);
    assert.match(storageState.get('heigoHomePromotionsDismissed'), /2026-07-16/);

    await context.openHomePromotionAction(1);
    assert.deepEqual(navigationCalls, [
        ['tab', 'competition'],
        ['subtab', 'standings'],
        ['level', '冠军杯'],
        ['history', 'push'],
    ]);
})();
