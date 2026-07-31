var coachesData = {levels: [], coaches: []};
var coachesLoaded = false;
var currentCoachDetail = null;
var coachReactionSubmitting = false;
var coachReactionCooldownTimer = null;
var coachReactionAnimatingType = '';
var pendingCoachOpenUid = '';
var coachLoginSuccessContext = '';
var coachForcedPasswordPromptOpen = false;
var coachForcedPasswordCompleteHandler = null;
var coachForcedQqPromptOpen = false;
var coachForcedQqCompleteHandler = null;
const COACH_HONOR_COMPETITIONS = ['超级杯', '冠军杯', '联盟杯', '无铭剑杯', '足总杯', '联赛杯', '联机联赛联盟杯', '世界杯', '新人赛', '超级联赛', '甲级联赛', '乙级联赛'];
const COACH_HONOR_PLACEMENTS = ['冠军', '亚军', '季军'];
const COACH_TITLE_COLORS = [
    {value: 'white', label: '白色'},
    {value: 'green', label: '绿色'},
    {value: 'blue', label: '蓝色'},
    {value: 'purple', label: '紫色'},
    {value: 'orange', label: '橙色'},
    {value: 'red', label: '红色'},
    {value: 'gold', label: '冠军金'},
    {value: 'cyan', label: '冰蓝'},
    {value: 'pink', label: '粉蓝'},
    {value: 'emerald', label: '翡翠'},
    {value: 'silver', label: '银灰'},
    {value: 'blackgold', label: '黑金'},
    {value: 'rainbow', label: '彩虹闪动'},
    {value: 'marquee', label: '跑马灯'},
    {value: 'pulse', label: '呼吸微光'},
    {value: 'blink', label: '低频闪烁'},
    {value: 'jump', label: '颜色跳变'},
    {value: 'aurora', label: '极光流动'},
];

const COACH_ASSISTANT_LEVELS = [
    {value: '全权助教', label: '全权助教'},
    {value: '正式助教', label: '正式助教'},
    {value: '实习助教', label: '实习助教'},
];

function normalizeCoachReactionSummary(summary = {}) {
    const cooldownSeconds = Math.max(0, Number(summary.cooldown_seconds) || 0);
    return {
        flowers: Math.max(0, Number(summary.flowers) || 0),
        eggs: Math.max(0, Number(summary.eggs) || 0),
        can_react: summary.can_react !== false && cooldownSeconds === 0,
        cooldown_seconds: cooldownSeconds,
    };
}

function getCoachInitials(name) {
    const clean = String(name || '').trim();
    if (!clean) return '教';
    return clean.slice(0, 2).toUpperCase();
}

function getCoachAvatarHtml(coach, className = 'coach-avatar') {
    if (coach?.avatar_path) {
        return `<img class="${className}" src="${escapeHtml(coach.avatar_path)}" alt="${escapeHtml(coach.nickname || '教练')}头像">`;
    }
    return `<div class="${className} coach-avatar-fallback">${escapeHtml(getCoachInitials(coach?.nickname))}</div>`;
}

function getCoachTitleColorClass(coach) {
    const color = String(coach?.title_color || 'white').trim().toLowerCase();
    return COACH_TITLE_COLORS.some(item => item.value === color) ? `coach-title-${color}` : 'coach-title-white';
}

function getCoachTitleColorOptions(selected = 'white') {
    return COACH_TITLE_COLORS.map(item => `<option value="${item.value}" ${item.value === selected ? 'selected' : ''}>${escapeHtml(item.label)}</option>`).join('');
}

function normalizeCoachLookupName(name) {
    return String(name || '').replace(/\s+/g, '').trim().toLowerCase();
}

function findCoachByName(name) {
    const target = normalizeCoachLookupName(name);
    if (!target) return null;
    return (coachesData.coaches || []).find(coach => normalizeCoachLookupName(coach.nickname) === target) || null;
}

async function ensureCoachesDataLoaded(options = {}) {
    if (coachesLoaded && options.force !== true) return;
    const response = await fetch('/api/coaches');
    if (!response.ok) throw new Error('coach-load-failed');
    coachesData = await response.json();
    coachesLoaded = true;
}

function renderCoachProfileLink(name, className = 'coach-profile-link') {
    const clean = String(name || '').trim();
    if (!clean || clean === '-') return escapeHtml(clean || '-');
    return `<button class="${className}" type="button" onclick="openCoachProfileByName(${htmlJsString(clean)})" title="查看${escapeHtml(clean)}的教练主页">${escapeHtml(clean)}</button>`;
}

async function openCoachProfileByName(name) {
    const clean = String(name || '').trim();
    if (!clean || clean === '-') return;
    try {
        await ensureCoachesDataLoaded();
        const coach = findCoachByName(clean);
        if (!coach) {
            showModal('未找到教练主页', `${escapeHtml(clean)} 暂未匹配到教练主页。`);
            return;
        }
        pendingCoachOpenUid = coach.uid;
        showTab('coaches', null, {syncHistory: false});
    } catch (error) {
        console.error('打开教练主页失败:', error);
        showModal('打开失败', '教练主页暂时无法打开，请稍后重试。');
    }
}

function groupCoachesByLevel() {
    const groups = {};
    for (const level of coachesData.levels || ['超级', '甲级', '乙级']) groups[level] = [];
    for (const coach of coachesData.coaches || []) {
        const level = coach.level || '未分级';
        if (!groups[level]) groups[level] = [];
        groups[level].push(coach);
    }
    Object.values(groups).forEach(items => {
        items.sort((a, b) => String(a.team_name || '').localeCompare(String(b.team_name || '')) || String(a.nickname || '').localeCompare(String(b.nickname || '')));
    });
    return groups;
}

function getOrderedCoachList() {
    const groups = groupCoachesByLevel();
    return (coachesData.levels || ['超级', '甲级', '乙级'])
        .flatMap(level => groups[level] || [])
        .concat(Object.entries(groups)
            .filter(([level]) => !(coachesData.levels || ['超级', '甲级', '乙级']).includes(level))
            .flatMap(([, items]) => items || []));
}

function getCoachDetailNeighbors(coachUid) {
    const ordered = getOrderedCoachList();
    const index = ordered.findIndex(coach => String(coach.uid) === String(coachUid));
    return {
        previous: index > 0 ? ordered[index - 1] : null,
        next: index >= 0 && index < ordered.length - 1 ? ordered[index + 1] : null,
    };
}

async function openAdjacentCoachDetail(direction) {
    if (!currentCoachDetail) return;
    const neighbors = getCoachDetailNeighbors(currentCoachDetail.uid);
    const target = direction === 'previous' ? neighbors.previous : neighbors.next;
    if (!target) return;
    await openCoachDetail(target.uid);
    if (typeof syncAppHistory === 'function') {
        syncAppHistory('push');
    }
}

function renderCoachDetailNavigation(coach) {
    const neighbors = getCoachDetailNeighbors(coach.uid);
    return `
        <div class="coach-detail-nav" aria-label="切换教练">
            <button class="btn btn-secondary coach-detail-nav-btn" type="button" onclick="openAdjacentCoachDetail('previous')" ${neighbors.previous ? '' : 'disabled'} title="${neighbors.previous ? `上一位：${escapeHtml(neighbors.previous.nickname || '-')}` : '已经是第一位教练'}">上一个</button>
            <button class="btn btn-secondary coach-detail-nav-btn" type="button" onclick="openAdjacentCoachDetail('next')" ${neighbors.next ? '' : 'disabled'} title="${neighbors.next ? `下一位：${escapeHtml(neighbors.next.nickname || '-')}` : '已经是最后一位教练'}">下一个</button>
        </div>
    `;
}

function showCoachDirectory() {
    document.getElementById('coachDirectoryView')?.classList.add('active');
    document.getElementById('coachDetailView')?.classList.remove('active');
    currentCoachDetail = null;
}

function showCoachDetailShell() {
    document.getElementById('coachDirectoryView')?.classList.remove('active');
    document.getElementById('coachDetailView')?.classList.add('active');
}

function canManageCoachProfiles() {
    return Boolean(currentAdminRole && canManageSchedule);
}

function canEditCurrentCoach(coach = currentCoachDetail) {
    return Boolean(coach && (canManageCoachProfiles() || (currentCoachAccount.authenticated && currentCoachAccount.coach_uid === coach.uid)));
}

function coachAccountHasWorkPermissions(account = currentCoachAccount) {
    return Boolean(!account?.must_change_password && account?.qq_number && (account?.can_manage_schedule || account?.can_manage_suspensions || account?.can_manage_candidate_lists));
}

function syncWorkPermissionsFromCoachAccount() {
    if (currentAdminRole) return;
    const securityReady = Boolean(currentCoachAccount.authenticated && !currentCoachAccount.must_change_password && currentCoachAccount.qq_number);
    canManageSchedule = Boolean(securityReady && currentCoachAccount.can_manage_schedule);
    canManageSuspensions = Boolean(securityReady && currentCoachAccount.can_manage_suspensions);
    canManageCandidateLists = Boolean(securityReady && currentCoachAccount.can_manage_candidate_lists);
}

async function syncCoachAuthStatus() {
    try {
        const response = await fetch('/api/coach/check', {credentials: 'same-origin'});
        currentCoachAccount = response.ok ? await response.json() : {authenticated: false};
    } catch (error) {
        currentCoachAccount = {authenticated: false};
    }
    syncWorkPermissionsFromCoachAccount();
    try {
        const workspaceResponse = await fetch('/api/workspace/session', {credentials: 'same-origin'});
        workspaceSessionState = workspaceResponse.ok ? await workspaceResponse.json() : {authenticated: false, identity: null};
    } catch (error) {
        workspaceSessionState = {authenticated: false, identity: null};
    }
    if (typeof syncLightweightAdminTabVisibility === 'function') syncLightweightAdminTabVisibility();
    renderCoachAuthBox();
    if (currentCoachAccount.authenticated && (currentCoachAccount.must_change_password || !currentCoachAccount.qq_number)) {
        setTimeout(() => beginCoachSecuritySetup(), 0);
    }
    return currentCoachAccount;
}

function renderCoachAuthBox() {
    if (typeof renderGlobalCoachAccount === 'function') renderGlobalCoachAccount();
    const host = document.getElementById('coachAuthBox');
    if (!host) return;
    if (currentCoachAccount.authenticated) {
        host.innerHTML = `
            <span class="coach-auth-pill">${escapeHtml(currentCoachAccount.nickname || currentCoachAccount.username || '教练')}</span>
            ${currentCoachAccount.qq_number ? `<span class="coach-auth-pill is-qq">QQ ${escapeHtml(currentCoachAccount.qq_number)}</span>` : ''}
            ${currentCoachAccount.must_change_password ? '<span class="coach-auth-pill is-security">待修改默认密码</span>' : ''}
            ${coachAccountHasWorkPermissions() ? '<span class="coach-auth-pill is-work">工作账号</span>' : ''}
            ${coachAccountHasWorkPermissions() ? '<button class="btn btn-primary" type="button" onclick="openCoachWorkspace()">进入工作台</button>' : ''}
            <button class="btn btn-secondary" type="button" onclick="coachLogout()">退出</button>
        `;
        return;
    }
    host.innerHTML = `<button class="btn btn-secondary" type="button" onclick="showCoachLoginPanel()">教练登录</button>`;
}

function showCoachLoginPanel(options = {}) {
    coachLoginSuccessContext = String(options.context || '');
    showModal('教练登录', `
        <form class="coach-login-form" onsubmit="event.preventDefault(); coachLogin();">
            <label class="ui-form-field" for="coachLoginUsername"><span>QQ号 / 旧账号</span><input id="coachLoginUsername" type="text" autocomplete="username" placeholder="输入已绑定 QQ 或旧账号"></label>
            <label class="ui-form-field" for="coachLoginPassword"><span>密码</span><input id="coachLoginPassword" type="password" autocomplete="current-password" placeholder="输入密码"></label>
            <span class="coach-login-hint">已绑定 QQ 的教练优先使用 QQ 号登录。</span>
            <div id="coachLoginFeedback" class="ui-inline-feedback" hidden></div>
            <button class="btn btn-primary" id="coachLoginSubmit" type="submit">登录</button>
        </form>
    `);
}

async function finalizeCoachLogin(data, successContext = '') {
    const workspaceResponse = await fetch('/api/workspace/session', {credentials: 'same-origin'});
    workspaceSessionState = workspaceResponse.ok ? await workspaceResponse.json() : {authenticated: false, identity: null};
    if (typeof syncLightweightAdminTabVisibility === 'function') syncLightweightAdminTabVisibility();
    renderCoachAuthBox();
    if (typeof renderTeamsTable === 'function') renderTeamsTable();
    if (typeof loadCompetitionData === 'function') loadCompetitionData({force: true});
    if (typeof renderCandidateDock === 'function') renderCandidateDock();
    if (typeof loadCandidateLists === 'function' && currentDatabaseSubtab === 'candidates') loadCandidateLists({force: true});
    if (typeof closeModal === 'function') closeModal({force: true});
    if (currentCoachDetail) renderCoachDetail();
    if (successContext === 'team-center' && typeof openCoachLinkedTeam === 'function') {
        await openCoachLinkedTeam(data);
    }
}

async function coachLogin() {
    const usernameInput = document.getElementById('coachLoginUsername');
    const passwordInput = document.getElementById('coachLoginPassword');
    const submitButton = document.getElementById('coachLoginSubmit');
    const username = usernameInput?.value.trim() || '';
    const password = passwordInput?.value || '';
    setUiFieldError(usernameInput);
    setUiFieldError(passwordInput);
    setUiInlineFeedback('coachLoginFeedback');
    if (!username || !password) {
        if (!username) setUiFieldError(usernameInput, '请输入 QQ 号或旧账号');
        if (!password) setUiFieldError(passwordInput, '请输入密码');
        (username ? passwordInput : usernameInput)?.focus();
        return;
    }
    setUiButtonBusy(submitButton, true, '正在登录');
    try {
        const response = await fetch('/api/coach/login', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password}),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || !data.authenticated) {
            setUiInlineFeedback('coachLoginFeedback', data.detail || '账号或密码错误，请检查后重试。', 'danger');
            passwordInput?.focus();
            passwordInput?.select();
            return;
        }
        currentCoachAccount = data;
        syncWorkPermissionsFromCoachAccount();
        const successContext = coachLoginSuccessContext;
        coachLoginSuccessContext = '';
        beginCoachSecuritySetup(() => finalizeCoachLogin(currentCoachAccount, successContext));
    } catch (error) {
        setUiInlineFeedback('coachLoginFeedback', '网络连接失败，请稍后重试。', 'danger');
    } finally {
        if (document.getElementById('coachLoginSubmit')) setUiButtonBusy(submitButton, false);
    }
}

async function openCoachWorkspace() {
    await showTab('admin', null, {syncHistory: true});
}

async function coachLogout() {
    await fetch('/api/coach/logout', {method: 'POST', credentials: 'same-origin'});
    currentCoachAccount = {authenticated: false};
    workspaceSessionState = {authenticated: false, identity: null};
    syncWorkPermissionsFromCoachAccount();
    if (typeof syncLightweightAdminTabVisibility === 'function') syncLightweightAdminTabVisibility();
    renderCoachAuthBox();
    if (typeof renderTeamsTable === 'function') renderTeamsTable();
    if (typeof loadCompetitionData === 'function') loadCompetitionData({force: true});
    if (typeof renderCandidateDock === 'function') renderCandidateDock();
    if (typeof loadCandidateLists === 'function' && currentDatabaseSubtab === 'candidates') loadCandidateLists({force: true});
    if (currentCoachDetail) renderCoachDetail();
}

async function loadCoaches(options = {}) {
    const board = document.getElementById('coachDirectoryBoard');
    if (!board) return;
    document.querySelectorAll('.coach-admin-only').forEach(item => {
        item.style.display = canManageCoachProfiles() ? '' : 'none';
    });
    await syncCoachAuthStatus();
    if (coachesLoaded && options.force !== true) {
        renderCoachDirectory();
        await openPendingCoachDetail();
        return;
    }
    board.innerHTML = '<div class="loading">加载中...</div>';
    try {
        await ensureCoachesDataLoaded({force: options.force === true});
        renderCoachDirectory();
        await openPendingCoachDetail();
    } catch (error) {
        console.error('Failed to load coaches:', error);
        board.innerHTML = renderUiState({tone: 'danger', title: '教练主页加载失败', message: '网络或服务暂时不可用，请稍后重试。', actionLabel: '重新加载', actionOnclick: 'loadCoaches({force:true})', compact: true});
    }
}

async function openPendingCoachDetail() {
    if (!pendingCoachOpenUid) return;
    const coachUid = pendingCoachOpenUid;
    pendingCoachOpenUid = '';
    await openCoachDetail(coachUid);
    if (typeof syncAppHistory === 'function') {
        syncAppHistory('push');
    }
}

function renderCoachDirectory() {
    const board = document.getElementById('coachDirectoryBoard');
    if (!board) return;
    showCoachDirectory();
    const groups = groupCoachesByLevel();
    board.innerHTML = `
        <div class="coach-level-grid">
            ${(coachesData.levels || ['超级', '甲级', '乙级']).map(level => `
                <section class="coach-level-column surface-card">
                    <div class="coach-level-head">
                        <h3>${escapeHtml(level)}教练</h3>
                        <span>${groups[level]?.length || 0} 人</span>
                    </div>
                    <div class="coach-card-list">
                        ${(groups[level] || []).length ? groups[level].map(coach => `
                            <button class="coach-list-card" type="button" onclick="openCoachDetail(${htmlJsString(coach.uid)})">
                                ${getCoachAvatarHtml(coach, 'coach-list-avatar')}
                                <span class="coach-list-main">
                                    <strong>${escapeHtml(coach.nickname || '-')}</strong>
                                    <span class="coach-list-title coach-title ${getCoachTitleColorClass(coach)}">${escapeHtml(coach.title || 'HEIGO 教练')}</span>
                                    <em>${escapeHtml(coach.team_name || '-')}</em>
                                </span>
                                <span class="coach-list-reactions">
                                    <span>花 ${Number(coach.reaction_summary?.flowers || 0)}</span>
                                    <span>蛋 ${Number(coach.reaction_summary?.eggs || 0)}</span>
                                </span>
                            </button>
                        `).join('') : renderUiState({tone: 'empty', title: '暂无教练主页', message: '同步教练资料后会显示在这里。', compact: true})}
                    </div>
                </section>
            `).join('')}
        </div>
    `;
}

async function openCoachDetail(coachUid) {
    showCoachDetailShell();
    const board = document.getElementById('coachDetailBoard');
    if (board) board.innerHTML = '<div class="loading">加载中...</div>';
    try {
        const response = await fetch(`/api/coaches/${encodeURIComponent(coachUid)}`);
        if (!response.ok) throw new Error('coach-detail-failed');
        currentCoachDetail = await response.json();
        renderCoachDetail();
        startCoachReactionCooldownTimer();
    } catch (error) {
        console.error('Failed to open coach detail:', error);
        if (board) board.innerHTML = '<div class="no-data">教练主页加载失败。</div>';
    }
}

function renderCoachReactionControls() {
    const host = document.getElementById('coachReactionControls');
    if (!host || !currentCoachDetail) return;
    currentCoachDetail.reaction_summary = normalizeCoachReactionSummary(currentCoachDetail.reaction_summary);
    const summary = currentCoachDetail.reaction_summary;
    const cooldownSeconds = Math.max(0, Number(summary.cooldown_seconds) || 0);
    const disabled = coachReactionSubmitting || cooldownSeconds > 0;
    host.innerHTML = `
        <div class="player-reaction-panel coach-reaction-panel" aria-label="教练互动">
            <div class="player-reaction-buttons">
                <button class="player-reaction-button is-flower ${coachReactionAnimatingType === 'flower' ? 'is-bouncing' : ''}" type="button" onclick="submitCoachReaction('flower')" ${disabled ? 'disabled' : ''} title="${cooldownSeconds > 0 ? `${cooldownSeconds} 秒后可再次互动` : '送花'}">
                    <span class="player-reaction-icon is-flower" aria-hidden="true"></span>
                    <span class="player-reaction-count">${summary.flowers}</span>
                </button>
                <button class="player-reaction-button is-egg ${coachReactionAnimatingType === 'egg' ? 'is-bouncing' : ''}" type="button" onclick="submitCoachReaction('egg')" ${disabled ? 'disabled' : ''} title="${cooldownSeconds > 0 ? `${cooldownSeconds} 秒后可再次互动` : '踩鸡蛋'}">
                    <span class="player-reaction-icon is-egg" aria-hidden="true"></span>
                    <span class="player-reaction-count">${summary.eggs}</span>
                </button>
            </div>
        </div>
    `;
}

function renderCoachHonors(coach) {
    const honors = coach.honors || [];
    if (!honors.length) return '<div class="coach-empty-block">暂无荣誉记录</div>';
    return honors.map(honor => `
        <article class="coach-honor-row">
            <div>
                <strong>${getCoachHonorIconHtml(honor)}${escapeHtml([honor.competition, honor.placement || honor.honor].filter(Boolean).join(' · ') || '-')}</strong>
                <span>${escapeHtml([honor.edition ? `第${honor.edition}届` : honor.season, honor.competition].filter(Boolean).join(' / ') || '未标注赛事')}</span>
                ${honor.description ? `<p>${escapeHtml(honor.description)}</p>` : ''}
            </div>
            ${canEditCurrentCoach(coach) ? `<button class="suspension-link-btn danger" type="button" onclick="deleteCoachHonor(${Number(honor.id)})">删除</button>` : ''}
        </article>
    `).join('');
}

function getCoachAssistantLevelClass(level) {
    const normalized = String(level || '').trim();
    if (normalized === '全权助教') return 'coach-assistant-level-full';
    if (normalized === '正式助教') return 'coach-assistant-level-regular';
    return 'coach-assistant-level-trainee';
}

function getCoachAssistantLevelOptions(selectedLevel = '正式助教') {
    return COACH_ASSISTANT_LEVELS
        .map(item => `<option value="${escapeHtml(item.value)}" ${item.value === selectedLevel ? 'selected' : ''}>${escapeHtml(item.label)}</option>`)
        .join('');
}

function renderCoachAssistants(coach) {
    const assistants = coach.assistants || [];
    const editable = canEditCurrentCoach(coach);
    return `
        <section class="coach-assistant-card surface-card">
            <div class="coach-assistant-head">
                <h3>助教团队</h3>
                ${editable ? `<button class="suspension-link-btn" type="button" onclick="showCoachAssistantModal()">新增</button>` : ''}
            </div>
            <div class="coach-assistant-list">
                ${assistants.length ? assistants.map(assistant => `
                    <article class="coach-assistant-row">
                        <div class="coach-assistant-main">
                            <span class="coach-assistant-level ${getCoachAssistantLevelClass(assistant.level)}">${escapeHtml(assistant.level || '实习助教')}</span>
                            <strong>${escapeHtml(assistant.name || '-')}</strong>
                            ${assistant.note ? `<p>${escapeHtml(assistant.note)}</p>` : ''}
                        </div>
                        ${editable ? `
                            <div class="coach-assistant-actions">
                                <button class="suspension-link-btn" type="button" onclick="showCoachAssistantModal(${Number(assistant.id)})">编辑</button>
                                <button class="suspension-link-btn danger" type="button" onclick="deleteCoachAssistant(${Number(assistant.id)})">删除</button>
                            </div>
                        ` : ''}
                    </article>
                `).join('') : '<div class="coach-empty-block">暂无助教记录</div>'}
            </div>
        </section>
    `;
}

function getCoachHonorIconHtml(honor) {
    const competition = String(honor?.competition || '').trim();
    const placement = honor?.placement || honor?.honor;
    if (competition === '新人赛' && String(placement || '').trim() === '冠军') {
        return '<span class="coach-pixel-chicken" aria-hidden="true"></span>';
    }
    return getCoachHonorMedalHtml(placement);
}

function getCoachHonorMedalHtml(placement) {
    const normalized = String(placement || '').trim();
    const className = normalized === '冠军' ? 'gold' : normalized === '亚军' ? 'silver' : normalized === '季军' ? 'bronze' : '';
    if (!className) return '';
    return `<span class="coach-medal coach-medal-${className}" aria-hidden="true"></span>`;
}

function getCoachHonorOptions(selectedCompetition = '冠军杯', selectedPlacement = '冠军') {
    const competitionOptions = COACH_HONOR_COMPETITIONS.map(item => `<option value="${escapeHtml(item)}" ${item === selectedCompetition ? 'selected' : ''}>${escapeHtml(item)}</option>`).join('');
    const placementOptions = COACH_HONOR_PLACEMENTS.map(item => `<option value="${escapeHtml(item)}" ${item === selectedPlacement ? 'selected' : ''}>${escapeHtml(item)}</option>`).join('');
    return {competitionOptions, placementOptions};
}

function renderCoachActionPanel(coach) {
    if (!canEditCurrentCoach(coach)) return '';
    return `
        <section class="coach-action-panel surface-card">
            <button class="btn btn-secondary" type="button" onclick="showCoachProfileModal()">修改资料/称号样式</button>
            <button class="btn btn-secondary" type="button" onclick="showCoachAvatarModal()">上传头像</button>
            <button class="btn btn-secondary" type="button" onclick="showCoachHonorModal()">添加荣誉</button>
            ${!canManageCoachProfiles() && currentCoachAccount.authenticated ? `<button class="btn btn-secondary" type="button" onclick="showCoachQqModal()">${currentCoachAccount.qq_number ? 'QQ与登录安全' : '绑定QQ与登录安全'}</button>` : ''}
            ${isAdmin ? `<button class="btn btn-secondary" type="button" onclick="showCoachAccountModal()">账号设置</button>` : ''}
        </section>
    `;
}

function showCoachProfileModal() {
    if (!canEditCurrentCoach() || !currentCoachDetail) return;
    showModal('修改资料', `
        <div class="coach-modal-form">
            ${canManageCoachProfiles() ? `<input id="coachEditNickname" type="text" value="${escapeHtml(currentCoachDetail.nickname || '')}" placeholder="教练昵称">` : ''}
            <input id="coachEditTitle" type="text" value="${escapeHtml(currentCoachDetail.title || '')}" placeholder="个人称号">
            <label class="coach-modal-field-label" for="coachEditTitleColor">称号样式</label>
            <select id="coachEditTitleColor">${getCoachTitleColorOptions(currentCoachDetail.title_color || 'white')}</select>
            <textarea id="coachEditBio" placeholder="个人介绍">${escapeHtml(currentCoachDetail.bio || '')}</textarea>
            <button class="btn btn-primary" type="button" onclick="saveCoachProfile()">保存资料</button>
        </div>
    `);
}

function showCoachAvatarModal() {
    if (!canEditCurrentCoach() || !currentCoachDetail) return;
    showModal('上传头像', `
        <div class="coach-modal-form">
            <input id="coachAvatarInput" type="file" accept="image/png,image/jpeg,image/webp">
            <span class="coach-upload-hint">JPG / PNG / WEBP，2MB 内，至少 240x240，自动裁成 512x512。</span>
            <button class="btn btn-primary" type="button" onclick="uploadCoachAvatar()">上传头像</button>
        </div>
    `);
}

function showCoachHonorModal() {
    if (!canEditCurrentCoach() || !currentCoachDetail) return;
    const {competitionOptions, placementOptions} = getCoachHonorOptions();
    showModal('添加荣誉', `
        <div class="coach-modal-form">
            <input id="coachHonorEdition" type="number" min="1" max="999" value="85" placeholder="届数，例如 85">
            <select id="coachHonorCompetition">${competitionOptions}</select>
            <select id="coachHonorPlacement">${placementOptions}</select>
            <input id="coachHonorSort" type="number" value="0" placeholder="排序">
            <textarea id="coachHonorDescription" placeholder="荣誉说明"></textarea>
            <button class="btn btn-primary" type="button" onclick="saveCoachHonor()">新增荣誉</button>
        </div>
    `);
}

function showCoachAssistantModal(assistantId = null) {
    if (!canEditCurrentCoach() || !currentCoachDetail) return;
    const assistant = assistantId
        ? (currentCoachDetail.assistants || []).find(item => Number(item.id) === Number(assistantId))
        : null;
    const selectedLevel = assistant?.level || '正式助教';
    showModal(assistant ? '编辑助教' : '新增助教', `
        <div class="coach-modal-form">
            <input id="coachAssistantName" type="text" value="${escapeHtml(assistant?.name || '')}" placeholder="助教姓名">
            <select id="coachAssistantLevel">${getCoachAssistantLevelOptions(selectedLevel)}</select>
            <input id="coachAssistantSort" type="number" value="${Number(assistant?.sort_order || 0)}" placeholder="排序">
            <textarea id="coachAssistantNote" placeholder="备注，可选">${escapeHtml(assistant?.note || '')}</textarea>
            <button class="btn btn-primary" type="button" onclick="saveCoachAssistant(${assistant ? Number(assistant.id) : 'null'})">${assistant ? '保存助教' : '新增助教'}</button>
        </div>
    `);
}

function showCoachPasswordModal() {
    if (!currentCoachAccount.authenticated) return;
    showModal('修改密码', `
        <div class="coach-modal-form">
            <input id="coachCurrentPassword" type="password" autocomplete="current-password" placeholder="当前密码">
            <input id="coachNewPassword" type="password" autocomplete="new-password" placeholder="新密码，至少 6 位">
            <button class="btn btn-primary" type="button" onclick="changeCoachPassword()">修改密码</button>
        </div>
    `);
}

function showCoachForcedPasswordModal(onComplete = null, errorMessage = '') {
    if (!currentCoachAccount.authenticated || !currentCoachAccount.must_change_password) return;
    if (typeof onComplete === 'function') coachForcedPasswordCompleteHandler = onComplete;
    if (coachForcedPasswordPromptOpen) return;
    coachForcedPasswordPromptOpen = true;
    showModal('首次登录 · 修改默认密码', `
        <div class="coach-security-gate">
            <div class="coach-security-gate-mark" aria-hidden="true">${uiIconSvg('check')}</div>
            <div><strong>先设置你自己的密码</strong><p>管理员提供的密码仅用于首次进入。修改完成前，球队中心、个人资料和工作台操作都会保持锁定。</p></div>
            ${errorMessage ? `<div class="coach-security-error">${escapeHtml(errorMessage)}</div>` : ''}
            <input id="coachCurrentPassword" type="password" autocomplete="current-password" placeholder="当前默认密码">
            <input id="coachNewPassword" type="password" autocomplete="new-password" placeholder="新密码，至少 6 位">
            <input id="coachConfirmPassword" type="password" autocomplete="new-password" placeholder="再次输入新密码">
            <button class="btn btn-primary" type="button" onclick="changeCoachPassword({forced: true})">保存新密码并继续</button>
        </div>
    `, {locked: true});
}

function beginCoachSecuritySetup(onComplete = null) {
    if (!currentCoachAccount.authenticated) return false;
    if (currentCoachAccount.must_change_password) {
        showCoachForcedPasswordModal(() => beginCoachSecuritySetup(onComplete));
        return false;
    }
    if (!currentCoachAccount.qq_number) {
        showCoachForcedQqModal(onComplete);
        return false;
    }
    if (typeof onComplete === 'function') Promise.resolve(onComplete());
    return true;
}

function showCoachForcedQqModal(onComplete = null, errorMessage = '') {
    if (!currentCoachAccount.authenticated || currentCoachAccount.must_change_password || currentCoachAccount.qq_number) return;
    if (typeof onComplete === 'function') coachForcedQqCompleteHandler = onComplete;
    if (coachForcedQqPromptOpen) return;
    coachForcedQqPromptOpen = true;
    showModal('登录安全 · 绑定 QQ', `
        <div class="coach-security-gate coach-qq-gate">
            <div class="coach-security-gate-mark" aria-hidden="true">Q</div>
            <div><strong>绑定你自己的 QQ 号</strong><p>QQ 将成为主要登录凭证。绑定完成前，球队中心、个人资料和联赛工作台都会保持锁定。</p></div>
            ${errorMessage ? `<div class="coach-security-error">${escapeHtml(errorMessage)}</div>` : ''}
            <input id="coachBindQqNumber" type="text" inputmode="numeric" autocomplete="off" placeholder="输入 5-12 位 QQ 号">
            <input id="coachBindQqPassword" type="password" autocomplete="current-password" placeholder="验证刚设置的密码">
            <button class="btn btn-primary" type="button" onclick="bindCoachQq({forced: true})">绑定 QQ 并进入</button>
        </div>
    `, {locked: true});
}

function showCoachQqModal() {
    if (!currentCoachAccount.authenticated) return;
    showModal('QQ 与登录安全', `
        <div class="coach-security-panel">
            <div class="coach-security-identity">
                <span>主要登录凭证</span>
                <strong>${currentCoachAccount.qq_number ? `QQ ${escapeHtml(currentCoachAccount.qq_number)}` : '尚未绑定 QQ'}</strong>
                <small>旧账号 ${escapeHtml(currentCoachAccount.username || '-')} 继续作为兼容入口。</small>
            </div>
            <label><span>${currentCoachAccount.qq_number ? '更换绑定 QQ' : '绑定你的 QQ'}</span><input id="coachBindQqNumber" type="text" inputmode="numeric" autocomplete="off" value="${escapeHtml(currentCoachAccount.qq_number || '')}" placeholder="5-12 位 QQ 号"></label>
            <label><span>验证当前密码</span><input id="coachBindQqPassword" type="password" autocomplete="current-password" placeholder="当前密码"></label>
            <button class="btn btn-primary" type="button" onclick="bindCoachQq()">${currentCoachAccount.qq_number ? '更新 QQ 绑定' : '绑定 QQ'}</button>
            <button class="btn btn-secondary" type="button" onclick="showCoachPasswordModal()">修改登录密码</button>
        </div>
    `);
}

async function bindCoachQq(options = {}) {
    const payload = {
        qq_number: document.getElementById('coachBindQqNumber')?.value || '',
        current_password: document.getElementById('coachBindQqPassword')?.value || '',
    };
    const result = await coachJsonRequest('/api/coach/me/qq', {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    });
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        if (options.forced) {
            coachForcedQqPromptOpen = false;
            showCoachForcedQqModal(coachForcedQqCompleteHandler, data.detail || data.message || 'QQ 绑定失败');
        } else {
            showModal('绑定失败', escapeHtml(data.detail || data.message || 'QQ 绑定失败'));
        }
        return;
    }
    await syncCoachAuthStatus();
    if (options.forced) {
        coachForcedQqPromptOpen = false;
        closeModal({force: true});
        const handler = coachForcedQqCompleteHandler;
        coachForcedQqCompleteHandler = null;
        if (typeof handler === 'function') await handler();
        return;
    }
    showModal('绑定成功', `以后可以使用 QQ ${escapeHtml(currentCoachAccount.qq_number || payload.qq_number)} 和密码登录。`);
    if (currentCoachDetail) renderCoachDetail();
}

async function showCoachAccountModal() {
    if (!isAdmin || !currentCoachDetail) return;
    showModal('教练账号', `
        <div class="coach-modal-form">
            <div id="coachAccountStatus" class="coach-account-status">加载账号状态...</div>
            <div id="coachAccountQqStatus" class="coach-account-qq-status"></div>
            <input id="coachAccountUsername" type="text" placeholder="账号名">
            <input id="coachAccountPassword" type="password" placeholder="新账号必填；已有账号留空则不改密码">
            <label class="coach-account-toggle"><input id="coachAccountActive" type="checkbox" checked> 启用账号</label>
            <section class="coach-account-permissions">
                <div>
                    <strong>工作权限</strong>
                    <span>勾选后，该教练账号可直接维护对应模块。</span>
                </div>
                <label class="coach-account-toggle"><input id="coachAccountSchedule" type="checkbox">赛程编辑</label>
                <label class="coach-account-toggle"><input id="coachAccountSuspensions" type="checkbox">伤停编辑</label>
                <label class="coach-account-toggle"><input id="coachAccountCandidates" type="checkbox">候选名单编辑</label>
            </section>
            <button class="btn btn-primary" type="button" onclick="saveCoachAccount()">保存/重置账号</button>
        </div>
    `);
    await loadCoachAccountStatus();
}

function renderCoachDetail() {
    const board = document.getElementById('coachDetailBoard');
    const coach = currentCoachDetail;
    if (!board || !coach) return;
    board.innerHTML = `
        <div class="coach-detail-shell">
            <div class="coach-detail-toolbar">
                <button class="btn btn-secondary" type="button" onclick="renderCoachDirectory()">返回教练列表</button>
                ${renderCoachDetailNavigation(coach)}
            </div>
            <section class="coach-profile-grid">
                <aside class="coach-side-column">
                    <section class="coach-profile-card surface-card">
                        ${getCoachAvatarHtml(coach, 'coach-profile-avatar')}
                        <h2>${escapeHtml(coach.nickname || '-')}</h2>
                        <p class="coach-title ${getCoachTitleColorClass(coach)}">${escapeHtml(coach.title || 'HEIGO 教练')}</p>
                        <div id="coachReactionControls" class="player-reaction-host"></div>
                        <div class="coach-info-list">
                            <span><strong>UID</strong>${escapeHtml(coach.uid)}</span>
                            <span><strong>球队</strong>${escapeHtml(coach.team_name || '-')}</span>
                            <span><strong>级别</strong>${escapeHtml(coach.level || '-')}</span>
                        </div>
                    </section>
                    ${renderCoachAssistants(coach)}
                </aside>
                <section class="coach-bio-card surface-card">
                    <h3>个人介绍</h3>
                    <p>${escapeHtml(coach.bio || '这位教练暂未填写个人介绍。')}</p>
                </section>
                <section class="coach-honor-card surface-card">
                    <h3>获得荣誉</h3>
                    <div class="coach-honor-list">${renderCoachHonors(coach)}</div>
                </section>
            </section>
            ${renderCoachActionPanel(coach)}
        </div>
    `;
    renderCoachReactionControls();
}

function clearCoachReactionCooldownTimer() {
    if (coachReactionCooldownTimer) {
        window.clearInterval(coachReactionCooldownTimer);
        coachReactionCooldownTimer = null;
    }
}

function startCoachReactionCooldownTimer() {
    clearCoachReactionCooldownTimer();
    if (!currentCoachDetail) return;
    currentCoachDetail.reaction_summary = normalizeCoachReactionSummary(currentCoachDetail.reaction_summary);
    if (!currentCoachDetail.reaction_summary.cooldown_seconds) return;
    coachReactionCooldownTimer = window.setInterval(() => {
        if (!currentCoachDetail) {
            clearCoachReactionCooldownTimer();
            return;
        }
        currentCoachDetail.reaction_summary.cooldown_seconds = Math.max(0, Number(currentCoachDetail.reaction_summary.cooldown_seconds || 0) - 1);
        if (!currentCoachDetail.reaction_summary.cooldown_seconds) {
            currentCoachDetail.reaction_summary.can_react = true;
            clearCoachReactionCooldownTimer();
        }
        renderCoachReactionControls();
    }, 1000);
}

async function submitCoachReaction(reactionType) {
    if (!currentCoachDetail || coachReactionSubmitting) return;
    coachReactionSubmitting = true;
    coachReactionAnimatingType = reactionType;
    renderCoachReactionControls();
    try {
        const response = await fetch(`/api/coaches/${encodeURIComponent(currentCoachDetail.uid)}/reactions/${reactionType}`, {method: 'POST'});
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || 'reaction-failed');
        currentCoachDetail.reaction_summary = normalizeCoachReactionSummary(payload.summary);
        const listCoach = (coachesData.coaches || []).find(item => item.uid === currentCoachDetail.uid);
        if (listCoach) listCoach.reaction_summary = currentCoachDetail.reaction_summary;
        startCoachReactionCooldownTimer();
    } catch (error) {
        showModal('互动失败', escapeHtml(error.message || '互动失败，请稍后重试。'));
    } finally {
        window.setTimeout(() => {
            coachReactionAnimatingType = '';
            coachReactionSubmitting = false;
            renderCoachReactionControls();
        }, 260);
    }
}

async function syncCoachesFromTeams() {
    if (!canManageCoachProfiles()) return;
    const result = await adminJsonRequest('/api/admin/coaches/sync', {method: 'POST'});
    if (!result) return;
    coachesLoaded = false;
    await loadCoaches({force: true});
}

async function saveCoachProfile() {
    if (!canEditCurrentCoach() || !currentCoachDetail) return;
    const payload = {
        nickname: document.getElementById('coachEditNickname')?.value || '',
        title: document.getElementById('coachEditTitle')?.value || '',
        title_color: document.getElementById('coachEditTitleColor')?.value || 'white',
        bio: document.getElementById('coachEditBio')?.value || '',
    };
    const useAdmin = canManageCoachProfiles();
    const url = useAdmin ? `/api/admin/coaches/${encodeURIComponent(currentCoachDetail.uid)}` : '/api/coach/me';
    const result = await coachJsonRequest(url, {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    }, useAdmin);
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('保存失败', escapeHtml(data.detail || data.message || '保存教练资料失败'));
        return;
    }
    if (typeof closeModal === 'function') closeModal();
    coachesLoaded = false;
    await openCoachDetail(currentCoachDetail.uid);
    if (currentCoachAccount.authenticated && currentCoachAccount.coach_uid === currentCoachDetail.uid) {
        currentCoachAccount.avatar_path = currentCoachDetail.avatar_path;
        renderGlobalCoachAccount();
    }
}

async function uploadCoachAvatar() {
    if (!canEditCurrentCoach() || !currentCoachDetail) return;
    const file = document.getElementById('coachAvatarInput')?.files?.[0];
    if (!file) {
        showModal('上传失败', '请先选择头像文件。');
        return;
    }
    const formData = new FormData();
    formData.append('avatar', file);
    const useAdmin = canManageCoachProfiles();
    const url = useAdmin ? `/api/admin/coaches/${encodeURIComponent(currentCoachDetail.uid)}/avatar` : '/api/coach/me/avatar';
    const result = await coachJsonRequest(url, {
        method: 'POST',
        body: formData,
    }, useAdmin);
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('上传失败', escapeHtml(data.detail || data.message || '上传头像失败'));
        return;
    }
    if (typeof closeModal === 'function') closeModal();
    coachesLoaded = false;
    await openCoachDetail(currentCoachDetail.uid);
    if (currentCoachAccount.authenticated && currentCoachAccount.coach_uid === currentCoachDetail.uid) {
        currentCoachAccount.avatar_path = currentCoachDetail.avatar_path;
        renderGlobalCoachAccount();
    }
}

async function saveCoachHonor() {
    if (!canEditCurrentCoach() || !currentCoachDetail) return;
    const edition = Number(document.getElementById('coachHonorEdition')?.value || 85);
    const competition = document.getElementById('coachHonorCompetition')?.value || '';
    const placement = document.getElementById('coachHonorPlacement')?.value || '';
    const payload = {
        coach_uid: currentCoachDetail.uid,
        edition,
        season: edition ? `第${edition}届` : '',
        competition,
        placement,
        honor: placement,
        sort_order: Number(document.getElementById('coachHonorSort')?.value || 0),
        description: document.getElementById('coachHonorDescription')?.value || '',
    };
    const useAdmin = canManageCoachProfiles();
    const url = useAdmin ? '/api/admin/coach-honors' : '/api/coach/me/honors';
    const result = await coachJsonRequest(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    }, useAdmin);
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('保存失败', escapeHtml(data.detail || data.message || '保存荣誉失败'));
        return;
    }
    if (typeof closeModal === 'function') closeModal();
    await openCoachDetail(currentCoachDetail.uid);
}

async function deleteCoachHonor(honorId) {
    if (!canEditCurrentCoach() || !currentCoachDetail) return;
    if (!confirm('确认删除这条教练荣誉？')) return;
    const useAdmin = canManageCoachProfiles();
    const url = useAdmin ? `/api/admin/coach-honors/${Number(honorId)}` : `/api/coach/me/honors/${Number(honorId)}`;
    const result = await coachJsonRequest(url, {method: 'DELETE'}, useAdmin);
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('删除失败', escapeHtml(data.detail || data.message || '删除荣誉失败'));
        return;
    }
    await openCoachDetail(currentCoachDetail.uid);
}

async function saveCoachAssistant(assistantId = null) {
    if (!canEditCurrentCoach() || !currentCoachDetail) return;
    const payload = {
        coach_uid: currentCoachDetail.uid,
        name: document.getElementById('coachAssistantName')?.value || '',
        level: document.getElementById('coachAssistantLevel')?.value || '正式助教',
        sort_order: Number(document.getElementById('coachAssistantSort')?.value || 0),
        note: document.getElementById('coachAssistantNote')?.value || '',
    };
    const isEdit = Number(assistantId) > 0;
    const useAdmin = canManageCoachProfiles();
    const url = useAdmin
        ? (isEdit ? `/api/admin/coach-assistants/${Number(assistantId)}` : '/api/admin/coach-assistants')
        : (isEdit ? `/api/coach/me/assistants/${Number(assistantId)}` : '/api/coach/me/assistants');
    const result = await coachJsonRequest(url, {
        method: isEdit ? 'PATCH' : 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    }, useAdmin);
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('保存失败', escapeHtml(data.detail || data.message || '保存助教失败'));
        return;
    }
    if (typeof closeModal === 'function') closeModal();
    await openCoachDetail(currentCoachDetail.uid);
}

async function deleteCoachAssistant(assistantId) {
    if (!canEditCurrentCoach() || !currentCoachDetail) return;
    if (!confirm('确认删除这位助教？')) return;
    const useAdmin = canManageCoachProfiles();
    const url = useAdmin
        ? `/api/admin/coach-assistants/${Number(assistantId)}`
        : `/api/coach/me/assistants/${Number(assistantId)}`;
    const result = await coachJsonRequest(url, {method: 'DELETE'}, useAdmin);
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('删除失败', escapeHtml(data.detail || data.message || '删除助教失败'));
        return;
    }
    await openCoachDetail(currentCoachDetail.uid);
}

async function coachJsonRequest(url, options = {}, useAdmin = false) {
    if (useAdmin) return adminJsonRequest(url, options);
    const response = await fetch(url, {...options, credentials: 'same-origin'});
    const data = await response.json();
    if (response.status === 401) {
        showModal('需要登录', '请先登录自己的教练账号。');
        await syncCoachAuthStatus();
        return null;
    }
    return {response, data};
}

async function loadCoachAccountStatus() {
    if (!isAdmin || !currentCoachDetail) return;
    const result = await adminJsonRequest(`/api/admin/coaches/${encodeURIComponent(currentCoachDetail.uid)}/account`);
    if (!result) return;
    const {response, data} = result;
    const status = document.getElementById('coachAccountStatus');
    const qqStatus = document.getElementById('coachAccountQqStatus');
    if (!response.ok) {
        if (status) status.textContent = '账号状态读取失败';
        return;
    }
    if (status) {
        const permissions = [];
        if (data.can_manage_schedule) permissions.push('赛程');
        if (data.can_manage_suspensions) permissions.push('伤停');
        if (data.can_manage_candidate_lists) permissions.push('候选名单');
        status.textContent = data.exists
            ? `当前账号：${data.username}${data.is_active ? '（启用）' : '（停用）'} · ${data.must_change_password ? '首次登录待改密' : '密码已由教练设置'} · 工作权限：${permissions.join('、') || '无'}`
            : '尚未设置教练账号';
    }
    if (qqStatus) {
        qqStatus.innerHTML = data.qq_number
            ? `<span>已绑定 QQ <strong>${escapeHtml(data.qq_number)}</strong></span><button class="btn btn-secondary" type="button" onclick="unbindCoachQqAsAdmin()">解除绑定</button>`
            : '<span>尚未绑定 QQ</span>';
    }
    const usernameInput = document.getElementById('coachAccountUsername');
    const activeInput = document.getElementById('coachAccountActive');
    const scheduleInput = document.getElementById('coachAccountSchedule');
    const suspensionsInput = document.getElementById('coachAccountSuspensions');
    const candidatesInput = document.getElementById('coachAccountCandidates');
    if (usernameInput && data.username) usernameInput.value = data.username;
    if (activeInput) activeInput.checked = data.exists ? Boolean(data.is_active) : true;
    if (scheduleInput) scheduleInput.checked = Boolean(data.can_manage_schedule);
    if (suspensionsInput) suspensionsInput.checked = Boolean(data.can_manage_suspensions);
    if (candidatesInput) candidatesInput.checked = Boolean(data.can_manage_candidate_lists);
}

async function unbindCoachQqAsAdmin() {
    if (!isAdmin || !currentCoachDetail) return;
    const result = await adminJsonRequest(`/api/admin/coaches/${encodeURIComponent(currentCoachDetail.uid)}/qq`, {method: 'DELETE'});
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('解绑失败', escapeHtml(data.detail || data.message || 'QQ 解绑失败'));
        return;
    }
    await showCoachAccountModal();
}

async function saveCoachAccount() {
    if (!isAdmin || !currentCoachDetail) return;
    const payload = {
        username: document.getElementById('coachAccountUsername')?.value || '',
        password: document.getElementById('coachAccountPassword')?.value || '',
        is_active: Boolean(document.getElementById('coachAccountActive')?.checked),
        can_manage_schedule: Boolean(document.getElementById('coachAccountSchedule')?.checked),
        can_manage_suspensions: Boolean(document.getElementById('coachAccountSuspensions')?.checked),
        can_manage_candidate_lists: Boolean(document.getElementById('coachAccountCandidates')?.checked),
    };
    const result = await adminJsonRequest(`/api/admin/coaches/${encodeURIComponent(currentCoachDetail.uid)}/account`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    });
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('保存失败', escapeHtml(data.detail || data.message || '保存教练账号失败'));
        return;
    }
    document.getElementById('coachAccountPassword').value = '';
    await loadCoachAccountStatus();
    showModal('保存成功', '教练账号已更新。');
}

async function changeCoachPassword(options = {}) {
    if (!currentCoachAccount.authenticated) return;
    const newPassword = document.getElementById('coachNewPassword')?.value || '';
    const confirmedPassword = document.getElementById('coachConfirmPassword')?.value || '';
    if (options.forced && newPassword !== confirmedPassword) {
        coachForcedPasswordPromptOpen = false;
        showCoachForcedPasswordModal(coachForcedPasswordCompleteHandler, '两次输入的新密码不一致，请重新填写。');
        return;
    }
    const payload = {
        current_password: document.getElementById('coachCurrentPassword')?.value || '',
        new_password: newPassword,
    };
    const result = await coachJsonRequest('/api/coach/me/password', {
        method: 'PATCH',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    });
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        if (options.forced) {
            coachForcedPasswordPromptOpen = false;
            showCoachForcedPasswordModal(coachForcedPasswordCompleteHandler, data.detail || data.message || '修改密码失败');
        } else {
            showModal('修改失败', escapeHtml(data.detail || data.message || '修改密码失败'));
        }
        return;
    }
    currentCoachAccount.must_change_password = false;
    if (options.forced) {
        coachForcedPasswordPromptOpen = false;
        closeModal({force: true});
        const handler = coachForcedPasswordCompleteHandler;
        coachForcedPasswordCompleteHandler = null;
        if (typeof handler === 'function') await handler();
        else await syncCoachAuthStatus();
        return;
    }
    showModal('修改成功', '密码已更新。');
}
