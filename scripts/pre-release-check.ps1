$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    & (Join-Path $PSScriptRoot 'release-docs-check.ps1')
    & (Join-Path $PSScriptRoot 'run-core-regressions.ps1')
} finally {
    Pop-Location
}
