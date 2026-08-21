var workspaceDrawSessions = [];
var workspaceCurrentDraw = null;
var workspaceSeasonArchives = [];
var workspaceDrawLotteryFilter = '';
var workspaceDrawRollTimer = null;
var workspaceDrawRolling = false;
var workspaceDrawRollIndex = 0;
var workspaceDrawRollCurrentEntryId = null;

const DRAW_TYPE_LABELS = {
    champions_group: '冠军杯六档小组抽签',
    league_group: '联盟杯六档小组抽签',
    champions_r16: '冠军杯16强种子抽签',
    league_r16: '联盟杯16强种子抽签',
    wumingjian_qualifying: '无铭剑杯44队预选赛',
    wumingjian_r32: '无铭剑杯32强抽签',
    lottery: '赛季末球员乐透',
    custom_team: '自由抽签 · 球队',
    custom_player: '自由抽签 · 球员',
};

const DRAW_STATUS_LABELS = {draft: '草稿', locked: '已锁池', drawing: '抽取中', completed: '已完成', published: '已发布', void: '已作废'};

async function drawApi(url, options = {}) {
    const result = await workJsonRequest(url, options);
    if (!result) return null;
    if (!result.response.ok) {
        showModal('操作失败', escapeHtml(result.data.detail || result.data.message || '当前操作未能完成'));
        return null;
    }
    return result.data;
}

async function loadWorkspaceDraws(options = {}) {
    if (!workspaceHasCapability('draws.write')) return;
    if (!workspaceDrawSessions.length || options.force === true) {
        const data = await drawApi('/api/admin/draws');
        if (!data) return;
        workspaceDrawSessions = Array.isArray(data) ? data : [];
    }
    renderDrawSessionList();
    if (workspaceCurrentDraw?.id) {
        await openWorkspaceDraw(workspaceCurrentDraw.id, {quiet: true});
    } else if (workspaceDrawSessions[0]) {
        await openWorkspaceDraw(workspaceDrawSessions[0].id, {quiet: true});
    } else {
        const stage = document.getElementById('drawSessionStage');
        if (stage) stage.innerHTML = '<div class="draw-empty-state"><strong>从一个空白草稿开始</strong><span>新建任务后会直接进入编辑台，再逐步添加球队或球员。</span></div>';
    }
}

function renderDrawSessionList() {
    const host = document.getElementById('drawSessionList');
    if (!host) return;
    if (!workspaceDrawSessions.length) {
        host.innerHTML = '<div class="draw-empty-state is-compact"><strong>暂无抽签任务</strong><span>新建后可自动预填或自定义导入候选池。</span></div>';
        return;
    }
    host.innerHTML = `<div class="draw-session-list">${workspaceDrawSessions.map(item => `
        <button class="draw-session-item ${Number(workspaceCurrentDraw?.id) === Number(item.id) ? 'active' : ''}" type="button" onclick="openWorkspaceDraw(${Number(item.id)})">
            <span>${escapeHtml(DRAW_STATUS_LABELS[item.status] || item.status)}</span>
            <strong>${escapeHtml(item.name)}</strong>
            <small>${escapeHtml(DRAW_TYPE_LABELS[item.draw_type] || item.draw_type)} · ${Number(item.pick_count || 0)} 个结果</small>
        </button>
    `).join('')}</div>`;
}

async function openWorkspaceDraw(sessionId, options = {}) {
    stopDrawRollTimer();
    const data = await drawApi(`/api/admin/draws/${sessionId}`);
    if (!data) return;
    workspaceCurrentDraw = data;
    renderDrawSessionList();
    renderCurrentDraw();
    if (!options.quiet) document.getElementById('drawSessionStage')?.scrollIntoView({behavior: 'smooth', block: 'nearest'});
}

function drawTypeUsesPots(type) {
    return ['champions_group', 'league_group'].includes(type);
}

function drawTypeUsesSeeds(type) {
    return ['champions_r16', 'league_r16'].includes(type);
}

function drawTypeIsCustom(type) {
    return ['custom_team', 'custom_player'].includes(type);
}

function updateLotteryEntryField(entryId, field, value) {
    const entry = workspaceCurrentDraw?.entries?.find(item => Number(item.id) === Number(entryId));
    if (!entry) return;
    if (field === 'self_save_count') {
        entry.self_save_count = Math.max(0, Number(value || 0));
        entry.weight = 2 ** entry.self_save_count;
        const label = document.getElementById(`draw-weight-${entryId}`);
        if (label) label.textContent = `×${entry.weight}`;
    } else if (field === 'is_active') entry.is_active = Boolean(value);
    else entry[field] = value;
}

function setLotteryPoolFilter(value) {
    workspaceDrawLotteryFilter = String(value || '').trim().toLowerCase();
    renderDrawPoolEditor();
}

function drawEntryRequestPayload(entry) {
    return {
        team_id: entry.team_id,
        player_uid: entry.player_uid,
        entity_name: entry.entity_name,
        team_name: entry.team_name,
        level: entry.level,
        source_rank: entry.source_rank,
        pot_no: entry.pot_no,
        seed_status: entry.seed_status,
        self_save_count: Number(entry.self_save_count || 0),
        is_active: Boolean(entry.is_active),
        metadata: entry.metadata || {},
    };
}

function drawEntryIdentity(entry, drawType = workspaceCurrentDraw?.draw_type) {
    if (entry.player_uid) return `player:${Number(entry.player_uid)}`;
    if (entry.team_id) return `team:${Number(entry.team_id)}`;
    const prefix = drawType === 'custom_player' ? 'custom-player' : 'custom-team';
    return `${prefix}:${String(entry.entity_name || '').trim().toLowerCase()}`;
}

function renderDrawPoolEditor() {
    const host = document.getElementById('drawPoolEditor');
    const draw = workspaceCurrentDraw;
    if (!host || !draw) return;
    let entries = draw.entries || [];
    if (draw.draw_type === 'lottery' && workspaceDrawLotteryFilter) {
        entries = entries.filter(item => [item.entity_name, item.team_name, item.player_uid].some(value => String(value || '').toLowerCase().includes(workspaceDrawLotteryFilter)));
    }
    const visible = draw.draw_type === 'lottery' ? entries.slice(0, 240) : entries;
    host.innerHTML = `
        ${draw.draw_type === 'lottery' ? `<div class="draw-pool-filter"><input type="search" value="${escapeHtml(workspaceDrawLotteryFilter)}" placeholder="搜索球员、球队或UID" oninput="setLotteryPoolFilter(this.value)"><span>候选池 ${draw.entries.length} 人 / ${new Set(draw.entries.map(item => item.team_id).filter(Boolean)).size} 队${entries.length > visible.length ? `，当前显示前 ${visible.length} 人` : ''}</span></div>` : ''}
        <div class="draw-pool-table">
            <div class="draw-pool-row is-head"><span>候选</span><span>球队 / 来源</span><span>抽签参数</span><span>有效</span><span>操作</span></div>
            ${visible.map(entry => {
                let controls = '<span class="draw-entry-rule">完全随机</span>';
                if (drawTypeUsesPots(draw.draw_type)) controls = `<label>第 <select onchange="updateLotteryEntryField(${entry.id}, 'pot_no', Number(this.value))">${[1,2,3,4,5,6].map(value => `<option value="${value}" ${Number(entry.pot_no) === value ? 'selected' : ''}>${value}</option>`).join('')}</select> 档</label>`;
                if (drawTypeUsesSeeds(draw.draw_type)) controls = `<select onchange="updateLotteryEntryField(${entry.id}, 'seed_status', this.value)"><option value="seeded" ${entry.seed_status === 'seeded' ? 'selected' : ''}>种子队</option><option value="unseeded" ${entry.seed_status === 'unseeded' ? 'selected' : ''}>非种子队</option></select>`;
                if (draw.draw_type === 'lottery') controls = `<label class="draw-weight-control">自保 <input type="number" min="0" max="20" value="${Number(entry.self_save_count || 0)}" onchange="updateLotteryEntryField(${entry.id}, 'self_save_count', this.value)"> 次</label><strong id="draw-weight-${entry.id}">×${Number(entry.weight || 1)}</strong><em>${entry.final_value == null ? '-' : Number(entry.final_value).toFixed(1)}M · ${escapeHtml(entry.slot_type || '无名额')}</em>`;
                return `<div class="draw-pool-row"><span><strong>${escapeHtml(entry.entity_name)}</strong><small>${entry.player_uid ? `UID ${entry.player_uid}` : escapeHtml(entry.level || '')}</small></span><span>${escapeHtml(entry.team_name || entry.level || '-')}<small>${entry.source_rank ? `上季第 ${entry.source_rank} 名` : ''}</small></span><span>${controls}</span><span><input type="checkbox" ${entry.is_active ? 'checked' : ''} onchange="updateLotteryEntryField(${entry.id}, 'is_active', this.checked)"></span><span><button class="draw-entry-remove" type="button" onclick="removeDrawPoolEntry(${Number(entry.id)})" aria-label="移除 ${escapeHtml(entry.entity_name)}">移除</button></span></div>`;
            }).join('') || '<div class="draw-empty-state is-compact"><strong>候选池为空</strong><span>使用自动预填、自定义导入或乐透筛选生成候选。</span></div>'}
        </div>
        <div class="draw-pool-save"><button class="btn btn-secondary" type="button" onclick="saveCurrentDrawPool()">保存候选池调整</button></div>`;
}

function renderDrawResults(draw) {
    const pendingPair = draw.result?.pending_pair;
    if (!draw.picks?.length && !pendingPair) return '<div class="draw-empty-state"><strong>尚未抽取</strong><span>锁定候选池后，在动态抽签台开始滚动，点击暂停时每次确定一个结果。</span></div>';
    if (draw.result?.groups) {
        return `<div class="draw-groups-grid">${Object.entries(draw.result.groups).map(([group, entries]) => `<article><span>${escapeHtml(group)} GROUP</span><h3>${escapeHtml(group)}组</h3>${entries.map((item, index) => `<div><em>${item.pot_no ? `第${Number(item.pot_no)}档` : `#${Number(item.slot_no || index + 1)}`}</em><span><strong>${escapeHtml(item.entity_name || item.team_name)}</strong>${item.entity_type === 'player' && item.team_name ? `<small>${escapeHtml(item.team_name)}</small>` : ''}</span></div>`).join('')}</article>`).join('')}</div>`;
    }
    if (draw.result?.mode === 'pairs' || Array.isArray(draw.result?.pairs) || pendingPair || draw.picks.some(pick => pick.paired_entry)) {
        const completed = draw.picks.filter(pick => pick.status === 'active').map(pick => `<article><span>#${pick.target_slot || pick.sequence_no}</span><strong>${escapeHtml(pick.entry.entity_name)}</strong><em>${pick.paired_entry ? 'VS' : 'BYE'}</em><strong>${escapeHtml(pick.paired_entry?.entity_name || '轮空')}</strong>${pick.entry.entity_type === 'player' ? `<small>${escapeHtml(pick.entry.team_name || '')}${pick.paired_entry?.team_name ? ` / ${escapeHtml(pick.paired_entry.team_name)}` : ''}</small>` : ''}</article>`).join('');
        const waiting = pendingPair ? `<article class="is-pending"><span>#${Number(pendingPair.target_slot || draw.picks.length + 1)}</span><strong>${escapeHtml(pendingPair.entity_name || '已确定')}</strong><em>等待</em><strong>等待对手</strong>${pendingPair.entity_type === 'player' && pendingPair.team_name ? `<small>${escapeHtml(pendingPair.team_name)}</small>` : ''}</article>` : '';
        return `<div class="draw-pairs-grid">${completed}${waiting}</div>`;
    }
    if (drawTypeIsCustom(draw.draw_type)) {
        return `<div class="draw-custom-list-results">${draw.picks.filter(pick => pick.status === 'active').map(pick => `<article><span>${Number(pick.sequence_no)}</span><div><strong>${escapeHtml(pick.entry.entity_name)}</strong>${pick.entry.entity_type === 'player' ? `<small>${escapeHtml(pick.entry.team_name || '自定义球员')}</small>` : ''}</div></article>`).join('')}</div>`;
    }
    return `<div class="draw-lottery-results">${draw.picks.map(pick => `<article class="${pick.status !== 'active' ? 'is-invalidated' : ''}"><span>${pick.sequence_no}</span><div><strong>${escapeHtml(pick.entry.entity_name)}</strong><small>${escapeHtml(pick.entry.team_name || '')} · ${pick.entry.final_value == null ? '-' : Number(pick.entry.final_value).toFixed(1)}M · 权重×${Number(pick.entry.weight || 1)}</small></div>${pick.status === 'active' && ['drawing','completed'].includes(draw.status) ? `<button type="button" onclick="showInvalidateLotteryPick(${pick.id})">作废</button>` : `<em>${escapeHtml(pick.reason || '已作废')}</em>`}</article>`).join('')}</div>`;
}

function drawRollCandidates(draw = workspaceCurrentDraw) {
    const entries = (draw?.entries || []).filter(entry => entry.is_active);
    const activePicks = (draw?.picks || []).filter(pick => pick.status === 'active');
    if (draw?.draw_type === 'lottery') {
        const selectedTeamIds = new Set(activePicks.map(pick => Number(pick.entry?.team_id)).filter(Boolean));
        return entries.filter(entry => !selectedTeamIds.has(Number(entry.team_id)));
    }
    const usedEntryIds = new Set();
    activePicks.forEach(pick => {
        if (pick.entry?.id) usedEntryIds.add(Number(pick.entry.id));
        if (pick.paired_entry?.id) usedEntryIds.add(Number(pick.paired_entry.id));
    });
    const pendingId = Number(draw?.result?.pending_pair?.entry_id || 0);
    if (pendingId) usedEntryIds.add(pendingId);
    const available = entries.filter(entry => !usedEntryIds.has(Number(entry.id)));
    if (drawTypeUsesPots(draw?.draw_type)) {
        const groupCount = draw.draw_type === 'champions_group' ? 5 : 4;
        const currentPot = Math.floor(activePicks.length / groupCount) + 1;
        return available.filter(entry => Number(entry.pot_no) === currentPot);
    }
    if (drawTypeUsesSeeds(draw?.draw_type)) {
        const side = pendingId ? 'unseeded' : 'seeded';
        return available.filter(entry => entry.seed_status === side);
    }
    if (drawTypeIsCustom(draw?.draw_type) && (draw.config?.mode || 'list') === 'list') {
        const resultCount = Number(draw.config?.result_count || entries.length);
        if (activePicks.length >= resultCount) return [];
    }
    return available;
}

function drawLiveProgress(draw) {
    const entries = (draw?.entries || []).filter(entry => entry.is_active);
    const picks = (draw?.picks || []).filter(pick => pick.status === 'active');
    const pending = draw?.result?.pending_pair;
    if (draw?.draw_type === 'lottery') {
        const total = Math.min(Number(draw.config?.limit || 15), new Set(entries.map(entry => entry.team_id).filter(Boolean)).size);
        return {done: picks.length, total, target: `第 ${picks.length + 1} 位球员`};
    }
    if (drawTypeUsesPots(draw?.draw_type)) {
        const groupCount = draw.draw_type === 'champions_group' ? 5 : 4;
        const done = picks.length;
        const pot = Math.floor(done / groupCount) + 1;
        const group = String.fromCharCode(65 + (done % groupCount));
        return {done, total: entries.length, target: `第 ${pot} 档 · ${group}组`};
    }
    const pairMode = drawTypeUsesSeeds(draw?.draw_type)
        || ['wumingjian_qualifying', 'wumingjian_r32'].includes(draw?.draw_type)
        || (drawTypeIsCustom(draw?.draw_type) && (draw.config?.mode || 'list') === 'pairs');
    if (pairMode) {
        const done = picks.reduce((count, pick) => count + (pick.paired_entry ? 2 : 1), 0) + (pending ? 1 : 0);
        return {done, total: entries.length, target: `第 ${picks.length + 1} 组 · ${pending ? '抽取对手' : '抽取第一方'}`};
    }
    const total = drawTypeIsCustom(draw?.draw_type) && (draw.config?.mode || 'list') === 'list'
        ? Number(draw.config?.result_count || entries.length)
        : entries.length;
    const groupCount = Number(draw.config?.group_count || 2);
    const target = drawTypeIsCustom(draw?.draw_type) && (draw.config?.mode || 'list') === 'groups'
        ? `${String.fromCharCode(65 + (picks.length % groupCount))}组 · 第 ${picks.length + 1} 签`
        : `第 ${picks.length + 1} 位`;
    return {done: picks.length, total, target};
}

function stopDrawRollTimer() {
    if (workspaceDrawRollTimer) window.clearTimeout(workspaceDrawRollTimer);
    workspaceDrawRollTimer = null;
    workspaceDrawRolling = false;
}

function renderDrawLiveMachine(draw) {
    if (!['locked', 'drawing'].includes(draw.status)) return '';
    const candidates = drawRollCandidates(draw);
    const noun = draw.draw_type === 'custom_player' || draw.draw_type === 'lottery' ? '球员' : '球队';
    const progress = drawLiveProgress(draw);
    const initial = candidates[workspaceDrawRollIndex % Math.max(1, candidates.length)];
    workspaceDrawRollCurrentEntryId = initial?.id || null;
    return `<section class="draw-live-machine ${workspaceDrawRolling ? 'is-rolling' : ''}" aria-live="polite">
        <div class="draw-live-machine-copy"><span>LIVE DRAW · ${progress.done} / ${progress.total}</span><strong>${escapeHtml(progress.target)}</strong><small>${workspaceDrawRolling ? `剩余${noun}正在闪烁，点击后只确定当前这一签。` : `开始后逐个确定${noun}，已抽结果会立即写入下方。`}</small></div>
        <div class="draw-live-window" id="drawLiveWindow"><i aria-hidden="true"></i><strong id="drawLiveName">${escapeHtml(initial?.entity_name || `暂无可抽${noun}`)}</strong><small id="drawLiveMeta">${escapeHtml(initial?.team_name && initial.entity_type === 'player' ? initial.team_name : `${candidates.length} 个有效候选`)}</small></div>
        <button class="btn btn-primary draw-live-toggle ${workspaceDrawRolling ? 'is-stop' : ''}" id="drawLiveToggle" type="button" onclick="toggleDrawRoll()" ${candidates.length ? '' : 'disabled'}>${workspaceDrawRolling ? '确定当前一签' : (progress.done ? '继续下一签' : '开始滚动')}</button>
    </section>`;
}

function drawRollRandomUnit() {
    if (window.crypto?.getRandomValues) {
        const value = new Uint32Array(1);
        window.crypto.getRandomValues(value);
        return value[0] / 4294967296;
    }
    return Math.random();
}

function pickDrawRollCandidate(candidates, draw = workspaceCurrentDraw) {
    if (!candidates.length) return null;
    if (draw?.draw_type !== 'lottery') {
        return candidates[Math.floor(drawRollRandomUnit() * candidates.length)] || candidates[0];
    }
    const totalWeight = candidates.reduce((sum, entry) => sum + Math.max(1, Number(entry.weight || 1)), 0);
    let target = drawRollRandomUnit() * totalWeight;
    for (const entry of candidates) {
        target -= Math.max(1, Number(entry.weight || 1));
        if (target < 0) return entry;
    }
    return candidates[candidates.length - 1];
}

function updateDrawRollFrame() {
    if (!workspaceDrawRolling) return;
    const candidates = drawRollCandidates();
    if (!candidates.length) {
        stopDrawRollTimer();
        renderCurrentDraw();
        return;
    }
    workspaceDrawRollIndex += 1;
    const entry = pickDrawRollCandidate(candidates);
    workspaceDrawRollCurrentEntryId = entry?.id || null;
    const name = document.getElementById('drawLiveName');
    const meta = document.getElementById('drawLiveMeta');
    const windowElement = document.getElementById('drawLiveWindow');
    if (name) name.textContent = entry.entity_name || '-';
    if (meta) meta.textContent = entry.entity_type === 'player' ? (entry.team_name || '自定义球员') : (entry.level || '候选球队');
    if (windowElement) {
        windowElement.classList.remove('is-tick');
        void windowElement.offsetWidth;
        windowElement.classList.add('is-tick');
    }
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;
    workspaceDrawRollTimer = window.setTimeout(updateDrawRollFrame, reducedMotion ? 420 : 74);
}

function startDrawRoll() {
    if (workspaceDrawRolling || !drawRollCandidates().length) return;
    workspaceDrawRolling = true;
    renderCurrentDraw();
    updateDrawRollFrame();
}

async function stopAndCommitDrawRoll() {
    if (!workspaceDrawRolling || !workspaceCurrentDraw) return;
    const selectedEntryId = Number(workspaceDrawRollCurrentEntryId || 0);
    if (workspaceDrawRollTimer) window.clearTimeout(workspaceDrawRollTimer);
    workspaceDrawRollTimer = null;
    workspaceDrawRolling = false;
    const button = document.getElementById('drawLiveToggle');
    if (button) {
        button.disabled = true;
        button.textContent = '正在确定结果…';
    }
    if (!selectedEntryId) {
        renderCurrentDraw();
        showModal('当前签未确定', '没有读取到正在闪烁的候选，请重新开始滚动。');
        return;
    }
    const data = await drawApi(`/api/admin/draws/${workspaceCurrentDraw.id}/next`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({entry_id: selectedEntryId}),
    });
    if (!data) {
        renderCurrentDraw();
        return;
    }
    workspaceCurrentDraw = data;
    workspaceDrawSessions = [];
    workspaceDrawRollIndex = 0;
    workspaceDrawRolling = ['locked', 'drawing'].includes(data.status) && drawRollCandidates(data).length > 0;
    renderCurrentDraw();
    document.querySelector('#drawSessionStage .draw-groups-grid, #drawSessionStage .draw-pairs-grid, #drawSessionStage .draw-lottery-results, #drawSessionStage .draw-custom-list-results')?.classList.add('is-revealed');
    if (workspaceDrawRolling) updateDrawRollFrame();
}

function toggleDrawRoll() {
    if (workspaceDrawRolling) {
        stopAndCommitDrawRoll();
        return;
    }
    startDrawRoll();
}

function renderDrawDraftWorkbench(draw) {
    const custom = drawTypeIsCustom(draw.draw_type);
    const mode = draw.config?.mode || 'list';
    const setupAction = draw.draw_type === 'lottery'
        ? '<button class="btn btn-secondary" type="button" onclick="showLotteryPoolDialog()">筛选球员池</button>'
        : custom
            ? ''
            : '<button class="btn btn-secondary" type="button" onclick="refillDrawFromProposal()">按规则预填</button>';
    let candidateLabel = '增量添加球队';
    let candidatePlaceholder = '每行：球队名或 ID';
    let candidateHelp = '每次可以只添加刚确认的一批球队，已有候选会保留。';
    if (draw.draw_type === 'lottery' || draw.draw_type === 'custom_player') {
        candidateLabel = '增量添加球员';
        candidatePlaceholder = '每行：球员 UID、唯一球员名，或临时球员名 | 临时球队';
        candidateHelp = draw.draw_type === 'lottery'
            ? '乐透候选必须匹配站内球员；同名球员请使用 UID。'
            : '同名球员请使用 UID；无法匹配的名称会作为临时候选保留。';
    } else if (drawTypeUsesPots(draw.draw_type)) {
        candidatePlaceholder = '每行：球队名或 ID | 档位\n例：阿森纳 | 1';
        candidateHelp = '未填写档位时会按当前候选数量顺延预填，添加后仍可逐队调整。';
    } else if (drawTypeUsesSeeds(draw.draw_type)) {
        candidatePlaceholder = '每行：球队名或 ID | 种子/非种子';
        candidateHelp = '未填写时默认按种子队加入，添加后可逐队调整。';
    } else if (draw.draw_type === 'custom_team') {
        candidatePlaceholder = '每行：球队 ID、站内球队名或临时球队名';
        candidateHelp = '无法匹配的名称会作为本次自由抽签的临时候选保留。';
    }
    return `<section class="draw-draft-workbench">
        <form class="draw-draft-settings" onsubmit="event.preventDefault(); saveDrawDraftSettings();">
            <div class="draw-draft-block-head"><div><span>SETUP</span><strong>任务设置</strong><small>草稿阶段可以随时修改，锁池后即固定。</small></div><button class="btn btn-secondary" type="submit">保存设置</button></div>
            <div class="draw-draft-settings-grid">
                <label><span>任务名称</span><input id="drawDraftName" type="text" maxlength="100" value="${escapeHtml(draw.name)}" required></label>
                <label><span>赛季标识</span><input id="drawDraftSeason" type="text" maxlength="40" value="${escapeHtml(draw.season_label || '')}" placeholder="例如：第52届"></label>
                <label><span>任务校验码</span><input id="drawDraftSeed" type="text" maxlength="100" value="${escapeHtml(draw.random_seed)}" required></label>
            </div>
            ${custom ? `<div class="draw-draft-settings-grid is-custom">
                <label><span>结果形式</span><select id="drawDraftCustomMode" onchange="syncDrawDraftConfigFields()"><option value="list" ${mode === 'list' ? 'selected' : ''}>形成顺序名单</option><option value="groups" ${mode === 'groups' ? 'selected' : ''}>随机分组</option><option value="pairs" ${mode === 'pairs' ? 'selected' : ''}>随机配对</option></select></label>
                <label class="draw-draft-custom-group" ${mode === 'groups' ? '' : 'hidden'}><span>分组数量</span><input id="drawDraftGroupCount" type="number" min="2" max="26" value="${Number(draw.config?.group_count || 4)}"></label>
                <label class="draw-draft-custom-count" ${mode === 'list' ? '' : 'hidden'}><span>名单人数</span><input id="drawDraftResultCount" type="number" min="1" max="500" value="${draw.config?.result_count ? Number(draw.config.result_count) : ''}" placeholder="留空抽取全部"></label>
            </div>` : ''}
        </form>
        <div class="draw-draft-add">
            <div class="draw-draft-block-head"><div><span>ADD</span><strong>${candidateLabel}</strong><small>${candidateHelp}</small></div><div>${setupAction}</div></div>
            <textarea id="drawDraftEntries" rows="4" placeholder="${escapeHtml(candidatePlaceholder)}"></textarea>
            <div class="draw-draft-add-actions"><span>当前 ${Number(draw.entry_count || 0)} 个候选</span><button class="btn btn-primary" type="button" onclick="appendDrawDraftEntries()">添加到候选池</button></div>
        </div>
    </section>`;
}

function renderCurrentDraw() {
    const host = document.getElementById('drawSessionStage');
    const draw = workspaceCurrentDraw;
    if (!host || !draw) return;
    const canWriteCup = workspaceHasCapability('schedule.write') && draw.competition;
    host.innerHTML = `
        <div class="draw-stage-head"><div><span>${escapeHtml(DRAW_TYPE_LABELS[draw.draw_type] || draw.draw_type)}</span><h3>${escapeHtml(draw.name)}</h3><p>${escapeHtml(draw.season_label || '未填写赛季')} · 创建者 ${escapeHtml(draw.created_by || '-')}</p></div><em class="draw-status is-${escapeHtml(draw.status)}">${escapeHtml(DRAW_STATUS_LABELS[draw.status] || draw.status)}</em></div>
        <div class="draw-audit-strip"><div><span>任务校验码</span><code>${escapeHtml(draw.random_seed)}</code></div><div><span>候选池哈希</span><code>${escapeHtml(draw.pool_hash || '锁池后生成')}</code></div></div>
        ${draw.status === 'draft' ? `${renderDrawDraftWorkbench(draw)}<section class="draw-stage-section"><div class="draw-panel-head"><div><span>POOL</span><strong>候选池与抽签参数</strong></div><div><button class="btn btn-primary" type="button" onclick="lockCurrentDraw()">确认并锁池</button></div></div><div id="drawPoolEditor"></div></section>` : `${renderDrawLiveMachine(draw)}<section class="draw-stage-section"><div class="draw-panel-head"><div><span>RESULT</span><strong>抽签结果</strong></div></div>${renderDrawResults(draw)}</section>`}
        <div class="draw-stage-actions">
            ${draw.status === 'completed' && draw.draw_type === 'lottery' && !draw.candidate_list_id ? '<button class="btn btn-secondary" type="button" onclick="createDrawCandidateList()">生成候选名单草稿</button>' : ''}
            ${draw.candidate_list_id ? `<button class="btn btn-secondary" type="button" onclick="openWorkspaceTask('database','candidates')">查看候选名单 #${draw.candidate_list_id}</button>` : ''}
            ${draw.status === 'completed' ? '<button class="btn btn-primary" type="button" onclick="publishCurrentDraw()">发布结果</button>' : ''}
            ${canWriteCup && ['completed','published'].includes(draw.status) ? '<button class="btn btn-secondary" type="button" onclick="writeCurrentDrawToCup()">写入杯赛</button>' : ''}
            ${['completed','published'].includes(draw.status) ? `<a class="btn btn-secondary" href="/api/admin/draws/${draw.id}/export.xlsx">导出 Excel</a><a class="btn btn-secondary" href="/api/admin/draws/${draw.id}/export.png">导出图片</a><a class="btn btn-secondary" href="/api/admin/draws/${draw.id}/export.txt">导出文字</a>` : ''}
            ${['locked','drawing','completed'].includes(draw.status) ? '<button class="btn btn-danger" type="button" onclick="showVoidCurrentDraw()">作废整场</button>' : ''}
            ${['draft','void'].includes(draw.status) ? '<button class="btn btn-danger" type="button" onclick="showDeleteDrawTask()">删除任务</button>' : ''}
        </div>`;
    if (draw.status === 'draft') renderDrawPoolEditor();
}

function resolveDrawTeamToken(token) {
    const clean = String(token || '').trim();
    if (!clean) return null;
    if (/^\d+$/.test(clean)) return teams.find(team => Number(team.id) === Number(clean)) || null;
    const normalized = clean.toLowerCase();
    return teams.find(team => String(team.name || '').trim().toLowerCase() === normalized) || null;
}

function resolveDrawPlayerToken(token) {
    const clean = String(token || '').trim();
    if (!clean) return null;
    if (/^\d+$/.test(clean)) return allPlayers.find(player => Number(player.uid) === Number(clean)) || null;
    const normalized = clean.toLowerCase();
    const matches = allPlayers.filter(player => String(player.name || '').trim().toLowerCase() === normalized);
    if (matches.length > 1) throw new Error(`球员“${clean}”存在同名，请改用 UID`);
    return matches[0] || null;
}

function parseCustomDrawEntries(text, drawType, startIndex = 0) {
    const lines = String(text || '').split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    if (!lines.length) return null;
    return lines.map((line, index) => {
        const [teamToken, ruleToken = ''] = line.split(/[|,，\t]/).map(item => item.trim());
        if (drawType === 'custom_player' || drawType === 'lottery') {
            const player = resolveDrawPlayerToken(teamToken);
            if (player) return {player_uid: Number(player.uid), entity_name: player.name, team_name: player.team_name, metadata: {custom_import: true}};
            if (drawType === 'lottery') throw new Error(`第 ${index + 1} 行无法匹配球员：${teamToken}；同名球员请使用 UID`);
            return {entity_name: teamToken, team_name: ruleToken || null, metadata: {custom_import: true, manual_entry: true}};
        }
        const team = resolveDrawTeamToken(teamToken);
        if (drawType === 'custom_team' && !team) {
            return {entity_name: teamToken, metadata: {custom_import: true, manual_entry: true}};
        }
        if (!team) throw new Error(`第 ${index + 1} 行无法匹配球队：${teamToken}`);
        const entry = {team_id: Number(team.id), entity_name: team.name, level: team.level, metadata: {custom_import: true}};
        if (drawTypeUsesPots(drawType)) entry.pot_no = Number(ruleToken || Math.floor((startIndex + index) / (drawType === 'champions_group' ? 5 : 4)) + 1);
        if (drawTypeUsesSeeds(drawType)) entry.seed_status = /非|un/i.test(ruleToken) ? 'unseeded' : 'seeded';
        return entry;
    });
}

async function showCreateDrawDialog() {
    showModal('新建抽签任务', `
        <form class="draw-create-form" onsubmit="event.preventDefault(); createWorkspaceDraw();">
            <label><span>抽签类型</span><select id="drawCreateType">${Object.entries(DRAW_TYPE_LABELS).map(([value, label]) => `<option value="${value}">${escapeHtml(label)}</option>`).join('')}</select></label>
            <label><span>任务名称</span><input id="drawCreateName" type="text" maxlength="100" placeholder="例如：第52届冠军杯小组抽签" required></label>
            <label><span>赛季标识</span><input id="drawCreateSeason" type="text" maxlength="40" placeholder="例如：第52届"></label>
            <label><span>任务校验码（可留空）</span><input id="drawCreateSeed" type="text" maxlength="100" placeholder="仅用于任务审计，不决定抽签结果"></label>
            <div class="draw-create-handoff"><strong>先建任务，再填名单</strong><span>创建后会立即打开草稿编辑台，可随时改设置、增量加人、移除候选或按规则预填。</span></div>
            <button class="btn btn-primary" type="submit">创建并进入编辑台</button>
        </form>`);
}

async function createWorkspaceDraw() {
    const drawType = document.getElementById('drawCreateType')?.value || 'champions_group';
    const payload = {
        name: document.getElementById('drawCreateName')?.value || '',
        draw_type: drawType,
        season_label: document.getElementById('drawCreateSeason')?.value || null,
        random_seed: document.getElementById('drawCreateSeed')?.value || null,
        config: drawType === 'lottery' ? {limit: 15} : drawTypeIsCustom(drawType) ? {mode: 'list'} : {},
        entries: [],
    };
    const data = await drawApi('/api/admin/draws', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
    if (!data) return;
    closeModal();
    workspaceCurrentDraw = data;
    workspaceDrawSessions = [];
    await loadWorkspaceDraws({force: true});
    showSuccessToast('空白草稿已创建，可开始编辑和添加候选');
}

function syncDrawDraftConfigFields() {
    const mode = document.getElementById('drawDraftCustomMode')?.value || 'list';
    const groupField = document.querySelector('.draw-draft-custom-group');
    const countField = document.querySelector('.draw-draft-custom-count');
    if (groupField) groupField.hidden = mode !== 'groups';
    if (countField) countField.hidden = mode !== 'list';
}

function drawDraftSettingsPayload() {
    const draw = workspaceCurrentDraw;
    if (!draw || draw.status !== 'draft') return {};
    const payload = {
        name: document.getElementById('drawDraftName')?.value || draw.name,
        season_label: document.getElementById('drawDraftSeason')?.value || null,
        random_seed: document.getElementById('drawDraftSeed')?.value || draw.random_seed,
    };
    if (drawTypeIsCustom(draw.draw_type)) {
        const mode = document.getElementById('drawDraftCustomMode')?.value || draw.config?.mode || 'list';
        const config = {mode};
        if (mode === 'groups') config.group_count = Number(document.getElementById('drawDraftGroupCount')?.value || draw.config?.group_count || 4);
        if (mode === 'list') {
            const resultCount = Number(document.getElementById('drawDraftResultCount')?.value || 0);
            if (resultCount > 0) config.result_count = resultCount;
        }
        payload.config = config;
    }
    return payload;
}

async function saveDrawDraftSettings(options = {}) {
    if (!workspaceCurrentDraw || workspaceCurrentDraw.status !== 'draft') return null;
    const data = await drawApi(`/api/admin/draws/${workspaceCurrentDraw.id}`, {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(drawDraftSettingsPayload())});
    if (!data) return null;
    workspaceCurrentDraw = data;
    workspaceDrawSessions = [];
    renderCurrentDraw();
    await loadWorkspaceDraws({force: true});
    if (!options.quiet) showSuccessToast('任务设置已保存');
    return data;
}

async function appendDrawDraftEntries() {
    const draw = workspaceCurrentDraw;
    const input = document.getElementById('drawDraftEntries');
    const text = input?.value || '';
    if (!draw || draw.status !== 'draft') return;
    if (!text.trim()) {
        showModal('还没有候选', '请先输入要添加的球队或球员，每行一个。');
        return;
    }
    try {
        if (typeof ensureTeamsLoaded === 'function') await ensureTeamsLoaded();
        if (['lottery', 'custom_player'].includes(draw.draw_type) && typeof ensurePlayersLoaded === 'function') await ensurePlayersLoaded();
    } catch (error) {
        showModal('候选索引加载失败', '球队或球员索引暂时无法读取，请稍后重试。');
        return;
    }
    let additions;
    try {
        additions = parseCustomDrawEntries(text, draw.draw_type, draw.entries.length) || [];
    } catch (error) {
        showModal('候选名单有误', escapeHtml(error.message));
        return;
    }
    const existing = draw.entries.map(drawEntryRequestPayload);
    const seen = new Set(existing.map(entry => drawEntryIdentity(entry, draw.draw_type)));
    let duplicate = null;
    additions.forEach(entry => {
        const identity = drawEntryIdentity(entry, draw.draw_type);
        if (!duplicate && seen.has(identity)) duplicate = entry;
        seen.add(identity);
    });
    if (duplicate) {
        showModal('候选已存在', `${escapeHtml(duplicate.entity_name || duplicate.team_name || '该候选')} 已经在当前候选池中。`);
        return;
    }
    const data = await drawApi(`/api/admin/draws/${draw.id}`, {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({...drawDraftSettingsPayload(), entries: [...existing, ...additions]})});
    if (!data) return;
    workspaceCurrentDraw = data;
    workspaceDrawSessions = [];
    renderCurrentDraw();
    await loadWorkspaceDraws({force: true});
    showSuccessToast(`已添加 ${additions.length} 个候选`);
}

async function removeDrawPoolEntry(entryId) {
    const draw = workspaceCurrentDraw;
    if (!draw || draw.status !== 'draft') return;
    const entry = draw.entries.find(item => Number(item.id) === Number(entryId));
    if (!entry) return;
    const entries = draw.entries.filter(item => Number(item.id) !== Number(entryId)).map(drawEntryRequestPayload);
    const data = await drawApi(`/api/admin/draws/${draw.id}`, {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({...drawDraftSettingsPayload(), entries})});
    if (!data) return;
    workspaceCurrentDraw = data;
    workspaceDrawSessions = [];
    renderCurrentDraw();
    await loadWorkspaceDraws({force: true});
    showSuccessToast(`已移除 ${entry.entity_name}`);
}

async function showDeleteDrawTask() {
    const draw = workspaceCurrentDraw;
    if (!draw || !['draft', 'void'].includes(draw.status)) return;
    const confirmed = await showConfirmDialog({title: '删除抽签任务', message: `“${draw.name}”及其候选池和抽取记录将被删除，操作审计仍会保留。`, confirmLabel: '确认删除', danger: true});
    if (!confirmed) return;
    const data = await drawApi(`/api/admin/draws/${draw.id}`, {method: 'DELETE'});
    if (!data) return;
    stopDrawRollTimer();
    workspaceCurrentDraw = null;
    workspaceDrawSessions = [];
    await loadWorkspaceDraws({force: true});
    showSuccessToast(data.message || '抽签任务已删除');
}

async function refillDrawFromProposal() {
    if (!workspaceCurrentDraw) return;
    const proposal = await drawApi(`/api/admin/draws/proposals/${workspaceCurrentDraw.draw_type}`);
    if (!proposal) return;
    const data = await drawApi(`/api/admin/draws/${workspaceCurrentDraw.id}`, {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({...drawDraftSettingsPayload(), entries: proposal.entries || []})});
    if (!data) return;
    workspaceCurrentDraw = data;
    renderCurrentDraw();
    showSuccessToast(proposal.unmatched?.length ? `已按规则顺延，未匹配：${proposal.unmatched.map(item => item.team_name).join('、')}` : '已按当前规则重新预填候选池');
}

async function saveCurrentDrawPool(options = {}) {
    if (!workspaceCurrentDraw) return;
    const data = await drawApi(`/api/admin/draws/${workspaceCurrentDraw.id}`, {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({...drawDraftSettingsPayload(), entries: workspaceCurrentDraw.entries.map(drawEntryRequestPayload)})});
    if (!data) return null;
    workspaceCurrentDraw = data;
    renderCurrentDraw();
    if (!options.quiet) showSuccessToast('候选池调整已保存');
    return data;
}

async function showLotteryPoolDialog() {
    const listsResult = await workJsonRequest('/api/admin/candidate-lists');
    const published = listsResult?.response?.ok ? (listsResult.data || []).filter(item => item.status === 'published') : [];
    const visibleTeams = (teams || []).filter(team => ['超级','甲级','乙级'].includes(team.level));
    showModal('生成乐透候选池', `
        <form class="lottery-pool-form" onsubmit="event.preventDefault(); buildLotteryPool();">
            <div class="lottery-pool-rules"><label><span>最低最终身价</span><input id="lotteryMinValue" type="number" min="0" max="50" step="0.5" value="${Number(workspaceCurrentDraw?.config?.min_final_value || 5)}"></label><label><span>计划抽取人数</span><input id="lotteryLimit" type="number" min="1" max="100" value="${Number(workspaceCurrentDraw?.config?.limit || 15)}"></label></div>
            <fieldset><legend>参与球队（由工作人员确认资格与豁免）</legend><div class="lottery-team-picker">${visibleTeams.map(team => `<label><input type="checkbox" name="lotteryTeam" value="${Number(team.id)}" checked><span>${escapeHtml(team.name)}</span><small>${escapeHtml(team.level)}</small></label>`).join('')}</div></fieldset>
            <fieldset><legend>排除已发布候选名单</legend><div class="lottery-list-picker">${published.map(item => `<label><input type="checkbox" name="lotteryExcludedList" value="${Number(item.id)}"><span>${escapeHtml(item.name)}</span><small>${Number(item.player_count || 0)} 人</small></label>`).join('') || '<span>暂无已发布候选名单</span>'}</div></fieldset>
            <label><span>额外排除球员 UID</span><textarea id="lotteryExcludedUids" rows="3" placeholder="逗号、空格或换行分隔"></textarea></label>
            <label><span>从排除名单恢复的球员 UID</span><textarea id="lotteryRestoredUids" rows="2" placeholder="用于恢复个别球员"></textarea></label>
            <button class="btn btn-primary" type="submit">生成并冻结预览</button>
        </form>`);
}

function parseUidList(value) {
    return [...new Set(String(value || '').split(/[^0-9]+/).filter(Boolean).map(Number).filter(Number.isFinite))];
}

async function buildLotteryPool() {
    const saved = await saveDrawDraftSettings({quiet: true});
    if (!saved) return;
    const payload = {
        min_final_value: Number(document.getElementById('lotteryMinValue')?.value || 5),
        limit: Number(document.getElementById('lotteryLimit')?.value || 15),
        team_ids: [...document.querySelectorAll('input[name="lotteryTeam"]:checked')].map(input => Number(input.value)),
        excluded_candidate_list_ids: [...document.querySelectorAll('input[name="lotteryExcludedList"]:checked')].map(input => Number(input.value)),
        excluded_player_uids: parseUidList(document.getElementById('lotteryExcludedUids')?.value),
        restored_player_uids: parseUidList(document.getElementById('lotteryRestoredUids')?.value),
        self_save_counts: {},
    };
    const data = await drawApi(`/api/admin/draws/${workspaceCurrentDraw.id}/lottery-pool`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
    if (!data) return;
    closeModal();
    workspaceCurrentDraw = data;
    workspaceDrawLotteryFilter = '';
    renderCurrentDraw();
    showSuccessToast(`候选池已生成：${data.entry_count} 名球员`);
}

async function lockCurrentDraw() {
    const saved = await saveCurrentDrawPool({quiet: true});
    if (!saved) return;
    const data = await drawApi(`/api/admin/draws/${workspaceCurrentDraw.id}/lock`, {method: 'POST'});
    if (!data) return;
    workspaceCurrentDraw = data;
    workspaceDrawSessions = [];
    renderCurrentDraw();
    showSuccessToast('候选池已锁定，任务校验码与池哈希已留存');
}

function showInvalidateLotteryPick(pickId) {
    showModal('作废本次乐透结果', `<form class="draw-reason-form" onsubmit="event.preventDefault(); invalidateLotteryPick(${Number(pickId)});"><p>原结果会保留为作废记录；下一次抽取只会从尚未中签的球队中补抽。</p><textarea id="drawInvalidateReason" rows="4" placeholder="例如：转会期内发生现实转会" required></textarea><button class="btn btn-danger" type="submit">作废并允许补抽</button></form>`);
}

async function invalidateLotteryPick(pickId) {
    const reason = document.getElementById('drawInvalidateReason')?.value || '';
    const data = await drawApi(`/api/admin/draws/${workspaceCurrentDraw.id}/picks/${pickId}/invalidate`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({reason})});
    if (!data) return;
    closeModal();
    workspaceCurrentDraw = data;
    renderCurrentDraw();
}

async function createDrawCandidateList() {
    const data = await drawApi(`/api/admin/draws/${workspaceCurrentDraw.id}/candidate-list`, {method: 'POST'});
    if (!data) return;
    workspaceCurrentDraw = data;
    renderCurrentDraw();
    showSuccessToast('候选名单草稿已生成');
}

async function publishCurrentDraw() {
    const data = await drawApi(`/api/admin/draws/${workspaceCurrentDraw.id}/publish`, {method: 'POST'});
    if (!data) return;
    workspaceCurrentDraw = data;
    renderCurrentDraw();
    showSuccessToast('抽签结果已发布');
}

async function writeCurrentDrawToCup() {
    const data = await drawApi(`/api/admin/draws/${workspaceCurrentDraw.id}/write-to-cup`, {method: 'POST'});
    if (!data) return;
    workspaceCurrentDraw = data;
    renderCurrentDraw();
    showSuccessToast('抽签结果已写入杯赛');
}

function showVoidCurrentDraw() {
    showModal('作废整场抽签', `<form class="draw-reason-form" onsubmit="event.preventDefault(); voidCurrentDraw();"><p>修改锁定后的名单必须作废整场并新建任务，原任务校验码、候选池和结果仍会保留。</p><textarea id="drawVoidReason" rows="4" placeholder="填写作废原因" required></textarea><button class="btn btn-danger" type="submit">确认作废</button></form>`);
}

async function voidCurrentDraw() {
    const reason = document.getElementById('drawVoidReason')?.value || '';
    const data = await drawApi(`/api/admin/draws/${workspaceCurrentDraw.id}/void`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({reason})});
    if (!data) return;
    closeModal();
    workspaceCurrentDraw = data;
    renderCurrentDraw();
}

async function loadSeasonArchives(options = {}) {
    if (!workspaceHasCapability('archives.write')) return;
    if (!workspaceSeasonArchives.length || options.force === true) {
        const data = await drawApi('/api/admin/season-archives');
        if (!data) return;
        workspaceSeasonArchives = Array.isArray(data) ? data : [];
    }
    const host = document.getElementById('seasonArchiveList');
    if (!host) return;
    host.innerHTML = workspaceSeasonArchives.length ? `<div class="season-archive-list">${workspaceSeasonArchives.map(item => `<article><span>REV ${item.revision_no}</span><div><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.season_key)} · ${item.status === 'confirmed' ? '已封存' : '草稿'}${item.revision_reason ? ` · ${escapeHtml(item.revision_reason)}` : ''}</small></div><button class="btn btn-secondary" type="button" onclick="showSeasonArchiveDetail(${Number(item.id)})">查看</button></article>`).join('')}</div>` : '<div class="draw-empty-state"><strong>还没有赛季档案</strong><span>赛季结束后生成草稿，完整性检查通过后再确认封存。</span></div>';
}

function showCreateSeasonArchiveDialog() {
    showModal('生成赛季档案', `<form class="draw-create-form" onsubmit="event.preventDefault(); createSeasonArchive();"><label><span>赛季标识</span><input id="seasonArchiveKey" type="text" placeholder="例如：第51届" required></label><label><span>档案标题</span><input id="seasonArchiveTitle" type="text" placeholder="留空使用默认标题"></label><label class="draw-confirm-toggle"><input id="seasonArchiveConfirm" type="checkbox"><span>完整性检查通过时直接确认封存</span></label><p>如果联赛、球员事件或杯赛冠军尚不完整，系统会拒绝直接封存；取消勾选可先保存草稿和缺项清单。</p><button class="btn btn-primary" type="submit">生成档案</button></form>`);
}

async function createSeasonArchive() {
    const payload = {season_key: document.getElementById('seasonArchiveKey')?.value || '', title: document.getElementById('seasonArchiveTitle')?.value || null, confirm: Boolean(document.getElementById('seasonArchiveConfirm')?.checked)};
    const data = await drawApi('/api/admin/season-archives', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
    if (!data) return;
    closeModal();
    workspaceSeasonArchives = [];
    await loadSeasonArchives({force: true});
    showSeasonArchiveDetail(data.id);
}

async function showSeasonArchiveDetail(archiveId) {
    const data = await drawApi(`/api/admin/season-archives/${archiveId}`);
    if (!data) return;
    const validation = data.validation || {};
    const championLabels = {champions_cup: '冠军杯', league_cup: '联盟杯', wumingjian_cup: '无铭剑杯'};
    showModal(data.title, `<div class="season-archive-detail"><div class="season-archive-state ${validation.ready ? 'is-ready' : ''}"><strong>${validation.ready ? '可以封存' : '仍有缺项'}</strong><span>修订版 ${data.revision_no} · ${data.status === 'confirmed' ? '已确认' : '草稿'}</span></div>${validation.blockers?.length ? `<ul>${validation.blockers.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>` : ''}<div class="season-archive-champions">${Object.entries(data.snapshot?.cup_champions || {}).map(([key, item]) => `<div><span>${escapeHtml(championLabels[key] || key)}</span><strong>${escapeHtml(item?.team_name || '未产生')}</strong></div>`).join('')}</div><p>积分榜 ${Number(data.snapshot?.standings?.length || 0)} 队；球员榜数据与球队、主教、队徽快照已保存在档案版本中。</p><div class="draw-stage-actions">${data.status === 'draft' && validation.ready ? `<button class="btn btn-primary" type="button" onclick="confirmSeasonArchive(${data.id})">确认封存</button>` : ''}${data.status === 'confirmed' ? `<button class="btn btn-secondary" type="button" onclick="showSeasonArchiveRevisionDialog(${data.id}, ${htmlJsString(data.title)})">创建修订版</button>` : ''}</div></div>`);
}

function showSeasonArchiveRevisionDialog(archiveId, title) {
    showModal('创建赛季档案修订版', `<form class="draw-create-form" onsubmit="event.preventDefault(); createSeasonArchiveRevision(${Number(archiveId)});"><p>原档案不会被覆盖；修订版会重新读取当前数据并单独保存原因。</p><label><span>修订版标题</span><input id="seasonRevisionTitle" type="text" value="${escapeHtml(title)}"></label><label><span>修订原因</span><textarea id="seasonRevisionReason" rows="4" placeholder="说明修订了哪些历史数据" required></textarea></label><label class="draw-confirm-toggle"><input id="seasonRevisionConfirm" type="checkbox" checked><span>完整性检查通过后直接确认</span></label><button class="btn btn-primary" type="submit">生成修订版</button></form>`);
}

async function createSeasonArchiveRevision(archiveId) {
    const payload = {season_key: 'revision', title: document.getElementById('seasonRevisionTitle')?.value || null, revision_of: archiveId, revision_reason: document.getElementById('seasonRevisionReason')?.value || '', confirm: Boolean(document.getElementById('seasonRevisionConfirm')?.checked)};
    const data = await drawApi('/api/admin/season-archives', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
    if (!data) return;
    closeModal();
    workspaceSeasonArchives = [];
    await loadSeasonArchives({force: true});
    showSeasonArchiveDetail(data.id);
}

async function confirmSeasonArchive(archiveId) {
    const data = await drawApi(`/api/admin/season-archives/${archiveId}/confirm`, {method: 'POST'});
    if (!data) return;
    closeModal();
    workspaceSeasonArchives = [];
    await loadSeasonArchives({force: true});
    showSuccessToast('赛季档案已确认封存');
}
