$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
$python = if (Test-Path $venvPython) { $venvPython } else { 'python' }

Push-Location $repoRoot
try {
    & $python -m unittest `
        test_health_contract.py `
        test_admin_bootstrap_config.py `
        test_admin_session_cookie.py `
        test_internal_share_page.py `
        test_internal_render_svg.py `
        test_share_card_presenter.py `
        test_search_normalization.py

    & node test_frontend_search_normalization.js
    & node test_frontend_admin_entry.js
    & node test_frontend_admin_auth.js
} finally {
    Pop-Location
}
