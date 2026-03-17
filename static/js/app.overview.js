var currentOverviewSort = {field: '', order: '', type: 'number'};
var overviewMetaExpanded = false;

const TEAM_SORT_CONFIG = {
    level: {label: '级别', type: 'text'},
    name: {label: '球队名', type: 'text'},
    manager: {label: '主教', type: 'text'},
    team_size: {label: '人数', type: 'number'},
    gk_count: {label: '门将', type: 'number'},
    wage: {label: '球员总工资', type: 'number'},
    extra_wage: {label: '额外工资', type: 'number'},
    final_wage: {label: '最终工资', type: 'number'},
    count_8m: {label: '8M', type: 'number'},
    count_7m: {label: '7M', type: 'number'},
    count_fake: {label: '伪名', type: 'number'},
    total_value: {label: '总身价', type: 'number'},
    avg_ca: {label: '平均CA', type: 'number'},
    avg_pa: {label: '平均PA', type: 'number'},
    total_growth: {label: '成长', type: 'number'},
    notes: {label: '备注', type: 'text'},
};

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

    if (!teams.length) {
        select.innerHTML = '';
        content.innerHTML = '<div class="no-data">当前没有可展示的球队调试数据。</div>';
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

function toggleOverviewMetaPanel() {
    overviewMetaExpanded = !overviewMetaExpanded;
    syncOverviewMetaPanelState();
    if (typeof syncAppHistory === 'function') {
        syncAppHistory('replace');
    }
}

function syncOverviewMetaPanelState() {
    const panel = document.getElementById('overviewMetaExpandedContent');
    const button = document.getElementById('overviewMetaToggle');
    if (!panel || !button) return;
    panel.classList.toggle('is-collapsed', !overviewMetaExpanded);
    button.textContent = overviewMetaExpanded ? '收起详细信息' : '展开详细信息';
    button.setAttribute('aria-expanded', overviewMetaExpanded ? 'true' : 'false');
}

function buildOverviewInfoCard(item) {
    return `<div class="info-card"><div class="label">${item.key}</div><div class="value">${item.value}</div></div>`;
}

function renderOverview() {
    const basic = leagueInfo.filter(item => item.category === '基本信息');
    const stats = leagueInfo.filter(item => item.category === '统计');
    const wage = leagueInfo.filter(item => item.category === '工资系数');
    const rosterSummary = [
        {key: '球队数量', value: teams.length},
        {key: '球员总数', value: allPlayers.length},
    ];
    const basicCards = [...basic, ...rosterSummary];

    const basicInfo = document.getElementById('basicInfo');
    const statsInfo = document.getElementById('statsInfo');
    const wageInfo = document.getElementById('wageInfo');
    if (basicInfo) {
        basicInfo.innerHTML = basicCards.map(buildOverviewInfoCard).join('');
    }
    if (statsInfo) {
        statsInfo.innerHTML = stats.map(buildOverviewInfoCard).join('');
    }
    if (wageInfo) {
        wageInfo.innerHTML = wage.map(buildOverviewInfoCard).join('');
    }

    renderOverviewStatusCards();
    syncOverviewMetaPanelState();
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

function getDefaultSortOrder(type) {
    return type === 'text' ? 'asc' : 'desc';
}

function compareTableValues(left, right, type, order) {
    if (type === 'text') {
        const lhs = String(left || '').trim();
        const rhs = String(right || '').trim();
        const result = lhs.localeCompare(rhs, ['en', 'zh-CN'], {numeric: true, sensitivity: 'base'});
        return order === 'asc' ? result : -result;
    }

    const lhs = Number(left || 0);
    const rhs = Number(right || 0);
    return order === 'asc' ? lhs - rhs : rhs - lhs;
}

function getSortedTeams(data) {
    if (!currentOverviewSort.field) return [...data];
    const {field, order, type} = currentOverviewSort;
    const sorted = [...data];
    sorted.sort((left, right) => compareTableValues(left[field], right[field], type, order));
    return sorted;
}

function toggleTeamSort(field) {
    const config = TEAM_SORT_CONFIG[field] || {type: 'text'};
    if (currentOverviewSort.field === field) {
        currentOverviewSort.order = currentOverviewSort.order === 'asc' ? 'desc' : 'asc';
    } else {
        currentOverviewSort = {
            field,
            type: config.type,
            order: getDefaultSortOrder(config.type),
        };
    }
    renderTeamsTable();
    if (typeof syncAppHistory === 'function') {
        syncAppHistory('replace');
    }
}

function getTeamSortIndicator(field) {
    if (currentOverviewSort.field !== field) return '<span class="sort-indicator">↕</span>';
    return `<span class="sort-indicator is-active">${currentOverviewSort.order === 'asc' ? '↑' : '↓'}</span>`;
}

function renderTeamHeader(label, field) {
    return `<th class="sortable-header" role="button" tabindex="0" onclick="toggleTeamSort('${field}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();toggleTeamSort('${field}');}"><span class="sortable-label">${label}</span>${getTeamSortIndicator(field)}</th>`;
}

function sortTeams() {
    renderTeamsTable();
}

function renderTeamsTable() {
    renderTeamsTableWithData(teams);
}

function renderTeamsTableWithData(data) {
    const levelWageCap = {'超级': 9.4, '甲级': 8.9, '乙级': 8.6};
    const levelMinWage = {'超级': 8.0, '甲级': 7.5, '乙级': 6.5};
    const sortedData = getSortedTeams(data);
    const html = `<table><thead><tr>${renderTeamHeader('级别', 'level')}${renderTeamHeader('球队名', 'name')}${renderTeamHeader('主教', 'manager')}${renderTeamHeader('人数', 'team_size')}${renderTeamHeader('门将', 'gk_count')}${renderTeamHeader('球员总工资', 'wage')}${renderTeamHeader('额外工资', 'extra_wage')}${renderTeamHeader('最终工资', 'final_wage')}<th>工资帽</th>${renderTeamHeader('8M', 'count_8m')}${renderTeamHeader('7M', 'count_7m')}${renderTeamHeader('伪名', 'count_fake')}${renderTeamHeader('总身价', 'total_value')}${renderTeamHeader('平均CA', 'avg_ca')}${renderTeamHeader('平均PA', 'avg_pa')}${renderTeamHeader('成长', 'total_growth')}${renderTeamHeader('备注', 'notes')}</tr></thead><tbody>${sortedData.map(team => {
        const baseWageCap = levelWageCap[team.level] || 0;
        const minWage = levelMinWage[team.level] || 0;
        const extraCap = team.notes && team.notes.includes('+0.1M') ? 0.1 : 0;
        const effectiveCap = baseWageCap + extraCap;

        const playerTotalWage = team.wage || 0;
        const extraWage = team.extra_wage || 0;
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
                finalWageDisplay = '<span style="color:#e74c3c;font-weight:bold;">拍卖</span>';
                wageClass = 'non-compliant';
            } else {
                const penaltyWage = overflow * 10 + playerTotalWage;
                const finalWage = Math.max(totalWage, penaltyWage);
                finalWageDisplay = `<span style="color:#f39c12;">${finalWage.toFixed(3)}M (惩罚)</span>`;
                wageClass = 'non-compliant';
            }
        }

        const sizeCompliant = team.team_size >= 16 && team.team_size <= 20;
        const gkCompliant = team.gk_count === 2;
        const sizeClass = sizeCompliant ? 'compliant' : 'non-compliant';
        const gkClass = gkCompliant ? 'compliant' : 'non-compliant';
        const notesDisplay = team.notes || '-';
        const notesClass = team.notes && team.notes.includes('+0.1M') ? 'notes-cell has-extra' : 'notes-cell';
        const capDisplay = extraCap > 0 ? `${baseWageCap.toFixed(1)}M (+${extraCap.toFixed(1)}M)` : `${baseWageCap.toFixed(1)}M`;
        const playerWageDisplay = `${playerTotalWage.toFixed(3)}M`;
        const extraWageDisplay = extraWage > 0 ? `${extraWage.toFixed(3)}M` : '-';

        if (isAdmin) {
            const levelCell = `<td><select class="editable-input" onchange="updateTeamField('${team.name.replace(/'/g, "\\'")}', 'level', this.value)" style="background:rgba(0,0,0,0.2);border:1px solid rgba(0,217,255,0.3);padding:4px 8px;border-radius:4px;color:#fff;"><option value="超级" ${team.level === '超级' ? 'selected' : ''}>超级</option><option value="甲级" ${team.level === '甲级' ? 'selected' : ''}>甲级</option><option value="乙级" ${team.level === '乙级' ? 'selected' : ''}>乙级</option></select></td>`;
            const teamNameCell = `<td><input type="text" class="editable-input" value="${team.name.replace(/"/g, '&quot;')}" onchange="updateTeamField('${team.name.replace(/'/g, "\\'")}', 'name', this.value)" style="background:rgba(0,0,0,0.2);border:1px solid rgba(0,217,255,0.3);padding:4px 8px;border-radius:4px;color:#fff;width:150px;"></td>`;
            const managerCell = `<td><input type="text" class="editable-input" value="${(team.manager || '').replace(/"/g, '&quot;')}" onchange="updateTeamField('${team.name.replace(/'/g, "\\'")}', 'manager', this.value)" style="background:rgba(0,0,0,0.2);border:1px solid rgba(0,217,255,0.3);padding:4px 8px;border-radius:4px;color:#fff;width:100px;"></td>`;
            return `<tr>${levelCell}${teamNameCell}${managerCell}<td class="${sizeClass}">${team.team_size}</td><td class="${gkClass}">${team.gk_count}</td><td>${playerWageDisplay}</td><td>${extraWageDisplay}</td><td class="${wageClass}">${finalWageDisplay}</td><td>${capDisplay}</td><td>${team.count_8m}</td><td>${team.count_7m}</td><td>${team.count_fake}</td><td>${team.total_value.toFixed(1)}M</td><td>${team.avg_ca.toFixed(1)}</td><td>${team.avg_pa.toFixed(1)}</td><td>${team.total_growth}</td><td class="${notesClass}" title="${notesDisplay.replace(/"/g, '&quot;')}">${notesDisplay}</td></tr>`;
        }

        return `<tr><td>${getLevelBadge(team.level)}</td><td><span class="team-name" onclick="viewTeamPlayers('${team.name.replace(/'/g, "\\'")}')">${team.name}</span></td><td>${team.manager || '-'}</td><td class="${sizeClass}">${team.team_size}</td><td class="${gkClass}">${team.gk_count}</td><td>${playerWageDisplay}</td><td>${extraWageDisplay}</td><td class="${wageClass}">${finalWageDisplay}</td><td>${capDisplay}</td><td>${team.count_8m}</td><td>${team.count_7m}</td><td>${team.count_fake}</td><td>${team.total_value.toFixed(1)}M</td><td>${team.avg_ca.toFixed(1)}</td><td>${team.avg_pa.toFixed(1)}</td><td>${team.total_growth}</td><td class="${notesClass}" title="${notesDisplay.replace(/"/g, '&quot;')}">${notesDisplay}</td></tr>`;
    }).join('')}</tbody></table>`;
    document.getElementById('teamsTable').innerHTML = html;
}

function getLevelBadge(level) {
    const classes = {'超级': 'level-super', '甲级': 'level-a', '乙级': 'level-b'};
    return `<span class="level-badge ${classes[level] || ''}">${level || '未知'}</span>`;
}

function viewTeamPlayers(teamName, options = {}) {
    showTab('players', null, {syncHistory: false});
    document.getElementById('teamSelect').value = teamName;
    document.getElementById('playerSearch').value = '';
    searchPlayers(options);
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
