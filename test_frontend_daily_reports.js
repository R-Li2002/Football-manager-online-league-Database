const assert = require('assert');
const fs = require('fs');

const html = fs.readFileSync('static/app.html', 'utf8');
const adminCode = fs.readFileSync('static/js/app.admin.js', 'utf8');
const homeCode = fs.readFileSync('static/js/app.home.js', 'utf8');
const css = fs.readFileSync('static/app.css', 'utf8');
const botPlugin = fs.readFileSync('bot_nonebot/src/plugins/heigo_bot/plugin.py', 'utf8');

assert.match(html, /data-workspace-view="dailyReports"[\s\S]*?>每日日报</, 'workspace navigation should expose daily reports');
assert.match(html, /id="workspaceDailyReportsView"[\s\S]*?日报终稿台[\s\S]*?日报话术库/, 'workspace should contain report desk and narrative library');
assert.match(html, /workspaceDailyReportContent[\s\S]*?保存草稿[\s\S]*?发布日报/, 'report desk should support editing, draft save and publishing');
assert.match(adminCode, /generateWorkspaceDailyReport[\s\S]*?\/api\/workspace\/daily-reports\/generate/, 'workspace should regenerate daily reports from current data');
assert.match(adminCode, /showWorkspaceDailyTemplateEditor[\s\S]*?saveWorkspaceDailyTemplate/, 'workspace should add and edit narrative templates');
assert.match(adminCode, /toggleWorkspaceDailyTemplate[\s\S]*?deleteWorkspaceDailyTemplate/, 'workspace should disable and delete narrative templates');
assert.match(homeCode, /renderHomeDailyReport[\s\S]*?openHomeDailyReport/, 'home dashboard should expose the current daily report');
assert.match(css, /\.workspace-daily-report-layout[\s\S]*?\.workspace-daily-template-library/, 'daily report workspace should have a dedicated responsive layout');
assert.match(botPlugin, /heigo_daily_report[\s\S]*?HEIGO 联赛日报/, 'bot scheduler should broadcast the HEIGO daily report');
assert.match(html, /id="comparisonOverlay"[^>]*aria-hidden="true"[^>]*hidden/, 'comparison workspace should be hidden before its lazy stylesheet loads');
assert.match(html, /id="compareDock"[^>]*hidden/, 'comparison dock should not flash during initial page load');
assert.match(botPlugin, /focus_only=True/, 'bot should request the focus front-page image');

console.log('Frontend daily report checks passed.');
