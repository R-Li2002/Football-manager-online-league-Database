let pendingUndoLogId = null;
const ADMIN_UNAUTHORIZED_ERROR = 'ADMIN_UNAUTHORIZED';
let lastAdminUnauthorizedNoticeAt = 0;

function isAdminUnauthorizedError(error) {
    return error?.code === ADMIN_UNAUTHORIZED_ERROR || error?.message === ADMIN_UNAUTHORIZED_ERROR;
}

function enterAdminLoggedOutState(options = {}) {
    isAdmin = false;
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
    const response = await fetch(url, {
        credentials: 'same-origin',
        ...fetchOptions,
    });
    if (response.status === 401) {
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
    const response = await fetch('/api/admin/check', {credentials: 'same-origin'});
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    isAdmin = Boolean(data.authenticated);
    syncAdminTabVisibility();
    syncAdminPanelVisibility({
        focusLogin: options.focusLogin !== false && !isAdmin,
    });
    return data;
}

function syncAdminTabVisibility() {
    const adminTab = document.getElementById('adminTab');
    if (!adminTab) return;
    adminTab.classList.toggle('hidden-tab', !(isAdmin || adminEntryUnlocked));
}

function syncAdminPanelVisibility(options = {}) {
    const loginSection = document.getElementById('adminLogin');
    const adminPanel = document.getElementById('adminPanel');
    if (!loginSection || !adminPanel) return;

    if (isAdmin) {
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
    syncAdminPanelVisibility();
    updateStats();
    renderFormalImportSummaryCard();
    renderSchemaBootstrapStatusCard();
    renderOperationsAuditCard();
    renderTeamStatSourceDebugView();
    populateAdminSelects();
    loadSchemaBootstrapStatus();
    loadLatestFormalImportSummary();
    loadOperationsAudit();
    loadSeaPlayers();
    loadTransferLogs();
    loadLogFile();
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
        <div class="maintenance-note" style="margin-top:8px;"><strong>Attributes CSV：</strong><code>${escapeHtml(data.attributes_csv_path || '')}</code></div>
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
        const res = await fetch('/api/admin/login', {
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
            showAdminTab();
            showTab('admin', null, {syncHistory: false});
            renderTeamsTable();
            renderTeamStatSourceDebugView();
            renderPlayers(currentPlayers);
            showModal('成功', `欢迎，${data.username}！`);
        }
    } catch (e) {
        if (isAdminUnauthorizedError(e)) return;
        console.error('登录错误:', e);
        showModal('错误', '登录请求失败');
    }
}

async function adminLogout() {
    try {
        await fetch('/api/admin/logout', {method: 'POST', credentials: 'same-origin'});
    } catch (e) {
        console.error('登出错误:', e);
    }
    enterAdminLoggedOutState({focusLogin: false, activateAdminTab: false});
    showTab('players');
}

function populateAdminSelects() {
    const selects = ['transferTeam'];
    selects.forEach(id => {
        const select = document.getElementById(id);
        if (!select) return;
        select.innerHTML = '<option value="">选择球队</option>';
        teams.forEach(t => {
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
    const html = `<table><thead><tr><th>UID</th><th>姓名</th><th>年龄</th><th>CA</th><th>PA</th><th>位置</th><th>国籍</th></tr></thead><tbody>${players.map(p => `<tr><td>${p.uid}</td><td>${p.name}</td><td>${p.age}</td><td>${p.ca}</td><td>${p.pa}</td><td>${p.position}</td><td title="${escapeHtml(p.nationality || '-')}">${escapeHtml(formatCompactNationality(p.nationality, {maxLength: 16}))}</td></tr>`).join('')}</tbody></table>`;
    document.getElementById('seaPlayersTable').innerHTML = html;
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
            showModal('成功', data.message);
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
        showModal(data.success ? '成功' : '错误', data.message || data.detail);
        if (data.success) {
            document.getElementById('transferUid').value = '';
            document.getElementById('transferNotes').value = '';
            await refreshAdminAfterMutation();
        }
    } catch (e) {
        showModal('错误', '交易请求失败');
    }
}

async function releasePlayer() {
    const uid = parseInt(document.getElementById('releaseUid').value);
    const notes = document.getElementById('releaseNotes').value;
    if (!uid) { showModal('错误', '请填写球员UID'); return; }
    try {
        const result = await adminJsonRequest('/api/admin/release', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({player_uid: uid, to_team: '85大海', notes})});
        if (!result) return;
        const {data} = result;
        showModal(data.success ? '成功' : '错误', data.message || data.detail);
        if (data.success) {
            document.getElementById('releaseUid').value = '';
            document.getElementById('releaseNotes').value = '';
            await refreshAdminAfterMutation();
        }
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
        showModal(data.success ? '成功' : '错误', data.message || data.detail);
        if (data.success) {
            document.getElementById('consumeUid').value = '';
            document.getElementById('consumeCa').value = '';
            document.getElementById('consumePa').value = '';
            await refreshAdminAfterMutation();
        }
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
    const confirmed = confirm('确定要执行正式导入吗？\n\n这会按严格模式读取最新的 HEIGO Excel 和球员属性 CSV/XLSX，先自动备份当前数据库，再正式写入联赛规则、球队、球员和属性库。球员属性会按版本并存。');
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

async function rebuildTeamStatCaches() {
    const confirmed = confirm('确定要安全全量重算所有可见球队的缓存统计吗？');
    if (!confirmed) return;
    try {
        const result = await adminJsonRequest('/api/admin/team-stats/rebuild-cache', {method: 'POST'});
        if (!result) return;
        const {data} = result;
        showModal(data.success ? '成功' : '错误', data.message || data.detail);
        if (data.success) {
            await refreshTeamDataset();
            loadSchemaBootstrapStatus();
            loadOperationsAudit();
            loadLogFile();
        }
    } catch (e) {
        showModal('错误', '安全全量重算请求失败');
    }
}

async function recalculateWages() {
    const confirmed = confirm('确定要执行全量工资重算吗？');
    if (!confirmed) return;
    try {
        const result = await adminJsonRequest('/api/admin/recalculate-wages', {method: 'POST'});
        if (!result) return;
        const {data} = result;
        showModal(data.success ? '成功' : '错误', data.message || data.detail);
        if (data.success) {
            await refreshPlayerDataset();
            await refreshTeamDataset();
            loadSchemaBootstrapStatus();
            loadOperationsAudit();
            loadLogFile();
        }
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
        <div class="form-group"><label>备注</label><textarea id="editTeamNotes" style="min-height:80px;">${team.notes || ''}</textarea></div>
        <div style="margin-top:15px;"><button class="btn btn-primary" onclick="saveTeamInfo('${teamName}')">保存修改</button><button class="btn btn-secondary" onclick="closeModal()" style="margin-left:10px;">取消</button></div>
    `;
    showModal(`编辑球队: ${teamName}`, html);
}

async function saveTeamInfo(originalName) {
    const newName = document.getElementById('editTeamName').value.trim();
    const manager = document.getElementById('editTeamManager').value.trim();
    const notes = document.getElementById('editTeamNotes').value.trim();
    if (!newName) { showModal('错误', '球队名不能为空'); return; }
    try {
        const result = await adminJsonRequest('/api/admin/team/update', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({team_name: originalName, name: newName !== originalName ? newName : null, manager, notes}),
        });
        if (!result) return;
        const {data} = result;
        if (data.success) {
            closeModal();
            showModal('成功', data.message);
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
    if (field === 'age') requestBody.age = parseInt(value);
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
        showModal('错误', '更新请求失败');
    }
}

async function updatePlayerUidConfirm(oldUid, newUid, inputElement) {
    if (oldUid == newUid) return;
    const confirmed = confirm(`确认修改 UID？\n\n从 ${oldUid} 修改为 ${newUid}`);
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
            showModal('成功', `UID 已从 ${oldUid} 更新为 ${newUid}`);
        } else {
            showModal('错误', data.detail || '更新 UID 失败');
            await refreshPlayerDataset();
        }
    } catch (e) {
        showModal('错误', '更新 UID 请求失败');
        await refreshPlayerDataset();
    }
}
