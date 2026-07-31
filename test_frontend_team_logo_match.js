const fs = require('fs');

const html = fs.readFileSync('static/app.html', 'utf8');
const js = fs.readFileSync('static/js/app.admin.js', 'utf8');
const css = fs.readFileSync('static/app.css', 'utf8');

function expect(value, message) {
    if (!value) throw new Error(message);
}

expect(html.includes('data-workspace-view="logos"'), 'missing team logo matcher navigation');
expect(html.includes('id="workspaceLogosView"'), 'missing team logo matcher workspace view');
expect(html.includes('id="workspaceLogoReview"'), 'missing current/candidate review area');
expect(html.includes('id="workspaceLogoUploadInput"'), 'missing local logo upload input');
expect(html.includes('FCLOGO 检索') && html.includes('本地上传'), 'missing multi-source tabs');
expect(html.includes('id="workspaceLogoUploadInput"'), 'missing local logo upload input');
expect(html.includes('FCLOGO 检索') && html.includes('本地上传'), 'missing multi-source tabs');
expect(`${html}\n${js}`.includes('我已人工核对队徽与球队'), 'missing manual confirmation language');
expect(js.includes('/api/admin/team-logo-match/overview'), 'missing matcher overview endpoint');
expect(js.includes('/api/admin/team-logo-match/search'), 'missing matcher search endpoint');
expect(js.includes('/api/admin/team-logo-match/apply'), 'missing matcher apply endpoint');
expect(js.includes('/api/admin/team-logo-match/upload'), 'missing local upload endpoint');
expect(js.includes('/api/admin/team-logo-match/upload'), 'missing local upload endpoint');
expect(js.includes('confirmed: true'), 'apply payload must include explicit confirmation');
expect(css.includes('.workspace-logo-scout'), 'missing matcher layout styles');
expect(css.includes('@media (max-width: 720px)'), 'missing mobile matcher layout');

console.log('team logo matcher frontend checks passed');
