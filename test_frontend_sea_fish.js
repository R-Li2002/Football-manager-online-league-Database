const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const html = fs.readFileSync(path.join(__dirname, 'static/app.html'), 'utf8');
const adminCode = fs.readFileSync(path.join(__dirname, 'static/js/app.admin.js'), 'utf8');

assert.match(html, /id="seaFishCard"/);
assert.match(html, /id="seaFishUid"/);
assert.match(html, /id="seaFishTeam"/);
assert.match(html, /支持球员数据库及所有非三级联赛球员/);

assert.match(adminCode, /\/api\/admin\/sea-fish/);
assert.match(adminCode, /function prepareSeaFish/);
assert.match(adminCode, /async function seaFishPlayer/);
assert.match(adminCode, /初始 CA/);
assert.match(adminCode, /fish_sea_player/);
