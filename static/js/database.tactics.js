const DB_TACTICS_STORAGE_KEY = 'heigo_database_tactics_board_v1';
const DB_TACTICS_GROWTH_THRESHOLDS = {1: 11, 2: 30, 3: 50, 4: 70, 5: 90};
const DB_TACTICS_FORMATIONS = {
    '4-3-3': [
        ['gk', 'GK', 50, 88], ['lb', 'LB', 17, 72], ['lcb', 'CB', 38, 74], ['rcb', 'CB', 62, 74], ['rb', 'RB', 83, 72],
        ['lcm', 'CM', 31, 52], ['cm', 'CM', 50, 56], ['rcm', 'CM', 69, 52], ['lw', 'LW', 20, 29], ['st', 'ST', 50, 22], ['rw', 'RW', 80, 29],
    ],
    '4-2-3-1': [
        ['gk', 'GK', 50, 88], ['lb', 'LB', 17, 72], ['lcb', 'CB', 38, 74], ['rcb', 'CB', 62, 74], ['rb', 'RB', 83, 72],
        ['ldm', 'DM', 39, 58], ['rdm', 'DM', 61, 58], ['lam', 'AM', 23, 39], ['amc', 'AM', 50, 37], ['ram', 'AM', 77, 39], ['st', 'ST', 50, 21],
    ],
    '3-4-3': [
        ['gk', 'GK', 50, 88], ['lcb', 'CB', 29, 73], ['cb', 'CB', 50, 76], ['rcb', 'CB', 71, 73],
        ['lm', 'LM', 16, 52], ['lcm', 'CM', 39, 55], ['rcm', 'CM', 61, 55], ['rm', 'RM', 84, 52], ['lw', 'LW', 22, 29], ['st', 'ST', 50, 21], ['rw', 'RW', 78, 29],
    ],
    '3-5-2': [
        ['gk', 'GK', 50, 88], ['lcb', 'CB', 29, 73], ['cb', 'CB', 50, 76], ['rcb', 'CB', 71, 73],
        ['lwb', 'WB', 15, 52], ['lcm', 'CM', 37, 57], ['cm', 'CM', 50, 47], ['rcm', 'CM', 63, 57], ['rwb', 'WB', 85, 52], ['lst', 'ST', 39, 22], ['rst', 'ST', 61, 22],
    ],
    '4-4-2': [
        ['gk', 'GK', 50, 88], ['lb', 'LB', 17, 72], ['lcb', 'CB', 38, 74], ['rcb', 'CB', 62, 74], ['rb', 'RB', 83, 72],
        ['lm', 'LM', 18, 50], ['lcm', 'CM', 39, 54], ['rcm', 'CM', 61, 54], ['rm', 'RM', 82, 50], ['lst', 'ST', 39, 22], ['rst', 'ST', 61, 22],
    ],
};

function readDatabaseTacticsState() {
    const fallback = {name: '我的战术方案', formation: '4-3-3', version: '', picks: {}};
    try {
        const parsed = JSON.parse(localStorage.getItem(DB_TACTICS_STORAGE_KEY) || 'null');
        if (!parsed || typeof parsed !== 'object') return fallback;
        return {
            name: String(parsed.name || fallback.name).slice(0, 40),
            formation: DB_TACTICS_FORMATIONS[parsed.formation] ? parsed.formation : fallback.formation,
            version: String(parsed.version || ''),
            picks: parsed.picks && typeof parsed.picks === 'object' ? parsed.picks : {},
        };
    } catch (error) {
        return fallback;
    }
}

var databaseTacticsState = {
    ...readDatabaseTacticsState(),
    players: {},
    searchResults: [],
    searchBusy: false,
    loadBusy: false,
    activePoint: null,
    status: '',
    statusState: 'idle',
};
var databaseTacticsDragState = null;

function setDatabaseTacticsStatus(message = '', state = 'info') {
    databaseTacticsState.status = message;
    databaseTacticsState.statusState = message ? state : 'idle';
}

function getDatabaseTacticsSlots(formation = databaseTacticsState.formation) {
    return (DB_TACTICS_FORMATIONS[formation] || DB_TACTICS_FORMATIONS['4-3-3'])
        .map(([key, label, x, y]) => ({key, label, x, y}));
}

function persistDatabaseTacticsState() {
    try {
        localStorage.setItem(DB_TACTICS_STORAGE_KEY, JSON.stringify({
            name: databaseTacticsState.name,
            formation: databaseTacticsState.formation,
            version: databaseTacticsState.version,
            picks: databaseTacticsState.picks,
        }));
    } catch (error) {
        // The board remains usable for the current session when storage is unavailable.
    }
}

function getDatabaseTacticsEligibleSteps(player) {
    const ca = Number(player?.ca || 0);
    const pa = Number(player?.pa || 0);
    const gap = Math.max(0, pa - ca);
    return [0, ...Object.entries(DB_TACTICS_GROWTH_THRESHOLDS)
        .filter(([, threshold]) => gap >= Number(threshold))
        .map(([step]) => Number(step))];
}

function getDatabaseTacticsPlayer(slotKey) {
    const uid = Number(databaseTacticsState.picks?.[slotKey]?.uid || 0);
    return uid ? databaseTacticsState.players[uid] || null : null;
}

function hasDatabaseTacticsMetric(value) {
    return value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
}

function getDatabaseTacticsMetrics(player, growthStep = 0) {
    if (!player || typeof buildPreviewPlayer !== 'function' || typeof calculateWeightedPower !== 'function') return null;
    const preview = buildPreviewPlayer(player, growthStep);
    const weighted = calculateWeightedPower(preview);
    const heigo = hasDatabaseTacticsMetric(weighted.score) && typeof calculateHeigoPowerMetrics === 'function'
        ? calculateHeigoPowerMetrics(weighted.score)
        : null;
    const caGain = Number(DB_TACTICS_GROWTH_THRESHOLDS[growthStep] || 0);
    return {
        weightedPower: weighted.score,
        heigoPower: heigo?.heigoPower ?? null,
        topPercentLabel: heigo?.topPercentLabel ?? null,
        projectedCa: Math.min(Number(player.pa || 0), Number(player.ca || 0) + caGain),
    };
}

function getDatabaseTacticsSummary() {
    const entries = Object.entries(databaseTacticsState.picks || {}).map(([slotKey, pick]) => {
        const player = databaseTacticsState.players[Number(pick?.uid || 0)];
        const metrics = getDatabaseTacticsMetrics(player, Number(pick?.growth_step || 0));
        return {slotKey, player, metrics};
    }).filter(item => item.player);
    const weighted = entries.map(item => item.metrics?.weightedPower).filter(hasDatabaseTacticsMetric).map(Number);
    const heigo = entries.map(item => item.metrics?.heigoPower).filter(hasDatabaseTacticsMetric).map(Number);
    const average = values => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
    return {count: entries.length, weightedAverage: average(weighted), heigoAverage: average(heigo)};
}

function normalizeDatabaseTacticsPicks() {
    const formationSlots = new Map(getDatabaseTacticsSlots().map(slot => [slot.key, slot]));
    const seen = new Set();
    const normalized = {};
    Object.entries(databaseTacticsState.picks || {}).forEach(([slotKey, rawPick]) => {
        const uid = Number(rawPick?.uid || 0);
        const referenceSlot = formationSlots.get(slotKey);
        if (!referenceSlot || !uid || seen.has(uid)) return;
        const player = databaseTacticsState.players[uid];
        const eligible = player ? getDatabaseTacticsEligibleSteps(player) : [0];
        const requestedStep = Number(rawPick?.growth_step || 0);
        const rawX = Number(rawPick?.x);
        const rawY = Number(rawPick?.y);
        normalized[slotKey] = {
            uid,
            growth_step: eligible.includes(requestedStep) ? requestedStep : 0,
            x: Number.isFinite(rawX) ? Math.max(4, Math.min(96, rawX)) : referenceSlot.x,
            y: Number.isFinite(rawY) ? Math.max(5, Math.min(95, rawY)) : referenceSlot.y,
        };
        seen.add(uid);
    });
    databaseTacticsState.picks = normalized;
}

async function fetchDatabaseTacticsPlayer(uid, version = databaseTacticsState.version) {
    const response = await fetch(buildAttributeVersionedPath(`/api/attributes/${Number(uid)}`, version));
    const payload = await response.json().catch(() => null);
    if (!response.ok || !payload?.uid) throw new Error(payload?.detail || `找不到 UID ${uid}`);
    return payload;
}

async function hydrateDatabaseTacticsPlayers() {
    const uids = [...new Set(Object.values(databaseTacticsState.picks || {}).map(item => Number(item?.uid || 0)).filter(Boolean))];
    if (!uids.length) return;
    const settled = await Promise.allSettled(uids.map(uid => fetchDatabaseTacticsPlayer(uid)));
    settled.forEach((result, index) => {
        const uid = uids[index];
        if (result.status === 'fulfilled') databaseTacticsState.players[uid] = result.value;
    });
    const loaded = new Set(Object.keys(databaseTacticsState.players).map(Number));
    Object.keys(databaseTacticsState.picks || {}).forEach(slotKey => {
        if (!loaded.has(Number(databaseTacticsState.picks[slotKey]?.uid || 0))) delete databaseTacticsState.picks[slotKey];
    });
    normalizeDatabaseTacticsPicks();
    persistDatabaseTacticsState();
}

function renderDatabaseTacticsGrowthOptions(player, selectedStep) {
    return getDatabaseTacticsEligibleSteps(player).map(step => {
        const label = step ? `+${step}` : '当前';
        return `<option value="${step}" ${Number(selectedStep) === step ? 'selected' : ''}>${label}</option>`;
    }).join('');
}

function getDatabaseTacticsZoneLabel(pick) {
    const y = Number(pick?.y || 50);
    if (y >= 82) return 'GK';
    if (y >= 65) return 'DEF';
    if (y >= 52) return 'DM';
    if (y >= 38) return 'MID';
    if (y >= 24) return 'AM';
    return 'ATT';
}

function buildDatabaseTacticsPlayerCard(slotKey, player, pick) {
    const growthStep = Number(pick?.growth_step || 0);
    const metrics = getDatabaseTacticsMetrics(player, growthStep);
    const growthLabel = growthStep ? `+${growthStep}` : '当前';
    return `
        <div class="db-tactics-player-card" role="group" tabindex="0" onclick="event.stopPropagation()" onpointerdown="startDatabaseTacticsDrag(event, ${htmlJsString(slotKey)})" onpointermove="moveDatabaseTacticsDrag(event)" onpointerup="finishDatabaseTacticsDrag(event)" onpointercancel="finishDatabaseTacticsDrag(event)" onkeydown="handleDatabaseTacticsCardKeydown(event, ${htmlJsString(slotKey)})" aria-label="拖动 ${escapeHtml(player.name || '')} 调整场上位置">
            <span class="formation-shirt-icon" aria-hidden="true"></span>
            <span class="db-tactics-role">${escapeHtml(getDatabaseTacticsZoneLabel(pick))}</span>
            <strong>${escapeHtml(player.name || '-')}</strong>
            <span class="db-tactics-player-meta">${escapeHtml(player.position || '-')} · ${escapeHtml(player.heigo_club || '大海')}</span>
            <span class="db-tactics-power">HEIGO ${hasDatabaseTacticsMetric(metrics?.heigoPower) ? Number(metrics.heigoPower).toFixed(2) : '--'}</span>
            <label class="db-tactics-growth" onclick="event.stopPropagation()" onpointerdown="event.stopPropagation()" aria-label="${escapeHtml(player.name || '')}成长状态">
                <span>${escapeHtml(growthLabel)}</span>
                <select onchange="setDatabaseTacticsGrowth(${htmlJsString(slotKey)}, this.value)">${renderDatabaseTacticsGrowthOptions(player, growthStep)}</select>
            </label>
            <button class="db-tactics-remove" type="button" onpointerdown="event.stopPropagation()" onclick="event.stopPropagation(); removeDatabaseTacticsPlayer(${htmlJsString(slotKey)})" aria-label="移除 ${escapeHtml(player.name || '')}">${uiIconSvg('close', 'ui-icon is-small')}</button>
        </div>
    `;
}

function renderDatabaseTacticsPitch() {
    const entries = Object.entries(databaseTacticsState.picks || {});
    const target = databaseTacticsState.activePoint;
    return `
        <section class="db-tactics-capture formation-capture surface-card" id="databaseTacticsCapture">
            <div class="formation-capture-head db-tactics-capture-head">
                <div><span class="panel-kicker">Tactics Lab</span><h3>${escapeHtml(databaseTacticsState.name || '我的战术方案')}</h3></div>
                <strong>${escapeHtml(databaseTacticsState.formation)}</strong>
            </div>
            <div class="formation-pitch db-tactics-pitch" aria-label="自定义战术板，可点击设置落点并拖动球员" onclick="setDatabaseTacticsDropPoint(event)">
                <div class="formation-pitch-line formation-pitch-center"></div><div class="formation-pitch-box formation-pitch-box-top"></div><div class="formation-pitch-box formation-pitch-box-bottom"></div>
                <div class="formation-goal-box formation-goal-box-top"></div><div class="formation-goal-box formation-goal-box-bottom"></div>
                <span class="formation-corner corner-tl"></span><span class="formation-corner corner-tr"></span><span class="formation-corner corner-bl"></span><span class="formation-corner corner-br"></span>
                ${target ? `<span class="db-tactics-drop-target" style="left:${target.x}%;top:${target.y}%;"><b><svg class="ui-icon is-small" viewBox="0 0 24 24" focusable="false" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg></b><small>下一位</small></span>` : ''}
                ${entries.map(([slotKey, pick]) => {
                    const player = getDatabaseTacticsPlayer(slotKey);
                    if (!player) return '';
                    return `<div class="db-tactics-slot has-player" style="left:${Number(pick.x)}%;top:${Number(pick.y)}%;" data-slot-key="${escapeHtml(slotKey)}">${buildDatabaseTacticsPlayerCard(slotKey, player, pick)}</div>`;
                }).join('')}
                ${entries.length ? '' : '<div class="db-tactics-pitch-empty"><strong>点击球场设置落点</strong><span>选择球员后可以直接拖到任意位置</span></div>'}
            </div>
        </section>
    `;
}

function renderDatabaseTacticsSearchResults() {
    if (databaseTacticsState.searchBusy) return '<div class="loading">正在搜索球员库...</div>';
    if (!databaseTacticsState.searchResults.length) {
        return '<div class="db-tactics-search-empty">输入姓名搜索全库球员，或直接输入 UID。可先点击球场设置落点，也可以加入后自由拖动。</div>';
    }
    return databaseTacticsState.searchResults.map(player => {
        const eligible = getDatabaseTacticsEligibleSteps(player);
        const growthText = eligible.length > 1 ? `可预览至 +${eligible[eligible.length - 1]}` : '仅当前状态';
        const alreadyPicked = Object.values(databaseTacticsState.picks || {}).some(pick => Number(pick?.uid) === Number(player.uid));
        return `<article class="db-tactics-search-result">
            <button class="db-tactics-result-main" type="button" onclick="showPlayerDetail(${Number(player.uid)}, {returnTab:'database', returnSubtab:'tactics', version:${htmlJsString(databaseTacticsState.version)}})">
                <strong>${escapeHtml(player.name || '-')}</strong><span>${escapeHtml(player.position || '-')} · CA ${Number(player.ca || 0)} / PA ${Number(player.pa || 0)}</span><small>${escapeHtml(player.heigo_club || '大海')} · HEIGO ${hasDatabaseTacticsMetric(player.heigo_power) ? Number(player.heigo_power).toFixed(2) : '--'}</small>
            </button>
            <div class="db-tactics-result-action"><span>${escapeHtml(growthText)}</span><button class="btn btn-primary" type="button" onclick="addDatabaseTacticsPlayer(${Number(player.uid)})">${alreadyPicked ? (databaseTacticsState.activePoint ? '移动到落点' : '已在场上') : '放入战术板'}</button></div>
        </article>`;
    }).join('');
}

function renderDatabaseTacticsBoard() {
    const board = document.getElementById('dbTacticsBoard');
    if (!board) return;
    const summary = getDatabaseTacticsSummary();
    const versions = (availableAttributeVersions || []).length ? availableAttributeVersions : [databaseTacticsState.version].filter(Boolean);
    board.innerHTML = `
        <section class="db-tactics-hero database-module-hero surface-card">
            <div><span class="panel-kicker">Build Your XI</span><h2>自定义战术板</h2><p>从完整球员库自由选人，为每名球员独立设置成长形态。阵型仅作为参考，场上 11 人都可以用鼠标或手指拖到任意位置。</p></div>
            <div class="db-tactics-summary">
                <span><strong>${summary.count}</strong><small>/ 11 人</small></span>
                <span><strong>${summary.heigoAverage === null ? '--' : summary.heigoAverage.toFixed(2)}</strong><small>平均 HEIGO</small></span>
                <span><strong>${summary.weightedAverage === null ? '--' : summary.weightedAverage.toFixed(2)}</strong><small>平均加权战力</small></span>
            </div>
        </section>
        <div class="db-tactics-toolbar database-filter-card surface-card">
            <label class="db-tactics-name"><span>方案名称</span><input type="text" maxlength="40" value="${escapeHtml(databaseTacticsState.name)}" oninput="setDatabaseTacticsName(this.value)"></label>
            <label><span>参考阵型</span><select onchange="changeDatabaseTacticsFormation(this.value)">${Object.keys(DB_TACTICS_FORMATIONS).map(name => `<option value="${name}" ${name === databaseTacticsState.formation ? 'selected' : ''}>${name}</option>`).join('')}</select></label>
            <label><span>数据库版本</span><select onchange="changeDatabaseTacticsVersion(this.value)">${versions.map(version => `<option value="${escapeHtml(version)}" ${version === databaseTacticsState.version ? 'selected' : ''}>${escapeHtml(version)}</option>`).join('')}</select></label>
            <div class="db-tactics-toolbar-actions"><button class="btn btn-secondary" type="button" onclick="resetDatabaseTacticsToFormation()">按阵型重排</button><button class="btn btn-secondary" type="button" onclick="clearDatabaseTacticsBoard()">清空战术板</button></div>
        </div>
        ${databaseTacticsState.status ? `<div class="db-tactics-status is-${escapeHtml(databaseTacticsState.statusState || 'info')}" role="${databaseTacticsState.statusState === 'error' ? 'alert' : 'status'}" aria-live="${databaseTacticsState.statusState === 'error' ? 'assertive' : 'polite'}">${escapeHtml(databaseTacticsState.status)}</div>` : ''}
        <div class="db-tactics-workspace">
            <div class="db-tactics-pitch-column">${renderDatabaseTacticsPitch()}</div>
            <aside class="db-tactics-picker surface-card">
                <div class="db-tactics-picker-head"><div><span class="panel-kicker">Player Pool</span><h3>选择球员</h3></div><span class="db-tactics-target">${databaseTacticsState.activePoint ? `落点 ${Math.round(databaseTacticsState.activePoint.x)} · ${Math.round(databaseTacticsState.activePoint.y)}` : '自动排位'}</span></div>
                <form class="db-tactics-search-form" onsubmit="event.preventDefault(); searchDatabaseTacticsPlayers();">
                    <input id="dbTacticsSearchInput" type="search" placeholder="输入球员姓名或 UID" autocomplete="off">
                    <button class="btn btn-primary" type="submit">搜索</button>
                </form>
                <div class="db-tactics-growth-legend"><span>成长状态</span><b>当前</b><b>+1</b><b>+2</b><b>+3</b><b>+4</b><b>+5</b><small>按球员 CA / PA 成长空间开放</small></div>
                <div class="db-tactics-results">${renderDatabaseTacticsSearchResults()}</div>
            </aside>
        </div>
    `;
}

async function loadDatabaseTacticsBoard(options = {}) {
    currentDatabaseSubtab = 'tactics';
    syncDatabaseSubtabUI();
    activateDatabaseView('tactics');
    const board = document.getElementById('dbTacticsBoard');
    if (board) board.innerHTML = '<div class="loading">正在载入战术方案...</div>';
    databaseTacticsState.loadBusy = true;
    await loadAttributeVersionCatalog();
    const versions = availableAttributeVersions || [];
    const selectedVersion = versions.includes(databaseTacticsState.version)
        ? databaseTacticsState.version
        : (getCurrentAttributeVersion() || versions[0] || '');
    databaseTacticsState.version = setCurrentAttributeVersion(selectedVersion);
    await loadHeigoPowerCalibration(databaseTacticsState.version);
    databaseTacticsState.players = {};
    await hydrateDatabaseTacticsPlayers();
    databaseTacticsState.loadBusy = false;
    renderDatabaseTacticsBoard();
    if (options.pushHistory !== false && typeof syncAppHistory === 'function') syncAppHistory(options.historyMode || 'push');
}

async function searchDatabaseTacticsPlayers() {
    const input = document.getElementById('dbTacticsSearchInput');
    const query = String(input?.value || '').trim();
    if (!query) {
        databaseTacticsState.searchResults = [];
        setDatabaseTacticsStatus('请输入球员姓名或 UID。', 'warning');
        renderDatabaseTacticsBoard();
        return;
    }
    databaseTacticsState.searchBusy = true;
    setDatabaseTacticsStatus();
    renderDatabaseTacticsBoard();
    try {
        let results;
        if (/^\d+$/.test(query)) {
            const player = await fetchDatabaseTacticsPlayer(Number(query));
            const metrics = getDatabaseTacticsMetrics(player, 0);
            results = [{...player, weighted_power: metrics?.weightedPower, heigo_power: metrics?.heigoPower}];
        } else {
            const path = buildAttributeVersionedPath(`/api/attributes/search/${encodeURIComponent(query)}`, databaseTacticsState.version);
            const response = await fetch(path);
            const payload = await response.json().catch(() => []);
            if (!response.ok) throw new Error(payload?.detail || `HTTP ${response.status}`);
            results = Array.isArray(payload) ? payload : [];
        }
        databaseTacticsState.searchResults = results;
        setDatabaseTacticsStatus(results.length ? `找到 ${results.length} 名球员` : '没有找到匹配球员，请尝试完整姓名或 UID。', results.length ? 'success' : 'warning');
    } catch (error) {
        databaseTacticsState.searchResults = [];
        setDatabaseTacticsStatus(`搜索失败：${error.message || '请稍后重试'}`, 'error');
    } finally {
        databaseTacticsState.searchBusy = false;
        renderDatabaseTacticsBoard();
        window.requestAnimationFrame(() => {
            const nextInput = document.getElementById('dbTacticsSearchInput');
            if (nextInput) nextInput.value = query;
        });
    }
}

async function addDatabaseTacticsPlayer(uid) {
    const numericUid = Number(uid || 0);
    if (!numericUid) return;
    const slots = getDatabaseTacticsSlots();
    const existingSlotKey = Object.keys(databaseTacticsState.picks || {}).find(slotKey => Number(databaseTacticsState.picks[slotKey]?.uid) === numericUid);
    if (!existingSlotKey && Object.keys(databaseTacticsState.picks || {}).length >= 11) {
        setDatabaseTacticsStatus('场上已经有 11 人，请先移除一名球员。', 'warning');
        renderDatabaseTacticsBoard();
        return;
    }
    const targetSlot = existingSlotKey || slots.find(slot => !databaseTacticsState.picks?.[slot.key])?.key;
    if (!targetSlot) return;
    try {
        const player = databaseTacticsState.players[numericUid] || await fetchDatabaseTacticsPlayer(numericUid);
        databaseTacticsState.players[numericUid] = player;
        const reference = slots.find(slot => slot.key === targetSlot) || slots[0];
        const previous = databaseTacticsState.picks[targetSlot] || {};
        databaseTacticsState.picks[targetSlot] = {
            uid: numericUid,
            growth_step: Number(previous.growth_step || 0),
            x: Number(databaseTacticsState.activePoint?.x ?? previous.x ?? reference?.x ?? 50),
            y: Number(databaseTacticsState.activePoint?.y ?? previous.y ?? reference?.y ?? 50),
        };
        databaseTacticsState.activePoint = null;
        setDatabaseTacticsStatus(existingSlotKey ? `${player.name || numericUid} 已移动到新落点` : `${player.name || numericUid} 已加入战术板，可直接拖动调整位置`, 'success');
        persistDatabaseTacticsState();
        renderDatabaseTacticsBoard();
    } catch (error) {
        setDatabaseTacticsStatus(`添加失败：${error.message || '请稍后重试'}`, 'error');
        renderDatabaseTacticsBoard();
    }
}

function getDatabaseTacticsPoint(event, pitch, card = null) {
    const rect = pitch.getBoundingClientRect();
    const halfX = card ? ((card.offsetWidth / 2 + 5) / rect.width) * 100 : 3;
    const halfY = card ? ((card.offsetHeight / 2 + 5) / rect.height) * 100 : 4;
    return {
        x: Math.max(halfX, Math.min(100 - halfX, ((event.clientX - rect.left) / rect.width) * 100)),
        y: Math.max(halfY, Math.min(100 - halfY, ((event.clientY - rect.top) / rect.height) * 100)),
    };
}

function setDatabaseTacticsDropPoint(event) {
    if (event.target?.closest?.('.db-tactics-player-card')) return;
    databaseTacticsState.activePoint = getDatabaseTacticsPoint(event, event.currentTarget);
    setDatabaseTacticsStatus('已设置下一名球员的落点', 'info');
    renderDatabaseTacticsBoard();
}

function startDatabaseTacticsDrag(event, slotKey) {
    if (event.button !== undefined && event.button !== 0) return;
    if (event.target?.closest?.('select, button, label')) return;
    const card = event.currentTarget;
    const pitch = card.closest('.db-tactics-pitch');
    if (!pitch || !databaseTacticsState.picks?.[slotKey]) return;
    event.preventDefault();
    event.stopPropagation();
    databaseTacticsDragState = {slotKey, pointerId: event.pointerId, card, pitch, moved: false};
    card.setPointerCapture?.(event.pointerId);
    card.classList.add('is-dragging');
    document.body.classList.add('db-tactics-dragging');
}

function moveDatabaseTacticsDrag(event) {
    const drag = databaseTacticsDragState;
    if (!drag || drag.pointerId !== event.pointerId) return;
    event.preventDefault();
    const point = getDatabaseTacticsPoint(event, drag.pitch, drag.card);
    const slot = drag.card.closest('.db-tactics-slot');
    if (slot) {
        slot.style.left = `${point.x}%`;
        slot.style.top = `${point.y}%`;
    }
    databaseTacticsState.picks[drag.slotKey].x = point.x;
    databaseTacticsState.picks[drag.slotKey].y = point.y;
    drag.moved = true;
}

function finishDatabaseTacticsDrag(event) {
    const drag = databaseTacticsDragState;
    if (!drag || drag.pointerId !== event.pointerId) return;
    event.preventDefault();
    event.stopPropagation();
    drag.card.releasePointerCapture?.(event.pointerId);
    drag.card.classList.remove('is-dragging');
    document.body.classList.remove('db-tactics-dragging');
    databaseTacticsDragState = null;
    if (drag.moved) {
        databaseTacticsState.activePoint = null;
        setDatabaseTacticsStatus('球员位置已保存', 'success');
        persistDatabaseTacticsState();
        renderDatabaseTacticsBoard();
    }
}

function handleDatabaseTacticsCardKeydown(event, slotKey) {
    const directions = {ArrowLeft: [-2, 0], ArrowRight: [2, 0], ArrowUp: [0, -2], ArrowDown: [0, 2]};
    const delta = directions[event.key];
    const pick = databaseTacticsState.picks?.[slotKey];
    if (!delta || !pick) return;
    event.preventDefault();
    pick.x = Math.max(5, Math.min(95, Number(pick.x || 50) + delta[0]));
    pick.y = Math.max(6, Math.min(94, Number(pick.y || 50) + delta[1]));
    setDatabaseTacticsStatus('球员位置已微调', 'success');
    persistDatabaseTacticsState();
    renderDatabaseTacticsBoard();
}

function setDatabaseTacticsGrowth(slotKey, value) {
    const pick = databaseTacticsState.picks?.[slotKey];
    const player = getDatabaseTacticsPlayer(slotKey);
    const step = Number(value || 0);
    if (!pick || !player || !getDatabaseTacticsEligibleSteps(player).includes(step)) return;
    pick.growth_step = step;
    setDatabaseTacticsStatus(`${player.name || '球员'} 已切换为${step ? ` +${step}` : '当前'}状态`, 'success');
    persistDatabaseTacticsState();
    renderDatabaseTacticsBoard();
}

function removeDatabaseTacticsPlayer(slotKey) {
    const player = getDatabaseTacticsPlayer(slotKey);
    delete databaseTacticsState.picks[slotKey];
    setDatabaseTacticsStatus(player ? `${player.name} 已移出战术板` : '', 'info');
    persistDatabaseTacticsState();
    renderDatabaseTacticsBoard();
}

function changeDatabaseTacticsFormation(formation) {
    if (!DB_TACTICS_FORMATIONS[formation] || formation === databaseTacticsState.formation) return;
    databaseTacticsState.formation = formation;
    resetDatabaseTacticsToFormation({render: false});
    setDatabaseTacticsStatus(`已切换为 ${formation} 并按参考阵型重排，之后仍可自由拖动`, 'info');
    persistDatabaseTacticsState();
    renderDatabaseTacticsBoard();
}

function resetDatabaseTacticsToFormation(options = {}) {
    const slots = getDatabaseTacticsSlots();
    const existing = Object.values(databaseTacticsState.picks || {});
    const nextPicks = {};
    existing.slice(0, 11).forEach((pick, index) => {
        const slot = slots[index];
        if (!slot) return;
        nextPicks[slot.key] = {...pick, x: slot.x, y: slot.y};
    });
    databaseTacticsState.picks = nextPicks;
    databaseTacticsState.activePoint = null;
    if (options.render !== false) {
        setDatabaseTacticsStatus(`已按 ${databaseTacticsState.formation} 参考阵型重新排列`, 'success');
        persistDatabaseTacticsState();
        renderDatabaseTacticsBoard();
    }
}

async function changeDatabaseTacticsVersion(version) {
    const normalized = String(version || '').trim();
    if (!normalized || normalized === databaseTacticsState.version) return;
    databaseTacticsState.version = setCurrentAttributeVersion(normalized);
    databaseTacticsState.players = {};
    databaseTacticsState.searchResults = [];
    setDatabaseTacticsStatus(`正在切换到 ${normalized} 版本...`, 'saving');
    persistDatabaseTacticsState();
    renderDatabaseTacticsBoard();
    await loadHeigoPowerCalibration(normalized);
    await hydrateDatabaseTacticsPlayers();
    setDatabaseTacticsStatus(`已切换到 ${normalized} 版本`, 'success');
    renderDatabaseTacticsBoard();
    if (typeof syncAppHistory === 'function') syncAppHistory('replace');
}

function setDatabaseTacticsName(value) {
    databaseTacticsState.name = String(value || '').slice(0, 40) || '我的战术方案';
    persistDatabaseTacticsState();
    const heading = document.querySelector('.db-tactics-capture-head h3');
    if (heading) heading.textContent = databaseTacticsState.name;
}

async function clearDatabaseTacticsBoard() {
    if (Object.keys(databaseTacticsState.picks || {}).length && !await showConfirmDialog({title: '清空战术板', message: '当前选人和自定义位置会被清空。', confirmLabel: '确认清空', danger: true})) return;
    databaseTacticsState.picks = {};
    databaseTacticsState.players = {};
    databaseTacticsState.activePoint = null;
    setDatabaseTacticsStatus('战术板已清空', 'info');
    persistDatabaseTacticsState();
    renderDatabaseTacticsBoard();
}
