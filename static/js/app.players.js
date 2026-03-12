function escapeQueryText(value) {
    return escapeHtml(value ?? '');
}

function renderPlayerQueryState() {
    const titleEl = document.getElementById('playerQueryTitle');
    const metaEl = document.getElementById('playerQueryMeta');
    const chipsEl = document.getElementById('playerQueryChips');
    if (!titleEl || !metaEl || !chipsEl) return;

    const teamName = document.getElementById('teamSelect')?.value || '';
    const playerName = document.getElementById('playerSearch')?.value.trim() || '';
    const sortField = document.getElementById('playerSortField')?.value || '';
    const sortOrder = document.getElementById('playerSortOrder')?.value || 'desc';
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
        : `当前结果共 ${count} 人。可以按球队、姓名和排序方式快速缩小范围。`;

    const chips = [];
    chips.push(`<span class="query-chip"><strong>${count}</strong>&nbsp;名结果</span>`);

    if (teamName) {
        chips.push(`<span class="query-chip">球队&nbsp;<strong>${escapeQueryText(teamName)}</strong></span>`);
    }
    if (playerName) {
        chips.push(`<span class="query-chip">姓名&nbsp;<strong>${escapeQueryText(playerName)}</strong></span>`);
    }
    if (sortField) {
        const fieldMap = {
            age: '年龄',
            initial_ca: '初始 CA',
            ca: '当前 CA',
            pa: 'PA',
            wage: '工资',
        };
        const orderLabel = sortOrder === 'asc' ? '升序' : '降序';
        chips.push(`<span class="query-chip is-muted">排序&nbsp;<strong>${fieldMap[sortField] || escapeQueryText(sortField)}</strong>&nbsp;${orderLabel}</span>`);
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
    const field = document.getElementById('playerSortField').value;
    const order = document.getElementById('playerSortOrder').value;
    currentRosterSort = {field, order};
    if (!field) {
        renderPlayers(currentPlayers);
        return;
    }
    const sorted = [...currentPlayers];
    sorted.sort((a, b) => {
        const va = a[field];
        const vb = b[field];
        if (typeof va === 'string' || typeof vb === 'string') {
            const sa = String(va || '');
            const sb = String(vb || '');
            return order === 'asc' ? sa.localeCompare(sb, 'zh-CN') : sb.localeCompare(sa, 'zh-CN');
        }
        return order === 'asc' ? va - vb : vb - va;
    });
    renderPlayers(sorted);
}

function renderPlayers(players) {
    const displayCount = document.getElementById('displayCount');
    if (displayCount) displayCount.textContent = players.length;
    renderPlayerQueryState();
    if (players.length === 0) {
        document.getElementById('playersTable').innerHTML = '<div class="no-data">没有找到符合条件的球员</div>';
        return;
    }
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
        <thead><tr><th class="numeric-column">UID</th><th>姓名</th><th class="numeric-column">年龄</th><th class="numeric-column">初始CA</th><th class="numeric-column">当前CA</th><th class="numeric-column">PA</th><th>位置</th><th>国籍</th><th>所属球队</th><th class="numeric-column">工资</th><th class="slot-column">名额</th>${isAdmin ? '<th class="detail-column">详情</th>' : ''}</tr></thead><tbody>${players.map(p => {
            const growth = p.ca - p.initial_ca;
            const growthClass = growth > 0 ? 'growth-positive' : (growth < 0 ? 'growth-negative' : '');
            const growthText = growth !== 0 ? `<span class="growth-indicator ${growthClass}">(${growth > 0 ? '+' : ''}${growth})</span>` : '';

            const uidCell = isAdmin
                ? `<td class="numeric-cell"><input type="number" class="editable-input" value="${p.uid}" onchange="updatePlayerUidConfirm(${p.uid}, this.value, this)" style="background:rgba(0,0,0,0.2);border:2px solid #e74c3c;padding:4px 6px;border-radius:4px;color:#fff;width:50px;font-weight:bold;" title="修改 UID 需要谨慎，请确认无误！"></td>`
                : `<td class="numeric-cell">${p.uid}</td>`;

            const nameCell = isAdmin
                ? `<td><input type="text" class="editable-input" value="${p.name.replace(/"/g, '&quot;')}" onchange="updatePlayerField(${p.uid}, 'name', this.value)" style="background:rgba(0,0,0,0.2);border:1px solid rgba(0,217,255,0.3);padding:4px 8px;border-radius:4px;color:#fff;width:100px;"></td>`
                : `<td><span class="player-link" onclick="viewPlayerInDatabase(${p.uid})">${p.name}</span></td>`;

            const ageCell = isAdmin
                ? `<td class="numeric-cell"><input type="number" class="editable-input" value="${p.age}" onchange="updatePlayerField(${p.uid}, 'age', this.value)" style="background:rgba(0,0,0,0.2);border:1px solid rgba(0,217,255,0.3);padding:4px 8px;border-radius:4px;color:#fff;width:50px;"></td>`
                : `<td class="numeric-cell">${p.age}</td>`;

            const positionCell = isAdmin
                ? `<td class="position-cell"><input type="text" class="editable-input" value="${p.position.replace(/"/g, '&quot;')}" onchange="updatePlayerField(${p.uid}, 'position', this.value)" style="background:rgba(0,0,0,0.2);border:1px solid rgba(0,217,255,0.3);padding:4px 8px;border-radius:4px;color:#fff;width:80px;"></td>`
                : `<td class="position-cell">${p.position}</td>`;

            const nationalityCell = isAdmin
                ? `<td class="nationality-cell" title="${p.nationality.replace(/"/g, '&quot;')}"><input type="text" class="editable-input" value="${p.nationality.replace(/"/g, '&quot;')}" onchange="updatePlayerField(${p.uid}, 'nationality', this.value)" style="background:rgba(0,0,0,0.2);border:1px solid rgba(0,217,255,0.3);padding:4px 8px;border-radius:4px;color:#fff;width:88px;"></td>`
                : `<td class="nationality-cell" title="${p.nationality.replace(/"/g, '&quot;')}">${p.nationality}</td>`;

            const detailCell = isAdmin
                ? `<td><button class="btn btn-secondary" style="padding:4px 8px;font-size:0.8rem;" onclick="togglePlayerDetail(${p.uid})">📊</button></td>`
                : '';

            const isSelected = Number(currentSelectedRosterUid) === Number(p.uid);
            const mainRow = `<tr id="player-row-${p.uid}" class="${isSelected ? 'row-selected' : ''}" data-player-uid="${p.uid}" tabindex="0" onclick="selectRosterPlayer(${p.uid})" onkeydown="handleRosterRowKeydown(event, ${p.uid})">${uidCell}${nameCell}${ageCell}<td class="numeric-cell">${p.initial_ca}</td><td class="numeric-cell"><strong>${p.ca}</strong>${growthText}</td><td class="numeric-cell">${p.pa}</td>${positionCell}${nationalityCell}<td class="team-name-cell"><span class="player-link" onclick="viewTeamPlayers('${p.team_name.replace(/'/g, "\\'")}')">${p.team_name}</span></td><td class="numeric-cell">${p.wage.toFixed(3)}M</td><td class="slot-cell">${getSlotBadge(p.slot_type)}</td>${detailCell}</tr>`;

            const detailRow = isAdmin
                ? `<tr id="player-detail-${p.uid}" class="player-detail-row" style="display:none;background:var(--bg-tertiary);"><td colspan="12"><div style="padding:15px;display:grid;grid-template-columns:repeat(4,1fr);gap:10px;">
                    <div><strong>初始身价:</strong> <span id="detail-initial-value-${p.uid}">加载中...</span></div>
                    <div><strong>当前身价:</strong> <span id="detail-current-value-${p.uid}">加载中...</span></div>
                    <div><strong>潜力身价:</strong> <span id="detail-potential-value-${p.uid}">加载中...</span></div>
                    <div><strong>最终身价:</strong> <span id="detail-final-value-${p.uid}">加载中...</span></div>
                    <div><strong>初始字段:</strong> <span id="detail-initial-field-${p.uid}">加载中...</span></div>
                    <div><strong>系数:</strong> <span id="detail-coefficient-${p.uid}">加载中...</span></div>
                    <div><strong>名额类型:</strong> <span id="detail-slot-type-${p.uid}">加载中...</span></div>
                    <div><strong>工资计算:</strong> <span id="detail-wage-calc-${p.uid}">加载中...</span></div>
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
            } catch (e) {
                document.getElementById(`detail-initial-value-${uid}`).textContent = '加载失败';
                document.getElementById(`detail-current-value-${uid}`).textContent = '加载失败';
                console.error(`Failed to load detail for player ${uid}:`, e);
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
    const hasSort = currentRosterSort.field && document.getElementById('playerSortField').value;
    if (hasSort) {
        sortPlayers();
        return;
    }
    renderPlayers(currentPlayers);
}

function resetPlayers() {
    document.getElementById('teamSelect').value = '';
    document.getElementById('playerSearch').value = '';
    document.getElementById('tableTitle').textContent = '全部联赛名单';
    document.getElementById('playerSortField').value = '';
    currentRosterSort = {field: '', order: 'desc'};
    currentSelectedRosterUid = null;
    currentPlayers = [...allPlayers];
    renderPlayers(currentPlayers);
}

document.getElementById('playerSearch')?.addEventListener('keypress', e => {
    if (e.key === 'Enter') searchPlayers();
});
document.getElementById('teamSelect')?.addEventListener('change', () => {
    searchPlayers();
});