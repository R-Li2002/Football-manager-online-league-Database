var fetchWithTimeout = globalThis.fetchWithTimeout || ((...args) => globalThis.fetch(...args));

const COMPARE_SLOT_COUNT = 4;
const COMPARE_ACCENT_CLASSES = ['is-blue', 'is-red', 'is-gold', 'is-mint'];
const COMPARISON_ADVANTAGE_FULL_DIFF = 10;

function createEmptyCompareSlots() {
    return Array.from({length: COMPARE_SLOT_COUNT}, () => null);
}

function getCompareAccentClass(slotIndex) {
    return COMPARE_ACCENT_CLASSES[slotIndex] || COMPARE_ACCENT_CLASSES[slotIndex % COMPARE_ACCENT_CLASSES.length] || 'is-blue';
}

function normalizeCompareSlots() {
    const normalized = createEmptyCompareSlots();
    if (Array.isArray(playerCompareSlots)) {
        playerCompareSlots.slice(0, COMPARE_SLOT_COUNT).forEach((slot, index) => {
            if (!slot || !slot.player) return;
            const player = {
                ...slot.player,
                data_version: slot.player.data_version || slot.data_version || getCurrentAttributeVersion(),
            };
            normalized[index] = {
                uid: slot.uid ?? player.uid,
                data_version: slot.data_version || getPlayerDataVersion(player),
                version_key: slot.version_key || getPlayerVersionKey(player),
                player,
                step: clampGrowthPreviewStep(slot.step),
            };
        });
    }
    playerCompareSlots = normalized;
    return playerCompareSlots;
}

function getCompareSlotIndex(playerOrUid, dataVersion = '') {
    normalizeCompareSlots();
    const targetKey = getPlayerVersionKey(playerOrUid, dataVersion);
    return playerCompareSlots.findIndex(slot => slot && slot.version_key === targetKey);
}

function syncComparedPlayerState(player) {
    const slotIndex = getCompareSlotIndex(player);
    if (slotIndex === -1) return;
    playerCompareSlots[slotIndex] = {
        ...playerCompareSlots[slotIndex],
        data_version: getPlayerDataVersion(player),
        version_key: getPlayerVersionKey(player),
        player: {...player},
    };
    renderCompareDock();
    if (comparisonModalOpen) {
        renderComparisonWorkspace();
    }
}

function queueCurrentPlayerForCompare() {
    if (!currentDetailPlayer) return;
    queuePlayerForCompare(currentDetailPlayer);
}

function queuePlayerForCompare(player) {
    normalizeCompareSlots();
    const slotIndex = getCompareSlotIndex(player);
    if (slotIndex !== -1) {
        playerCompareSlots[slotIndex] = {
            ...playerCompareSlots[slotIndex],
            data_version: getPlayerDataVersion(player),
            version_key: getPlayerVersionKey(player),
            player: {...player},
        };
        compareDockExpanded = true;
        renderCompareDock();
        if (currentDetailPlayer) renderGrowthPreviewToolbar(currentDetailPlayer);
        if (comparisonModalOpen) renderComparisonWorkspace();
        return;
    }

    const emptyIndex = playerCompareSlots.findIndex(slot => !slot);
    if (emptyIndex === -1) {
        compareDockExpanded = true;
        renderCompareDock();
        showModal('对比夹已满', '最多同时对比 4 名球员，请先从对比夹中移除一名后再加入。');
        return;
    }

    playerCompareSlots[emptyIndex] = {
        uid: player.uid,
        data_version: getPlayerDataVersion(player),
        version_key: getPlayerVersionKey(player),
        player: {...player},
        step: 0,
    };
    compareDockExpanded = true;
    renderCompareDock();
    if (currentDetailPlayer) renderGrowthPreviewToolbar(currentDetailPlayer);
    if (comparisonModalOpen) renderComparisonWorkspace();
}

function removePlayerFromCompare(slotIndex) {
    normalizeCompareSlots();
    if (slotIndex < 0 || slotIndex >= COMPARE_SLOT_COUNT) return;
    playerCompareSlots[slotIndex] = null;
    if (!playerCompareSlots.some(Boolean)) {
        compareDockExpanded = false;
    }
    renderCompareDock();
    if (currentDetailPlayer) renderGrowthPreviewToolbar(currentDetailPlayer);
    if (comparisonModalOpen) {
        if (playerCompareSlots.filter(Boolean).length < 2) {
            closeComparisonWorkspace();
        } else {
            renderComparisonWorkspace();
        }
    }
}

function clearCompareSlots() {
    playerCompareSlots = createEmptyCompareSlots();
    compareDockExpanded = false;
    renderCompareDock();
    if (currentDetailPlayer) renderGrowthPreviewToolbar(currentDetailPlayer);
    if (comparisonModalOpen) {
        closeComparisonWorkspace();
    }
}

function toggleCompareDock() {
    compareDockExpanded = !compareDockExpanded;
    if (
        compareDockExpanded &&
        typeof isMobileViewport === 'function' &&
        isMobileViewport() &&
        typeof candidateDockExpanded !== 'undefined' &&
        candidateDockExpanded
    ) {
        candidateDockExpanded = false;
        if (typeof renderCandidateDock === 'function') {
            renderCandidateDock();
        }
    }
    renderCompareDock();
}

function buildComparisonEntry(slot, slotIndex) {
    const previewPlayer = buildPreviewPlayer(slot.player, slot.step);
    return {
        slot,
        slotIndex,
        accentClass: getCompareAccentClass(slotIndex),
        previewPlayer,
        weightedPower: calculateWeightedPower(previewPlayer),
        weakFootPreview: getWeakFootPreview(slot.player, slot.step),
        collections: getPlayerFieldCollections(previewPlayer),
    };
}

function buildCompareSlotMarkup(slot, index, detailReturnTab, detailReturnSubtab) {
    if (!slot) {
        return `
            <div class="compare-slot is-empty">
                <span class="compare-slot-index">槽位 ${index + 1}</span>
                <p>在球员详情页点击“加入对比”</p>
            </div>
        `;
    }

    return `
        <div class="compare-slot is-filled ${getCompareAccentClass(index)}">
            <span class="compare-slot-index">槽位 ${index + 1}</span>
            <div class="compare-slot-name">${escapeHtml(slot.player.name)}</div>
            <div class="compare-slot-meta">${escapeHtml(slot.player.position || '-')} · ${escapeHtml(getAttributeVersionLabel(getPlayerDataVersion(slot.player)))} · 成长预览 +${clampGrowthPreviewStep(slot.step)}</div>
            <div class="compare-slot-actions">
                <button class="compare-slot-action" type="button" onclick="showPlayerDetail(${slot.player.uid}, {returnTab: '${detailReturnTab}', returnSubtab: '${detailReturnSubtab}', version: '${escapeHtml(getPlayerDataVersion(slot.player))}'})">查看球员</button>
                <button class="compare-slot-action is-danger" type="button" onclick="removePlayerFromCompare(${index})">移除</button>
            </div>
        </div>
    `;
}

function renderCompareDock() {
    const dock = document.getElementById('compareDock');
    if (!dock) return;

    normalizeCompareSlots();
    const activeTab = document.body.dataset.activeTab || document.querySelector('.tab-content.active')?.id || 'home';
    const mobileDetailActive = activeTab === 'database'
        && document.getElementById('dbDetailView')?.classList.contains('active')
        && typeof isMobileViewport === 'function'
        && isMobileViewport();
    const shouldShowDock = activeTab === 'players' || (activeTab === 'database' && !mobileDetailActive);
    document.body.classList.toggle('has-compare-dock', shouldShowDock);
    document.body.classList.toggle('has-expanded-compare-dock', shouldShowDock && compareDockExpanded);
    dock.hidden = !shouldShowDock;
    dock.classList.toggle('is-hidden', !shouldShowDock);
    if (!shouldShowDock) {
        dock.innerHTML = '';
        return;
    }

    const filledSlots = playerCompareSlots.filter(Boolean);
    const filledCount = filledSlots.length;
    const compareNames = filledSlots.map(slot => `${escapeHtml(slot.player.name)} (${escapeHtml(getPlayerDataVersion(slot.player))})`);
    const detailReturnTab = activeTab === 'players' ? 'players' : 'database';
    const detailReturnSubtab = detailReturnTab === 'database' ? currentDatabaseSubtab || 'search' : 'search';

    dock.innerHTML = `
        <div class="compare-dock-shell ${compareDockExpanded ? 'is-expanded' : 'is-collapsed'} ${filledCount ? 'has-items' : 'is-empty'}">
            ${compareDockExpanded ? `
                <div class="compare-dock-card ${filledCount ? 'has-items' : 'is-empty'}">
                    <div class="compare-dock-head">
                        <div>
                            <span class="panel-kicker">Compare Folder</span>
                            <h4>对比夹</h4>
                            <div class="compare-dock-summary">${compareNames.length ? compareNames.join(' · ') : '还没有加入对比球员'}</div>
                        </div>
                        ${filledCount ? '<button class="compare-dock-clear" type="button" onclick="clearCompareSlots()">清空</button>' : ''}
                    </div>
                    <div class="compare-slot-list">
                        ${playerCompareSlots.map((slot, index) => buildCompareSlotMarkup(slot, index, detailReturnTab, detailReturnSubtab)).join('')}
                    </div>
                    <div class="compare-dock-actions">
                        <button class="btn btn-primary compare-run-button" type="button" onclick="openComparisonWorkspace()" ${filledCount < 2 ? 'disabled' : ''}>查看对比页</button>
                    </div>
                </div>
            ` : ''}
            <button
                class="compare-dock-handle ${filledCount ? 'has-items' : 'is-empty'} ${compareDockExpanded ? 'is-expanded' : ''}"
                type="button"
                onclick="toggleCompareDock()"
                aria-expanded="${compareDockExpanded}"
                aria-label="${compareDockExpanded ? '收起对比夹' : '展开对比夹'}"
            >
                <span class="compare-dock-handle-dot">${filledCount ? filledCount : '+'}</span>
                <span class="compare-dock-handle-label">${compareDockExpanded ? '收起' : '对比夹'}</span>
                <span class="compare-dock-handle-meta">${filledCount}/${COMPARE_SLOT_COUNT}</span>
            </button>
        </div>
    `;
}

function buildComparisonSlider(slotIndex, slot, accentClass) {
    const labels = ['当前', '+1', '+2', '+3', '+4', '+5'];
    return `
        <div class="comparison-slider-box ${accentClass}">
            <div class="comparison-slider-labels">
                ${labels.map((label, index) => `<span class="comparison-slider-label ${index === clampGrowthPreviewStep(slot.step) ? 'is-active' : ''}">${label}</span>`).join('')}
            </div>
            <input
                class="growth-preview-slider comparison-slider ${accentClass}"
                type="range"
                min="0"
                max="5"
                step="1"
                value="${clampGrowthPreviewStep(slot.step)}"
                aria-label="对比成长预览"
                oninput="setCompareSlotGrowthStep(${slotIndex}, this.value)"
            >
        </div>
    `;
}

function buildComparisonPlayerCard(entry) {
    const {slot, slotIndex, accentClass, previewPlayer, weakFootPreview, weightedPower} = entry;
    const weightedPowerLabel = weightedPower.score === null ? '—' : weightedPower.score.toFixed(2);
    const heigoMetrics = calculateHeigoPowerMetrics(weightedPower.score);
    return `
        <section class="comparison-player-card ${accentClass}">
            <div class="comparison-player-head">
                <div>
                    <div class="comparison-player-name">${escapeHtml(slot.player.name)}</div>
                    <div class="comparison-player-version">UID ${escapeHtml(slot.player.uid)} · ${escapeHtml(getAttributeVersionLabel(getPlayerDataVersion(slot.player)))}</div>
                </div>
                <div class="comparison-player-tag">${escapeHtml(slot.player.position || '-')}</div>
            </div>
            <div class="comparison-player-club">${escapeHtml(slot.player.heigo_club || '-')} / ${escapeHtml(slot.player.club || '-')}</div>
            <div class="comparison-weighted-power ${getHeigoPowerTone(heigoMetrics?.heigoPower)}">
                <div class="comparison-power-entry">
                    <span>加权战力值</span>
                    <strong>${escapeHtml(weightedPowerLabel)}${weightedPower.score === null ? '' : '<small>/100</small>'}</strong>
                </div>
                <div class="comparison-power-entry is-heigo">
                    <span>HEIGO战力 ${heigoMetrics ? `<em>前 ${heigoMetrics.topPercentLabel}%</em>` : ''}</span>
                    <strong>${heigoMetrics ? heigoMetrics.heigoPower.toFixed(2) : '—'}</strong>
                </div>
            </div>
            ${buildComparisonSlider(slotIndex, slot, accentClass)}
            <div class="comparison-player-badges">
                <span class="foot-badge">成长预览 <strong>+${clampGrowthPreviewStep(slot.step)}</strong></span>
                <span class="foot-badge">CA <strong>${escapeHtml(previewPlayer.ca ?? '-')}</strong></span>
                <span class="foot-badge">PA <strong>${escapeHtml(previewPlayer.pa ?? '-')}</strong></span>
                <span class="foot-badge">左脚 <strong>${escapeHtml(previewPlayer.left_foot ?? '-')}</strong></span>
                <span class="foot-badge">右脚 <strong>${escapeHtml(previewPlayer.right_foot ?? '-')}</strong></span>
                ${weakFootPreview ? `<span class="foot-badge">${weakFootPreview.label}逆足 <strong>+1</strong></span>` : ''}
            </div>
        </section>
    `;
}

function getComparisonLegendMarkup(entries, options = {}) {
    return `
        <div class="comparison-legend-row ${options.compact ? 'is-compact' : ''}">
            ${entries.map(entry => `
                <span class="comparison-legend-chip ${entry.accentClass}">
                    <span class="comparison-legend-dot"></span>
                    <span class="comparison-legend-text">${escapeHtml(entry.slot.player.name)}</span>
                </span>
            `).join('')}
        </div>
    `;
}

function getHighlightIndexes(values) {
    const numericValues = values
        .map((value, index) => ({value: Number(value), index}))
        .filter(item => Number.isFinite(item.value));
    if (numericValues.length < 2) return new Set();

    const maxValue = Math.max(...numericValues.map(item => item.value));
    const minValue = Math.min(...numericValues.map(item => item.value));
    if (maxValue === minValue) return new Set();

    return new Set(numericValues.filter(item => item.value === maxValue).map(item => item.index));
}

function formatComparisonDifference(diff) {
    if (!Number.isFinite(diff)) return '';
    return Number.isInteger(diff) ? String(diff) : diff.toFixed(1).replace(/\.0$/, '');
}

function getComparisonAdvantage(row) {
    const numericValues = (row.highlightValues || row.values)
        .map((value, index) => ({value: Number(value), index}))
        .filter(item => Number.isFinite(item.value));
    if (numericValues.length < 2) return null;

    numericValues.sort((left, right) => right.value - left.value);
    const [leader, runnerUp] = numericValues;
    const diff = leader.value - runnerUp.value;
    if (diff <= 0) return null;

    return {
        index: leader.index,
        diff,
        width: Math.max(18, Math.min(100, (diff / COMPARISON_ADVANTAGE_FULL_DIFF) * 100)),
    };
}

function renderComparisonMetaRow(row, entries) {
    const highlightIndexes = getHighlightIndexes(row.highlightValues || row.values);
    return `
        <div class="comparison-meta-stack-row">
            <div class="comparison-meta-stack-label">${escapeHtml(row.label)}</div>
            <div class="comparison-meta-stack-values">
                ${row.values.map((value, index) => {
                    const displayValue = value === null || value === undefined || value === '' ? '-' : String(value);
                    return `
                        <div class="comparison-meta-stack-value ${entries[index].accentClass} ${highlightIndexes.has(index) ? 'is-max' : ''}">
                            <span class="comparison-meta-stack-player">${escapeHtml(entries[index].slot.player.name)}</span>
                            <span class="comparison-meta-stack-copy">${escapeHtml(displayValue)}</span>
                        </div>
                    `;
                }).join('')}
            </div>
        </div>
    `;
}

function buildComparisonMetaRows(entries) {
    return [
        {label: 'UID', values: entries.map(entry => entry.previewPlayer.uid)},
        {label: '版本', values: entries.map(entry => getAttributeVersionLabel(getPlayerDataVersion(entry.previewPlayer)) || '-')},
        {label: '国籍', values: entries.map(entry => entry.previewPlayer.nationality || '-')},
        {label: '生日', values: entries.map(entry => entry.previewPlayer.birth_date || '未知')},
        {label: '年龄', values: entries.map(entry => entry.previewPlayer.age ?? '-'), highlightValues: entries.map(entry => Number(entry.previewPlayer.age) || null)},
        {label: '位置', values: entries.map(entry => entry.previewPlayer.position || '-')},
        {label: 'CA', values: entries.map(entry => entry.previewPlayer.ca ?? '-'), highlightValues: entries.map(entry => Number(entry.previewPlayer.ca) || null)},
        {label: 'PA', values: entries.map(entry => entry.previewPlayer.pa ?? '-'), highlightValues: entries.map(entry => Number(entry.previewPlayer.pa) || null)},
        {
            label: '加权战力值',
            values: entries.map(entry => entry.weightedPower.score === null ? '—' : entry.weightedPower.score.toFixed(2)),
            highlightValues: entries.map(entry => entry.weightedPower.score),
        },
        {
            label: 'HEIGO战力 / 联赛位置',
            values: entries.map(entry => {
                const metrics = calculateHeigoPowerMetrics(entry.weightedPower.score);
                return metrics ? `${metrics.heigoPower.toFixed(2)} · 前 ${metrics.topPercentLabel}%` : '—';
            }),
            highlightValues: entries.map(entry => calculateHeigoPowerMetrics(entry.weightedPower.score)?.heigoPower ?? null),
        },
        {label: '身高', values: entries.map(entry => formatHeight(entry.previewPlayer.height)), highlightValues: entries.map(entry => Number(entry.previewPlayer.height) || null)},
        {label: '左脚', values: entries.map(entry => entry.previewPlayer.left_foot ?? '-'), highlightValues: entries.map(entry => Number(entry.previewPlayer.left_foot) || null)},
        {label: '右脚', values: entries.map(entry => entry.previewPlayer.right_foot ?? '-'), highlightValues: entries.map(entry => Number(entry.previewPlayer.right_foot) || null)},
        {label: 'HEIGO', values: entries.map(entry => entry.previewPlayer.heigo_club || '-')},
        {label: '现实俱乐部', values: entries.map(entry => entry.previewPlayer.club || '-')},
    ];
}

function buildComparisonMetaCard(entries) {
    const rows = buildComparisonMetaRows(entries);
    return `
        <section class="comparison-meta-card comparison-panel-wide">
            <div class="comparison-panel-head">
                <h4>基础信息</h4>
                <div class="comparison-panel-note">显示具体数值，数值字段自动高亮最高值</div>
            </div>
            <div class="comparison-meta-stack">
                ${rows.map(row => renderComparisonMetaRow(row, entries)).join('')}
            </div>
        </section>
    `;
}

function mergeComparisonItems(entries, picker, options = {}) {
    const registry = new Map();
    entries.forEach((entry, entryIndex) => {
        picker(entry).forEach(item => {
            if (!registry.has(item.key)) {
                registry.set(item.key, {
                    key: item.key,
                    label: item.label,
                    values: Array(entries.length).fill(null),
                });
            }
            const row = registry.get(item.key);
            const numericValue = Number(item.value);
            row.values[entryIndex] = Number.isFinite(numericValue) ? numericValue : null;
        });
    });

    return [...registry.values()].filter(row => {
        if (options.includeLowValues) return true;
        return row.values.some(value => Number(value) > 0);
    });
}

function renderComparisonMetricRow(row, entries) {
    const advantage = getComparisonAdvantage(row);
    if (!advantage) return '';
    const entry = entries[advantage.index];
    const value = row.values[advantage.index];
    const displayValue = value === null || value === undefined || value === '' ? '-' : String(value);
    const diffText = formatComparisonDifference(advantage.diff);
    return `
        <div class="comparison-metric-row">
            <div class="comparison-metric-label">${escapeHtml(row.label)}</div>
            <div class="comparison-metric-bars is-advantage">
                <div class="comparison-metric-bar-row comparison-metric-advantage-row ${entry.accentClass} is-max">
                    <div class="comparison-metric-track" title="领先 ${escapeHtml(diffText)}">
                        <span class="comparison-metric-fill ${entry.accentClass}" style="width:${advantage.width}%"></span>
                    </div>
                    <span class="comparison-metric-bar-value">
                        <span class="comparison-metric-player">${escapeHtml(entry.slot.player.name)}</span>
                        <strong>${escapeHtml(displayValue)}</strong>
                        <span class="comparison-metric-diff">+${escapeHtml(diffText)}</span>
                    </span>
                </div>
            </div>
        </div>
    `;
}

function renderComparisonMetricPanel(title, rows, entries, options = {}) {
    const advantageRows = rows.filter(row => getComparisonAdvantage(row));
    if (!advantageRows.length) return '';
    return `
        <section class="comparison-panel ${options.wide ? 'comparison-panel-wide' : ''}">
            <div class="comparison-panel-head">
                <h4>${escapeHtml(title)}</h4>
                <div class="comparison-panel-note">仅显示优势项</div>
            </div>
            <div class="comparison-metric-list">
                ${advantageRows.map(row => renderComparisonMetricRow(row, entries)).join('')}
            </div>
        </section>
    `;
}

function setCompareSlotGrowthStep(slotIndex, step) {
    normalizeCompareSlots();
    if (!playerCompareSlots[slotIndex]) return;
    playerCompareSlots[slotIndex].step = clampGrowthPreviewStep(step);
    renderCompareDock();
    if (comparisonModalOpen) {
        renderComparisonWorkspace();
    }
}

async function openComparisonWorkspace() {
    normalizeCompareSlots();
    if (playerCompareSlots.filter(Boolean).length < 2) {
        showModal('无法开始对比', '请先在球员详情页加入至少两名球员，再打开对比界面。');
        return;
    }
    comparisonModalOpen = true;
    const overlay = document.getElementById('comparisonOverlay');
    overlay.hidden = false;
    overlay.classList.add('active');
    overlay.setAttribute('aria-hidden', 'false');
    const content = document.getElementById('comparisonContent');
    if (content) content.innerHTML = '<div class="loading">正在计算 HEIGO 相对战力...</div>';
    await loadHeigoPowerCalibration(getPlayerDataVersion(playerCompareSlots.find(Boolean)?.player));
    renderComparisonWorkspace();
}

function closeComparisonWorkspace() {
    comparisonModalOpen = false;
    const overlay = document.getElementById('comparisonOverlay');
    overlay.classList.remove('active');
    overlay.setAttribute('aria-hidden', 'true');
    overlay.hidden = true;
}

function renderComparisonWorkspace() {
    const content = document.getElementById('comparisonContent');
    if (!content) return;

    normalizeCompareSlots();
    const activeEntries = playerCompareSlots
        .map((slot, index) => slot ? buildComparisonEntry(slot, index) : null)
        .filter(Boolean);

    if (activeEntries.length < 2) {
        content.innerHTML = '<div class="no-data">对比夹中需要至少两名球员才能打开对比页。</div>';
        return;
    }

    const technicalTitle = activeEntries.some(entry => entry.collections.isGoalkeeper) ? '技术 / 门将' : '技术';
    const technicalRows = mergeComparisonItems(
        activeEntries,
        entry => entry.collections.technical,
        {includeLowValues: false}
    );
    const setPieceRows = mergeComparisonItems(activeEntries, entry => entry.collections.setPieces, {includeLowValues: false});
    const mentalRows = mergeComparisonItems(activeEntries, entry => entry.collections.mental, {includeLowValues: false});
    const physicalRows = mergeComparisonItems(activeEntries, entry => entry.collections.physical, {includeLowValues: false});
    const hiddenRows = mergeComparisonItems(activeEntries, entry => entry.collections.hidden, {includeLowValues: false});
    const positionRows = mergeComparisonItems(
        activeEntries,
        entry => entry.collections.positions.filter(item => Number(item.value) > 1),
        {includeLowValues: false}
    );

    content.innerHTML = `
        <div class="comparison-stage" style="--compare-player-count:${activeEntries.length};">
            <div class="comparison-player-grid">
                ${activeEntries.map(buildComparisonPlayerCard).join('')}
            </div>
            ${getComparisonLegendMarkup(activeEntries)}
            <div class="comparison-grid">
                <div class="comparison-core-grid comparison-panel-wide">
                    ${renderComparisonMetricPanel(technicalTitle, technicalRows, activeEntries)}
                    ${renderComparisonMetricPanel('定位球', setPieceRows, activeEntries)}
                    ${renderComparisonMetricPanel('精神', mentalRows, activeEntries)}
                    ${renderComparisonMetricPanel('身体', physicalRows, activeEntries)}
                </div>
                <div class="comparison-secondary-grid comparison-panel-wide">
                    ${buildComparisonMetaCard(activeEntries)}
                    ${renderComparisonMetricPanel('隐藏', hiddenRows, activeEntries, {wide: true})}
                    ${renderComparisonMetricPanel('位置熟练度', positionRows, activeEntries, {wide: true})}
                </div>
            </div>
        </div>
    `;
}
