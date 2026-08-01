const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const databaseCode = fs.readFileSync(path.join(__dirname, 'static/js/app.database.js'), 'utf8');
const databaseCompareCode = fs.readFileSync(path.join(__dirname, 'static/js/database.compare.js'), 'utf8');
const appCss = [
    fs.readFileSync(path.join(__dirname, 'static/app.css'), 'utf8'),
    fs.readFileSync(path.join(__dirname, 'static/css/pages/database.css'), 'utf8'),
    fs.readFileSync(path.join(__dirname, 'static/css/responsive.css'), 'utf8'),
].join('\n');

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

const document = {
    body: {classList: {contains() { return false; }}},
    getElementById() { return null; },
    addEventListener() {},
};

const context = {
    console,
    document,
    window: {document},
    history: {back() {}},
    escapeHtml,
    uiIconSvg(name, className = '') {
        return `<svg class="${className}" data-icon="${name}"></svg>`;
    },
    setTimeout,
    clearTimeout,
};

vm.createContext(context);
vm.runInContext(databaseCode, context, {filename: 'app.database.js'});
vm.runInContext(databaseCompareCode, context, {filename: 'database.compare.js'});

function buildBoundaryPlayer(positiveValue, negativeValue) {
    const player = {pos_gk: 1};
    vm.runInContext(`Object.entries(WEIGHTED_POWER_WEIGHTS)`, context).forEach(([key, weight]) => {
        player[key] = weight < 0 ? negativeValue : positiveValue;
    });
    return player;
}

const minimumPlayer = buildBoundaryPlayer(1, 20);
const maximumPlayer = buildBoundaryPlayer(20, 1);
const midpointPlayer = buildBoundaryPlayer(10.5, 10.5);

vm.runInContext(`currentHeigoPowerCalibration = {
    median_score: 50,
    robust_scale: 10,
    sorted_scores: [30, 40, 50, 60, 70]
}`, context);

assert.equal(context.calculateWeightedPower(minimumPlayer).score, 0);
assert.equal(context.calculateWeightedPower(maximumPlayer).score, 100);
assert.equal(context.calculateWeightedPower(midpointPlayer).score, 50);
assert.equal(context.getHeigoPowerTone(49.99), 'is-level-white');
assert.equal(context.getHeigoPowerTone(50), 'is-level-green');
assert.equal(context.getHeigoPowerTone(60), 'is-level-blue');
assert.equal(context.getHeigoPowerTone(70), 'is-level-purple');
assert.equal(context.getHeigoPowerTone(80), 'is-level-orange');
assert.equal(context.getHeigoPowerTone(90), 'is-level-red');
assert.equal(context.getHeigoPowerTone(49.99), 'is-level-white');
assert.equal(context.getHeigoPowerTone(50), 'is-level-green');
assert.equal(context.getHeigoPowerTone(60), 'is-level-blue');
assert.equal(context.getHeigoPowerTone(70), 'is-level-purple');
assert.equal(context.getHeigoPowerTone(80), 'is-level-orange');
assert.equal(context.getHeigoPowerTone(90), 'is-level-red');

const partialResult = context.calculateWeightedPower({pos_gk: 1, passing: 10.5});
assert.equal(partialResult.score, 50);
assert.equal(partialResult.included, 1);

const goalkeeperResult = context.calculateWeightedPower({pos_gk: 15, passing: 20});
assert.equal(goalkeeperResult.score, null);
assert.equal(goalkeeperResult.isGoalkeeper, true);

const cardMarkup = context.buildWeightedPowerCard(midpointPlayer);
assert.match(cardMarkup, />50\.00</);
assert.match(cardMarkup, /加权战力值/);
assert.match(cardMarkup, /\/ 100/);
assert.match(cardMarkup, /HEIGO战力/);
assert.match(cardMarkup, /前 60%/);
assert.match(cardMarkup, /is-level-green/);
assert.match(cardMarkup, /weighted-power-metrics/);
assert.doesNotMatch(cardMarkup, /weighted-power-note/);
assert.match(cardMarkup, /is-level-green/);

const collapsibleCardMarkup = context.buildWeightedPowerCard(midpointPlayer, {collapsible: true});
assert.match(collapsibleCardMarkup, /收起/);
assert.match(collapsibleCardMarkup, />50\.00</);
assert.match(collapsibleCardMarkup, /is-side-control/);
assert.doesNotMatch(collapsibleCardMarkup, /weighted-power-controls/);

context.setWeightedPowerCollapsed(true);
const collapsedCardMarkup = context.buildWeightedPowerCard(midpointPlayer, {collapsible: true});
assert.match(collapsedCardMarkup, /战力数值已隐藏/);
assert.match(collapsedCardMarkup, /显示/);
assert.doesNotMatch(collapsedCardMarkup, />50\.00</);

const exportCardMarkup = context.buildWeightedPowerCard(midpointPlayer);
assert.match(exportCardMarkup, />50\.00</);
context.setWeightedPowerCollapsed(false);

const comparisonPlayer = {...midpointPlayer, uid: 10, name: 'Midpoint', data_version: '2630', position: 'MC'};
const comparisonEntry = context.buildComparisonEntry({player: comparisonPlayer, step: 0}, 0);
const comparisonMarkup = context.buildComparisonPlayerCard(comparisonEntry);
assert.match(comparisonMarkup, /comparison-weighted-power/);
assert.ok(comparisonMarkup.includes(`>${comparisonEntry.weightedPower.score.toFixed(2)}<`));

assert.match(databaseCode, /player-detail-scroll-snap/);
assert.match(appCss, /scroll-snap-type:\s*y proximity/);
assert.match(appCss, /scroll-snap-stop:\s*always/);
assert.match(appCss, /detail-section-skills > \.detail-skills-grid > \.attribute-group/);
