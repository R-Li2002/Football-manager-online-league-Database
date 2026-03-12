function hideTeamStatSourceDebugView() {
    const panel = document.getElementById('teamStatDebugPanel');
    const content = document.getElementById('teamStatDebugContent');
    const select = document.getElementById('teamStatDebugSelect');
    if (!panel || !content || !select) return;
    panel.style.display = 'none';
    select.innerHTML = '';
    content.innerHTML = '<div class="loading">等待管理员登录...</div>';
}

function populateTeamStatDebugSelect() {
    const select = document.getElementById('teamStatDebugSelect');
    if (!select) return;
    const previousValue = select.value;
    select.innerHTML = '';
    teams.forEach(team => {
        const option = document.createElement('option');
        option.value = team.name;
        option.textContent = `${team.name} (${team.level})`;
        select.appendChild(option);
    });
    if (teams.some(team => team.name === previousValue)) {
        select.value = previousValue;
    }
}

function formatDebugStatValue(value) {
    if (value === null || value === undefined || value === '') return '-';
    if (typeof value === 'number') {
        return Number.isInteger(value) ? String(value) : value.toFixed(3);
    }
    return String(value);
}

function formatDebugTime(value) {
    if (!value) return '未记录';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return String(value);
    return parsed.toLocaleString();
}

function renderTeamStatSourceDebugView() {
    const panel = document.getElementById('teamStatDebugPanel');
    const content = document.getElementById('teamStatDebugContent');
    const select = document.getElementById('teamStatDebugSelect');
    if (!panel || !content || !select) return;

    if (!isAdmin) {
        hideTeamStatSourceDebugView();
        return;
    }

    panel.style.display = 'block';

    if (teams.length === 0) {
        select.innerHTML = '';
        content.innerHTML = '<div class="no-data">当前没有可显示的球队调试数据。</div>';
        return;
    }

    const statSources = teams.find(team => team.stat_sources)?.stat_sources;
    if (!statSources) {
        select.innerHTML = '';
        content.innerHTML = '<div class="no-data">当前接口没有返回 stat_sources 调试信息。</div>';
        return;
    }

    populateTeamStatDebugSelect();
    const selectedTeam = teams.find(team => team.name === select.value) || teams[0];
    const selectedStatSources = selectedTeam.stat_sources || statSources;
    const cachedFields = selectedStatSources.cached_fields || [];
    const realtimeFields = selectedStatSources.realtime_fields || [];
    const refreshState = selectedStatSources.refresh_state || {};
    const orderedFields = [...cachedFields, ...realtimeFields];
    const fieldRows = orderedFields.map(fieldName => {
        const mode = selectedStatSources.field_modes?.[fieldName] || 'cached';
        const modeLabel = mode === 'realtime' ? '实时聚合' : '持久缓存';
        return `<tr><td><code>${fieldName}</code></td><td><span class="source-badge ${mode}">${modeLabel}</span></td><td>${formatDebugStatValue(selectedTeam[fieldName])}</td></tr>`;
    }).join('');
    const renderFieldChips = (fieldNames, mode) => fieldNames.length
        ? fieldNames.map(fieldName => `<span class="field-chip ${mode}">${fieldName}</span>`).join('')
        : `<span class="field-chip ${mode}">无</span>`;

    content.innerHTML = `
        <div class="team-debug-grid">
            <div class="team-debug-card">
                <h4>持久缓存字段</h4>
                <div class="field-chip-list">${renderFieldChips(cachedFields, 'cached')}</div>
            </div>
            <div class="team-debug-card">
                <h4>实时聚合字段</h4>
                <div class="field-chip-list">${renderFieldChips(realtimeFields, 'realtime')}</div>
            </div>
            <div class="team-debug-card">
                <h4>刷新元数据</h4>
                <div class="team-debug-summary">
                    <span class="source-badge cached">${refreshState.cached_read_label || '缓存命中'}</span>
                    <span class="source-badge realtime">${refreshState.realtime_read_label || '实时覆盖'}</span>
                    <span class="field-chip cached">${refreshState.last_cache_refresh_label || '历史缓存状态未记录'}</span>
                </div>
                <div class="team-debug-detail">
                    <div><strong>最近一次缓存刷新:</strong> ${refreshState.last_cache_refresh_summary || '未记录'}</div>
                    <div><strong>刷新时间:</strong> ${formatDebugTime(refreshState.last_cache_refresh_at)}</div>
                    <div><strong>刷新范围:</strong> ${(refreshState.last_cache_refresh_scopes || []).length ? refreshState.last_cache_refresh_scopes.join(', ') : '未记录'}</div>
                </div>
            </div>
        </div>
        <div class="table-container team-debug-table">
            <table>
                <thead>
                    <tr><th>字段</th><th>来源</th><th>${selectedTeam.name} 示例值</th></tr>
                </thead>
                <tbody>${fieldRows}</tbody>
            </table>
        </div>
    `;
}

function renderOverview() {
    const basic = leagueInfo.filter(i => i.category === '基本信息');
    const stats = leagueInfo.filter(i => i.category === '统计');
    const wage = leagueInfo.filter(i => i.category === '工资系数');
    document.getElementById('basicInfo').innerHTML = basic.map(item => `<div class="info-card"><div class="label">${item.key}</div><div class="value">${item.value}</div></div>`).join('');
    document.getElementById('statsInfo').innerHTML = stats.map(item => `<div class="info-card"><div class="label">${item.key}</div><div class="value">${item.value}</div></div>`).join('');
    document.getElementById('wageInfo').innerHTML = wage.map(item => `<div class="info-card"><div class="label">${item.key}</div><div class="value">${item.value}</div></div>`).join('');
    renderOverviewStatusCards();
}

function renderOverviewStatusCards() {
    const updateContainer = document.getElementById('overviewUpdateStatus');
    const opsContainer = document.getElementById('overviewOpsSummary');
    if (!updateContainer || !opsContainer) return;

    const refreshTimes = teams
        .map(team => (team.stat_sources || {}).refresh_state || {})
        .map(state => state.last_cache_refresh_at)
        .filter(Boolean)
        .map(time => new Date(time))
        .filter(date => !Number.isNaN(date.getTime()))
        .sort((a, b) => b.getTime() - a.getTime());

    const latestRefresh = refreshTimes.length ? refreshTimes[0].toLocaleString() : '暂无记录';
    const refreshCoveredTeams = teams.filter(team => {
        const state = (team.stat_sources || {}).refresh_state || {};
        return Boolean(state.last_cache_refresh_at);
    }).length;

    updateContainer.innerHTML = [
        `<div class="info-card"><div class="label">最近缓存刷新时间</div><div class="value">${escapeHtml(latestRefresh)}</div></div>`,
        `<div class="info-card"><div class="label">已记录刷新球队数</div><div class="value">${refreshCoveredTeams} / ${teams.length}</div></div>`,
        `<div class="info-card"><div class="label">当前查询模式</div><div class="value">${isAdmin ? '管理员含维护能力' : '公开查询模式'}</div></div>`,
    ].join('');

    const latestAudit = Array.isArray(recentOperationAudits) && recentOperationAudits.length ? recentOperationAudits[0] : null;
    const latestImport = lastFormalImportSummary;
    opsContainer.innerHTML = [
        `<div class="info-card"><div class="label">最近维护动作</div><div class="value">${latestAudit ? escapeHtml(latestAudit.operation_label || latestAudit.action || '未知动作') : '暂无记录'}</div></div>`,
        `<div class="info-card"><div class="label">最近维护时间</div><div class="value">${latestAudit ? escapeHtml(latestAudit.created_at || '-') : '-'}</div></div>`,
        `<div class="info-card"><div class="label">最近正式导入</div><div class="value">${latestImport ? escapeHtml(latestImport.executed_at || latestImport.started_at || '已执行') : '暂无记录'}</div></div>`,
    ].join('');
}

function sortTeams() {
    const field = document.getElementById('teamSortField').value;
    const order = document.getElementById('teamSortOrder').value;
    if (!field) { renderTeamsTable(); return; }
    let sorted = [...teams];
    sorted.sort((a, b) => {
        let va = a[field] || 0;
        let vb = b[field] || 0;
        return order === 'asc' ? va - vb : vb - va;
    });
    renderTeamsTableWithData(sorted);
}

function renderTeamsTable() { renderTeamsTableWithData(teams); }

function renderTeamsTableWithData(data) {
    const levelWageCap = {'超级': 9.4, '甲级': 8.9, '乙级': 8.6};
    const levelMinWage = {'超级': 8.0, '甲级': 7.5, '乙级': 6.5};
    const html = `<table><thead><tr><th>级别</th><th>球队名</th><th>主教</th><th>人数</th><th>门将</th><th>球员总工资</th><th>额外工资</th><th>最终工资</th><th>工资帽</th><th>8M</th><th>7M</th><th>伪名</th><th>总身价</th><th>平均CA</th><th>平均PA</th><th>成长</th><th>备注</th></tr></thead><tbody>${data.map(t => {
        const baseWageCap = levelWageCap[t.level] || 0;
        const minWage = levelMinWage[t.level] || 0;
        const extraCap = (t.notes && t.notes.includes('+0.1M')) ? 0.1 : 0;
        const effectiveCap = baseWageCap + extraCap;

        const playerTotalWage = t.wage || 0;
        const extraWage = t.extra_wage || 0;
        const totalWage = playerTotalWage + extraWage;

        let finalWageDisplay = '';
        let wageClass = '';

        if (totalWage < minWage) {
            finalWageDisplay = `${minWage.toFixed(3)}M (底线)`;
            wageClass = 'compliant';
        } else if (totalWage <= effectiveCap) {
            finalWageDisplay = `${totalWage.toFixed(3)}M`;
            wageClass = 'compliant';
        } else {
            const overflow = totalWage - effectiveCap;
            if (overflow > 0.3) {
                finalWageDisplay = `<span style="color:#e74c3c;font-weight:bold;">拍卖！</span>`;
                wageClass = 'non-compliant';
            } else {
                const penaltyWage = overflow * 10 + playerTotalWage;
                const finalWage = Math.max(totalWage, penaltyWage);
                finalWageDisplay = `<span style="color:#f39c12;">${finalWage.toFixed(3)}M (惩罚)</span>`;
                wageClass = 'non-compliant';
            }
        }

        const sizeCompliant = t.team_size >= 16 && t.team_size <= 20;
        const gkCompliant = t.gk_count === 2;
        const sizeClass = sizeCompliant ? 'compliant' : 'non-compliant';
        const gkClass = gkCompliant ? 'compliant' : 'non-compliant';
        const notesDisplay = t.notes || '-';
        const notesClass = (t.notes && t.notes.includes('+0.1M')) ? 'notes-cell has-extra' : 'notes-cell';
        const capDisplay = extraCap > 0 ? `${baseWageCap.toFixed(1)}M (+${extraCap.toFixed(1)}M)` : `${baseWageCap.toFixed(1)}M`;
        const playerWageDisplay = `${playerTotalWage.toFixed(3)}M`;
        const extraWageDisplay = extraWage > 0 ? `${extraWage.toFixed(3)}M` : '-';

        if (isAdmin) {
            const levelCell = `<td><select class="editable-input" onchange="updateTeamField('${t.name.replace(/'/g, "\\'")}', 'level', this.value)" style="background:rgba(0,0,0,0.2);border:1px solid rgba(0,217,255,0.3);padding:4px 8px;border-radius:4px;color:#fff;"><option value="超级" ${t.level === '超级' ? 'selected' : ''}>超级</option><option value="甲级" ${t.level === '甲级' ? 'selected' : ''}>甲级</option><option value="乙级" ${t.level === '乙级' ? 'selected' : ''}>乙级</option></select></td>`;
            const teamNameCell = `<td><input type="text" class="editable-input" value="${t.name.replace(/"/g, '&quot;')}" onchange="updateTeamField('${t.name.replace(/'/g, "\\'")}', 'name', this.value)" style="background:rgba(0,0,0,0.2);border:1px solid rgba(0,217,255,0.3);padding:4px 8px;border-radius:4px;color:#fff;width:150px;"></td>`;
            const managerCell = `<td><input type="text" class="editable-input" value="${(t.manager || '').replace(/"/g, '&quot;')}" onchange="updateTeamField('${t.name.replace(/'/g, "\\'")}', 'manager', this.value)" style="background:rgba(0,0,0,0.2);border:1px solid rgba(0,217,255,0.3);padding:4px 8px;border-radius:4px;color:#fff;width:100px;"></td>`;
            return `<tr>${levelCell}${teamNameCell}${managerCell}<td class="${sizeClass}">${t.team_size}</td><td class="${gkClass}">${t.gk_count}</td><td>${playerWageDisplay}</td><td>${extraWageDisplay}</td><td class="${wageClass}">${finalWageDisplay}</td><td>${capDisplay}</td><td>${t.count_8m}</td><td>${t.count_7m}</td><td>${t.count_fake}</td><td>${t.total_value.toFixed(1)}M</td><td>${t.avg_ca.toFixed(1)}</td><td>${t.avg_pa.toFixed(1)}</td><td>${t.total_growth}</td><td class="${notesClass}" title="${notesDisplay.replace(/"/g, '&quot;')}">${notesDisplay}</td></tr>`;
        }
        return `<tr><td>${getLevelBadge(t.level)}</td><td><span class="team-name" onclick="viewTeamPlayers('${t.name.replace(/'/g, "\\'")}')">${t.name}</span></td><td>${t.manager || '-'}</td><td class="${sizeClass}">${t.team_size}</td><td class="${gkClass}">${t.gk_count}</td><td>${playerWageDisplay}</td><td>${extraWageDisplay}</td><td class="${wageClass}">${finalWageDisplay}</td><td>${capDisplay}</td><td>${t.count_8m}</td><td>${t.count_7m}</td><td>${t.count_fake}</td><td>${t.total_value.toFixed(1)}M</td><td>${t.avg_ca.toFixed(1)}</td><td>${t.avg_pa.toFixed(1)}</td><td>${t.total_growth}</td><td class="${notesClass}" title="${notesDisplay.replace(/"/g, '&quot;')}">${notesDisplay}</td></tr>`;
    }).join('')}</tbody></table>`;
    document.getElementById('teamsTable').innerHTML = html;
}

function getLevelBadge(level) {
    const classes = {'超级': 'level-super', '甲级': 'level-a', '乙级': 'level-b'};
    return `<span class="level-badge ${classes[level] || ''}">${level || '未知'}</span>`;
}

function viewTeamPlayers(teamName) {
    showTab('players');
    document.getElementById('teamSelect').value = teamName;
    document.getElementById('playerSearch').value = '';
    searchPlayers();
}

function populateTeamSelect() {
    ['teamSelect'].forEach(id => {
        const select = document.getElementById(id);
        if (!select) return;
        const previousValue = select.value;
        select.innerHTML = '<option value="">-- 全部球队 --</option>';
        teams.forEach(team => {
            const option = document.createElement('option');
            option.value = team.name;
            option.textContent = `${team.name} (${team.level})`;
            select.appendChild(option);
        });
        if (teams.some(team => team.name === previousValue)) {
            select.value = previousValue;
        }
    });
}