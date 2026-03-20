$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    & (Join-Path $PSScriptRoot 'release-docs-check.ps1')
    & (Join-Path $PSScriptRoot 'run-core-regressions.ps1')
    $venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
    $python = if (Test-Path $venvPython) { $venvPython } else { 'python' }
    & $python -m unittest `
        test_bot_callback.py `
        test_bot_command_service.py `
        test_bot_health.py `
        test_bot_player_image_reply.py `
        test_bot_render_service.py `
        test_bot_signature_service.py `
        test_bot_svg_renderer.py
} finally {
    Pop-Location
}
