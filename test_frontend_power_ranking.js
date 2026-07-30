const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, 'static/js/database.search.js'), 'utf8');
const code = source.slice(source.indexOf('function getPowerShapeLabel'), source.indexOf('function sortDbPlayers'));
const table = {innerHTML: ''};
const title = {textContent: ''};
const context = {
    console,
    URLSearchParams,
    document: {getElementById(id) { return id === 'dbPowerRankingTable' ? table : id === 'dbPowerRankingTitle' ? title : null; }},
    escapeHtml(value) { return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;'); },
};
vm.createContext(context);
vm.runInContext(code, context, {filename: 'database.search.js'});

context.renderPowerRanking({
    shape: 'all', limit: 'all', data_version: '2630',
    items: [{rank: 1, uid: 7, name: '潜力球员', growth_step: 3, weighted_power: 88.67, heigo_power: 82.34, top_percent: 3.18, ca: 100, projected_ca: 150, pa: 170, potential_gap: 70, position: 'AMC', heigo_club: '测试队', club: 'Test FC', data_version: '2630'}],
});

assert.match(table.innerHTML, /潜力球员/);
assert.match(table.innerHTML, /power-growth-badge">\+3/);
assert.match(table.innerHTML, /previewStep: 3/);
assert.match(table.innerHTML, /88\.67/);
assert.match(table.innerHTML, /82\.34/);
assert.match(table.innerHTML, /前 4%/);
assert.match(table.innerHTML, /HEIGO战力 \/ 联赛位置/);
assert.match(table.innerHTML, /mobile-power-ranking/);
assert.match(title.textContent, /全部 1 条/);
