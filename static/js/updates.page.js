function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function applyStoredTheme() {
    const mode = localStorage.getItem('themeMode') || 'light';
    document.body.classList.toggle('light-mode', mode !== 'dark');
}

function renderUpdates(entries) {
    const container = document.getElementById('updatesTimeline');
    if (!container) return;

    if (!Array.isArray(entries) || !entries.length) {
        container.innerHTML = '<div class="no-data">暂时还没有可展示的项目更新记录。</div>';
        return;
    }

    container.innerHTML = entries.map(entry => `
        <article class="update-entry">
            <div class="update-entry-head">
                <div>
                    <div class="update-version">${escapeHtml(entry.version)}</div>
                    <div class="update-date">${escapeHtml(entry.release_date || '未标注日期')}</div>
                </div>
                ${entry.is_unreleased ? '<span class="update-badge">Unreleased</span>' : ''}
            </div>
            <div class="update-section-list">
                ${(entry.sections || []).map(section => `
                    <section class="update-section">
                        <h3>${escapeHtml(section.heading)}</h3>
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
