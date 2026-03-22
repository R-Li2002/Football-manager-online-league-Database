$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    & (Join-Path $PSScriptRoot 'release-docs-check.ps1')
    & (Join-Path $PSScriptRoot 'run-core-regressions.ps1')
    $venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
    $python = if (Test-Path $venvPython) { $venvPython } else { 'python' }
    & $python -m unittest `
        test_bot_nonebot_parser.py `
        test_bot_nonebot_service.py
    & $python -m compileall bot_nonebot
} finally {
    Pop-Location
}
