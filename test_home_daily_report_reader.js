const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const source = fs.readFileSync('static/js/app.home.js', 'utf8');
const context = {
    console,
    fetch: async () => ({ok: true}),
    setTimeout,
    clearTimeout,
    window: {setTimeout, addEventListener() {}},
    document: {getElementById: () => null, addEventListener() {}},
    teams: [{name: '阿森纳'}, {name: '切尔西'}, {name: '马赛'}, {name: '里昂'}],
    escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    },
};
context.globalThis = context;
vm.createContext(context);
vm.runInContext(source, context);

const regularStories = Array.from({length: 7}, (_, index) => (
    `甲级联赛｜马赛 vs 里昂：第${index + 1}轮 马赛 ${index % 3 + 1}:0 里昂。常规比赛解读。`
));
const report = {
    report_date: '2026-08-03',
    title: 'HEIGO 联赛日报｜8月3日',
    status: 'generated',
    match_count: 9,
    goal_count: 24,
    focus_count: 1,
    suspension_count: 1,
    focus_content: '今日共更新 9 场比赛。\n\n【焦点头版】\n【争冠·帽子戏法】超级联赛｜阿森纳 vs 切尔西：第1轮 阿森纳 4:1 切尔西。Saka 上演帽子戏法。',
    content: [
        '今日共更新 9 场比赛。',
        '',
        '【焦点头版】',
        '【争冠·帽子戏法】超级联赛｜阿森纳 vs 切尔西：第1轮 阿森纳 4:1 切尔西。Saka 上演帽子戏法。',
        '',
        '【常规战报】',
        ...regularStories,
        '冠军杯｜阿森纳 vs 切尔西：A组第1轮 阿森纳 2:0 切尔西。冠军杯比赛解读。',
        '',
        '【伤停动态】',
        '马赛：Player One（2黄）',
    ].join('\n'),
};

const pages = context.buildHomeDailyReportPages(report);
assert.equal(pages.length, 5, 'focus, two first-division pages, one Champions Cup page, and one suspension page should be created');
assert.equal(pages[0].kind, 'focus');
assert.equal(pages[0].entries.length, 1);
assert.equal(pages[1].label, '甲级 1');
assert.equal(pages[1].entries.length, 6);
assert.equal(pages[2].label, '甲级 2');
assert.equal(pages[2].entries.length, 1);
assert.equal(pages[3].label, '冠军杯');
assert.equal(pages[3].entries.length, 1);
assert.equal(pages[4].label, '伤停');
assert.equal(pages[4].entries.length, 1);
assert.ok(pages.slice(1).every(page => page.entries.every(entry => entry.section !== '焦点头版')));

const focusHtml = context.renderHomeDailyReportReader(report, 0);
assert.match(focusHtml, /焦点头版/);
assert.match(focusHtml, /home-daily-report-entity is-score">4:1</);
assert.match(focusHtml, /home-daily-report-entity is-team">阿森纳</);
assert.match(focusHtml, /home-daily-report-entity is-player">Saka</);
assert.match(focusHtml, /第 1 页，共 5 页/);

const eventHtml = context.renderHomeDailyReportReader(report, 1);
assert.match(eventHtml, /甲级/);
assert.doesNotMatch(eventHtml, /Saka 上演帽子戏法/);

assert.equal(context.shiftHomeDailyReportIsoDate('2026-03-01', -1), '2026-02-28');
assert.equal(context.shiftHomeDailyReportIsoDate('2026-01-01', -1), '2025-12-31');
assert.equal(context.shiftHomeDailyReportIsoDate('2025-12-31', 1), '2026-01-01');
assert.match(focusHtml, /input type="date" value="2026-08-03" max="2026-08-03"/);
assert.match(focusHtml, /EDITION ARCHIVE/);

console.log('home daily report reader checks passed');
