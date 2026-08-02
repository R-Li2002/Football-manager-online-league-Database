const assert = require('node:assert/strict');
const fs = require('node:fs');

const html = fs.readFileSync('static/app.html', 'utf8');
const app = fs.readFileSync('static/app.js', 'utf8');
const core = fs.readFileSync('static/js/app.core.js', 'utf8');
const responsive = fs.readFileSync('static/css/responsive.css', 'utf8');
const shell = fs.readFileSync('static/css/shell.css', 'utf8');
const admin = fs.readFileSync('static/js/app.admin.js', 'utf8');
const coaches = fs.readFileSync('static/js/app.coaches.js', 'utf8');
const mainScripts = [
    'static/app.js',
    ...fs.readdirSync('static/js')
        .filter(name => /^(?:app\.|database\.).*\.js$/.test(name))
        .map(name => `static/js/${name}`),
].map(path => fs.readFileSync(path, 'utf8')).join('\n');

const themeScriptIndex = html.indexOf("localStorage.getItem('themeMode')");
const firstStylesheetIndex = html.indexOf('/static/app.css');
assert(themeScriptIndex > 0 && themeScriptIndex < firstStylesheetIndex, 'saved theme should be resolved before blocking stylesheets');
assert.match(html, /<body>\s*<script>document\.body\.classList\.toggle\('light-mode'/, 'the body theme should be applied before visible content is parsed');
assert.doesNotMatch(html, /<body class="light-mode">/, 'the first paint should not be forced to light mode');

const initBlock = app.match(/async function init\(\) \{([\s\S]*?)\n\}\n\nfunction handleTablistKeyboard/)?.[1] || '';
assert.match(initBlock, /Promise\.allSettled\(/, 'startup endpoints should settle independently');
assert.match(initBlock, /await initializeAppHistory\(\)/, 'history restoration should still run after partial bootstrap failure');
assert.match(initBlock, /公开页面仍可使用；刷新页面即可重试/, 'partial startup failure should provide a recovery path');

assert.match(core, /const DEFAULT_REQUEST_TIMEOUT_MS = 15000/, 'normal API reads should use a bounded timeout');
assert.match(core, /const LONG_REQUEST_TIMEOUT_MS = 120000/, 'uploads and exports should retain a larger bounded timeout');
assert.match(core, /async function fetchWithTimeout\(input, options = \{\}\)/, 'the main app should expose one request timeout helper');
assert.match(core, /timeoutError\.code = 'REQUEST_TIMEOUT'/, 'timeouts should be distinguishable from ordinary request failures');
assert.doesNotMatch(mainScripts, /(?<!globalThis\.)\bfetch\(/, 'main-site requests should use the shared timeout helper');
assert.match(core, /globalThis\.fetch\(input/, 'the native fetch calls should stay inside the timeout helper and its compatibility fallback');
assert.match(core, /heigoPendingWorkContext:v1/, 'expired work sessions should use a versioned session-scoped recovery record');
assert.match(core, /capturePendingWorkContext\(\{reason: 'work-session-expired'\}\)/, 'work requests should preserve the current context before clearing expired identity');
assert.match(core, /async function resumePendingWorkContext\(\)/, 'the shared core should restore saved work context after authentication');
assert.match(core, /editor: matchEventEditorMatchId > 0/, 'an open match-event editor should be recoverable through its local draft');
assert.match(admin, /capturePendingWorkContext\(\{reason: 'admin-session-expired'\}\)/, 'admin requests should preserve context before handling a 401');
assert.match(admin, /await resumePendingWorkContext\(\)/, 'workspace and admin logins should resume pending work');
assert.match(coaches, /await resumePendingWorkContext\(\)/, 'coach login should resume pending work');

assert.match(shell, /\.global-coach-copy small[\s\S]*font-size: var\(--text-xs\)/, 'coach identity helper text should use the 12px floor');
assert.match(responsive, /\.mobile-standings-strip em,[\s\S]*\.mobile-bottom-nav-item[\s\S]*font-size: var\(--text-xs\) !important/, 'visible mobile helper labels should use the 12px floor');

console.log('frontend bootstrap resilience checks passed');
