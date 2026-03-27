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
        showModal('瀵规瘮澶瑰凡婊?, '鏈€澶氭敮鎸佸悓鏃跺姣?2 鍚嶇悆鍛橈紝璇峰厛浠庡彸渚у姣斿す绉婚櫎涓€鍚嶅悗鍐嶅姞鍏ャ€?);
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
                            <h4>瀵规瘮澶?/h4>
                            <div class="compare-dock-summary">${compareNames.length ? compareNames.join(' vs ') : '杩樻病鏈夊姞鍏ュ姣旂悆鍛?}</div>
                        </div>
                        ${filledCount ? '<button class="compare-dock-clear" type="button" onclick="clearCompareSlots()">娓呯┖</button>' : ''}
                    </div>
                    <div class="compare-slot-list">
                        ${playerCompareSlots.map((slot, index) => {
                            if (!slot) {
                                return `
                                    <div class="compare-slot is-empty">
                                        <span class="compare-slot-index">妲戒綅 ${index + 1}</span>
                                        <p>鍦ㄧ悆鍛樿鎯呴〉鐐瑰嚮鈥滃姞鍏ュ姣斺€?/p>
                                    </div>
                                `;
                            }
                            const previewPlayer = buildPreviewPlayer(slot.player, slot.step);
                            return `
                                <div class="compare-slot is-filled is-${index === 0 ? 'blue' : 'red'}">
                                    <span class="compare-slot-index">妲戒綅 ${index + 1}</span>
                                    <div class="compare-slot-name">${escapeHtml(slot.player.name)}</div>
                                    <div class="compare-slot-meta">${escapeHtml(slot.player.position || '-')} 路 ${escapeHtml(getPlayerDataVersion(slot.player))} 路 成长预览 +${clampGrowthPreviewStep(slot.step)}</div>
                                    <div class="compare-slot-actions">
                                        <button class="compare-slot-action" type="button" onclick="showPlayerDetail(${slot.player.uid}, {returnTab: '${detailReturnTab}', returnSubtab: '${detailReturnSubtab}', version: '${escapeHtml(getPlayerDataVersion(slot.player))}'})">鏌ョ湅鐞冨憳</button>
                                        <button class="compare-slot-action is-danger" type="button" onclick="removePlayerFromCompare(${index})">绉婚櫎</button>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                    <div class="compare-dock-actions">
                        <button class="btn btn-primary compare-run-button" type="button" onclick="openComparisonWorkspace()" ${filledCount < 2 ? 'disabled' : ''}>鏌ョ湅瀵规瘮椤?/button>
                    </div>
                </div>
            ` : ''}
            <button
                class="compare-dock-handle ${filledCount ? 'has-items' : 'is-empty'} ${compareDockExpanded ? 'is-expanded' : ''}"
                type="button"
                onclick="toggleCompareDock()"
                aria-expanded="${compareDockExpanded}"
                aria-label="${compareDockExpanded ? '鏀惰捣瀵规瘮澶? : '灞曞紑瀵规瘮澶?}"
            >
                <span class="compare-dock-handle-dot">${filledCount ? filledCount : '+'}</span>
                <span class="compare-dock-handle-label">${compareDockExpanded ? '鏀惰捣' : '瀵规瘮澶?}</span>
                <span class="compare-dock-handle-meta">${filledCount}/2</span>
            </button>
        </div>
    `;
}

function buildComparisonSlider(slotIndex, slot) {
    const labels = ['褰撳墠', '+1', '+2', '+3', '+4', '+5'];
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
                aria-label="瀵规瘮鎴愰暱棰勮"
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
                    <div class="comparison-player-version">UID ${escapeHtml(slot.player.uid)} 路 ${escapeHtml(getPlayerDataVersion(slot.player))}</div>
                </div>
                <div class="comparison-player-tag">${escapeHtml(slot.player.position || '-')}</div>
            </div>
            <div class="comparison-player-club">${escapeHtml(slot.player.heigo_club || '-')} / ${escapeHtml(slot.player.club || '-')}</div>
            ${buildComparisonSlider(slotIndex, slot)}
            <div class="comparison-player-badges">
                <span class="foot-badge">成长预览 <strong>+${clampGrowthPreviewStep(slot.step)}</strong></span>
                <span class="foot-badge">PA <strong>${escapeHtml(slot.player.pa ?? '-')}</strong></span>
                <span class="foot-badge">宸﹁剼 <strong>${escapeHtml(previewPlayer.left_foot ?? '-')}</strong></span>
                <span class="foot-badge">鍙宠剼 <strong>${escapeHtml(previewPlayer.right_foot ?? '-')}</strong></span>
                ${weakFootPreview ? `<span class="foot-badge">${weakFootPreview.label}閫嗚冻 <strong>+1</strong></span>` : ''}
            </div>
        </section>
    `;
}

function buildComparisonMetaCard(leftPreview, rightPreview) {
    const rows = [
        ['UID', leftPreview.uid, rightPreview.uid],
        ['鐗堟湰', getPlayerDataVersion(leftPreview) || '-', getPlayerDataVersion(rightPreview) || '-'],
        ['鍥界睄', leftPreview.nationality || '-', rightPreview.nationality || '-'],
        ['鐢熸棩', leftPreview.birth_date || '鏈煡', rightPreview.birth_date || '鏈煡'],
        ['骞撮緞', leftPreview.age ?? '-', rightPreview.age ?? '-'],
        ['浣嶇疆', leftPreview.position || '-', rightPreview.position || '-'],
        ['CA / PA', `${leftPreview.ca ?? '-'} / ${leftPreview.pa ?? '-'}`, `${rightPreview.ca ?? '-'} / ${rightPreview.pa ?? '-'}`],
        ['韬珮', formatHeight(leftPreview.height), formatHeight(rightPreview.height)],
        ['宸﹁剼', leftPreview.left_foot ?? '-', rightPreview.left_foot ?? '-'],
        ['鍙宠剼', leftPreview.right_foot ?? '-', rightPreview.right_foot ?? '-'],
        ['HEIGO', leftPreview.heigo_club || '-', rightPreview.heigo_club || '-'],
    ];

    return `
        <section class="comparison-meta-card">
            <h4>鍩虹淇℃伅</h4>
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
        showModal('鏃犳硶寮€濮嬪姣?, '璇峰厛鍦ㄧ悆鍛樿鎯呴〉鍔犲叆涓ゅ悕鐞冨憳锛屽啀鎵撳紑瀵规瘮鐣岄潰銆?);
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
        content.innerHTML = '<div class="no-data">瀵规瘮澶逛腑闇€瑕佸悓鏃跺瓨鍦ㄤ袱鍚嶇悆鍛樸€?/div>';
        return;
    }

    const leftPreview = buildPreviewPlayer(leftSlot.player, leftSlot.step);
    const rightPreview = buildPreviewPlayer(rightSlot.player, rightSlot.step);
    const leftCollections = getPlayerFieldCollections(leftPreview);
    const rightCollections = getPlayerFieldCollections(rightPreview);
    const technicalTitle = leftCollections.isGoalkeeper || rightCollections.isGoalkeeper ? '鎶€鏈?/ 闂ㄥ皢' : '鎶€鏈?/ 瀹氫綅鐞?;
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
                ${renderComparisonMetricPanel('绮剧', leftCollections.mental, rightCollections.mental)}
                ${renderComparisonMetricPanel('韬綋', leftCollections.physical, rightCollections.physical)}
                ${renderComparisonMetricPanel('闅愯棌', leftCollections.hidden, rightCollections.hidden, {wide: true})}
                ${renderComparisonMetricPanel('浣嶇疆鐔熺粌搴?, positionItemsLeft, positionItemsRight, {wide: true})}
            </div>
        </div>
    `;
}


