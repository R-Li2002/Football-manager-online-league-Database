const SECTION_HEADING_LABELS = {
    Added: '新增',
    Changed: '变更',
    Refactored: '重构',
    Fixed: '修复',
    Removed: '移除',
    Docs: '文档',
    Tests: '测试',
    Summary: '摘要',
};

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function getSectionHeadingLabel(heading) {
    return SECTION_HEADING_LABELS[heading] || heading || '未分类';
}

function getVersionLabel(version, isUnreleased) {
    if (isUnreleased || version === 'Unreleased') {
        return '开发中';
    }
    return version;
}

function getReleaseDateLabel(entry) {
    if (entry.is_unreleased || entry.version === 'Unreleased') {
        return '尚未正式发布';
    }
    return entry.release_date || '未标注日期';
}

function renderUpdates(entries) {
    const container = document.getElementById('updatesTimeline');
    if (!container) return;

    if (!Array.isArray(entries) || !entries.length) {
        container.innerHTML = '<div class="no-data">暂时还没有可展示的更新记录。</div>';
        return;
    }

    container.innerHTML = entries.map(entry => `
        <article class="update-entry">
            <div class="update-entry-head">
                <div>
                    <div class="update-version">${escapeHtml(getVersionLabel(entry.version, entry.is_unreleased))}</div>
                    <div class="update-date">${escapeHtml(getReleaseDateLabel(entry))}</div>
                </div>
                ${entry.is_unreleased ? '<span class="update-badge">未发布</span>' : ''}
            </div>
            <div class="update-section-list">
                ${(entry.sections || []).map(section => `
                    <section class="update-section">
                        <h3>${escapeHtml(getSectionHeadingLabel(section.heading))}</h3>
                        <ul>
                            ${(section.items || []).map(item => `<li>${escapeHtml(item)}</li>`).join('')}
                        </ul>
                    </section>
                `).join('')}
            </div>
        </article>
    `).join('');
}

async function loadProjectUpdates() {
    const container = document.getElementById('updatesTimeline');
    try {
        const response = await fetch('/api/project-updates?limit=20');
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload?.detail || `HTTP ${response.status}`);
        }
        renderUpdates(payload);
    } catch (error) {
        if (container) {
            container.innerHTML = `<div class="no-data">更新记录加载失败：${escapeHtml(error.message || '未知错误')}</div>`;
        }
    }
}

applyStoredTheme();
loadProjectUpdates();
