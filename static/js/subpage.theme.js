function updateSubpageThemeToggle() {
    const mode = localStorage.getItem('themeMode') || 'light';
    const icon = document.getElementById('themeIcon');
    const text = document.getElementById('themeText');

    if (icon) {
        icon.textContent = mode === 'dark' ? '☀️' : '🌙';
    }

    if (text) {
        text.textContent = mode === 'dark' ? '切换白天' : '切换夜间';
    }
}

function applyStoredTheme() {
    const mode = localStorage.getItem('themeMode') || 'light';
    document.body.classList.toggle('light-mode', mode !== 'dark');
    updateSubpageThemeToggle();
}

function toggleTheme() {
    const nextMode = document.body.classList.contains('light-mode') ? 'dark' : 'light';
    localStorage.setItem('themeMode', nextMode);
    applyStoredTheme();
}

window.applyStoredTheme = applyStoredTheme;
window.toggleTheme = toggleTheme;
