const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = __dirname;
const html = fs.readFileSync(path.join(root, 'static/app.html'), 'utf8');
const admin = fs.readFileSync(path.join(root, 'static/js/app.admin.js'), 'utf8');
const competition = fs.readFileSync(path.join(root, 'static/js/app.competition.js'), 'utf8');

assert.match(competition, /exportStandingsExcel/);
assert.match(competition, /\/api\/export\/standings\.xlsx\?level=/);
assert.match(competition, />Excel表格<\/button>/);
assert.doesNotMatch(competition, /onclick="selectScheduleImportFile\(\)">上传赛程/);

assert.match(html, /id="workspaceImportsView"/);
assert.match(html, /id="scheduleImportFile"/);
assert.match(html, /id="rosterImportFile"/);
assert.match(html, /id="attributesImportFile"/);
assert.equal((html.match(/id="rosterImportFile"/g) || []).length, 1);
assert.equal((html.match(/id="formalImportSummaryCard"/g) || []).length, 1);
assert.match(admin, /uploadWorkspaceScheduleFile/);
assert.match(admin, /\/api\/admin\/matches\/import\/upload/);

console.log('standings export and unified import frontend checks passed');
