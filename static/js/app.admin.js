var fetchWithTimeout = globalThis.fetchWithTimeout || ((...args) => globalThis.fetch(...args));

let pendingUndoLogId = null;
const ADMIN_UNAUTHORIZED_ERROR = 'ADMIN_UNAUTHORIZED';
let lastAdminUnauthorizedNoticeAt = 0;
let recentDataFeedbackReports = [];
let workspaceSessionData = null;
let workspaceDashboardData = null;
let workspaceAccountsData = [];
let workspacePromotionsData = [];
let workspaceLogoMatcherData = null;
let workspaceLogoSelectedTeamId = null;
let workspaceLogoCandidates = [];
let workspaceLogoSelectedCandidateIndex = -1;
let workspaceLogoSourceMode = 'fclogo';
let workspaceLogoLocalFile = null;
let workspaceLogoLocalPreviewUrl = '';
let workspaceAdminOperationsLoaded = false;
let workspaceAdminOperationsLoadPromise = null;

const WORKSPACE_CAPABILITY_LABELS = {
    'schedule.write': '赛程维护',
    'match_events.write': '比赛事件',
    'cup_standings.write': '杯赛积分榜',
    'rankings.write': '排位统计',
    'suspensions.write': '伤停维护',
    'candidate_lists.write': '候选名单',
    'roster.write': '球员操作',
    'coach_profile.write_self': '个人中心',
    'coach_profiles.manage': '教练管理',
    'accounts.manage': '人员与权限',
    'imports.execute': '正式导入',
    'system.maintain': '系统维护',
    'audit.read': '操作记录',
    'feedback.manage': '数据纠错',
};

function workspaceHasCapability(capability) {
    return Boolean(workspaceSessionData?.identity?.capabilities?.includes(capability));
}

function workspaceHasWorkAccess(identity = workspaceSessionData?.identity) {
    return Boolean(identity && (identity.is_full_admin || (identity.capabilities || []).some(item => item !== 'coach_profile.write_self')));
}

function showWorkspaceLoginMode(mode) {
    const isCoachMode = mode === 'coach';
    document.getElementById('workspaceAdminLoginTab')?.classList.toggle('active', !isCoachMode);
    document.getElementById('workspaceCoachLoginTab')?.classList.toggle('active', isCoachMode);
    document.getElementById('workspaceAdminLoginTab')?.setAttribute('aria-selected', isCoachMode ? 'false' : 'true');
    document.getElementById('workspaceCoachLoginTab')?.setAttribute('aria-selected', isCoachMode ? 'true' : 'false');
    document.getElementById('workspaceAdminLoginForm')?.classList.toggle('active', !isCoachMode);
    document.getElementById('workspaceCoachLoginForm')?.classList.toggle('active', isCoachMode);
}

async function loadWorkspaceSession(options = {}) {
    if (workspaceSessionData && options.force !== true) return workspaceSessionData;
    const response = await fetchWithTimeout('/api/workspace/session', {credentials: 'same-origin'});
    workspaceSessionData = response.ok ? await response.json() : {authenticated: false, identity: null};
    workspaceSessionState = workspaceSessionData;
    const identity = workspaceSessionData.identity;
    if (identity) {
        const capabilities = new Set(identity.capabilities || []);
        canManageSchedule = capabilities.has('schedule.write');
        canManageCupStandings = capabilities.has('cup_standings.write');
        canManageRankings = capabilities.has('rankings.write');
        canManageSuspensions = capabilities.has('suspensions.write');
        canManageCandidateLists = capabilities.has('candidate_lists.write');
        if (identity.source === 'coach_account') {
            currentCoachAccount = {
                ...currentCoachAccount,
                authenticated: true,
                username: identity.username,
                qq_number: identity.qq_number,
                nickname: identity.display_name,
                coach_uid: identity.coach_uid,
                team_name: identity.team_name,
                can_manage_schedule: canManageSchedule,
                can_manage_cup_standings: canManageCupStandings,
                can_manage_rankings: canManageRankings,
                can_manage_suspensions: canManageSuspensions,
                can_manage_candidate_lists: canManageCandidateLists,
            };
            if (typeof renderGlobalCoachAccount === 'function') renderGlobalCoachAccount();
        }
    }
    syncAdminTabVisibility();
    return workspaceSessionData;
}

function renderWorkspaceIdentity() {
    const container = document.getElementById('workspaceIdentityCard');
    const identity = workspaceSessionData?.identity;
    if (!container || !identity) return;
    const accountLabel = identity.is_full_admin
        ? '完整管理员'
        : identity.source === 'coach_account' ? '教练工作账号' : '赛事工作账号';
    const capabilityLabels = (identity.capability_labels || []).filter(label => label !== '个人中心');
    container.innerHTML = `
        <span class="workspace-identity-type">${escapeHtml(accountLabel)}</span>
        <strong>${escapeHtml(identity.display_name || identity.username)}</strong>
        ${identity.team_name ? `<span>${escapeHtml(identity.team_name)}</span>` : ''}
        <div class="workspace-identity-permissions">
            ${capabilityLabels.length ? capabilityLabels.map(label => `<em>${escapeHtml(label)}</em>`).join('') : '<em>未分配工作权限</em>'}
        </div>
        ${identity.coach_uid ? '<button class="workspace-personal-link" type="button" onclick="openWorkspacePersonalCenter()">进入个人中心</button>' : ''}
    `;
}

function syncWorkspaceNavigation() {
    const identity = workspaceSessionData?.identity;
    const capabilities = new Set(identity?.capabilities || []);
    document.querySelectorAll('[data-workspace-capability]').forEach(button => {
        button.hidden = !capabilities.has(button.dataset.workspaceCapability);
    });
    document.querySelectorAll('[data-workspace-admin-only]').forEach(button => {
        button.hidden = !identity?.is_full_admin;
    });
    document.querySelectorAll('[data-workspace-imports]').forEach(button => {
        button.hidden = !(identity?.is_full_admin || capabilities.has('schedule.write'));
    });
}

async function openWorkspace(options = {}) {
    const session = await loadWorkspaceSession({force: options.force === true});
    const login = document.getElementById('adminLogin');
    const panel = document.getElementById('adminPanel');
    if (!session.authenticated || !workspaceHasWorkAccess(session.identity)) {
        if (login) login.style.display = 'block';
        if (panel) panel.style.display = 'none';
        showWorkspaceLoginMode(session.identity?.source === 'coach_account' ? 'coach' : 'admin');
        window.setTimeout(() => {
            const targetId = session.identity?.source === 'coach_account' ? 'workspaceCoachUsername' : 'adminUsername';
            document.getElementById(targetId)?.focus();
        }, 0);
        return;
    }
    if (login) login.style.display = 'none';
    if (panel) panel.style.display = 'block';
    renderWorkspaceIdentity();
    syncWorkspaceNavigation();
    showWorkspaceView(options.view || 'home');
    await loadWorkspaceDashboard({force: options.force === true});
}

function showWorkspaceView(viewName, scrollTarget = '') {
    const normalized = ['home', 'accounts', 'imports', 'promotions', 'logos', 'operations'].includes(viewName) ? viewName : 'home';
    document.querySelectorAll('.workspace-view').forEach(view => view.classList.remove('active'));
    document.getElementById(`workspace${normalized[0].toUpperCase()}${normalized.slice(1)}View`)?.classList.add('active');
    document.querySelectorAll('[data-workspace-view]').forEach(button => {
        button.classList.toggle('active', button.dataset.workspaceView === normalized);
    });
    if (normalized === 'accounts') loadWorkspaceAccounts();
    if (normalized === 'promotions') loadWorkspacePromotions();
    if (normalized === 'logos') loadWorkspaceLogoMatcher();
    if (normalized === 'imports') loadWorkspaceAdminOperations();
    if (normalized === 'operations') loadWorkspaceAdminOperations();
    if (scrollTarget) {
        window.setTimeout(() => document.getElementById(scrollTarget)?.scrollIntoView({behavior: 'smooth', block: 'start'}), 80);
    }
}

function workspaceLogoLevelRank(level) {
    return {'超级': 0, '甲级': 1, '乙级': 2}[level] ?? 9;
}

function workspaceLogoImage(path, teamName, className = '') {
    const safeName = escapeHtml(teamName || '球队');
    return path
        ? `<img class="${className}" src="${escapeHtml(path)}" alt="${safeName}队徽" onerror="this.hidden=true;this.nextElementSibling.hidden=false"><span class="workspace-logo-fallback" hidden>${safeName.slice(0, 1)}</span>`
        : `<span class="workspace-logo-fallback">${safeName.slice(0, 1)}</span>`;
}

async function loadWorkspaceLogoMatcher(options = {}) {
    if (workspaceLogoMatcherData && options.force !== true) {
        renderWorkspaceLogoTeams();
        return workspaceLogoMatcherData;
    }
    const list = document.getElementById('workspaceLogoTeamList');
    if (list) list.innerHTML = '<div class="loading">读取联赛球队...</div>';
    const response = await fetchWithTimeout('/api/admin/team-logo-match/overview', {credentials: 'same-origin'});
    if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        if (list) list.innerHTML = `<div class="workspace-logo-empty">${escapeHtml(payload.detail || '球队读取失败')}</div>`;
        return null;
    }
    workspaceLogoMatcherData = await response.json();
    const teams = workspaceLogoMatcherData.teams || [];
    if (!workspaceLogoSelectedTeamId && teams.length) workspaceLogoSelectedTeamId = teams[0].id;
    renderWorkspaceLogoTeams();
    const selected = teams.find(team => team.id === workspaceLogoSelectedTeamId);
    const input = document.getElementById('workspaceLogoSearchInput');
    if (selected && input && !input.value) input.value = selected.name;
    renderWorkspaceLogoReview();
    return workspaceLogoMatcherData;
}

function renderWorkspaceLogoTeams() {
    const list = document.getElementById('workspaceLogoTeamList');
    if (!list || !workspaceLogoMatcherData) return;
    const filter = (document.getElementById('workspaceLogoTeamFilter')?.value || '').trim().toLowerCase();
    const teams = [...(workspaceLogoMatcherData.teams || [])]
        .filter(team => !filter || `${team.name} ${team.level}`.toLowerCase().includes(filter))
        .sort((a, b) => workspaceLogoLevelRank(a.level) - workspaceLogoLevelRank(b.level) || a.name.localeCompare(b.name, 'zh-CN'));
    document.getElementById('workspaceLogoTeamCount').textContent = `${teams.length} CLUBS`;
    list.innerHTML = teams.length ? teams.map(team => `
        <button class="workspace-logo-team ${team.id === workspaceLogoSelectedTeamId ? 'active' : ''}" type="button" onclick="selectWorkspaceLogoTeam(${Number(team.id)})">
            <span class="workspace-logo-team-crest">${workspaceLogoImage(team.logo_path, team.name)}</span>
            <span class="workspace-logo-team-copy"><strong>${escapeHtml(team.name)}</strong><small>${team.latest_source ? `${team.latest_source.provider === 'local_upload' ? '本地上传' : 'FCLOGO'} · ${escapeHtml(team.latest_source.source_version || team.latest_source.source_variant || '已采用')}` : '尚无匹配记录'}</small></span>
            <em class="workspace-logo-level level-${workspaceLogoLevelRank(team.level)}">${escapeHtml(team.level)}</em>
        </button>
    `).join('') : '<div class="workspace-logo-empty">没有符合条件的球队。</div>';
}

function selectWorkspaceLogoTeam(teamId) {
    workspaceLogoSelectedTeamId = Number(teamId);
    workspaceLogoCandidates = [];
    workspaceLogoSelectedCandidateIndex = -1;
    clearWorkspaceLogoLocalFile();
    renderWorkspaceLogoTeams();
    const team = (workspaceLogoMatcherData?.teams || []).find(item => item.id === workspaceLogoSelectedTeamId);
    const input = document.getElementById('workspaceLogoSearchInput');
    if (input && team) {
        input.value = team.name;
        input.focus();
        input.select();
    }
    const candidates = document.getElementById('workspaceLogoCandidateList');
    if (candidates) candidates.innerHTML = '<div class="workspace-logo-empty">搜索该球队在 FCLOGO 中的候选队徽。</div>';
    renderWorkspaceLogoReview();
}

function setWorkspaceLogoSource(mode) {
    workspaceLogoSourceMode = mode === 'upload' ? 'upload' : 'fclogo';
    document.getElementById('workspaceLogoFclogoTab')?.classList.toggle('active', workspaceLogoSourceMode === 'fclogo');
    document.getElementById('workspaceLogoUploadTab')?.classList.toggle('active', workspaceLogoSourceMode === 'upload');
    document.getElementById('workspaceLogoFclogoPane')?.classList.toggle('active', workspaceLogoSourceMode === 'fclogo');
    document.getElementById('workspaceLogoUploadPane')?.classList.toggle('active', workspaceLogoSourceMode === 'upload');
    workspaceLogoSelectedCandidateIndex = -1;
    if (workspaceLogoSourceMode === 'upload' && workspaceLogoLocalFile) {
        setWorkspaceLogoLocalCandidate();
    } else {
        renderWorkspaceLogoReview();
    }
}

function clearWorkspaceLogoLocalFile() {
    if (workspaceLogoLocalPreviewUrl) URL.revokeObjectURL(workspaceLogoLocalPreviewUrl);
    workspaceLogoLocalFile = null;
    workspaceLogoLocalPreviewUrl = '';
    const input = document.getElementById('workspaceLogoUploadInput');
    if (input) input.value = '';
    const preview = document.getElementById('workspaceLogoUploadPreview');
    if (preview) preview.innerHTML = '<div class="workspace-logo-empty">文件只在确认后上传，选择文件不会立即替换队徽。</div>';
}

function handleWorkspaceLogoUpload(file) {
    if (!workspaceLogoSelectedTeamId) {
        clearWorkspaceLogoLocalFile();
        return showModal('提示', '请先选择球队');
    }
    if (!file) return clearWorkspaceLogoLocalFile();
    const isSvg = file.type === 'image/svg+xml' || file.name.toLowerCase().endsWith('.svg');
    const maxBytes = isSvg ? 5 * 1024 * 1024 : 2 * 1024 * 1024;
    if (file.size > maxBytes) {
        clearWorkspaceLogoLocalFile();
        return showModal('错误', `该文件超过${isSvg ? '5MB' : '2MB'}上限`);
    }
    if (workspaceLogoLocalPreviewUrl) URL.revokeObjectURL(workspaceLogoLocalPreviewUrl);
    workspaceLogoLocalFile = file;
    workspaceLogoLocalPreviewUrl = URL.createObjectURL(file);
    setWorkspaceLogoLocalCandidate();
}

function setWorkspaceLogoLocalCandidate() {
    const team = (workspaceLogoMatcherData?.teams || []).find(item => item.id === workspaceLogoSelectedTeamId);
    if (!workspaceLogoLocalFile || !team) return;
    const extension = workspaceLogoLocalFile.name.split('.').pop()?.toUpperCase() || 'FILE';
    workspaceLogoCandidates = [{
        source_kind: 'local',
        preview_url: workspaceLogoLocalPreviewUrl,
        name: workspaceLogoLocalFile.name,
        full_name: team.name,
        version: `${(workspaceLogoLocalFile.size / 1024).toFixed(0)} KB`,
        variant: extension,
        variant_zh: extension,
        confidence: null,
        detail_url: '',
    }];
    workspaceLogoSelectedCandidateIndex = 0;
    const preview = document.getElementById('workspaceLogoUploadPreview');
    if (preview) preview.innerHTML = `
        <div class="workspace-logo-upload-file">
            <img src="${escapeHtml(workspaceLogoLocalPreviewUrl)}" alt="本地队徽预览">
            <span><strong>${escapeHtml(workspaceLogoLocalFile.name)}</strong><small>${escapeHtml(extension)} · ${(workspaceLogoLocalFile.size / 1024).toFixed(0)} KB</small></span>
            <button type="button" onclick="clearWorkspaceLogoLocalFile(); workspaceLogoCandidates=[]; workspaceLogoSelectedCandidateIndex=-1; renderWorkspaceLogoReview();">移除</button>
        </div>`;
    renderWorkspaceLogoReview();
}

async function searchWorkspaceLogoCandidates() {
    const query = (document.getElementById('workspaceLogoSearchInput')?.value || '').trim();
    if (!workspaceLogoSelectedTeamId) return showModal('提示', '请先选择球队');
    if (!query) return showModal('提示', '请输入球队搜索词');
    const button = document.getElementById('workspaceLogoSearchButton');
    const list = document.getElementById('workspaceLogoCandidateList');
    if (button) { button.disabled = true; button.textContent = '检索中...'; }
    if (list) list.innerHTML = '<div class="loading">正在连接 FCLOGO...</div>';
    try {
        const response = await fetchWithTimeout(`/api/admin/team-logo-match/search?team_id=${encodeURIComponent(workspaceLogoSelectedTeamId)}&q=${encodeURIComponent(query)}`, {credentials: 'same-origin'});
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.detail || '搜索失败');
        workspaceLogoCandidates = payload.candidates || [];
        workspaceLogoSelectedCandidateIndex = -1;
        renderWorkspaceLogoCandidates();
        renderWorkspaceLogoReview();
    } catch (error) {
        workspaceLogoCandidates = [];
        if (list) list.innerHTML = `<div class="workspace-logo-empty is-error">${escapeHtml(error.message || '搜索失败')}</div>`;
    } finally {
        if (button) { button.disabled = false; button.textContent = '搜索 FCLOGO'; }
    }
}

function renderWorkspaceLogoCandidates() {
    const list = document.getElementById('workspaceLogoCandidateList');
    if (!list) return;
    list.innerHTML = workspaceLogoCandidates.length ? workspaceLogoCandidates.map((candidate, index) => `
        <button class="workspace-logo-candidate ${index === workspaceLogoSelectedCandidateIndex ? 'active' : ''}" type="button" onclick="selectWorkspaceLogoCandidate(${index})">
            <span class="workspace-logo-candidate-image"><img src="${escapeHtml(candidate.preview_url || '')}" alt="${escapeHtml(candidate.name || '候选队徽')}" loading="lazy"></span>
            <span class="workspace-logo-candidate-copy"><strong>${escapeHtml(candidate.name || candidate.full_name || '未命名')}</strong><small>${escapeHtml(candidate.full_name || candidate.local_name || '')}</small><span><em>${escapeHtml(candidate.variant_zh || candidate.variant || '版本')}</em><em>${escapeHtml(candidate.version || '年份未知')}</em></span></span>
            <b>${Number(candidate.confidence || 0).toFixed(0)}<small>%</small></b>
        </button>
    `).join('') : '<div class="workspace-logo-empty">没有找到候选。可调整为英文全名、当地名称或常用简称后重试。</div>';
}

function selectWorkspaceLogoCandidate(index) {
    workspaceLogoSelectedCandidateIndex = Number(index);
    renderWorkspaceLogoCandidates();
    renderWorkspaceLogoReview();
}

function renderWorkspaceLogoReview() {
    const host = document.getElementById('workspaceLogoReview');
    if (!host) return;
    const team = (workspaceLogoMatcherData?.teams || []).find(item => item.id === workspaceLogoSelectedTeamId);
    const candidate = workspaceLogoCandidates[workspaceLogoSelectedCandidateIndex];
    if (!team || !candidate) {
        host.innerHTML = '<div class="workspace-logo-empty">选择候选后，这里会显示新旧队徽对照。</div>';
        return;
    }
    const isLocal = candidate.source_kind === 'local';
    host.innerHTML = `
        <div class="workspace-logo-versus">
            <div><span>当前</span><div class="workspace-logo-review-crest">${workspaceLogoImage(team.logo_path, team.name)}</div><strong>${escapeHtml(team.name)}</strong></div>
            <i aria-hidden="true">${uiIconSvg('arrow-right', 'ui-icon is-small')}</i>
            <div class="is-candidate"><span>候选</span><div class="workspace-logo-review-crest"><img src="${escapeHtml(candidate.preview_url || '')}" alt="候选队徽"></div><strong>${escapeHtml(candidate.name || candidate.full_name || '')}</strong></div>
        </div>
        <dl class="workspace-logo-metadata">
            <div><dt>${isLocal ? '文件大小' : '版本'}</dt><dd>${escapeHtml(candidate.version || '未知')}</dd></div>
            <div><dt>类型</dt><dd>${escapeHtml(candidate.variant_zh || candidate.variant || '未知')}</dd></div>
            <div><dt>匹配度</dt><dd>${isLocal ? '人工确认' : `${Number(candidate.confidence || 0).toFixed(0)}%`}</dd></div>
            <div><dt>来源</dt><dd>${isLocal ? '本地上传' : `<a href="${escapeHtml(candidate.detail_url)}" target="_blank" rel="noopener noreferrer">FCLOGO ↗</a>`}</dd></div>
        </dl>
        <label class="workspace-logo-confirm"><input id="workspaceLogoConfirm" type="checkbox"><span><strong>我已人工核对队徽与球队</strong><small>确认后才会替换网站当前队徽，并保留来源记录。</small></span></label>
        <button class="btn btn-primary workspace-logo-apply" id="workspaceLogoApplyButton" type="button" onclick="applyWorkspaceLogoCandidate()">${isLocal ? '上传并采用此队徽' : '确认采用此队徽'}</button>
    `;
}

async function applyWorkspaceLogoCandidate() {
    const team = (workspaceLogoMatcherData?.teams || []).find(item => item.id === workspaceLogoSelectedTeamId);
    const candidate = workspaceLogoCandidates[workspaceLogoSelectedCandidateIndex];
    if (!team || !candidate) return showModal('提示', '请先选择候选队徽');
    if (!document.getElementById('workspaceLogoConfirm')?.checked) return showModal('提示', '请先完成并勾选人工核对');
    const isLocal = candidate.source_kind === 'local';
    if (isLocal && !workspaceLogoLocalFile) return showModal('提示', '请重新选择本地队徽文件');
    if (!await showConfirmDialog({title: '替换球队队徽', message: `将 ${team.name} 的当前队徽替换为所选${isLocal ? '本地文件' : ' FCLOGO 候选'}，来源记录会被保留。`, confirmLabel: '确认替换'})) return;
    const button = document.getElementById('workspaceLogoApplyButton');
    if (button) { button.disabled = true; button.textContent = '清洗并保存中...'; }
    try {
        let response;
        if (isLocal) {
            const formData = new FormData();
            formData.append('team_id', String(team.id));
            formData.append('confirmed', 'true');
            formData.append('logo', workspaceLogoLocalFile, workspaceLogoLocalFile.name);
            response = await fetchWithTimeout('/api/admin/team-logo-match/upload', {method: 'POST', credentials: 'same-origin', body: formData});
        } else {
            response = await fetchWithTimeout('/api/admin/team-logo-match/apply', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    team_id: team.id,
                    slug: candidate.slug,
                    matched_query: (document.getElementById('workspaceLogoSearchInput')?.value || team.name).trim(),
                    source_name: candidate.full_name || candidate.name || '',
                    source_version: candidate.version || null,
                    source_variant: candidate.variant || null,
                    matched_score: Number(candidate.confidence || 0),
                    confirmed: true,
                }),
            });
        }
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.detail || '队徽保存失败');
        showSuccessToast(payload.message || '队徽已更新');
        workspaceLogoMatcherData = null;
        workspaceLogoCandidates = [];
        workspaceLogoSelectedCandidateIndex = -1;
        clearWorkspaceLogoLocalFile();
        await loadWorkspaceLogoMatcher({force: true});
    } catch (error) {
        showModal('错误', error.message || '队徽保存失败，原队徽未改变');
        if (button) { button.disabled = false; button.textContent = isLocal ? '上传并采用此队徽' : '确认采用此队徽'; }
    }
}

async function openWorkspaceTask(tabName, subtab) {
    await showTab(tabName, null, {syncHistory: false});
    if (tabName === 'competition' && typeof showCompetitionSubtab === 'function') {
        showCompetitionSubtab(subtab);
    } else if (tabName === 'database' && typeof showDatabaseSubtab === 'function') {
        showDatabaseSubtab(subtab);
        if (subtab === 'candidates' && typeof loadCandidateLists === 'function') {
            await loadCandidateLists();
        }
    }
    syncAppHistory('push');
}

async function openWorkspacePersonalCenter() {
    const coachUid = workspaceSessionData?.identity?.coach_uid;
    await showTab('coaches', null, {syncHistory: false});
    if (coachUid && typeof openCoachDetail === 'function') {
        await openCoachDetail(coachUid);
    }
    syncAppHistory('push');
}

function renderWorkspaceMetrics() {
    const container = document.getElementById('workspaceMetrics');
    const metrics = workspaceDashboardData?.metrics || [];
    if (!container) return;
    if (!metrics.length) {
        container.innerHTML = '<div class="workspace-empty">当前没有需要处理的联赛工作。</div>';
        return;
    }
    container.innerHTML = metrics.map(metric => `
        <button class="workspace-metric" type="button" onclick="openWorkspaceMetric('${escapeHtml(metric.target_tab || 'admin')}', '${escapeHtml(metric.target_subtab || '')}', '${escapeHtml(metric.key)}')">
            <span>${escapeHtml(metric.label)}</span>
            <strong>${Number(metric.value || 0).toLocaleString()}</strong>
            <em>${escapeHtml(metric.detail || '')}</em>
        </button>
    `).join('');
}

function renderWorkspaceTasks() {
    const container = document.getElementById('workspaceTaskList');
    if (!container) return;
    const tasks = workspaceDashboardData?.tasks || [];
    const isAdmin = Boolean(workspaceSessionData?.identity?.is_full_admin);
    const scope = document.getElementById('workspaceTaskScopeLabel');
    if (scope) scope.textContent = isAdmin ? '待分配与待复核总览' : '按当前身份分配';
    if (!tasks.length) {
        container.innerHTML = '<div class="workspace-empty">当前没有分配给你的轮次任务。</div>';
        return;
    }
    container.innerHTML = `<div class="workspace-task-list">${tasks.map(task => `
        <button class="workspace-task-row" type="button" onclick="openWorkspaceCompetitionTask(${htmlJsString(task.level)}, ${Number(task.round_start)}, ${htmlJsString(task.target_subtab || 'schedule')})">
            <span class="workspace-task-level">${escapeHtml(task.level)}</span>
            <span class="workspace-task-copy"><strong>${escapeHtml(task.round_label)}</strong><em>${escapeHtml((task.responsibility_labels || []).join('、') || '职责待任命')} · ${escapeHtml(task.assignee_display_name || '尚未任命')}</em></span>
            <span class="workspace-task-state is-${escapeHtml(task.status || 'unassigned')}">${escapeHtml(task.status_label || '待任命')}</span>
            <span class="workspace-task-count">${Number(task.pending_count || 0)} 项待处理</span>
        </button>
    `).join('')}</div>`;
}

function renderWorkspaceDataStatuses() {
    const container = document.getElementById('workspaceDataStatusList');
    if (!container) return;
    const items = workspaceDashboardData?.data_statuses || [];
    if (!items.length) {
        container.innerHTML = '<div class="workspace-empty">当前数据状态正常，没有需要跟进的提醒。</div>';
        return;
    }
    container.innerHTML = `<div class="workspace-data-status-list">${items.map(item => `
        <button class="workspace-data-status-row is-${escapeHtml(item.status || 'unknown')}" type="button" onclick="openDataStatusItem(${dataStatusJsString(item.key)}, ${dataStatusJsString(item.scope || 'all')})">
            <span class="workspace-data-status-icon">${dataStatusIconSvg(item.status)}</span>
            <span class="workspace-data-status-copy"><strong>${escapeHtml(item.scope === 'all' ? item.label : `${item.scope}${item.label}`)}</strong><em>${escapeHtml(item.message || '')}</em></span>
            <span class="workspace-data-status-state">${escapeHtml(item.status_label || '状态未知')}</span>
            <span class="workspace-data-status-count">${Number(item.issue_count || 0) > 0 ? `${Number(item.issue_count)} 项` : '查看'}</span>
        </button>
    `).join('')}</div>`;
}

async function openWorkspaceCompetitionTask(level, roundStart, subtab = 'schedule') {
    await showTab('competition', null, {syncHistory: false});
    currentCompetitionLevel = level;
    currentCompetitionSubtab = subtab;
    currentCompetitionWorkFilter = 'all';
    showCompetitionSubtab(subtab);
    if (typeof loadCompetitionData === 'function') await loadCompetitionData();
    if (subtab === 'schedule') renderScheduleBoard();
    const select = document.getElementById('scheduleRoundSelect');
    if (select) select.value = String(roundStart);
    if (subtab === 'schedule') renderScheduleBoard();
    if (typeof syncAppHistory === 'function') syncAppHistory('replace');
}

async function openWorkspaceMetric(tabName, subtab, key) {
    if (tabName === 'admin') {
        showWorkspaceView(key === 'accounts' ? 'accounts' : 'operations', key === 'feedback' ? 'dataFeedbackReportsCard' : '');
        return;
    }
    await openWorkspaceTask(tabName, subtab);
    if (key === 'cup_standings' && typeof setCompetitionLevel === 'function') {
        setCompetitionLevel('冠军杯');
        if (typeof setCupGroupScheduleView === 'function') setCupGroupScheduleView('results');
        return;
    }
    if (tabName === 'competition' && subtab === 'schedule' && typeof openCompetitionWorkQueue === 'function') {
        if (typeof loadCompetitionWorkSummary === 'function') {
            await loadCompetitionWorkSummary();
        }
        const filters = {
            schedule: 'missing_result',
            match_events: 'missing_events',
            data_issues: 'invalid',
        };
        openCompetitionWorkQueue(filters[key] || 'all');
    }
}

function renderWorkspaceRecentActions() {
    const container = document.getElementById('workspaceRecentActions');
    const actions = workspaceDashboardData?.recent_actions || [];
    if (!container) return;
    if (!actions.length) {
        container.innerHTML = '<div class="workspace-empty">当前身份还没有可显示的操作记录。</div>';
        return;
    }
    container.innerHTML = actions.map(action => `
        <div class="workspace-recent-row">
            <span class="workspace-action-status is-${escapeHtml(action.status || 'unknown')}"></span>
            <strong>${escapeHtml(action.summary || '-')}</strong>
            <span>${action.created_at ? new Date(action.created_at).toLocaleString() : '-'}</span>
        </div>
    `).join('');
}

async function loadWorkspaceDashboard(options = {}) {
    if (workspaceDashboardData && options.force !== true) {
        renderWorkspaceMetrics();
        renderWorkspaceTasks();
        renderWorkspaceDataStatuses();
        renderWorkspaceRecentActions();
        return;
    }
    const response = await fetchWithTimeout('/api/workspace/dashboard', {credentials: 'same-origin'});
    if (!response.ok) {
        workspaceDashboardData = {metrics: [], tasks: [], data_statuses: [], recent_actions: []};
        renderWorkspaceMetrics();
        renderWorkspaceTasks();
        renderWorkspaceDataStatuses();
        renderWorkspaceRecentActions();
        return;
    }
    workspaceDashboardData = await response.json();
    renderWorkspaceMetrics();
    renderWorkspaceTasks();
    renderWorkspaceDataStatuses();
    renderWorkspaceRecentActions();
}

function getWorkspaceAccountTypeLabel(item) {
    const labels = {administrator: '完整管理员', worker: '赛事工作人员', coach_worker: '教练工作账号', coach: '普通教练'};
    return labels[item.account_type] || '账号';
}

function renderWorkspaceAccounts() {
    const container = document.getElementById('workspaceAccountsTable');
    if (!container) return;
    const query = String(document.getElementById('workspaceAccountSearch')?.value || '').trim().toLowerCase();
    const type = document.getElementById('workspaceAccountTypeFilter')?.value || '';
    const items = workspaceAccountsData.filter(item => {
        if (type && item.account_type !== type) return false;
        if (!query) return true;
        return [item.display_name, item.qq_number, item.username, item.team_name, item.level].some(value => String(value || '').toLowerCase().includes(query));
    });
    if (!items.length) {
        container.innerHTML = '<div class="workspace-empty">没有符合条件的账号。</div>';
        return;
    }
    container.innerHTML = `<div class="workspace-account-list">${items.map(item => {
        const permissions = (item.capabilities || [])
            .filter(capability => capability !== 'coach_profile.write_self')
            .map(capability => WORKSPACE_CAPABILITY_LABELS[capability] || capability);
        return `
            <article class="workspace-account-row">
                <div class="workspace-account-person">
                    <strong>${escapeHtml(item.display_name || '-')}</strong>
                    <span>${escapeHtml(item.team_name || item.level || '未关联球队')}</span>
                </div>
                <span class="workspace-account-type">${escapeHtml(getWorkspaceAccountTypeLabel(item))}</span>
                <div class="workspace-account-login">
                    <strong>${item.qq_number ? `QQ ${escapeHtml(item.qq_number)}` : escapeHtml(item.username || '尚未创建')}</strong>
                    <span>${item.qq_number ? `旧账号 ${escapeHtml(item.username || '-')}` : (item.last_login_at ? `最近登录 ${new Date(item.last_login_at).toLocaleString()}` : '暂无登录记录')}</span>
                </div>
                <div class="workspace-account-permissions">${permissions.length ? permissions.map(label => `<span>${escapeHtml(label)}</span>`).join('') : '<span class="is-muted">无联赛工作权限</span>'}</div>
                <span class="workspace-account-state ${item.is_active ? 'is-active' : ''}">${item.is_active ? '启用' : '未启用'}</span>
                ${item.source === 'coach_account' ? `<button class="btn btn-secondary" type="button" onclick="showWorkspaceAccountEditor(${htmlJsString(item.coach_uid || '')})">管理</button>` : '<span class="workspace-account-readonly">系统配置</span>'}
            </article>
        `;
    }).join('')}</div>`;
}

async function loadWorkspaceAccounts(options = {}) {
    if (workspaceAccountsData.length && options.force !== true) {
        renderWorkspaceAccounts();
        return;
    }
    const response = await fetchWithTimeout('/api/workspace/accounts', {credentials: 'same-origin'});
    if (!response.ok) {
        document.getElementById('workspaceAccountsTable').innerHTML = '<div class="workspace-empty">账号列表加载失败或当前身份没有权限。</div>';
        return;
    }
    const payload = await response.json();
    workspaceAccountsData = Array.isArray(payload.items) ? payload.items : [];
    renderWorkspaceAccounts();
}

function showWorkspaceAccountEditor(coachUid) {
    const item = workspaceAccountsData.find(account => account.coach_uid === coachUid);
    if (!item) return;
    const capabilities = new Set(item.capabilities || []);
    const leagueOrder = {超级: 0, 甲级: 1, 乙级: 2};
    const teamOptions = [...(Array.isArray(teams) ? teams : [])]
        .filter(team => Object.hasOwn(leagueOrder, team.level))
        .sort((a, b) => (leagueOrder[a.level] - leagueOrder[b.level]) || String(a.name || '').localeCompare(String(b.name || ''), 'zh-CN'))
        .map(team => `<option value="${Number(team.id)}" ${Number(item.team_id) === Number(team.id) ? 'selected' : ''}>${escapeHtml(`${team.level} · ${team.name}${team.manager && team.manager !== '-' ? `（${team.manager}）` : ''}`)}</option>`)
        .join('');
    const mergeOptions = workspaceAccountsData
        .filter(account => account.source === 'coach_account' && account.coach_uid && account.coach_uid !== coachUid)
        .map(account => `<option value="${escapeHtml(account.coach_uid)}">${escapeHtml(`${account.display_name}${account.team_name ? ` · ${account.team_name}` : ''}${account.username ? ` · ${account.username}` : ''}`)}</option>`)
        .join('');
    showModal('教练账号与工作权限', `
        <div class="workspace-account-editor">
            <div class="workspace-account-editor-head"><strong>${escapeHtml(item.display_name)}</strong><span>${escapeHtml(item.team_name || '未关联球队')}</span></div>
            <section class="workspace-team-link-panel">
                <div class="workspace-editor-section-title"><span>球队关联</span><small>教练 → 球队</small></div>
                <div class="workspace-team-link-control">
                    <span class="workspace-team-link-coach">${escapeHtml(item.display_name)}</span>
                    <span class="workspace-team-link-arrow" aria-hidden="true">${uiIconSvg('arrow-right', 'ui-icon is-small')}</span>
                    <select id="workspaceEditTeam"><option value="">未关联球队</option>${teamOptions}</select>
                    <button class="btn btn-secondary" type="button" onclick="saveWorkspaceCoachTeam(${htmlJsString(coachUid)})">保存关联</button>
                </div>
                <p>保存后会同步球队的主教练字段；该球队原先关联的教练会自动解除关联。</p>
            </section>
            <form class="workspace-account-form" onsubmit="event.preventDefault(); saveWorkspaceAccount(${htmlJsString(coachUid)});">
                <div class="workspace-editor-section-title"><span>登录与权限</span><small>${escapeHtml(item.coach_uid || '')}</small></div>
                <div class="workspace-account-security-state">
                    <div><span>QQ 登录</span><strong>${item.qq_number ? escapeHtml(item.qq_number) : '未绑定'}</strong></div>
                    <div><span>密码状态</span><strong>${item.must_change_password ? '首次登录待修改' : '已由教练设置'}</strong></div>
                    ${item.qq_number ? `<button class="btn btn-secondary" type="button" onclick="unbindWorkspaceCoachQq(${htmlJsString(coachUid)})">管理员解绑 QQ</button>` : ''}
                </div>
                <label class="form-group"><span>登录账号</span><input id="workspaceEditUsername" type="text" value="${escapeHtml(item.username || '')}" autocomplete="username" required></label>
                <label class="form-group"><span>${item.username ? '重置密码（留空则不修改）' : '初始密码'}</span><input id="workspaceEditPassword" type="password" autocomplete="new-password" ${item.username ? '' : 'required'}></label>
                <p class="workspace-account-security-hint">创建账号或由管理员重置密码后，教练下次登录必须先修改默认密码。</p>
                <label class="workspace-permission-toggle"><input id="workspaceEditActive" type="checkbox" ${item.is_active ? 'checked' : ''}>启用账号</label>
                <fieldset class="workspace-permission-grid">
                    <legend>联赛工作权限</legend>
                    <label><input id="workspaceEditSchedule" type="checkbox" ${capabilities.has('schedule.write') ? 'checked' : ''}>赛程与比赛事件</label>
                    <label><input id="workspaceEditCupStandings" type="checkbox" ${capabilities.has('cup_standings.write') ? 'checked' : ''}>杯赛积分榜</label>
                    <label><input id="workspaceEditRankings" type="checkbox" ${capabilities.has('rankings.write') ? 'checked' : ''}>排位统计</label>
                    <label><input id="workspaceEditSuspensions" type="checkbox" ${capabilities.has('suspensions.write') ? 'checked' : ''}>纪律与伤停</label>
                    <label><input id="workspaceEditCandidates" type="checkbox" ${capabilities.has('candidate_lists.write') ? 'checked' : ''}>候选名单</label>
                </fieldset>
                <button class="btn btn-primary" type="submit">保存账号与权限</button>
            </form>
            <section class="workspace-merge-panel">
                <div class="workspace-editor-section-title"><span>重复教练处理</span><small>不可撤销</small></div>
                <p>将当前教练的荣誉、助教、互动和可用资料迁移到目标教练，再删除当前重复记录。</p>
                <div class="workspace-merge-control">
                    <select id="workspaceMergeTarget"><option value="">选择合并目标</option>${mergeOptions}</select>
                    <button class="btn workspace-merge-button" type="button" onclick="showWorkspaceMergeConfirmation(${htmlJsString(coachUid)})">合并当前教练</button>
                </div>
            </section>
        </div>
    `);
}

async function saveWorkspaceCoachTeam(coachUid) {
    const rawTeamId = document.getElementById('workspaceEditTeam')?.value || '';
    const response = await fetchWithTimeout(`/api/admin/coaches/${encodeURIComponent(coachUid)}/team`, {
        method: 'PATCH',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({team_id: rawTeamId ? Number(rawTeamId) : null}),
    });
    const data = await response.json();
    if (!response.ok || !data.success) {
        showModal('关联失败', escapeHtml(data.detail || data.message || '球队关联保存失败'));
        return;
    }
    closeModal();
    workspaceAccountsData = [];
    await Promise.all([loadWorkspaceAccounts({force: true}), loadData()]);
}

function showWorkspaceMergeConfirmation(sourceCoachUid) {
    const targetCoachUid = document.getElementById('workspaceMergeTarget')?.value || '';
    const source = workspaceAccountsData.find(account => account.coach_uid === sourceCoachUid);
    const target = workspaceAccountsData.find(account => account.coach_uid === targetCoachUid);
    if (!source || !target) {
        showModal('请选择合并目标', '先选择要保留的教练记录。');
        return;
    }
    showModal('确认合并重复教练', `
        <div class="workspace-merge-confirmation">
            <div class="workspace-merge-route"><span>${escapeHtml(source.display_name)}</span><strong>合并到</strong><span>${escapeHtml(target.display_name)}</span></div>
            <ul>
                <li>保留目标教练的昵称和已有主页资料，空缺资料由当前教练补齐。</li>
                <li>荣誉、助教和互动记录会迁移到目标教练。</li>
                <li>当前教练资料及其登录账号会被删除，只保留目标教练账号。</li>
                <li>两个账号现有登录会话都会退出。</li>
            </ul>
            <div class="workspace-merge-account-result"><span>合并后登录</span><strong>${target.qq_number ? `QQ ${escapeHtml(target.qq_number)}` : escapeHtml(target.username || '目标教练尚无登录账号')}</strong></div>
            <div class="workspace-merge-confirm-actions">
                <button class="btn btn-secondary" type="button" onclick="showWorkspaceAccountEditor(${htmlJsString(sourceCoachUid)})">返回</button>
                <button class="btn workspace-merge-button" type="button" onclick="mergeWorkspaceCoach(${htmlJsString(sourceCoachUid)}, ${htmlJsString(targetCoachUid)})">确认合并并退出相关登录</button>
            </div>
        </div>
    `);
}

async function mergeWorkspaceCoach(sourceCoachUid, targetCoachUid) {
    const response = await fetchWithTimeout(`/api/admin/coaches/${encodeURIComponent(sourceCoachUid)}/merge`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({target_coach_uid: targetCoachUid}),
    });
    const data = await response.json();
    if (!response.ok || !data.success) {
        showModal('合并失败', escapeHtml(data.detail || data.message || '教练合并失败'));
        return;
    }
    closeModal();
    workspaceAccountsData = [];
    await Promise.all([loadWorkspaceAccounts({force: true}), loadData()]);
}

async function unbindWorkspaceCoachQq(coachUid) {
    const response = await fetchWithTimeout(`/api/admin/coaches/${encodeURIComponent(coachUid)}/qq`, {
        method: 'DELETE',
        credentials: 'same-origin',
    });
    const data = await response.json();
    if (!response.ok || !data.success) {
        showModal('解绑失败', escapeHtml(data.detail || data.message || 'QQ 解绑失败'));
        return;
    }
    workspaceAccountsData = [];
    await loadWorkspaceAccounts({force: true});
    showSuccessToast(data.message || 'QQ 已解绑');
}

async function saveWorkspaceAccount(coachUid) {
    const payload = {
        username: document.getElementById('workspaceEditUsername')?.value || '',
        password: document.getElementById('workspaceEditPassword')?.value || null,
        is_active: Boolean(document.getElementById('workspaceEditActive')?.checked),
        can_manage_schedule: Boolean(document.getElementById('workspaceEditSchedule')?.checked),
        can_manage_cup_standings: Boolean(document.getElementById('workspaceEditCupStandings')?.checked),
        can_manage_rankings: Boolean(document.getElementById('workspaceEditRankings')?.checked),
        can_manage_suspensions: Boolean(document.getElementById('workspaceEditSuspensions')?.checked),
        can_manage_candidate_lists: Boolean(document.getElementById('workspaceEditCandidates')?.checked),
    };
    const response = await fetchWithTimeout(`/api/admin/coaches/${encodeURIComponent(coachUid)}/account`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok || !data.success) {
        showModal('保存失败', escapeHtml(data.detail || data.message || '账号保存失败'));
        return;
    }
    closeModal();
    workspaceAccountsData = [];
    if (typeof invalidateCompetitionAssignableAccounts === 'function') invalidateCompetitionAssignableAccounts();
    await loadWorkspaceAccounts({force: true});
}

function getWorkspacePromotionTypeLabel(type) {
    return {announcement: '联赛公告', honor: '荣誉发布', update: '版本更新', event: '活动宣传'}[type] || '联赛公告';
}

function getWorkspacePromotionThemeLabel(theme) {
    return {violet: '紫罗兰', blue: '澄蓝', green: '薄荷绿', gold: '冠军金', rose: '玫瑰红', neutral: '银灰'}[theme] || '紫罗兰';
}

function getWorkspacePromotionState(item) {
    if (!item.is_active) return {key: 'offline', label: '已下线'};
    const now = Date.now();
    if (item.starts_at && new Date(item.starts_at).getTime() > now) return {key: 'scheduled', label: '待发布'};
    if (item.ends_at && new Date(item.ends_at).getTime() < now) return {key: 'expired', label: '已结束'};
    return {key: 'live', label: '展示中'};
}

function formatWorkspacePromotionDate(value) {
    if (!value) return '长期';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString('zh-CN', {month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'});
}

function workspacePromotionRequestPayload(item, overrides = {}) {
    const source = {...item, ...overrides};
    return {
        content_type: source.content_type || 'announcement',
        theme: source.theme || 'violet',
        icon: source.icon || 'megaphone',
        eyebrow: source.eyebrow || 'HEIGO Broadcast',
        title: source.title || '',
        body: source.body || '',
        image_url: source.image_url || null,
        action_label: source.action_label || null,
        action_kind: source.action_kind || 'none',
        action_target: source.action_target || null,
        display_mode: source.display_mode || 'board',
        is_active: Boolean(source.is_active),
        is_pinned: Boolean(source.is_pinned),
        is_dismissible: source.is_dismissible !== false,
        sort_order: Number(source.sort_order || 0),
        starts_at: source.starts_at || null,
        ends_at: source.ends_at || null,
    };
}

function renderWorkspacePromotions() {
    const container = document.getElementById('workspacePromotionsList');
    if (!container) return;
    if (!workspacePromotionsData.length) {
        container.innerHTML = '<div class="workspace-promotion-empty"><strong>还没有主页宣传</strong><p>新增一条联赛公告，或同步当前杯赛冠军。</p><button class="btn btn-primary" type="button" onclick="showWorkspacePromotionEditor()">新增第一条宣传</button></div>';
        return;
    }
    container.innerHTML = `<div class="workspace-promotion-list">${workspacePromotionsData.map(item => {
        const state = getWorkspacePromotionState(item);
        const schedule = `${formatWorkspacePromotionDate(item.starts_at)} — ${item.ends_at ? formatWorkspacePromotionDate(item.ends_at) : '长期'}`;
        return `
            <article class="workspace-promotion-row is-${escapeHtml(item.theme)}">
                <div class="workspace-promotion-rank"><span>${String(Number(item.sort_order || 0)).padStart(2, '0')}</span>${item.is_pinned ? '<strong>置顶</strong>' : ''}</div>
                <div class="workspace-promotion-summary">
                    <div class="workspace-promotion-meta"><span>${escapeHtml(getWorkspacePromotionTypeLabel(item.content_type))}</span><span>${escapeHtml(getWorkspacePromotionThemeLabel(item.theme))}</span><span>${escapeHtml({board: '主页卡片', modal: '访问弹窗', both: '卡片 + 弹窗'}[item.display_mode] || '主页卡片')}</span><span>${escapeHtml(item.source_type === 'cup_champion' ? '杯赛冠军' : item.source_type === 'league_champion' ? '联赛冠军' : item.source_type === 'site_intro' ? '网站介绍' : item.source_type === 'legacy' ? '历史迁移' : '自定义')}</span></div>
                    <strong>${escapeHtml(item.title)}</strong>
                    <p>${escapeHtml(item.body || '未填写宣传正文')}</p>
                    <small>${escapeHtml(schedule)}</small>
                </div>
                <span class="workspace-promotion-state is-${state.key}">${state.label}</span>
                <div class="workspace-promotion-row-actions">
                    <button class="btn btn-secondary" type="button" onclick="previewWorkspacePromotion(${Number(item.id)})">预览</button>
                    <button class="btn btn-secondary" type="button" onclick="showWorkspacePromotionEditor(${Number(item.id)})">编辑</button>
                    <button class="btn btn-secondary" type="button" onclick="toggleWorkspacePromotion(${Number(item.id)})">${item.is_active ? '下线' : '发布'}</button>
                    <button class="workspace-promotion-delete" type="button" onclick="confirmDeleteWorkspacePromotion(${Number(item.id)})">删除</button>
                </div>
            </article>`;
    }).join('')}</div>`;
}

async function loadWorkspacePromotions(options = {}) {
    if (workspacePromotionsData.length && options.force !== true) {
        renderWorkspacePromotions();
        return workspacePromotionsData;
    }
    const response = await fetchWithTimeout('/api/workspace/home-promotions', {credentials: 'same-origin'});
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        document.getElementById('workspacePromotionsList').innerHTML = `<div class="workspace-empty">${escapeHtml(data.detail || '主页宣传加载失败或当前身份没有权限。')}</div>`;
        return [];
    }
    workspacePromotionsData = await response.json();
    renderWorkspacePromotions();
    return workspacePromotionsData;
}

function toWorkspaceDatetimeLocal(value) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    const offset = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function syncWorkspacePromotionActionFields() {
    const kind = document.getElementById('workspacePromotionActionKind')?.value || 'none';
    const fields = document.getElementById('workspacePromotionActionFields');
    if (fields) fields.hidden = kind === 'none';
    const tabTarget = document.getElementById('workspacePromotionActionTargetTab');
    const urlTarget = document.getElementById('workspacePromotionActionTargetUrl');
    if (tabTarget) tabTarget.hidden = kind !== 'tab';
    if (urlTarget) urlTarget.hidden = kind !== 'url';
}

function getWorkspacePromotionTargetOptions(selectedTarget = '') {
    const groups = [
        ['主要页面', [
            ['home', '首页'], ['overview', '联赛概览'], ['players', '完整联赛名单'], ['team', '球队中心'], ['coaches', '教练主页'],
        ]],
        ['数据统计', [
            ['competition:standings', '积分榜'], ['competition:schedule', '赛程'], ['competition:playerRankings', '球员榜'], ['competition:suspensions', '伤停'],
            ['competition:standings:超级', '超级 · 积分榜'], ['competition:schedule:超级', '超级 · 赛程'], ['competition:playerRankings:超级', '超级 · 球员榜'], ['competition:suspensions:超级', '超级 · 伤停'],
            ['competition:standings:甲级', '甲级 · 积分榜'], ['competition:schedule:甲级', '甲级 · 赛程'], ['competition:playerRankings:甲级', '甲级 · 球员榜'], ['competition:suspensions:甲级', '甲级 · 伤停'],
            ['competition:standings:乙级', '乙级 · 积分榜'], ['competition:schedule:乙级', '乙级 · 赛程'], ['competition:playerRankings:乙级', '乙级 · 球员榜'], ['competition:suspensions:乙级', '乙级 · 伤停'],
            ['competition:standings:冠军杯', '冠军杯 · 积分榜/阶段'], ['competition:schedule:冠军杯', '冠军杯 · 赛程'],
            ['competition:standings:联盟杯', '联盟杯 · 积分榜/阶段'], ['competition:schedule:联盟杯', '联盟杯 · 赛程'],
            ['competition:standings:无铭剑杯', '无铭剑杯 · 积分榜/阶段'], ['competition:schedule:无铭剑杯', '无铭剑杯 · 赛程'],
        ]],
        ['球员库', [
            ['database:search', '球员搜索'], ['database:candidates', '候选名单'], ['database:power', '战力排行榜'], ['database:tactics', '自定义战术板'], ['database:leaderboard', '互动排行榜'],
        ]],
    ];
    const normalizedSelected = selectedTarget === 'competition:rankings' ? 'competition:playerRankings' : selectedTarget;
    return groups.map(([label, options]) => `<optgroup label="${label}">${options.map(([value, text]) => `<option value="${value}" ${normalizedSelected === value ? 'selected' : ''}>${text}</option>`).join('')}</optgroup>`).join('');
}

function updateWorkspacePromotionImagePreview() {
    const url = String(document.getElementById('workspacePromotionImage')?.value || '').trim();
    const preview = document.getElementById('workspacePromotionImagePreview');
    if (!preview) return;
    preview.classList.toggle('has-image', Boolean(url));
    preview.innerHTML = url ? `<img src="${escapeHtml(url)}" alt="宣传图片预览">` : '<span>IMAGE</span><small>可选宣传配图</small>';
}

function clearWorkspacePromotionImage() {
    const urlInput = document.getElementById('workspacePromotionImage');
    const fileInput = document.getElementById('workspacePromotionImageFile');
    const status = document.getElementById('workspacePromotionImageStatus');
    if (urlInput) urlInput.value = '';
    if (fileInput) fileInput.value = '';
    if (status) status.textContent = '';
    updateWorkspacePromotionImagePreview();
}

async function uploadWorkspacePromotionImage(input) {
    const file = input?.files?.[0];
    if (!file) return;
    const status = document.getElementById('workspacePromotionImageStatus');
    const preview = document.getElementById('workspacePromotionImagePreview');
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
        if (status) status.textContent = '仅支持 JPG、PNG、WEBP。';
        input.value = '';
        return;
    }
    if (file.size > 5 * 1024 * 1024) {
        if (status) status.textContent = '图片不能超过 5MB。';
        input.value = '';
        return;
    }
    if (status) status.textContent = '正在上传并优化图片…';
    preview?.classList.add('is-uploading');
    const formData = new FormData();
    formData.append('image', file);
    try {
        const response = await fetchWithTimeout('/api/workspace/home-promotions/image', {method: 'POST', credentials: 'same-origin', body: formData});
        const data = await response.json().catch(() => ({}));
        if (!response.ok || !data.image_url) throw new Error(data.detail || '图片上传失败');
        const urlInput = document.getElementById('workspacePromotionImage');
        if (urlInput) urlInput.value = data.image_url;
        updateWorkspacePromotionImagePreview();
        if (status) status.textContent = `上传完成 · ${Number(data.width || 0)} × ${Number(data.height || 0)}`;
    } catch (error) {
        if (status) status.textContent = error.message || '图片上传失败';
    } finally {
        preview?.classList.remove('is-uploading');
    }
}

function showWorkspacePromotionEditor(promotionId = 0) {
    const item = workspacePromotionsData.find(entry => Number(entry.id) === Number(promotionId)) || {
        content_type: 'announcement', theme: 'violet', icon: 'megaphone', eyebrow: 'HEIGO Broadcast', title: '', body: '',
        action_kind: 'none', action_target: '', action_label: '', display_mode: 'board', is_active: true, is_pinned: false, is_dismissible: true, sort_order: 100,
    };
    showModal(promotionId ? '编辑主页宣传' : '新增主页宣传', `
        <form class="workspace-promotion-editor" onsubmit="event.preventDefault(); saveWorkspacePromotion(${Number(promotionId)});">
            <div class="workspace-promotion-editor-intro"><span>PUBLIC BROADCAST</span><strong>让每条信息有明确层级、发布时间和去向。</strong></div>
            <div class="workspace-promotion-editor-grid">
                <label class="form-group"><span>内容类型</span><select id="workspacePromotionType">
                    ${[['announcement','联赛公告'],['honor','荣誉发布'],['update','版本更新'],['event','活动宣传']].map(([value,label]) => `<option value="${value}" ${item.content_type === value ? 'selected' : ''}>${label}</option>`).join('')}
                </select></label>
                <label class="form-group"><span>视觉主题</span><select id="workspacePromotionTheme">
                    ${[['violet','紫罗兰'],['blue','澄蓝'],['green','薄荷绿'],['gold','冠军金'],['rose','玫瑰红'],['neutral','银灰']].map(([value,label]) => `<option value="${value}" ${item.theme === value ? 'selected' : ''}>${label}</option>`).join('')}
                </select></label>
                <label class="form-group"><span>识别图标</span><select id="workspacePromotionIcon">
                    ${[['megaphone','播报'],['trophy','奖杯'],['list','名单'],['star','焦点'],['whistle','赛事'],['info','信息']].map(([value,label]) => `<option value="${value}" ${item.icon === value ? 'selected' : ''}>${label}</option>`).join('')}
                </select></label>
                <label class="form-group"><span>展示方式</span><select id="workspacePromotionDisplayMode">
                    ${[['board','主页卡片'],['modal','访问弹窗'],['both','主页卡片 + 访问弹窗']].map(([value,label]) => `<option value="${value}" ${(item.display_mode || 'board') === value ? 'selected' : ''}>${label}</option>`).join('')}
                </select></label>
                <label class="form-group"><span>排序值（小在前）</span><input id="workspacePromotionOrder" type="number" min="0" max="9999" value="${Number(item.sort_order || 0)}"></label>
            </div>
            <label class="form-group"><span>眉题</span><input id="workspacePromotionEyebrow" maxlength="60" value="${escapeHtml(item.eyebrow || '')}" placeholder="例如 HEIGO HONORS"></label>
            <label class="form-group"><span>宣传标题</span><input id="workspacePromotionTitle" maxlength="120" value="${escapeHtml(item.title || '')}" required placeholder="一句话说清最重要的信息"></label>
            <label class="form-group"><span>宣传正文</span><textarea id="workspacePromotionBody" maxlength="600" rows="5" placeholder="补充时间、范围或重要说明；弹窗模式下可每行填写一个功能要点">${escapeHtml(item.body || '')}</textarea></label>
            <div class="workspace-promotion-image-field">
                <div class="workspace-promotion-image-preview ${item.image_url ? 'has-image' : ''}" id="workspacePromotionImagePreview">${item.image_url ? `<img src="${escapeHtml(item.image_url)}" alt="宣传图片预览">` : '<span>IMAGE</span><small>可选宣传配图</small>'}</div>
                <div class="workspace-promotion-image-control">
                    <strong>宣传图片</strong>
                    <p>支持 JPG、PNG、WEBP，最大 5MB；上传后自动压缩为 WebP。</p><span class="workspace-promotion-image-status" id="workspacePromotionImageStatus"></span>
                    <input id="workspacePromotionImageFile" class="workspace-promotion-file-input" type="file" accept="image/jpeg,image/png,image/webp" onchange="uploadWorkspacePromotionImage(this)">
                    <div><button class="btn btn-secondary" type="button" onclick="document.getElementById('workspacePromotionImageFile')?.click()">从本地选择</button><button class="workspace-promotion-image-clear" type="button" onclick="clearWorkspacePromotionImage()">移除图片</button></div>
                    <label class="form-group"><span>或填写图片地址</span><input id="workspacePromotionImage" type="text" maxlength="300" value="${escapeHtml(item.image_url || '')}" oninput="updateWorkspacePromotionImagePreview()" placeholder="/static/... 或 https://..."></label>
                </div>
            </div>
            <div class="workspace-promotion-editor-grid">
                <label class="form-group"><span>开始展示</span><input id="workspacePromotionStarts" type="datetime-local" value="${toWorkspaceDatetimeLocal(item.starts_at)}"></label>
                <label class="form-group"><span>结束展示</span><input id="workspacePromotionEnds" type="datetime-local" value="${toWorkspaceDatetimeLocal(item.ends_at)}"></label>
            </div>
            <label class="form-group"><span>按钮行为</span><select id="workspacePromotionActionKind" onchange="syncWorkspacePromotionActionFields()">
                <option value="none" ${item.action_kind === 'none' ? 'selected' : ''}>不显示按钮</option>
                <option value="tab" ${item.action_kind === 'tab' ? 'selected' : ''}>打开站内页面</option>
                <option value="url" ${item.action_kind === 'url' ? 'selected' : ''}>打开链接</option>
            </select></label>
            <div id="workspacePromotionActionFields" class="workspace-promotion-editor-grid" ${item.action_kind === 'none' ? 'hidden' : ''}>
                <label class="form-group"><span>按钮文字</span><input id="workspacePromotionActionLabel" maxlength="40" value="${escapeHtml(item.action_label || '')}" placeholder="例如 查看名单"></label>
                <label class="form-group"><span>按钮目标</span><select id="workspacePromotionActionTargetTab" ${item.action_kind === 'tab' ? '' : 'hidden'}>${getWorkspacePromotionTargetOptions(item.action_target || '')}</select><input id="workspacePromotionActionTargetUrl" type="text" maxlength="300" value="${item.action_kind === 'url' ? escapeHtml(item.action_target || '') : ''}" placeholder="https://... 或站内 /path" ${item.action_kind === 'url' ? '' : 'hidden'}></label>
            </div>
            <div class="workspace-promotion-switches">
                <label><input id="workspacePromotionActive" type="checkbox" ${item.is_active ? 'checked' : ''}>立即启用</label>
                <label><input id="workspacePromotionPinned" type="checkbox" ${item.is_pinned ? 'checked' : ''}>置顶展示</label>
                <label><input id="workspacePromotionDismissible" type="checkbox" ${item.is_dismissible !== false ? 'checked' : ''}>允许访客关闭</label>
            </div>
            <div class="workspace-promotion-editor-actions"><button class="btn btn-secondary" type="button" onclick="closeModal()">取消</button><button class="btn btn-primary" type="submit">${promotionId ? '保存修改' : '发布宣传'}</button></div>
        </form>
    `);
}

function readWorkspacePromotionEditor() {
    const value = id => document.getElementById(id)?.value || '';
    const actionKind = value('workspacePromotionActionKind');
    return {
        content_type: value('workspacePromotionType'), theme: value('workspacePromotionTheme'), icon: value('workspacePromotionIcon'),
        eyebrow: value('workspacePromotionEyebrow'), title: value('workspacePromotionTitle'), body: value('workspacePromotionBody'),
        image_url: value('workspacePromotionImage') || null, action_kind: actionKind,
        display_mode: value('workspacePromotionDisplayMode') || 'board',
        action_label: value('workspacePromotionActionLabel') || null,
        action_target: (actionKind === 'tab' ? value('workspacePromotionActionTargetTab') : value('workspacePromotionActionTargetUrl')) || null,
        is_active: Boolean(document.getElementById('workspacePromotionActive')?.checked),
        is_pinned: Boolean(document.getElementById('workspacePromotionPinned')?.checked),
        is_dismissible: Boolean(document.getElementById('workspacePromotionDismissible')?.checked),
        sort_order: Number(value('workspacePromotionOrder') || 0), starts_at: value('workspacePromotionStarts') || null, ends_at: value('workspacePromotionEnds') || null,
    };
}

async function refreshHomePromotionsAfterAdminChange() {
    workspacePromotionsData = [];
    await loadWorkspacePromotions({force: true});
    if (typeof loadHomePromotions === 'function') {
        homePromotionsLoaded = false;
        await loadHomePromotions({force: true});
    }
}

async function saveWorkspacePromotion(promotionId = 0) {
    const response = await fetchWithTimeout(promotionId ? `/api/workspace/home-promotions/${promotionId}` : '/api/workspace/home-promotions', {
        method: promotionId ? 'PATCH' : 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(readWorkspacePromotionEditor()),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        showModal('保存失败', escapeHtml(data.detail || '主页宣传保存失败'));
        return;
    }
    closeModal();
    await refreshHomePromotionsAfterAdminChange();
}

async function toggleWorkspacePromotion(promotionId) {
    const item = workspacePromotionsData.find(entry => Number(entry.id) === Number(promotionId));
    if (!item) return;
    const response = await fetchWithTimeout(`/api/workspace/home-promotions/${promotionId}`, {method: 'PATCH', credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(workspacePromotionRequestPayload(item, {is_active: !item.is_active}))});
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        showModal('操作失败', escapeHtml(data.detail || '宣传状态更新失败'));
        return;
    }
    await refreshHomePromotionsAfterAdminChange();
}

function previewWorkspacePromotion(promotionId) {
    const item = workspacePromotionsData.find(entry => Number(entry.id) === Number(promotionId));
    if (!item) return;
    const symbol = typeof homePromotionIconSvg === 'function' ? homePromotionIconSvg(item.icon) : '';
    if (['modal', 'both'].includes(item.display_mode) && typeof showHomePromotionModal === 'function') {
        showHomePromotionModal(item, {preview: true});
        return;
    }
    showModal('主页展示预览', `<article class="home-promotion-card is-${escapeHtml(item.theme)} is-featured is-admin-preview"><span class="home-promotion-media ${item.image_url ? '' : 'is-symbol'}">${item.image_url ? `<img src="${escapeHtml(item.image_url)}" alt="">` : symbol}</span><div class="home-promotion-copy"><span>${escapeHtml(item.eyebrow)}</span><h2>${escapeHtml(item.title)}</h2>${item.body ? `<p>${escapeHtml(item.body)}</p>` : ''}</div>${item.action_label ? `<div class="home-promotion-actions"><span class="btn home-promotion-action">${escapeHtml(item.action_label)}</span></div>` : ''}</article>`);
}

function confirmDeleteWorkspacePromotion(promotionId) {
    const item = workspacePromotionsData.find(entry => Number(entry.id) === Number(promotionId));
    if (!item) return;
    showModal('删除主页宣传', `<div class="workspace-promotion-delete-confirm"><strong>${escapeHtml(item.title)}</strong><p>删除后无法恢复；如果只想暂时停止展示，请使用“下线”。</p><div><button class="btn btn-secondary" type="button" onclick="closeModal()">取消</button><button class="btn btn-danger" type="button" onclick="deleteWorkspacePromotion(${Number(item.id)})">确认删除</button></div></div>`);
}

async function deleteWorkspacePromotion(promotionId) {
    const response = await fetchWithTimeout(`/api/workspace/home-promotions/${promotionId}`, {method: 'DELETE', credentials: 'same-origin'});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        showModal('删除失败', escapeHtml(data.detail || '主页宣传删除失败'));
        return;
    }
    closeModal();
    await refreshHomePromotionsAfterAdminChange();
}

async function syncWorkspaceChampionPromotions() {
    const response = await fetchWithTimeout('/api/workspace/home-promotions/sync-cup-champions', {method: 'POST', credentials: 'same-origin'});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        showModal('同步失败', escapeHtml(data.detail || '当前杯赛冠军同步失败'));
        return;
    }
    workspacePromotionsData = Array.isArray(data) ? data : [];
    renderWorkspacePromotions();
    if (typeof loadHomePromotions === 'function') {
        homePromotionsLoaded = false;
        await loadHomePromotions({force: true});
    }
}

async function syncWorkspaceLeagueChampionPromotions() {
    const response = await fetchWithTimeout('/api/workspace/home-promotions/sync-league-champions', {method: 'POST', credentials: 'same-origin'});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        showModal('同步失败', escapeHtml(data.detail || '联赛冠军同步失败'));
        return;
    }
    workspacePromotionsData = Array.isArray(data) ? data : [];
    renderWorkspacePromotions();
    const leagueChampions = workspacePromotionsData.filter(item => item.source_type === 'league_champion');
    if (typeof loadHomePromotions === 'function') {
        homePromotionsLoaded = false;
        await loadHomePromotions({force: true});
    }
    if (!leagueChampions.length) {
        showModal('暂未产生联赛冠军', '超级、甲级、乙级需要完成全部 34 轮，且所有球队积分榜已赛达到 34 场后才会同步。');
    } else {
        showModal('联赛冠军已同步', `当前共 ${leagueChampions.length} 条联赛冠军宣传，可关闭提示后继续编辑、自定义图片或调整发布时间。`);
    }
}

async function workspaceCoachLogin() {
    const username = document.getElementById('workspaceCoachUsername')?.value || '';
    const password = document.getElementById('workspaceCoachPassword')?.value || '';
    const response = await fetchWithTimeout('/api/coach/login', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, password}),
    });
    const data = await response.json();
    if (!response.ok || !data.authenticated) {
        showModal('登录失败', escapeHtml(data.detail || '账号或密码错误'));
        return;
    }
    await ensureAppModule('coaches');
    currentCoachAccount = data;
    beginCoachSecuritySetup(() => finishWorkspaceCoachLogin(currentCoachAccount));
}

async function finishWorkspaceCoachLogin(data) {
    if (!(data.can_manage_schedule || data.can_manage_cup_standings || data.can_manage_rankings || data.can_manage_suspensions || data.can_manage_candidate_lists)) {
        showModal('没有工作权限', '该教练账号可以使用个人中心，但尚未获得数据工作权限。');
        return;
    }
    workspaceSessionData = null;
    workspaceDashboardData = null;
    await openWorkspace({force: true});
    if (typeof resumePendingWorkContext === 'function') await resumePendingWorkContext();
}

async function workspaceLogout() {
    const source = workspaceSessionData?.identity?.source;
    const endpoint = source === 'coach_account' ? '/api/coach/logout' : '/api/admin/logout';
    await fetchWithTimeout(endpoint, {method: 'POST', credentials: 'same-origin'});
    workspaceSessionData = null;
    workspaceDashboardData = null;
    workspaceAccountsData = [];
    workspacePromotionsData = [];
    workspaceSessionState = {authenticated: false, identity: null};
    if (source === 'coach_account') currentCoachAccount = {authenticated: false};
    await openWorkspace({force: true});
}

function loadWorkspaceAdminOperations() {
    if (!workspaceSessionData?.identity?.is_full_admin || workspaceAdminOperationsLoaded) return Promise.resolve();
    if (workspaceAdminOperationsLoadPromise) return workspaceAdminOperationsLoadPromise;
    workspaceAdminOperationsLoadPromise = (async () => {
        await Promise.all([
            ensureAppModule('overview'),
            ensureTeamsLoaded(),
            ensurePlayersLoaded(),
            ensureLeagueInfoLoaded(),
        ]);
        updateStats();
        renderFormalImportSummaryCard();
        renderSchemaBootstrapStatusCard();
        renderOperationsAuditCard();
        renderTeamStatSourceDebugView();
        populateAdminSelects();
        loadSchemaBootstrapStatus();
        loadLatestFormalImportSummary();
        loadOperationsAudit();
        loadDataFeedbackReports();
        loadSeaPlayers();
        loadTransferLogs();
        loadLogFile();
        workspaceAdminOperationsLoaded = true;
    })().catch(error => {
        console.error('Failed to load workspace operations:', error);
        showModal('工作区加载失败', '数据与系统工作区暂时无法加载，请稍后重试。');
    }).finally(() => {
        workspaceAdminOperationsLoadPromise = null;
    });
    return workspaceAdminOperationsLoadPromise;
}

function isAdminUnauthorizedError(error) {
    return error?.code === ADMIN_UNAUTHORIZED_ERROR || error?.message === ADMIN_UNAUTHORIZED_ERROR;
}

function enterAdminLoggedOutState(options = {}) {
    isAdmin = false;
    currentAdminRole = '';
    canManageSchedule = false;
    canManageCupStandings = false;
    canManageRankings = false;
    canManageSuspensions = false;
    canManageCandidateLists = false;
    if (typeof endCandidateListMaintenance === 'function') {
        endCandidateListMaintenance();
    }
    if (options.reveal !== false) {
        adminEntryUnlocked = true;
    }
    syncAdminTabVisibility();
    syncAdminPanelVisibility({focusLogin: options.focusLogin !== false});
    if (typeof hideTeamStatSourceDebugView === 'function') {
        hideTeamStatSourceDebugView();
    }
    if (typeof renderTeamsTable === 'function') {
        renderTeamsTable();
    }
    if (typeof renderPlayers === 'function') {
        renderPlayers(Array.isArray(currentPlayers) ? currentPlayers : []);
    }
    if (typeof loadCompetitionData === 'function') {
        loadCompetitionData({force: true});
    }
    if (typeof updateStats === 'function') {
        updateStats();
    }
    if (options.activateAdminTab !== false && typeof showTab === 'function') {
        showTab('admin', null, {syncHistory: false});
    }
}

function notifyAdminUnauthorized(message = '管理员登录已失效，请重新验证管理员账户。') {
    const now = Date.now();
    if (now - lastAdminUnauthorizedNoticeAt < 1000) return;
    lastAdminUnauthorizedNoticeAt = now;
    showModal('未授权', message);
}

function isCoachWorkAccountActive() {
    const coachAccount = typeof currentCoachAccount !== 'undefined' ? currentCoachAccount : null;
    return Boolean(
        !currentAdminRole
        && coachAccount?.authenticated
        && (canManageSchedule || canManageCupStandings || canManageRankings || canManageSuspensions || canManageCandidateLists)
    );
}

async function handleCoachWorkUnauthorized(message = '工作账号登录已失效，请重新登录教练账号。') {
    if (typeof coachLogout === 'function') {
        await coachLogout();
    } else {
        currentCoachAccount = {authenticated: false};
        canManageSchedule = false;
        canManageCupStandings = false;
        canManageRankings = false;
        canManageSuspensions = false;
        canManageCandidateLists = false;
    }
    notifyAdminUnauthorized(message);
}

function handleAdminUnauthorized(message = '管理员登录已失效，请重新验证管理员账户。', options = {}) {
    enterAdminLoggedOutState({
        focusLogin: options.focusLogin !== false,
        activateAdminTab: options.activateAdminTab !== false,
    });
    if (!options.silent) {
        notifyAdminUnauthorized(message);
    }
}

async function adminFetch(url, options = {}) {
    const {
        silentUnauthorized = false,
        unauthorizedMessage = '管理员登录已失效，请重新验证管理员账户。',
        focusLoginOnUnauthorized = true,
        activateAdminTabOnUnauthorized = true,
        ...fetchOptions
    } = options;
    const response = await fetchWithTimeout(url, {
        credentials: 'same-origin',
        ...fetchOptions,
    });
    if (response.status === 401) {
        if (typeof capturePendingWorkContext === 'function') {
            capturePendingWorkContext({reason: 'admin-session-expired'});
        }
        if (isCoachWorkAccountActive()) {
            await handleCoachWorkUnauthorized('工作账号登录已失效，请重新登录教练账号。');
            const error = new Error(ADMIN_UNAUTHORIZED_ERROR);
            error.code = ADMIN_UNAUTHORIZED_ERROR;
            throw error;
        }
        handleAdminUnauthorized(unauthorizedMessage, {
            silent: silentUnauthorized,
            focusLogin: focusLoginOnUnauthorized,
            activateAdminTab: activateAdminTabOnUnauthorized,
        });
        const error = new Error(ADMIN_UNAUTHORIZED_ERROR);
        error.code = ADMIN_UNAUTHORIZED_ERROR;
        throw error;
    }
    return response;
}

async function adminJsonRequest(url, options = {}) {
    try {
        const response = await adminFetch(url, options);
        const data = await response.json();
        return {response, data};
    } catch (error) {
        if (isAdminUnauthorizedError(error)) {
            return null;
        }
        throw error;
    }
}

async function syncAdminAuthStatus(options = {}) {
    const response = await fetchWithTimeout('/api/admin/check', {credentials: 'same-origin'});
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    currentAdminRole = data.role || '';
    isAdmin = Boolean(data.authenticated && data.can_manage_admin);
    canManageSchedule = Boolean(data.authenticated && data.can_manage_schedule);
    canManageCupStandings = Boolean(data.authenticated && data.can_manage_cup_standings);
    canManageRankings = Boolean(data.authenticated && data.can_manage_rankings);
    canManageSuspensions = Boolean(data.authenticated && data.can_manage_suspensions);
    canManageCandidateLists = Boolean(data.authenticated && data.can_manage_candidate_lists);
    syncAdminTabVisibility();
    syncAdminPanelVisibility({
        focusLogin: options.focusLogin !== false && !isAdmin,
    });
    return data;
}

async function logoutCurrentWorkAccount() {
    if (currentAdminRole) {
        await adminLogout();
        return;
    }
    if (typeof coachLogout === 'function') {
        await coachLogout();
    }
}

function syncAdminTabVisibility() {
    const adminTab = document.getElementById('adminTab');
    if (!adminTab) return;
    const hasWorkspaceAccess = workspaceHasWorkAccess(
        typeof workspaceSessionState !== 'undefined' ? workspaceSessionState?.identity : null,
    );
    adminTab.classList.toggle('hidden-tab', !(isAdmin || adminEntryUnlocked || hasWorkspaceAccess));
    if (typeof syncMobileNavState === 'function') {
        syncMobileNavState({closeMenu: false});
    }
}

function syncAdminPanelVisibility(options = {}) {
    const loginSection = document.getElementById('adminLogin');
    const adminPanel = document.getElementById('adminPanel');
    if (!loginSection || !adminPanel) return;

    const fallbackIdentity = typeof workspaceSessionState !== 'undefined' ? workspaceSessionState?.identity : null;
    if (isAdmin || workspaceHasWorkAccess(workspaceSessionData?.identity || fallbackIdentity)) {
        loginSection.style.display = 'none';
        adminPanel.style.display = 'block';
        return;
    }

    loginSection.style.display = 'block';
    adminPanel.style.display = 'none';

    if (options.focusLogin) {
        window.setTimeout(() => {
            document.getElementById('adminUsername')?.focus();
        }, 0);
    }
}

function showAdminLoginPanel(options = {}) {
    if (options.reveal !== false) {
        adminEntryUnlocked = true;
    }
    syncAdminTabVisibility();
    syncAdminPanelVisibility({focusLogin: options.focusLogin !== false});
}

function openAdminEntry() {
    showAdminLoginPanel({reveal: true, focusLogin: false});
    if (typeof showTab === 'function') {
        showTab('admin', null, {syncHistory: false});
    }
}

function showAdminTab() {
    adminEntryUnlocked = true;
    syncAdminTabVisibility();
    openWorkspace({force: true});
}

function getDataFeedbackIssueTypeLabel(issueType) {
    const labels = {
        player_profile: '球员资料',
        attribute_value: '属性数值',
        team_assignment: '球队归属',
        wage_slot: '工资 / 名额',
        other: '其他',
    };
    return labels[issueType] || issueType || '未分类';
}

function renderDataFeedbackReportsCard() {
    const container = document.getElementById('dataFeedbackReportsCard');
    if (!container) return;
    if (!recentDataFeedbackReports.length) {
        container.innerHTML = '<div class="import-summary-placeholder">当前还没有收到新的数据纠错反馈。</div>';
        return;
    }

    container.innerHTML = recentDataFeedbackReports.map(item => `
        <div class="feedback-admin-item">
            <div class="feedback-admin-head">
                <span class="bootstrap-status-pill info">${escapeHtml(getDataFeedbackIssueTypeLabel(item.issue_type))}</span>
                <span class="feedback-admin-meta">#${escapeHtml(item.id)} 路 ${escapeHtml(item.status || 'open')} 路 ${escapeHtml(item.created_at || '-')}</span>
            </div>
            <div class="feedback-admin-title">${escapeHtml(item.summary || '未填写摘要')}</div>
            <div class="feedback-admin-meta">
                ${item.player_uid ? `UID：${escapeHtml(item.player_uid)}` : 'UID：未填写'}
                ${item.player_name ? ` 路 球员：${escapeHtml(item.player_name)}` : ''}
                ${item.source_page ? ` 路 来源：${escapeHtml(item.source_page)}` : ''}
            </div>
            <div class="feedback-admin-body">${escapeHtml(item.details || '')}</div>
            ${item.suggested_correction ? `<div class="feedback-admin-extra"><strong>建议更正：</strong>${escapeHtml(item.suggested_correction)}</div>` : ''}
            ${item.contact ? `<div class="feedback-admin-extra"><strong>联系方式：</strong>${escapeHtml(item.contact)}</div>` : ''}
        </div>
    `).join('');
}

async function loadDataFeedbackReports() {
    try {
        const result = await adminJsonRequest('/api/admin/data-feedback?limit=20', {silentUnauthorized: true});
        if (!result) return;
        const {response: res, data} = result;
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        recentDataFeedbackReports = Array.isArray(data) ? data : [];
    } catch (error) {
        recentDataFeedbackReports = [];
    }
    renderDataFeedbackReportsCard();
}

function formatDatasetCounters(summary) {
    if (!summary) return '';
    return `新增 ${summary.created} / 更新 ${summary.updated} / 未变 ${summary.unchanged} / 跳过 ${summary.skipped}`;
}

function formatFormalImportResult(data) {
    const datasetEntries = Object.entries(data.datasets || {});
    const datasetHtml = datasetEntries.map(([name, summary]) => {
        const warningHtml = (summary.warnings || []).slice(0, 3).map(item => `<li>${escapeHtml(item)}</li>`).join('');
        const errorHtml = (summary.errors || []).slice(0, 3).map(item => `<li>${escapeHtml(item)}</li>`).join('');
        return `
            <div class="admin-action-card" style="margin-top:12px;">
                <h4 style="margin-bottom:8px;">${escapeHtml(name)}</h4>
                <div class="maintenance-note">${formatDatasetCounters(summary)}</div>
                ${warningHtml ? `<div class="maintenance-note" style="margin-top:8px;"><strong>警告：</strong><ul style="margin:6px 0 0 18px;">${warningHtml}</ul></div>` : ''}
                ${errorHtml ? `<div class="maintenance-note" style="margin-top:8px;color:#ff8a80;"><strong>错误：</strong><ul style="margin:6px 0 0 18px;">${errorHtml}</ul></div>` : ''}
            </div>
        `;
    }).join('');
    const cleanup = data.datasets && data.datasets.team_cleanup ? data.datasets.team_cleanup.details || {} : {};
    const removedTeams = cleanup.removed_teams || [];
    return `
        <div class="maintenance-note"><strong>结果：</strong>${escapeHtml(data.message || '')}</div>
        <div class="maintenance-note" style="margin-top:8px;"><strong>Workbook：</strong><code>${escapeHtml(data.workbook_path || '')}</code></div>
        <div class="maintenance-note" style="margin-top:8px;"><strong>Attributes CSV：</strong><code>${escapeHtml(data.skip_attributes ? '已跳过' : (data.attributes_csv_path || ''))}</code></div>
        <div class="maintenance-note" style="margin-top:8px;"><strong>备份：</strong><code>${escapeHtml(data.backup_path || '未创建')}</code></div>
        ${removedTeams.length ? `<div class="maintenance-note" style="margin-top:8px;"><strong>清理的过期球队：</strong>${removedTeams.map(item => `<code>${escapeHtml(item)}</code>`).join(', ')}</div>` : ''}
        ${datasetHtml}
    `;
}

function getBootstrapEventType(eventLine) {
    const match = String(eventLine || '').match(/\]\s+([a-z_]+)\s+/i);
    return match ? match[1] : 'unknown';
}

function getBootstrapEventMeta(eventType) {
    const meta = {
        alembic_upgrade: {label: 'Alembic 升级', tone: 'safe'},
        runtime_schema_repair: {label: '运行时修复', tone: 'warning'},
        database_bootstrap: {label: '数据库启动', tone: 'info'},
    };
    return meta[eventType] || {label: eventType || '未知事件', tone: 'info'};
}

function renderSchemaBootstrapStatusCard() {
    const container = document.getElementById('schemaBootstrapStatusCard');
    if (!container) return;
    if (!lastSchemaBootstrapStatus) {
        container.innerHTML = '<div class="import-summary-placeholder">管理员面板加载后，这里会显示最近一次数据库 schema 启动状态和最近几条 bootstrap 日志。</div>';
        return;
    }
    const status = lastSchemaBootstrapStatus;
    const latestEvent = status.latest_event || '暂无 bootstrap 事件';
    const latestType = getBootstrapEventType(latestEvent);
    const latestMeta = getBootstrapEventMeta(latestType);
    const recentEvents = (status.recent_events || []).slice().reverse();
    const eventHtml = recentEvents.length
        ? recentEvents.map(eventLine => {
            const eventType = getBootstrapEventType(eventLine);
            const eventMeta = getBootstrapEventMeta(eventType);
            return `<div class="bootstrap-status-event"><div><strong>${escapeHtml(eventMeta.label)}</strong></div><div class="event-line">${escapeHtml(eventLine)}</div></div>`;
        }).join('')
        : '<div class="import-summary-placeholder">暂无 bootstrap 事件。</div>';
    container.innerHTML = `
        <div class="bootstrap-status-pill ${latestMeta.tone}">${escapeHtml(latestMeta.label)}</div>
        <div class="bootstrap-status-meta">${escapeHtml(latestEvent)}</div>
        ${eventHtml}
    `;
}

async function loadSchemaBootstrapStatus() {
    try {
        const result = await adminJsonRequest('/api/admin/schema-bootstrap-status', {silentUnauthorized: true});
        if (!result) return;
        const {response: res, data} = result;
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        lastSchemaBootstrapStatus = data;
    } catch (error) {
        lastSchemaBootstrapStatus = null;
    }
    renderSchemaBootstrapStatusCard();
}

function getOperationAuditStatusMeta(status) {
    const meta = {
        success: {label: '成功', tone: 'safe'},
        failed: {label: '失败', tone: 'warning'},
        skipped: {label: '跳过', tone: 'info'},
    };
    return meta[status] || {label: status || '未知', tone: 'info'};
}

function getOperationAuditCategoryLabel(category, action) {
    if (category === 'transfer' && action === 'transfer_player') return '球员交易';
    if (category === 'transfer' && action === 'fish_player') return '海捞球员';
    if (category === 'transfer' && action === 'fish_sea_player') return '大海海捞';
    if (category === 'transfer' && action === 'release_player') return '球员解约';
    if (category === 'roster' && action === 'consume_player') return '球员消费';
    if (category === 'roster' && action === 'rejuvenate_player') return '球员返老';
    if (category === 'roster' && action === 'update_player_info') return '球员资料修改';
    if (category === 'roster' && action === 'update_player_uid') return '球员 UID 修改';
    if (category === 'maintenance' && action === 'recalculate_wages') return '工资重算';
    if (category === 'maintenance' && action === 'rebuild_team_stat_caches') return '球队缓存重算';
    return category || action || '未知动作';
}

function handleOperationAuditFilterChange() {
    const select = document.getElementById('operationsAuditCategoryFilter');
    currentOperationAuditCategory = select ? select.value : '';
    loadOperationsAudit();
}

function renderOperationsAuditCard() {
    const container = document.getElementById('operationsAuditCard');
    if (!container) return;
    if (!recentOperationAudits.length) {
        const emptyLabel = currentOperationAuditCategory ? `“${escapeHtml(currentOperationAuditCategory)}”分类下还没有记录。` : '当前还没有持久化运维审计记录。';
        container.innerHTML = `<div class="import-summary-placeholder">${emptyLabel}</div>`;
        return;
    }
    const itemsHtml = recentOperationAudits.map(item => {
        const statusMeta = getOperationAuditStatusMeta(item.status);
        const title = item.operation_label || getOperationAuditCategoryLabel(item.category, item.action);
        const operator = item.operator ? `操作人：${escapeHtml(item.operator)}` : '操作人：系统';
        return `
            <div class="operations-audit-item">
                <div class="operations-audit-meta">${escapeHtml(title)} · ${operator} · ${escapeHtml(item.created_at || '-')}</div>
                <div class="operations-audit-summary">${escapeHtml(item.summary || statusMeta.label)}</div>
            </div>
        `;
    }).join('');
    container.innerHTML = itemsHtml;
}

async function loadLatestFormalImportSummary() {
    try {
        const result = await adminJsonRequest('/api/admin/import/latest', {silentUnauthorized: true});
        if (!result) return;
        const {response: res, data} = result;
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        lastFormalImportSummary = data;
    } catch (error) {
        if (!lastFormalImportSummary) lastFormalImportSummary = null;
    }
    renderFormalImportSummaryCard();
    if (typeof renderOverviewStatusCards === 'function') renderOverviewStatusCards();
}

async function loadOperationsAudit() {
    try {
        const params = new URLSearchParams({limit: '12'});
        if (currentOperationAuditCategory) params.set('category', currentOperationAuditCategory);
        const result = await adminJsonRequest(`/api/admin/operations-audit?${params.toString()}`, {silentUnauthorized: true});
        if (!result) return;
        const {response: res, data} = result;
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        recentOperationAudits = data;
    } catch (error) {
        recentOperationAudits = [];
    }
    renderOperationsAuditCard();
    if (typeof renderOverviewStatusCards === 'function') renderOverviewStatusCards();
}

async function exportOperationAudits() {
    try {
        const params = new URLSearchParams();
        if (currentOperationAuditCategory) params.set('category', currentOperationAuditCategory);
        const response = await adminFetch(`/api/admin/operations-audit/export?${params.toString()}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const disposition = response.headers.get('Content-Disposition') || '';
        const match = disposition.match(/filename="([^"]+)"/);
        a.download = match ? match[1] : 'operation_audits.csv';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        showModal('错误', `导出审计记录失败：${error.message}`);
    }
}

function showLatestFormalImportDetails() {
    if (!lastFormalImportSummary) {
        showModal('提示', '当前还没有正式导入记录。');
        return;
    }
    showModal('最近一次正式导入明细', formatFormalImportResult(lastFormalImportSummary));
}

function renderFormalImportSummaryCard() {
    const container = document.getElementById('formalImportSummaryCard');
    if (!container) return;
    if (!lastFormalImportSummary) {
        container.innerHTML = '<div class="import-summary-placeholder">本次会话还没有执行正式导入。执行一次“正式导入最新联赛数据”后，这里会直接显示新增、更新、未变和清理结果。</div>';
        return;
    }
    const datasets = lastFormalImportSummary.datasets || {};
    const importDatasetKeys = ['league_info', 'teams', 'players', 'player_attributes'];
    const datasetLabels = {league_info: '联赛规则', teams: '球队', players: '球员', player_attributes: '属性库'};
    const breakdownHtml = importDatasetKeys.map(key => {
        const summary = datasets[key];
        if (!summary) return '';
        return `<div class="import-summary-breakdown-item"><strong>${datasetLabels[key]}</strong><span>${formatDatasetCounters(summary)}</span></div>`;
    }).join('');
    container.innerHTML = `
        <div class="import-summary-meta">
            <span>执行时间：${escapeHtml(lastFormalImportSummary.executed_at || lastFormalImportSummary.started_at || '-')}</span>
            <span>结果：${escapeHtml(lastFormalImportSummary.message || '-')}</span>
        </div>
        ${breakdownHtml}
    `;
}

async function adminLogin() {
    const username = document.getElementById('adminUsername').value;
    const password = document.getElementById('adminPassword').value;
    if (!username || !password) { showModal('错误', '请输入用户名和密码'); return; }
    try {
        const res = await fetchWithTimeout('/api/admin/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'same-origin',
            body: JSON.stringify({username, password}),
        });
        const data = await res.json();
        if (!res.ok) {
            showModal('错误', data.detail || '验证失败');
            return;
        }
        if (data.success) {
            const authStatus = await syncAdminAuthStatus({focusLogin: false});
            if (!authStatus.authenticated) {
                enterAdminLoggedOutState({focusLogin: true, activateAdminTab: true});
                showModal('错误', '登录态未生效，请检查 HTTPS / Session Cookie 配置后重试。');
                return;
            }
            workspaceSessionData = null;
            workspaceDashboardData = null;
            await loadWorkspaceSession({force: true});
            await showTab('admin', null, {syncHistory: false});
            const resumed = typeof resumePendingWorkContext === 'function'
                ? await resumePendingWorkContext()
                : false;
            if (!resumed) showSuccessToast(`欢迎 ${data.username}，已进入联赛工作台`);
        }
    } catch (e) {
        if (isAdminUnauthorizedError(e)) return;
        console.error('登录错误:', e);
        showModal('错误', '登录请求失败');
    }
}

async function adminLogout() {
    try {
        await fetchWithTimeout('/api/admin/logout', {method: 'POST', credentials: 'same-origin'});
    } catch (e) {
        console.error('登出错误:', e);
    }
    enterAdminLoggedOutState({focusLogin: false, activateAdminTab: false});
    showTab('players');
}

function populateAdminSelects() {
    const selects = [
        {id: 'transferTeam', leagueOnly: false},
        {id: 'seaFishTeam', leagueOnly: true},
    ];
    selects.forEach(({id, leagueOnly}) => {
        const select = document.getElementById(id);
        if (!select) return;
        select.innerHTML = '<option value="">选择球队</option>';
        teams.filter(t => !leagueOnly || ['超级', '甲级', '乙级'].includes(t.level)).forEach(t => {
            const option = document.createElement('option');
            option.value = t.name;
            option.textContent = `${t.name} (${t.level})`;
            select.appendChild(option);
        });
    });
}

async function loadSeaPlayers() {
    const result = await adminJsonRequest('/api/admin/sea-players', {silentUnauthorized: true});
    if (!result) return;
    const {data: players} = result;
    if (players.length === 0) {
        document.getElementById('seaPlayersTable').innerHTML = '<div class="no-data">大海中没有球员</div>';
        return;
    }
    const html = `<table><thead><tr><th>UID</th><th>姓名</th><th>年龄</th><th>初始 CA</th><th>当前 CA</th><th>PA</th><th>位置</th><th>国籍</th><th>操作</th></tr></thead><tbody>${players.map(p => `<tr><td>${p.uid}</td><td>${escapeHtml(p.name || '-')}</td><td>${p.age}</td><td>${p.initial_ca}</td><td>${p.ca}</td><td>${p.pa}</td><td>${escapeHtml(p.position || '-')}</td><td title="${escapeHtml(p.nationality || '-')}">${escapeHtml(formatCompactNationality(p.nationality, {maxLength: 16}))}</td><td><button class="btn btn-secondary sea-fish-table-action" onclick="prepareSeaFish(${p.uid})">海捞</button></td></tr>`).join('')}</tbody></table>`;
    document.getElementById('seaPlayersTable').innerHTML = html;
}

function prepareSeaFish(uid) {
    const uidInput = document.getElementById('seaFishUid');
    const card = document.getElementById('seaFishCard');
    if (!uidInput || !card) return;
    uidInput.value = uid;
    card.scrollIntoView({behavior: 'smooth', block: 'center'});
    window.setTimeout(() => document.getElementById('seaFishTeam')?.focus(), 350);
}

async function loadTransferLogs() {
    const result = await adminJsonRequest('/api/admin/transfer-logs', {silentUnauthorized: true});
    if (!result) return;
    const {data: logs} = result;
    if (logs.length === 0) {
        document.getElementById('logsTable').innerHTML = '<div class="no-data">暂无操作日志</div>';
        return;
    }
    const supportedOps = ['交易', '批量交易', '解约', '批量解约', '海捞', '消费', '批量消费', '返老'];
    const html = `<table><thead><tr><th>时间</th><th>操作</th><th>球员</th><th>原球队</th><th>新球队</th><th>CA变化</th><th>PA变化</th><th>年龄变化</th><th>操作者</th><th>备注</th><th>操作</th></tr></thead><tbody>${logs.map(l => {
        const canUndo = supportedOps.includes(l.operation);
        const undoBtn = canUndo ? `<button class="btn btn-danger" style="padding:4px 10px;font-size:0.8rem;" onclick="undoOperation(${l.id}, '${l.operation.replace(/'/g, "\\'")}', '${l.player_name.replace(/'/g, "\\'")}')">撤销</button>` : '-';
        return `<tr><td>${new Date(l.created_at).toLocaleString()}</td><td>${l.operation}</td><td>${l.player_name}</td><td>${l.from_team}</td><td>${l.to_team}</td><td>${l.ca_change || '-'}</td><td>${l.pa_change || '-'}</td><td>${l.age_change || '-'}</td><td>${l.operator}</td><td>${l.notes || '-'}</td><td>${undoBtn}</td></tr>`;
    }).join('')}</tbody></table>`;
    document.getElementById('logsTable').innerHTML = html;
}

async function undoOperation(logId, operation, playerName) {
    pendingUndoLogId = logId;
    showModal('确认撤销', `<p>确定要撤销操作 "${escapeHtml(operation)} - ${escapeHtml(playerName)}" 吗？</p><div style="margin-top:20px;display:flex;gap:10px;justify-content:center;"><button class="btn btn-danger" onclick="confirmUndo()">确认撤销</button><button class="btn btn-secondary" onclick="closeModal()">取消</button></div>`);
}

async function confirmUndo() {
    if (!pendingUndoLogId) return;
    closeModal();
    try {
        const result = await adminJsonRequest(`/api/admin/undo/${pendingUndoLogId}`, {method: 'POST'});
        if (!result) return;
        const {data} = result;
        if (data.success) {
            showSuccessToast(data.message || '撤销成功');
            await refreshPlayerDataset();
            await refreshTeamDataset();
            loadTransferLogs();
            loadLogFile();
            loadSeaPlayers();
        } else {
            showModal('错误', data.detail || '撤销失败');
        }
    } catch (e) {
        showModal('错误', '撤销请求失败');
    }
    pendingUndoLogId = null;
}

async function loadLogFile() {
    const result = await adminJsonRequest('/api/admin/logs', {silentUnauthorized: true});
    if (!result) return;
    const {data} = result;
    document.getElementById('logFileContent').textContent = data.logs || '暂无日志记录';
}

async function refreshAdminAfterMutation() {
    await refreshPlayerDataset();
    await refreshTeamDataset();
    loadTransferLogs();
    loadLogFile();
    if (isAdmin) {
        loadSeaPlayers();
        loadOperationsAudit();
    }
}

async function transferPlayer() {
    const uid = parseInt(document.getElementById('transferUid').value);
    const team = document.getElementById('transferTeam').value;
    const notes = document.getElementById('transferNotes').value;
    if (!uid || !team) { showModal('错误', '请填写球员UID和目标球队'); return; }
    try {
        const result = await adminJsonRequest('/api/admin/transfer', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({player_uid: uid, to_team: team, notes})});
        if (!result) return;
        const {data} = result;
        if (data.success) {
            showSuccessToast(data.message || '球员交易已完成');
            document.getElementById('transferUid').value = '';
            document.getElementById('transferNotes').value = '';
            await refreshAdminAfterMutation();
        } else showModal('错误', data.detail || data.message || '交易失败');
    } catch (e) {
        showModal('错误', '交易请求失败');
    }
}

async function seaFishPlayer() {
    const uid = parseInt(document.getElementById('seaFishUid').value);
    const team = document.getElementById('seaFishTeam').value;
    const notes = document.getElementById('seaFishNotes').value;
    if (!uid || !team) { showModal('错误', '请选择大海球员和目标球队'); return; }
    try {
        const result = await adminJsonRequest('/api/admin/sea-fish', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({player_uid: uid, to_team: team, notes}),
        });
        if (!result) return;
        const {response, data} = result;
        if (response.ok && data.success) {
            showSuccessToast(data.message || '海捞已完成');
            document.getElementById('seaFishUid').value = '';
            document.getElementById('seaFishNotes').value = '';
            await refreshAdminAfterMutation();
        } else showModal('错误', data.detail || data.message || '海捞失败');
    } catch (e) {
        showModal('错误', '海捞请求失败');
    }
}

async function releasePlayer() {
    const uid = parseInt(document.getElementById('releaseUid').value);
    const notes = document.getElementById('releaseNotes').value;
    if (!uid) { showModal('错误', '请填写球员UID'); return; }
    try {
        const result = await adminJsonRequest('/api/admin/release', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({player_uid: uid, to_team: '大海', notes})});
        if (!result) return;
        const {data} = result;
        if (data.success) {
            showSuccessToast(data.message || '球员解约已完成');
            document.getElementById('releaseUid').value = '';
            document.getElementById('releaseNotes').value = '';
            await refreshAdminAfterMutation();
        } else showModal('错误', data.detail || data.message || '解约失败');
    } catch (e) {
        showModal('错误', '解约请求失败');
    }
}

async function consumePlayer() {
    const uid = parseInt(document.getElementById('consumeUid').value);
    const caChange = parseInt(document.getElementById('consumeCa').value) || 0;
    const paChange = parseInt(document.getElementById('consumePa').value) || 0;
    if (!uid) { showModal('错误', '请填写球员UID'); return; }
    if (caChange === 0 && paChange === 0) { showModal('错误', '请填写CA或PA的变化值'); return; }
    try {
        const result = await adminJsonRequest('/api/admin/consume', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({player_uid: uid, ca_change: caChange, pa_change: paChange})});
        if (!result) return;
        const {data} = result;
        if (data.success) {
            showSuccessToast(data.message || '球员属性调整已完成');
            document.getElementById('consumeUid').value = '';
            document.getElementById('consumeCa').value = '';
            document.getElementById('consumePa').value = '';
            await refreshAdminAfterMutation();
        } else showModal('错误', data.detail || data.message || '消费失败');
    } catch (e) {
        showModal('错误', '消费请求失败');
    }
}

function parseBatchLines(raw, mapper) {
    return raw.split('\n').filter(line => line.trim()).map(mapper).filter(Boolean);
}

async function batchTransfer() {
    const data = document.getElementById('batchTransferData').value.trim();
    if (!data) { showModal('错误', '请输入批量交易数据'); return; }
    const items = parseBatchLines(data, line => {
        const parts = line.split(',').map(p => p.trim());
        if (parts.length < 2) return null;
        return {uid: parseInt(parts[0]), to_team: parts[1], notes: parts[2] || ''};
    });
    if (!items.length) { showModal('错误', '没有有效的数据行'); return; }
    try {
        const response = await adminJsonRequest('/api/admin/batch-transfer', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({items})});
        if (!response) return;
        const {data: result} = response;
        document.getElementById('batchTransferResult').innerHTML = `<div class="batch-result ${result.success ? 'success' : 'error'}">成功: ${result.success_count}/${items.length}</div>`;
        if (result.success_count > 0) await refreshAdminAfterMutation();
    } catch (e) {
        showModal('错误', '批量交易请求失败');
    }
}

async function batchRelease() {
    const data = document.getElementById('batchReleaseData').value.trim();
    if (!data) { showModal('错误', '请输入批量解约数据'); return; }
    const items = parseBatchLines(data, line => {
        const parts = line.split(',').map(p => p.trim());
        if (parts.length < 1) return null;
        return {uid: parseInt(parts[0]), notes: parts[1] || ''};
    });
    if (!items.length) { showModal('错误', '没有有效的数据行'); return; }
    try {
        const response = await adminJsonRequest('/api/admin/batch-release', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({items})});
        if (!response) return;
        const {data: result} = response;
        document.getElementById('batchReleaseResult').innerHTML = `<div class="batch-result ${result.success ? 'success' : 'error'}">成功: ${result.success_count}/${items.length}</div>`;
        if (result.success_count > 0) await refreshAdminAfterMutation();
    } catch (e) {
        showModal('错误', '批量解约请求失败');
    }
}

async function batchConsume() {
    const data = document.getElementById('batchConsumeData').value.trim();
    if (!data) { showModal('错误', '请输入批量消费数据'); return; }
    const items = parseBatchLines(data, line => {
        const parts = line.split(',').map(p => p.trim());
        if (parts.length < 1) return null;
        return {uid: parseInt(parts[0]), ca_change: parseInt(parts[1]) || 0, pa_change: parseInt(parts[2]) || 0, notes: parts[3] || ''};
    });
    if (!items.length) { showModal('错误', '没有有效的数据行'); return; }
    try {
        const response = await adminJsonRequest('/api/admin/batch-consume', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({items})});
        if (!response) return;
        const {data: result} = response;
        document.getElementById('batchConsumeResult').innerHTML = `<div class="batch-result ${result.success ? 'success' : 'error'}">成功: ${result.success_count}/${items.length}</div>`;
        if (result.success_count > 0) await refreshAdminAfterMutation();
    } catch (e) {
        showModal('错误', '批量消费请求失败');
    }
}

async function runFormalImport() {
    const confirmed = await showConfirmDialog({title: '导入最新联赛名单', message: '系统会先备份数据库，再按严格模式同步联赛规则、球队和球员名单。', confirmLabel: '开始导入', danger: true});
    if (!confirmed) return;
    try {
        const result = await adminJsonRequest('/api/admin/import/formal', {method: 'POST'});
        if (!result) return;
        const {data} = result;
        lastFormalImportSummary = data;
        renderFormalImportSummaryCard();
        showModal(data.success ? '导入完成' : '导入未提交', formatFormalImportResult(data));
        await loadLatestFormalImportSummary();
        await loadOperationsAudit();
        if (data.success) {
            await refreshLeagueInfoDataset();
            await refreshPlayerDataset();
            await refreshTeamDataset();
            if (typeof loadAttributeVersionCatalog === 'function') {
                await loadAttributeVersionCatalog({force: true});
            }
            if (typeof refreshAttributeVersionBanner === 'function') {
                refreshAttributeVersionBanner();
            }
            loadSchemaBootstrapStatus();
            loadSeaPlayers();
            loadLogFile();
        }
    } catch (e) {
        showModal('错误', '正式导入请求失败');
    }
}

async function uploadAdminImportFile(kind) {
    const config = kind === 'attributes'
        ? {
            inputId: 'attributesImportFile',
            buttonId: 'attributesImportButton',
            endpoint: '/api/admin/import/upload/attributes',
            title: '球员数据库',
            confirmText: '确定上传并正式更新球员数据库吗？\n\n系统会先备份数据库，校验失败时不会提交任何属性变更。',
        }
        : {
            inputId: 'rosterImportFile',
            buttonId: 'rosterImportButton',
            endpoint: '/api/admin/import/upload/roster',
            title: '联赛名单',
            confirmText: '确定上传并正式更新联赛名单吗？\n\n这是全量同步操作，不在新文件中的旧名单球员会被移出当前名单。系统会先自动备份数据库。',
        };
    const input = document.getElementById(config.inputId);
    const file = input?.files?.[0];
    if (!file) {
        showModal('请选择文件', `请先选择要上传的${config.title}文件。`);
        return;
    }
    if (!await showConfirmDialog({title: `上传并更新${config.title}`, message: config.confirmText.replace(/^.*?\n\n/, ''), confirmLabel: '上传并更新', danger: true})) return;

    const button = document.getElementById(config.buttonId);
    if (button) button.disabled = true;
    const formData = new FormData();
    formData.append('file', file, file.name);
    try {
        const result = await adminJsonRequest(config.endpoint, {method: 'POST', body: formData});
        if (!result) return;
        const {response, data} = result;
        lastFormalImportSummary = data;
        renderFormalImportSummaryCard();
        showModal(response.ok && data.success ? '更新完成' : '更新未提交', formatFormalImportResult(data));
        await loadOperationsAudit();
        if (response.ok && data.success) {
            if (kind === 'attributes') {
                if (typeof loadAttributeVersionCatalog === 'function') await loadAttributeVersionCatalog({force: true});
                if (typeof refreshAttributeVersionBanner === 'function') refreshAttributeVersionBanner();
            } else {
                await refreshLeagueInfoDataset();
                await refreshPlayerDataset();
                await refreshTeamDataset();
                loadSeaPlayers();
            }
            if (input) input.value = '';
        }
    } catch (error) {
        showModal('上传失败', escapeHtml(error?.message || `${config.title}上传请求失败`));
    } finally {
        if (button) button.disabled = false;
    }
}

function formatScheduleImportResult(data) {
    const warningHtml = (data?.warnings || []).slice(0, 10).map(item => `<li>${escapeHtml(item)}</li>`).join('');
    return `
        <div class="maintenance-note">${escapeHtml(data?.message || '')}</div>
        ${data?.source_file ? `<div class="maintenance-note" style="margin-top:8px;"><strong>来源：</strong><code>${escapeHtml(data.source_file)}</code></div>` : ''}
        ${warningHtml ? `<div class="maintenance-note" style="margin-top:8px;"><strong>未匹配球队：</strong><ul style="margin:6px 0 0 18px;">${warningHtml}</ul></div>` : ''}
    `;
}

async function refreshAfterScheduleImport() {
    if (typeof competitionDataLoaded !== 'undefined') competitionDataLoaded = false;
    if (typeof loadCompetitionData === 'function') await loadCompetitionData({force: true});
    await loadWorkspaceDashboard({force: true});
}

async function uploadWorkspaceScheduleFile() {
    const input = document.getElementById('scheduleImportFile');
    const file = input?.files?.[0];
    if (!file) {
        showModal('请选择文件', '请先选择要上传的赛程 Excel。');
        return;
    }
    if (!await showConfirmDialog({title: '上传并更新赛程', message: `文件：${file.name}\n同一场比赛已录入的比分和状态会保留。`, confirmLabel: '上传并更新'})) return;
    const button = document.getElementById('scheduleImportButton');
    if (button) button.disabled = true;
    const formData = new FormData();
    formData.append('file', file, file.name);
    try {
        const result = await adminJsonRequest('/api/admin/matches/import/upload', {method: 'POST', body: formData});
        if (!result) return;
        const {response, data} = result;
        if (!response.ok || !data.success) {
            showModal('赛程更新失败', escapeHtml(data.detail || data.message || '上传或导入失败'));
            return;
        }
        if (input) input.value = '';
        await refreshAfterScheduleImport();
        showModal('赛程更新完成', formatScheduleImportResult(data));
    } catch (error) {
        showModal('上传失败', escapeHtml(error?.message || '赛程上传请求失败'));
    } finally {
        if (button) button.disabled = false;
    }
}

async function importWorkspaceLatestSchedule() {
    if (!await showConfirmDialog({title: '导入服务器最新赛程', message: '将读取 imports/schedules/ 下最新的赛程 Excel，同一场已录入比分会保留。', confirmLabel: '开始导入'})) return;
    const result = await adminJsonRequest('/api/admin/matches/import', {method: 'POST'});
    if (!result) return;
    const {response, data} = result;
    if (!response.ok || !data.success) {
        showModal('赛程导入失败', escapeHtml(data.detail || data.message || '导入失败'));
        return;
    }
    await refreshAfterScheduleImport();
    showModal('赛程导入完成', formatScheduleImportResult(data));
}

async function rebuildTeamStatCaches() {
    const confirmed = await showConfirmDialog({title: '全量重算球队统计', message: '将安全重算所有可见球队的缓存统计。', confirmLabel: '开始重算'});
    if (!confirmed) return;
    try {
        const result = await adminJsonRequest('/api/admin/team-stats/rebuild-cache', {method: 'POST'});
        if (!result) return;
        const {data} = result;
        if (data.success) {
            showSuccessToast(data.message || '球队统计已重算');
            await refreshTeamDataset();
            loadSchemaBootstrapStatus();
            loadOperationsAudit();
            loadLogFile();
        } else showModal('错误', data.detail || data.message || '球队统计重算失败');
    } catch (e) {
        showModal('错误', '安全全量重算请求失败');
    }
}

async function recalculateWages() {
    const confirmed = await showConfirmDialog({title: '全量工资重算', message: '将按当前规则重新计算全部球员工资与球队汇总。', confirmLabel: '开始重算'});
    if (!confirmed) return;
    try {
        const result = await adminJsonRequest('/api/admin/recalculate-wages', {method: 'POST'});
        if (!result) return;
        const {data} = result;
        if (data.success) {
            showSuccessToast(data.message || '工资已重算');
            await refreshPlayerDataset();
            await refreshTeamDataset();
            loadSchemaBootstrapStatus();
            loadOperationsAudit();
            loadLogFile();
        } else showModal('错误', data.detail || data.message || '工资重算失败');
    } catch (e) {
        showModal('错误', '工资重算请求失败');
    }
}

async function editTeam(teamName) {
    const adminData = await syncAdminAuthStatus({focusLogin: false});
    if (!adminData.authenticated) {
        showModal('提示', '请先登录管理员账户才能编辑球队信息');
        return;
    }
    const result = await adminJsonRequest(`/api/admin/team/${encodeURIComponent(teamName)}`);
    if (!result) return;
    const {data: team} = result;
    if (team.detail) {
        showModal('错误', team.detail);
        return;
    }
    const html = `
        <div class="form-group"><label>球队名</label><input type="text" id="editTeamName" value="${team.name}"></div>
        <div class="form-group"><label>主教练</label><input type="text" id="editTeamManager" value="${team.manager || ''}"></div>
        <div class="form-group"><label>球队工资帽（M）</label><input type="number" id="editTeamWageCap" min="0.1" max="100" step="0.01" value="${team.wage_cap ?? ''}" placeholder="留空则使用级别默认工资帽"><small>填写后覆盖该级别统一工资帽；留空保存可恢复默认值。</small></div>
        <div class="form-group"><label>备注</label><textarea id="editTeamNotes" style="min-height:80px;">${team.notes || ''}</textarea></div>
        <div style="margin-top:15px;"><button class="btn btn-primary" onclick="saveTeamInfo('${teamName}')">保存修改</button><button class="btn btn-secondary" onclick="closeModal()" style="margin-left:10px;">取消</button></div>
    `;
    showModal(`编辑球队: ${teamName}`, html);
}

async function saveTeamInfo(originalName) {
    const newName = document.getElementById('editTeamName').value.trim();
    const manager = document.getElementById('editTeamManager').value.trim();
    const wageCapRaw = document.getElementById('editTeamWageCap').value.trim();
    const wageCap = wageCapRaw === '' ? null : Number.parseFloat(wageCapRaw);
    const notes = document.getElementById('editTeamNotes').value.trim();
    if (!newName) { showModal('错误', '球队名不能为空'); return; }
    if (wageCap !== null && (!Number.isFinite(wageCap) || wageCap <= 0 || wageCap > 100)) { showModal('错误', '球队工资帽必须大于 0 且不超过 100M'); return; }
    try {
        const result = await adminJsonRequest('/api/admin/team/update', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({team_name: originalName, name: newName !== originalName ? newName : null, manager, wage_cap: wageCap, notes}),
        });
        if (!result) return;
        const {data} = result;
        if (data.success) {
            closeModal();
            showSuccessToast(data.message || '球队信息已保存');
            await refreshTeamDataset();
        } else {
            showModal('错误', data.detail || '保存失败');
        }
    } catch (e) {
        showModal('错误', '保存请求失败');
    }
}

async function updateTeamField(originalName, field, value) {
    const requestBody = {team_name: originalName};
    if (field === 'name') requestBody.name = value;
    if (field === 'manager') requestBody.manager = value;
    if (field === 'level') requestBody.level = value;
    if (field === 'wage_cap') {
        const wageCap = Number.parseFloat(value);
        if (!Number.isFinite(wageCap) || wageCap <= 0 || wageCap > 100) {
            showModal('错误', '球队工资帽必须大于 0 且不超过 100M');
            await refreshTeamDataset();
            return;
        }
        requestBody.wage_cap = wageCap;
    }
    try {
        const result = await adminJsonRequest('/api/admin/team/update', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(requestBody)});
        if (!result) return;
        const {data} = result;
        if (data.success) {
            await refreshTeamDataset();
        } else {
            showModal('错误', data.detail || '更新失败');
        }
    } catch (e) {
        showModal('错误', '更新请求失败');
    }
}

async function updatePlayerField(uid, field, value) {
    const requestBody = {uid};
    if (field === 'name') requestBody.name = value;
    if (field === 'position') requestBody.position = value;
    if (field === 'nationality') requestBody.nationality = value;
    if (['age', 'ca', 'pa'].includes(field)) {
        const parsedValue = Number.parseInt(value, 10);
        const minimum = field === 'pa' ? -10 : 1;
        if (!Number.isInteger(parsedValue) || parsedValue < minimum || parsedValue > 200) {
            showModal('错误', `${field.toUpperCase()} 必须是 ${minimum} 到 200 之间的整数`);
            await refreshPlayerDataset();
            return;
        }
        requestBody[field] = parsedValue;
    }
    try {
        const result = await adminJsonRequest('/api/admin/player/update', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(requestBody)});
        if (!result) return;
        const {data} = result;
        if (data.success) {
            await refreshPlayerDataset();
            await refreshTeamDataset();
        } else {
            showModal('错误', data.detail || '更新失败');
        }
    } catch (e) {
        await refreshPlayerDataset();
        showModal('错误', '更新请求失败');
    }
}

async function updatePlayerUidConfirm(oldUid, newUid, inputElement) {
    if (oldUid == newUid) return;
    const confirmed = await showConfirmDialog({title: '修改球员 UID', message: `UID 将从 ${oldUid} 修改为 ${newUid}，请确认目标 UID 无误。`, confirmLabel: '确认修改', danger: true});
    if (!confirmed) {
        inputElement.value = oldUid;
        return;
    }
    await updatePlayerUid(oldUid, newUid);
}

async function updatePlayerUid(oldUid, newUid) {
    if (oldUid == newUid) return;
    try {
        const result = await adminJsonRequest('/api/admin/player/update-uid', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({old_uid: parseInt(oldUid), new_uid: parseInt(newUid)})});
        if (!result) return;
        const {data} = result;
        if (data.success) {
            await refreshPlayerDataset();
            showSuccessToast(`UID 已从 ${oldUid} 更新为 ${newUid}`);
        } else {
            showModal('错误', data.detail || '更新 UID 失败');
            await refreshPlayerDataset();
        }
    } catch (e) {
        showModal('错误', '更新 UID 请求失败');
        await refreshPlayerDataset();
    }
}
