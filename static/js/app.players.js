const ROSTER_SORT_FIELD_CONFIG = {
    uid: {label: 'UID', type: 'number', align: 'center'},
    name: {label: '姓名', type: 'text', align: 'left'},
    age: {label: '年龄', type: 'number', align: 'center'},
    initial_ca: {label: '初始 CA', type: 'number', align: 'center'},
    ca: {label: '当前 CA', type: 'number', align: 'center'},
    pa: {label: 'PA', type: 'number', align: 'center'},
    position: {label: '位置', type: 'text', align: 'center'},
    nationality: {label: '国籍', type: 'text', align: 'center'},
    team_name: {label: '所属球队', type: 'text', align: 'left'},
    wage: {label: '工资', type: 'number', align: 'center'},
    slot_type: {label: '名额', type: 'text', align: 'center'},
};

function escapeQueryText(value) {
    return escapeHtml(value ?? '');
}

function getDefaultRosterSortOrder(type) {
    return type === 'text' ? 'asc' : 'desc';
}

function compareRosterValues(left, right, type, order) {
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

function getSortedRosterPlayers(players) {
    if (!currentRosterSort.field) return [...players];
    const sorted = [...players];
    sorted.sort((left, right) => compareRosterValues(
        left[currentRosterSort.field],
        right[currentRosterSort.field],
        currentRosterSort.type || 'number',
        currentRosterSort.order || 'desc'
    ));
    return sorted;
}

function toggleRosterSort(field) {
    const config = ROSTER_SORT_FIELD_CONFIG[field] || {type: 'text', label: field};
    if (currentRosterSort.field === field) {
        currentRosterSort.order = currentRosterSort.order === 'asc' ? 'desc' : 'asc';
    } else {
        currentRosterSort = {
            field,
            type: config.type,
            order: getDefaultRosterSortOrder(config.type),
        };
    }
    renderPlayers(currentPlayers);
}

function getRosterSortIndicator(field) {
    if (currentRosterSort.field !== field) return '<span class="sort-indicator">↕</span>';
    return `<span class="sort-indicator is-active">${currentRosterSort.order === 'asc' ? '↑' : '↓'}</span>`;
}

function buildRosterHeader(label, field, numeric = false) {
    const config = ROSTER_SORT_FIELD_CONFIG[field] || {align: 'left'};
    const className = numeric ? `sortable-header numeric-column header-align-${config.align}` : `sortable-header header-align-${config.align}`;
    return `<th class="${className}" role="button" tabindex="0" onclick="toggleRosterSort('${field}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();toggleRosterSort('${field}');}"><span class="sortable-heading"><span class="sortable-label">${label}</span>${getRosterSortIndicator(field)}</span></th>`;
}

function renderPlayerQueryState() {
    const titleEl = document.getElementById('playerQueryTitle');
    const metaEl = document.getElementById('playerQueryMeta');
    const chipsEl = document.getElementById('playerQueryChips');
    if (!titleEl || !metaEl || !chipsEl) return;

    const teamName = document.getElementById('teamSelect')?.value || '';
    const playerName = document.getElementById('playerSearch')?.value.trim() || '';
    const sortField = currentRosterSort.field || '';
    const sortOrder = currentRosterSort.order || 'desc';
    const hasFilters = Boolean(teamName || playerName || sortField);
    const count = Array.isArray(currentPlayers) ? currentPlayers.length : 0;

    if (playerName && teamName) {
        titleEl.textContent = `正在查看 ${teamName} 中与“${playerName}”匹配的联赛球员`;
    } else if (playerName) {
        titleEl.textContent = `正在查看与“${playerName}”匹配的联赛球员`;
    } else if (teamName) {
        titleEl.textContent = `正在查看 ${teamName} 的联赛名单`;
    } else {
        titleEl.textContent = '当前正在查看全部联赛名单';
    }

    metaEl.textContent = hasFilters
        ? `当前结果共 ${count} 人。你可以继续调整球队、姓名和排序方式，快速缩小范围。`
        : `当前结果共 ${count} 人。可以按球队、姓名和表头排序快速缩小范围。`;

    const chips = [];
    chips.push(`<span class="query-chip"><strong>${count}</strong>&nbsp;名结果</span>`);

    if (teamName) {
        chips.push(`<span class="query-chip">球队&nbsp;<strong>${escapeQueryText(teamName)}</strong></span>`);
    }
    if (playerName) {
        chips.push(`<span class="query-chip">姓名&nbsp;<strong>${escapeQueryText(playerName)}</strong></span>`);
    }
    if (sortField) {
        const fieldMeta = ROSTER_SORT_FIELD_CONFIG[sortField];
        const orderLabel = sortOrder === 'asc' ? '升序' : '降序';
        chips.push(`<span class="query-chip is-muted">排序&nbsp;<strong>${fieldMeta?.label || escapeQueryText(sortField)}</strong>&nbsp;${orderLabel}</span>`);
    }
    if (!hasFilters) {
        chips.push('<span class="query-chip is-muted">未应用额外筛选</span>');
    }

    chipsEl.innerHTML = chips.join('');
}

function getSlotBadge(slot) {
    if (!slot) return '';
    const badges = {'7M': 'slot-7m', '8M': 'slot-8m', '伪名': 'slot-fake'};
    return `<span class="slot-badge ${badges[slot] || ''}">${slot}</span>`;
}

function sortPlayers() {
    renderPlayers(currentPlayers);
}

function renderPlayers(players) {
    const displayCount = document.getElementById('displayCount');
    if (displayCount) displayCount.textContent = players.length;
    renderPlayerQueryState();
    if (players.length === 0) {
        document.getElementById('playersTable').innerHTML = '<div class="no-data">没有找到符合条件的球员</div>';
        return;
    }

    const sortedPlayers = getSortedRosterPlayers(players);
    const html = `<table class="players-list-table" aria-label="联赛名单数据表">
        <colgroup>
            <col class="uid-column">
            <col class="name-column">
            <col class="age-column">
            <col class="ca-column">
            <col class="ca-column">
            <col class="ca-column">
            <col class="position-column">
            <col class="nation-column">
            <col class="team-column">
            <col class="wage-column">
            <col class="table-slot-col">
            ${isAdmin ? '<col class="detail-column">' : ''}
        </colgroup>
        <thead><tr>${buildRosterHeader('UID', 'uid', true)}${buildRosterHeader('姓名', 'name')}${buildRosterHeader('年龄', 'age', true)}${buildRosterHeader('初始CA', 'initial_ca', true)}${buildRosterHeader('当前CA', 'ca', true)}${buildRosterHeader('PA', 'pa', true)}${buildRosterHeader('位置', 'position')}${buildRosterHeader('国籍', 'nationality')}${buildRosterHeader('所属球队', 'team_name')}${buildRosterHeader('工资', 'wage', true)}${buildRosterHeader('名额', 'slot_type')}${isAdmin ? '<th class="detail-column">详情</th>' : ''}</tr></thead><tbody>${sortedPlayers.map(player => {
            const uidCell = isAdmin
                ? `<td class="numeric-cell"><input type="number" class="editable-input" value="${player.uid}" onchange="updatePlayerUidConfirm(${player.uid}, this.value, this)" style="background:rgba(0,0,0,0.2);border:2px solid #e74c3c;padding:4px 6px;border-radius:4px;color:#fff;width:50px;font-weight:bold;" title="修改 UID 需要谨慎，请确认无误！"></td>`
                : `<td class="numeric-cell">${player.uid}</td>`;

            const nameCell = isAdmin
                ? `<td class="name-cell"><input type="text" class="editable-input" value="${player.name.replace(/"/g, '&quot;')}" onchange="updatePlayerField(${player.uid}, 'name', this.value)" style="background:rgba(0,0,0,0.2);border:1px solid rgba(0,217,255,0.3);padding:4px 8px;border-radius:4px;color:#fff;width:118px;"></td>`
                : `<td class="name-cell" title="${player.name.replace(/"/g, '&quot;')}"><span class="player-link roster-player-link" onclick="viewPlayerInDatabase(${player.uid})">${player.name}</span></td>`;

            const ageCell = isAdmin
                ? `<td class="numeric-cell"><input type="number" class="editable-input" value="${player.age}" onchange="updatePlayerField(${player.uid}, 'age', this.value)" style="background:rgba(0,0,0,0.2);border:1px solid rgba(0,217,255,0.3);padding:4px 8px;border-radius:4px;color:#fff;width:50px;"></td>`
                : `<td class="numeric-cell">${player.age}</td>`;

            const positionCell = isAdmin
                ? `<td class="position-cell"><input type="text" class="editable-input" value="${player.position.replace(/"/g, '&quot;')}" onchange="updatePlayerField(${player.uid}, 'position', this.value)" style="background:rgba(0,0,0,0.2);border:1px solid rgba(0,217,255,0.3);padding:4px 8px;border-radius:4px;color:#fff;width:80px;"></td>`
                : `<td class="position-cell">${player.position}</td>`;

            const nationalityCell = isAdmin
                ? `<td class="nationality-cell" title="${player.nationality.replace(/"/g, '&quot;')}"><input type="text" class="editable-input" value="${player.nationality.replace(/"/g, '&quot;')}" onchange="updatePlayerField(${player.uid}, 'nationality', this.value)" style="background:rgba(0,0,0,0.2);border:1px solid rgba(0,217,255,0.3);padding:4px 8px;border-radius:4px;color:#fff;width:88px;"></td>`
                : `<td class="nationality-cell" title="${player.nationality.replace(/"/g, '&quot;')}">${player.nationality}</td>`;

            const detailCell = isAdmin
                ? `<td><button class="btn btn-secondary" style="padding:4px 8px;font-size:0.8rem;" onclick="togglePlayerDetail(${player.uid})">📊</button></td>`
                : '';

            const isSelected = Number(currentSelectedRosterUid) === Number(player.uid);
            const mainRow = `<tr id="player-row-${player.uid}" class="${isSelected ? 'row-selected' : ''}" data-player-uid="${player.uid}" tabindex="0" onclick="selectRosterPlayer(${player.uid})" onkeydown="handleRosterRowKeydown(event, ${player.uid})">${uidCell}${nameCell}${ageCell}<td class="numeric-cell">${player.initial_ca}</td><td class="numeric-cell"><strong>${player.ca}</strong></td><td class="numeric-cell">${player.pa}</td>${positionCell}${nationalityCell}<td class="team-name-cell"><span class="player-link roster-player-link" onclick="viewTeamPlayers('${player.team_name.replace(/'/g, "\\'")}')">${player.team_name}</span></td><td class="numeric-cell">${player.wage.toFixed(3)}M</td><td class="slot-cell">${getSlotBadge(player.slot_type)}</td>${detailCell}</tr>`;

            const detailRow = isAdmin
                ? `<tr id="player-detail-${player.uid}" class="player-detail-row" style="display:none;background:var(--bg-tertiary);"><td colspan="12"><div style="padding:15px;display:grid;grid-template-columns:repeat(4,1fr);gap:10px;">
                    <div><strong>初始身价:</strong> <span id="detail-initial-value-${player.uid}">加载中...</span></div>
                    <div><strong>当前身价:</strong> <span id="detail-current-value-${player.uid}">加载中...</span></div>
                    <div><strong>潜力身价:</strong> <span id="detail-potential-value-${player.uid}">加载中...</span></div>
                    <div><strong>最终身价:</strong> <span id="detail-final-value-${player.uid}">加载中...</span></div>
                    <div><strong>初始字段:</strong> <span id="detail-initial-field-${player.uid}">加载中...</span></div>
                    <div><strong>系数:</strong> <span id="detail-coefficient-${player.uid}">加载中...</span></div>
                    <div><strong>名额类型:</strong> <span id="detail-slot-type-${player.uid}">加载中...</span></div>
                    <div><strong>工资计算:</strong> <span id="detail-wage-calc-${player.uid}">加载中...</span></div>
                </div></td></tr>`
                : '';

            return mainRow + detailRow;
        }).join('')}</tbody></table>`;
    document.getElementById('playersTable').innerHTML = html;
    bindRosterKeyboardNavigation();
}

function selectRosterPlayer(uid) {
    currentSelectedRosterUid = Number(uid);
    document.querySelectorAll('#playersTable tr.row-selected').forEach(row => row.classList.remove('row-selected'));
    const row = document.getElementById(`player-row-${uid}`);
    if (row) {
        row.classList.add('row-selected');
    }
}

function handleRosterRowKeydown(event, uid) {
    if (event.key === 'Enter') {
        event.preventDefault();
        viewPlayerInDatabase(uid);
    }
}

function bindRosterKeyboardNavigation() {
    const rows = Array.from(document.querySelectorAll('#playersTable tr[data-player-uid]'));
    if (!rows.length) return;
    rows.forEach((row, index) => {
        row.addEventListener('keydown', event => {
            if (event.key === 'ArrowDown') {
                event.preventDefault();
                const next = rows[Math.min(index + 1, rows.length - 1)];
                next?.focus();
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                const prev = rows[Math.max(index - 1, 0)];
                prev?.focus();
            }
        });
    });
}

const playerDetailCache = {};

async function togglePlayerDetail(uid) {
    const detailRow = document.getElementById(`player-detail-${uid}`);
    if (detailRow.style.display === 'none') {
        detailRow.style.display = 'table-row';
        if (playerDetailCache[uid]) {
            updateDetailDisplay(uid, playerDetailCache[uid]);
        } else {
            try {
                const res = await fetch(`/api/player/wage-detail/${uid}`);
                const data = await res.json();
                playerDetailCache[uid] = data;
                updateDetailDisplay(uid, data);
            } catch (error) {
                document.getElementById(`detail-initial-value-${uid}`).textContent = '加载失败';
                document.getElementById(`detail-current-value-${uid}`).textContent = '加载失败';
                console.error(`Failed to load detail for player ${uid}:`, error);
            }
        }
    } else {
        detailRow.style.display = 'none';
    }
}

function updateDetailDisplay(uid, data) {
    document.getElementById(`detail-initial-value-${uid}`).textContent = data.initial_value;
    document.getElementById(`detail-current-value-${uid}`).textContent = data.current_value;
    document.getElementById(`detail-potential-value-${uid}`).textContent = data.potential_value;
    document.getElementById(`detail-final-value-${uid}`).textContent = data.final_value.toFixed(3);
    document.getElementById(`detail-initial-field-${uid}`).textContent = data.initial_field.toFixed(3);
    document.getElementById(`detail-coefficient-${uid}`).textContent = data.coefficient;
    document.getElementById(`detail-slot-type-${uid}`).textContent = data.slot_type || '-';
    document.getElementById(`detail-wage-calc-${uid}`).textContent = `${data.final_value.toFixed(3)} × ${data.coefficient} = ${data.wage.toFixed(3)}M`;
}

async function searchPlayers() {
    const teamName = document.getElementById('teamSelect').value;
    const playerName = document.getElementById('playerSearch').value.trim();

    if (playerName.toLowerCase() === 'heigomanage') {
        document.getElementById('adminTab').classList.remove('hidden-tab');
        showTab('admin');
        document.getElementById('playerSearch').value = '';
        return;
    }

    if (playerName) {
        document.getElementById('tableTitle').textContent = teamName
            ? `搜索结果: "${playerName}" · ${teamName}`
            : `搜索结果: "${playerName}"`;
        const res = await fetch(`/api/players/search/${encodeURIComponent(playerName)}`);
        currentPlayers = await res.json();
        if (teamName) {
            currentPlayers = currentPlayers.filter(player => player.team_name === teamName);
        }
    } else if (teamName) {
        document.getElementById('tableTitle').textContent = `${teamName} 联赛名单`;
        const res = await fetch(`/api/players/team/${encodeURIComponent(teamName)}`);
        currentPlayers = await res.json();
    } else {
        document.getElementById('tableTitle').textContent = '全部联赛名单';
        currentPlayers = [...allPlayers];
    }

    renderPlayers(currentPlayers);
}

function resetPlayers() {
    document.getElementById('teamSelect').value = '';
    document.getElementById('playerSearch').value = '';
    document.getElementById('tableTitle').textContent = '全部联赛名单';
    currentRosterSort = {field: '', order: 'desc', type: 'number'};
    currentSelectedRosterUid = null;
    currentPlayers = [...allPlayers];
    renderPlayers(currentPlayers);
}

document.getElementById('playerSearch')?.addEventListener('keypress', event => {
    if (event.key === 'Enter') searchPlayers();
});
document.getElementById('teamSelect')?.addEventListener('change', () => {
    searchPlayers();
});
