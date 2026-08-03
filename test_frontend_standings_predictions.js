const assert = require('node:assert/strict');
const fs = require('node:fs');

const competition = fs.readFileSync('static/js/app.competition.js', 'utf8');
const competitionCss = fs.readFileSync('static/css/pages/competition.css', 'utf8');
const responsiveCss = fs.readFileSync('static/css/responsive.css', 'utf8');

assert.match(competition, /function renderStandingPrediction\(/, 'standings should render the predicted rank and interval');
assert.match(competition, /predicted_rank_min/, 'standings should expose the lower prediction bound');
assert.match(competition, /predicted_rank_max/, 'standings should expose the upper prediction bound');
assert.match(competition, />预测排名<\/th>/, 'desktop standings should include a prediction column');
assert.match(competition, /mobile-standing-prediction-row/, 'mobile expanded standings should include the prediction lane');
assert.match(competition, /prediction_summaries/, 'standings should explain the current simulation phase');
assert.match(competition, /1,200 次赛季模拟|toLocaleString\('zh-CN'\)/, 'the simulation scale should be visible to users');
assert.match(competitionCss, /\.standing-prediction-rail/, 'the prediction interval should use a compact rank rail');
assert.match(competitionCss, /\.standings-prediction-summary/, 'prediction methodology should use a compact contextual summary');
assert.match(responsiveCss, /\.standing-prediction\.is-mobile/, 'the prediction lane should adapt to mobile cards');

console.log('standings prediction frontend checks passed');
