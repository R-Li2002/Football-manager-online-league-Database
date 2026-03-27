function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function renderFeedbackSubmitResult(payload, isError = false) {
    const container = document.getElementById('feedbackSubmitResult');
    if (!container) return;
    container.innerHTML = isError
        ? `<div class="feedback-result-card is-error">${escapeHtml(payload)}</div>`
        : `
            <div class="feedback-result-card is-success">
                <strong>提交成功</strong>
                <p>${escapeHtml(payload.message || '')}</p>
                <div class="feedback-result-meta">反馈编号：#${escapeHtml(payload.report_id)} | 当前状态：${escapeHtml(payload.status)}</div>
            </div>
        `;
}

async function handleDataFeedbackSubmit(event) {
    event.preventDefault();

    const payload = {
        player_uid: document.getElementById('feedbackPlayerUid')?.value ? Number(document.getElementById('feedbackPlayerUid').value) : null,
        player_name: document.getElementById('feedbackPlayerName')?.value.trim() || null,
        issue_type: document.getElementById('feedbackIssueType')?.value || 'other',
        summary: document.getElementById('feedbackSummary')?.value.trim() || '',
        details: document.getElementById('feedbackDetails')?.value.trim() || '',
        suggested_correction: document.getElementById('feedbackSuggestedCorrection')?.value.trim() || null,
        contact: document.getElementById('feedbackContact')?.value.trim() || null,
        source_page: document.referrer || '/data-feedback',
        website: document.getElementById('feedbackWebsite')?.value || '',
    };

    try {
        const response = await fetch('/api/data-feedback', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload),
        });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(result?.detail || `HTTP ${response.status}`);
        }
        renderFeedbackSubmitResult(result);
        document.getElementById('dataFeedbackForm')?.reset();
    } catch (error) {
        renderFeedbackSubmitResult(`提交失败：${error.message || '未知错误'}`, true);
    }
}

applyStoredTheme();
document.getElementById('dataFeedbackForm')?.addEventListener('submit', handleDataFeedbackSubmit);
