async function searchDatabase(nameOverride = null) {
    const name = nameOverride ?? document.getElementById('dbPlayerSearch').value.trim();
    if (!name) {
        document.getElementById('dbPlayersTable').innerHTML = '<div class="no-data">请输入球员姓名或 UID 进行搜索</div>';
        return;
    }
    if (/^\d+$/.test(name)) {
        await showPlayerDetail(name, {returnTab: 'database'});
        return;
    }
    document.getElementById('dbPlayersTable').innerHTML = '<div class="loading">搜索中...</div>';
    currentDbPlayers = await fetchDatabaseSearchResults(name);
    document.getElementById('dbSortField').value = '';
    renderDbPlayers(currentDbPlayers);
}

function sortDbPlayers() {
    const field = document.getElementById('dbSortField').value;
    const order = document.getElementById('dbSortOrder').value;
    if (!field) { renderDbPlayers(currentDbPlayers); return; }
    let sorted = [...currentDbPlayers];
    sorted.sort((a, b) => {
        let va = a[field] || 0;
        let vb = b[field] || 0;
        return order === 'asc' ? va - vb : vb - va;
    });
    renderDbPlayers(sorted);
}

function renderDbPlayers(players) {
    if (players.length === 0) {
        document.getElementById('dbPlayersTable').innerHTML = '<div class="no-data">没有找到符合条件的球员</div>';
        return;
    }
    document.getElementById('dbTableTitle').textContent = `搜索结果 (${players.length} 名球员)`;
    const html = `<table><thead><tr><th>姓名</th><th>位置</th><th>年龄</th><th>CA</th><th>PA</th><th>国籍</th><th>HEIGO俱乐部</th><th>现实俱乐部</th></tr></thead><tbody>${players.map(p => `<tr><td><span class="player-link" onclick="showPlayerDetail(${p.uid}, {returnTab: 'database'})">${p.name}</span></td><td>${p.position}</td><td>${p.age}</td><td><strong>${p.ca}</strong></td><td>${p.pa}</td><td>${p.nationality}</td><td class="${p.heigo_club !== '大海' ? 'heigo-club' : ''}">${p.heigo_club}</td><td class="real-club">${p.club}</td></tr>`).join('')}</tbody></table>`;
    document.getElementById('dbPlayersTable').innerHTML = html;
}

async function viewPlayerInDatabase(uid) {
    if (typeof selectRosterPlayer === 'function') {
        selectRosterPlayer(uid);
    }
    await showPlayerDetail(uid, {returnTab: 'players'});
}

async function showPlayerDetail(uid, options = {}) {
    const returnTab = options.returnTab || 'database';
    dbDetailReturnState = {tab: returnTab};
    showTab('database');
    document.getElementById('dbListView').classList.remove('active');
    document.getElementById('dbDetailView').classList.add('active');
    document.getElementById('playerDetailContent').innerHTML = '<div class="loading">加载中...</div>';
    const detailToolbar = document.getElementById('playerDetailToolbar');
    if (detailToolbar) detailToolbar.innerHTML = '';
    const res = await fetch(`/api/attributes/${uid}`);
    const player = await res.json();
    if (!player) {
        document.getElementById('playerDetailContent').innerHTML = '<div class="no-data">找不到球员信息</div>';
        return;
    }
    if (typeof selectRosterPlayer === 'function') {
        selectRosterPlayer(uid);
    }
    currentDetailPlayer = player;
    renderPlayerDetail(player);
}

function getAttrClass(val) {
    const normalized = Math.min(20, Math.max(1, Number(val) || 1));
    if (normalized <= 4) return 'attr-tier-1';
    if (normalized <= 8) return 'attr-tier-2';
    if (normalized <= 12) return 'attr-tier-3';
    if (normalized <= 16) return 'attr-tier-4';
    return 'attr-tier-5';
}

function renderAttributeList(attrs) {
    return attrs.map(attr => {
        const value = Number(attr.value) || 0;
        return `<div class="attribute-bar ${getAttrClass(value)}"><span class="attr-name">${attr.label}</span><span class="attr-value">${value}</span></div>`;
    }).join('');
}

function renderPlayerDetail(p) {
    const technical = [
        ['passing', '传球'], ['crossing', '传中'], ['marking', '盯人'], ['technique', '技术'],
        ['dribbling', '盘带'], ['tackling', '抢断'], ['finishing', '射门'], ['first_touch', '停球'],
        ['heading', '头球'], ['long_shots', '远射']
    ].map(([key, label]) => ({key, label, value: p[key]}));
    const mental = [
        ['flair', '才华'], ['positioning', '站位'], ['work_rate', '投入'], ['concentration', '集中'],
        ['decisions', '决断'], ['leadership', '领导力'], ['aggression', '侵略性'], ['vision', '视野'],
        ['teamwork', '团队合作'], ['off_the_ball', '无球跑动'], ['determination', '意志力'], ['bravery', '勇敢']
    ].map(([key, label]) => ({key, label, value: p[key]}));
    const physical = [
        ['acceleration', '爆发力'], ['jumping', '弹跳'], ['agility', '灵活'], ['stamina', '耐力'],
        ['balance', '平衡'], ['strength', '强壮'], ['pace', '速度'], ['natural_fitness', '体质']
    ].map(([key, label]) => ({key, label, value: p[key]}));
    const hidden = [
        ['consistency', '稳定'], ['adaptability', '适应性'], ['pressure', '抗压'], ['ambition', '雄心'],
        ['professionalism', '职业'], ['important_matches', '大赛'], ['injury_proneness', '伤病'], ['versatility', '多样性']
    ].map(([key, label]) => ({key, label, value: p[key]}));

    const html = `
        <div class="player-detail-container">
            <div class="player-info-panel">
                <div class="player-identity-block">
                    <div class="player-name">${escapeHtml(p.name)}</div>
                    <div class="player-uid">UID: ${escapeHtml(p.uid)}</div>
                </div>
                <div class="info-row"><span class="info-label">国籍</span><span class="info-value">${escapeHtml(p.nationality || '-')}</span></div>
                <div class="info-row"><span class="info-label">年龄</span><span class="info-value">${escapeHtml(p.age ?? '-')}</span></div>
                <div class="info-row"><span class="info-label">生日</span><span class="info-value">${escapeHtml(p.birth_date || '未知')}</span></div>
                <div class="info-row"><span class="info-label">位置</span><span class="info-value">${escapeHtml(p.position || '-')}</span></div>
                <div class="info-row"><span class="info-label">CA / PA</span><span class="info-value"><strong>${escapeHtml(p.ca ?? '-')}</strong> / ${escapeHtml(p.pa ?? '-')}</span></div>
                <div class="info-row"><span class="info-label">身高</span><span class="info-value">${escapeHtml(p.height || '-')} cm</span></div>
                <div class="info-row"><span class="info-label">HEIGO俱乐部</span><span class="info-value ${p.heigo_club !== '大海' ? 'heigo-club' : ''}">${escapeHtml(p.heigo_club || '-')}</span></div>
                <div class="info-row"><span class="info-label">现实俱乐部</span><span class="info-value real-club">${escapeHtml(p.club || '-')}</span></div>
                ${p.player_habits ? `<div class="detail-note-block"><div class="detail-note-title">球员习惯</div><div class="detail-note-copy">${escapeHtml(p.player_habits)}</div></div>` : ''}
            </div>
            <div class="attributes-panel">
                <div class="attribute-group">
                    <h3>技术</h3>
                    <div class="attribute-list">${renderAttributeList(technical)}</div>
                </div>
                <div class="attribute-group">
                    <h3>精神</h3>
                    <div class="attribute-list">${renderAttributeList(mental)}</div>
                </div>
                <div class="attribute-group">
                    <h3>身体</h3>
                    <div class="attribute-list">${renderAttributeList(physical)}</div>
                </div>
                <div class="attribute-group attribute-group-wide">
                    <h3>隐藏</h3>
                    <div class="attribute-list attribute-list-grid">${renderAttributeList(hidden)}</div>
                </div>
            </div>
        </div>
    `;
    document.getElementById('playerDetailContent').innerHTML = html;
}

function backToList() {
    document.getElementById('dbDetailView').classList.remove('active');
    document.getElementById('dbListView').classList.add('active');
    const detailToolbar = document.getElementById('playerDetailToolbar');
    if (detailToolbar) detailToolbar.innerHTML = '';
    const returnTab = dbDetailReturnState.tab || 'database';
    if (returnTab !== 'database') {
        showTab(returnTab);
    } else {
        showTab('database');
    }
}

document.getElementById('dbPlayerSearch')?.addEventListener('keypress', e => {
    if (e.key === 'Enter') searchDatabase();
});