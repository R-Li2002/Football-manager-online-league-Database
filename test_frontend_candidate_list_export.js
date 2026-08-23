const assert = require('node:assert/strict');
const fs = require('node:fs');

const code = fs.readFileSync('static/js/database.search.js', 'utf8');
const css = fs.readFileSync('static/css/pages/database.css', 'utf8');

assert.match(code, /function downloadCandidateListExcel\(/);
assert.match(code, /\/api\/candidate-lists\/\$\{numericListId\}\/export\.xlsx/);
assert.match(code, /\/api\/admin\/candidate-lists\/\$\{numericListId\}\/export\.xlsx/);
assert.match(code, /候选名单 Excel 已开始下载/);
assert.match(code, /candidate-public-export/);
assert.match(code, /downloadCandidateListExcel\(\$\{listId\}, true, this\)/);
assert.match(css, /\.candidate-public-card-actions/);
assert.match(css, /\.candidate-public-export/);

console.log('frontend candidate-list export checks passed');
