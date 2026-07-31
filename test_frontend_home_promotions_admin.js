const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const html = fs.readFileSync(path.join(__dirname, 'static/app.html'), 'utf8');
const adminCode = fs.readFileSync(path.join(__dirname, 'static/js/app.admin.js'), 'utf8');
const homeCode = fs.readFileSync(path.join(__dirname, 'static/js/app.home.js'), 'utf8');

assert.match(html, /data-workspace-view="promotions"/);
assert.match(html, /id="workspacePromotionsView"/);
assert.match(html, /同步杯赛冠军/);
assert.match(html, /同步联赛冠军/);
assert.match(html, /新增宣传/);

assert.match(adminCode, /\/api\/workspace\/home-promotions/);
assert.match(adminCode, /sync-cup-champions/);
assert.match(adminCode, /sync-league-champions/);
assert.match(adminCode, /home-promotions\/image/);
assert.match(adminCode, /uploadWorkspacePromotionImage/);
assert.match(adminCode, /saveWorkspacePromotion/);
assert.match(adminCode, /toggleWorkspacePromotion/);
assert.match(adminCode, /deleteWorkspacePromotion/);
assert.match(adminCode, /starts_at/);
assert.match(adminCode, /ends_at/);
assert.match(adminCode, /competition:playerRankings/);
assert.match(adminCode, /完整联赛名单/);
assert.match(adminCode, /球队中心/);
assert.match(adminCode, /getWorkspacePromotionTargetOptions/);
assert.match(adminCode, /workspacePromotionDisplayMode/);
assert.match(adminCode, /访问弹窗/);
assert.match(homeCode, /showPendingHomePromotionModal/);
assert.match(homeCode, /homePromotionModalShownThisVisit/);
assert.match(html, /id="homePromotionModalLayer"/);

assert.match(homeCode, /\/api\/home-promotions/);
assert.match(homeCode, /openHomePromotionAction/);
assert.match(homeCode, /dismissHomePromotion/);
