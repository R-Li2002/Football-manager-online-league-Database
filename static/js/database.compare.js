function normalizeCompareSlots() {
    if (!Array.isArray(playerCompareSlots) || playerCompareSlots.length !== 2) {
        playerCompareSlots = [null, null];
    }
    playerCompareSlots = playerCompareSlots.map(slot => {
        if (!slot || !slot.player) return null;
        const player = {
            ...slot.player,
            data_version: slot.player.data_version || slot.data_version || getCurrentAttributeVersion(),
        };
        return {
            uid: slot.uid ?? player.uid,
            data_version: slot.data_version || getPlayerDataVersion(player),
            version_key: slot.version_key || getPlayerVersionKey(player),
            player,
            step: clampGrowthPreviewStep(slot.step),
        };
    });
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
        showModal('对比夹已满', '最多支持同时对比 2 名球员，请先从右侧对比夹移除一名后再加入。');
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
}

function removePlayerFromCompare(slotIndex) {
    normalizeCompareSlots();
    if (slotIndex < 0 || slotIndex > 1) return;
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
    playerCompareSlots = [null, null];
    compareDockExpanded = false;
    renderCompareDock();
    if (currentDetailPlayer) renderGrowthPreviewToolbar(currentDetailPlayer);
    if (comparisonModalOpen) {
        closeComparisonWorkspace();
    }
}

function toggleCompareDock() {
    compareDockExpanded = !compareDockExpanded;
    renderCompareDock();
}

function renderCompareDock() {
    const dock = document.getElementById('compareDock');
    if (!dock) return;

    normalizeCompareSlots();
    const activeTab = document.body.dataset.activeTab || document.querySelector('.tab-content.active')?.id || 'home';
    const shouldShowDock = activeTab === 'players' || activeTab === 'database';
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
                            <div class="compare-dock-summary">${compareNames.length ? compareNames.join(' vs ') : '还没有加入对比球员'}</div>
                        </div>
                        ${filledCount ? '<button class="compare-dock-clear" type="button" onclick="clearCompareSlots()">清空</button>' : ''}
                    </div>
                    <div class="compare-slot-list">
                        ${playerCompareSlots.map((slot, index) => {
                            if (!slot) {
                                return `
                                    <div class="compare-slot is-empty">
                                        <span class="compare-slot-index">槽位 ${index + 1}</span>
                                        <p>在球员详情页点击“加入对比”</p>
                                    </div>
                                `;
                            }
                            const previewPlayer = buildPreviewPlayer(slot.player, slot.step);
                            return `
                                <div class="compare-slot is-filled is-${index === 0 ? 'blue' : 'red'}">
                                    <span class="compare-slot-index">槽位 ${index + 1}</span>
                                    <div class="compare-slot-name">${escapeHtml(slot.player.name)}</div>
                                    <div class="compare-slot-meta">${escapeHtml(slot.player.position || '-')} · ${escapeHtml(getPlayerDataVersion(slot.player))} · CA ${escapeHtml(previewPlayer.preview_ca ?? slot.player.ca ?? '-')}</div>
                                    <div class="compare-slot-actions">
                                        <button class="compare-slot-action" type="button" onclick="showPlayerDetail(${slot.player.uid}, {returnTab: '${detailReturnTab}', returnSubtab: '${detailReturnSubtab}', version: '${escapeHtml(getPlayerDataVersion(slot.player))}'})">查看球员</button>
                                        <button class="compare-slot-action is-danger" type="button" onclick="removePlayerFromCompare(${index})">移除</button>
                                    </div>
                                </div>
                            `;
                        }).join('')}
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
                <span class="compare-dock-handle-meta">${filledCount}/2</span>
            </button>
        </div>
    `;
}

function buildComparisonSlider(slotIndex, slot) {
    const labels = ['当前', '+1', '+2', '+3', '+4', '+5'];
    const accentClass = slotIndex === 0 ? 'is-blue' : 'is-red';
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

function buildComparisonPlayerCard(slot, slotIndex) {
    const previewPlayer = buildPreviewPlayer(slot.player, slot.step);
    const accentClass = slotIndex === 0 ? 'is-blue' : 'is-red';
    const weakFootPreview = getWeakFootPreview(slot.player, slot.step);

    return `
        <section class="comparison-player-card ${accentClass}">
            <div class="comparison-player-head">
                <div>
                    <div class="comparison-player-name">${escapeHtml(slot.player.name)}</div>
                    <div class="comparison-player-version">UID ${escapeHtml(slot.player.uid)} · ${escapeHtml(getPlayerDataVersion(slot.player))}</div>
                </div>
                <div class="comparison-player-tag">${escapeHtml(slot.player.position || '-')}</div>
            </div>
            <div class="comparison-player-club">${escapeHtml(slot.player.heigo_club || '-')} / ${escapeHtml(slot.player.club || '-')}</div>
            ${buildComparisonSlider(slotIndex, slot)}
            <div class="comparison-player-badges">
                <span class="foot-badge">CA <strong>${escapeHtml(previewPlayer.preview_ca ?? slot.player.ca ?? '-')}</strong></span>
                <span class="foot-badge">PA <strong>${escapeHtml(slot.player.pa ?? '-')}</strong></span>
                <span class="foot-badge">左脚 <strong>${escapeHtml(previewPlayer.left_foot ?? '-')}</strong></span>
                <span class="foot-badge">右脚 <strong>${escapeHtml(previewPlayer.right_foot ?? '-')}</strong></span>
                ${weakFootPreview ? `<span class="foot-badge">${weakFootPreview.label}逆足 <strong>+1</strong></span>` : ''}
            </div>
        </section>
    `;
}

function buildComparisonMetaCard(leftPreview, rightPreview) {
    const rows = [
        ['UID', leftPreview.uid, rightPreview.uid],
        ['版本', getPlayerDataVersion(leftPreview) || '-', getPlayerDataVersion(rightPreview) || '-'],
        ['国籍', leftPreview.nationality || '-', rightPreview.nationality || '-'],
        ['生日', leftPreview.birth_date || '未知', rightPreview.birth_date || '未知'],
        ['年龄', leftPreview.age ?? '-', rightPreview.age ?? '-'],
        ['位置', leftPreview.position || '-', rightPreview.position || '-'],
        ['CA / PA', `${leftPreview.preview_ca ?? leftPreview.ca ?? '-'} / ${leftPreview.pa ?? '-'}`, `${rightPreview.preview_ca ?? rightPreview.ca ?? '-'} / ${rightPreview.pa ?? '-'}`],
        ['身高', formatHeight(leftPreview.height), formatHeight(rightPreview.height)],
        ['左脚', leftPreview.left_foot ?? '-', rightPreview.left_foot ?? '-'],
        ['右脚', leftPreview.right_foot ?? '-', rightPreview.right_foot ?? '-'],
        ['HEIGO', leftPreview.heigo_club || '-', rightPreview.heigo_club || '-'],
    ];

    return `
        <section class="comparison-meta-card">
            <h4>基础信息</h4>
            <div class="comparison-meta-list">
                ${rows.map(([label, leftValue, rightValue]) => `
                    <div class="comparison-meta-row">
                        <span class="comparison-meta-value is-blue">${escapeHtml(leftValue)}</span>
                        <span class="comparison-meta-label">${escapeHtml(label)}</span>
                        <span class="comparison-meta-value is-red">${escapeHtml(rightValue)}</span>
                    </div>
                `).join('')}
            </div>
        </section>
    `;
}

function mergeCompareItems(leftItems, rightItems) {
    const registry = new Map();
    const merged = [];

    leftItems.forEach(item => {
        const entry = {key: item.key, label: item.label, left: Number(item.value) || 0, right: 0};
        registry.set(item.key, entry);
        merged.push(entry);
    });

    rightItems.forEach(item => {
        const rightValue = Number(item.value) || 0;
        if (registry.has(item.key)) {
            registry.get(item.key).right = rightValue;
            return;
        }
        const entry = {key: item.key, label: item.label, left: 0, right: rightValue};
        registry.set(item.key, entry);
        merged.push(entry);
    });

    return merged;
}

function renderComparisonMetricRow(item) {
    const leftValue = Math.max(0, Number(item.left) || 0);
    const rightValue = Math.max(0, Number(item.right) || 0);
    const delta = Math.abs(leftValue - rightValue);
    const leftLead = leftValue > rightValue;
    const rightLead = rightValue > leftValue;
    const leftWidth = leftLead ? Math.min(50, (delta / 20) * 50) : 0;
    const rightWidth = rightLead ? Math.min(50, (delta / 20) * 50) : 0;
    const leftDisplay = leftLead ? `+${delta}` : '';
    const rightDisplay = rightLead ? `+${delta}` : '';
    const rowState = delta === 0 ? 'is-even' : leftLead ? 'is-blue-win' : 'is-red-win';

    return `
        <div class="compare-row ${rowState}">
            <div class="compare-value is-blue ${leftLead ? 'is-lead' : 'is-muted'}">${leftDisplay || '&nbsp;'}</div>
            <div class="compare-track-wrap">
                <div class="compare-track-label">${escapeHtml(item.label)}</div>
                <div class="compare-track">
                    <span class="compare-track-center"></span>
                    <span class="compare-track-fill compare-track-fill-blue" style="width:${leftWidth}%;"></span>
                    <span class="compare-track-fill compare-track-fill-red" style="width:${rightWidth}%;"></span>
                </div>
            </div>
            <div class="compare-value is-red ${rightLead ? 'is-lead' : 'is-muted'}">${rightDisplay || '&nbsp;'}</div>
        </div>
    `;
}

function renderComparisonMetricPanel(title, leftItems, rightItems, options = {}) {
    const merged = mergeCompareItems(leftItems, rightItems).filter(item => options.includeLowValues || item.left > 0 || item.right > 0);
    if (!merged.length) return '';
    return `
        <section class="comparison-panel ${options.wide ? 'comparison-panel-wide' : ''}">
            <div class="comparison-panel-head">
                <h4>${escapeHtml(title)}</h4>
            </div>
            <div class="comparison-metric-list">
                ${merged.map(renderComparisonMetricRow).join('')}
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

function openComparisonWorkspace() {
    normalizeCompareSlots();
    if (playerCompareSlots.filter(Boolean).length < 2) {
        showModal('无法开始对比', '请先在球员详情页加入两名球员，再打开对比界面。');
        return;
    }
    comparisonModalOpen = true;
    const overlay = document.getElementById('comparisonOverlay');
    overlay.classList.add('active');
    overlay.setAttribute('aria-hidden', 'false');
    renderComparisonWorkspace();
}

function closeComparisonWorkspace() {
    comparisonModalOpen = false;
    const overlay = document.getElementById('comparisonOverlay');
    overlay.classList.remove('active');
    overlay.setAttribute('aria-hidden', 'true');
}

function renderComparisonWorkspace() {
    const content = document.getElementById('comparisonContent');
    if (!content) return;

    normalizeCompareSlots();
    const leftSlot = playerCompareSlots[0];
    const rightSlot = playerCompareSlots[1];
    if (!leftSlot || !rightSlot) {
        content.innerHTML = '<div class="no-data">对比夹中需要同时存在两名球员。</div>';
        return;
    }

    const leftPreview = buildPreviewPlayer(leftSlot.player, leftSlot.step);
    const rightPreview = buildPreviewPlayer(rightSlot.player, rightSlot.step);
    const leftCollections = getPlayerFieldCollections(leftPreview);
    const rightCollections = getPlayerFieldCollections(rightPreview);
    const technicalTitle = leftCollections.isGoalkeeper || rightCollections.isGoalkeeper ? '技术 / 门将' : '技术 / 定位球';
    const positionItemsLeft = leftCollections.positions.filter(item => item.value > 1);
    const positionItemsRight = rightCollections.positions.filter(item => item.value > 1);

    content.innerHTML = `
        <div class="comparison-stage">
            <div class="comparison-hero-grid">
                ${buildComparisonPlayerCard(leftSlot, 0)}
                <div class="comparison-center-stack">
                    ${buildComparisonRadarSvg(leftPreview, rightPreview)}
                    ${buildComparisonMetaCard(leftPreview, rightPreview)}
                </div>
                ${buildComparisonPlayerCard(rightSlot, 1)}
            </div>
            <div class="comparison-grid">
                ${renderComparisonMetricPanel(technicalTitle, leftCollections.technical.concat(leftCollections.setPieces), rightCollections.technical.concat(rightCollections.setPieces))}
                ${renderComparisonMetricPanel('精神', leftCollections.mental, rightCollections.mental)}
                ${renderComparisonMetricPanel('身体', leftCollections.physical, rightCollections.physical)}
                ${renderComparisonMetricPanel('隐藏', leftCollections.hidden, rightCollections.hidden, {wide: true})}
                ${renderComparisonMetricPanel('位置熟练度', positionItemsLeft, positionItemsRight, {wide: true})}
            </div>
        </div>
    `;
}

