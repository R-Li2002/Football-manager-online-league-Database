[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$versionPath = Join-Path $repoRoot "VERSION"
$readmePath = Join-Path $repoRoot "README.md"
$changelogPath = Join-Path $repoRoot "CHANGELOG.md"
$manualPath = Join-Path $repoRoot "docs\PROJECT_MANUAL.md"

$errors = New-Object System.Collections.Generic.List[string]
$warnings = New-Object System.Collections.Generic.List[string]
$infos = New-Object System.Collections.Generic.List[string]

function Add-CheckError {
    param([string]$Message)
    $script:errors.Add($Message)
}

function Add-CheckWarning {
    param([string]$Message)
    $script:warnings.Add($Message)
}

function Add-CheckInfo {
    param([string]$Message)
    $script:infos.Add($Message)
}

function Require-File {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        Add-CheckError "Missing file: $Path"
        return $false
    }
    return $true
}

function Read-Utf8File {
    param([string]$Path)
    Get-Content -Path $Path -Raw -Encoding UTF8
}

function Test-Contains {
    param(
        [string]$Content,
        [string]$Needle,
        [string]$Label
    )

    if ($Content -notmatch [regex]::Escape($Needle)) {
        Add-CheckError "$Label is missing required reference: $Needle"
    }
}

Add-CheckInfo "Repo root: $repoRoot"

$allPresent = $true
foreach ($path in @($versionPath, $readmePath, $changelogPath, $manualPath)) {
    if (-not (Require-File $path)) {
        $allPresent = $false
    }
}

if (-not $allPresent) {
    $errors | ForEach-Object { Write-Host "ERROR: $_" -ForegroundColor Red }
    exit 1
}

$version = (Read-Utf8File $versionPath).Trim()
$readme = Read-Utf8File $readmePath
$changelog = Read-Utf8File $changelogPath
$manual = Read-Utf8File $manualPath

if ([string]::IsNullOrWhiteSpace($version)) {
    Add-CheckError "VERSION is empty."
}
elseif ($version -notmatch "^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$") {
    Add-CheckError "VERSION format is invalid: $version"
}
else {
    Add-CheckInfo "Detected version: $version"
}

Test-Contains -Content $readme -Needle "VERSION" -Label "README.md"
Test-Contains -Content $readme -Needle "CHANGELOG.md" -Label "README.md"
Test-Contains -Content $readme -Needle "docs/PROJECT_MANUAL.md" -Label "README.md"

if ($readme -notmatch "唯一来源") {
    if ($readme -notmatch [regex]::Escape("Get-Content .\VERSION") -and $readme -notmatch [regex]::Escape("cat ./VERSION")) {
        Add-CheckWarning "README.md does not show how to read VERSION."
    }
}

if (-not [string]::IsNullOrWhiteSpace($version) -and $readme -match [regex]::Escape($version)) {
    Add-CheckError "README.md contains a hardcoded version string: $version"
}

Test-Contains -Content $manual -Needle "VERSION" -Label "docs/PROJECT_MANUAL.md"
Test-Contains -Content $manual -Needle "CHANGELOG.md" -Label "docs/PROJECT_MANUAL.md"
Test-Contains -Content $manual -Needle "README.md" -Label "docs/PROJECT_MANUAL.md"

if ($manual -notmatch "唯一来源") {
    if ($manual -notmatch [regex]::Escape("CHANGELOG.md") -or $manual -notmatch [regex]::Escape("README.md")) {
        Add-CheckWarning "docs/PROJECT_MANUAL.md may be missing version maintenance guidance."
    }
}

if ($changelog -notmatch "(?m)^## \[Unreleased\]\s*$") {
    Add-CheckError "CHANGELOG.md is missing the [Unreleased] section."
}

$releaseMatches = [regex]::Matches($changelog, "(?m)^## \[(?<version>[^\]]+)\] - (?<date>\d{4}-\d{2}-\d{2})\s*$")
if ($releaseMatches.Count -eq 0) {
    Add-CheckError "CHANGELOG.md is missing a released version entry."
}
else {
    $latestReleaseVersion = $releaseMatches[0].Groups["version"].Value.Trim()
    $latestReleaseDate = $releaseMatches[0].Groups["date"].Value.Trim()
    Add-CheckInfo "Latest CHANGELOG release: $latestReleaseVersion ($latestReleaseDate)"

    if (-not [string]::IsNullOrWhiteSpace($version) -and $latestReleaseVersion -ne $version) {
        Add-CheckError "Latest CHANGELOG release ($latestReleaseVersion) does not match VERSION ($version)."
    }
}

foreach ($section in @("### Added", "### Changed", "### Fixed", "### Refactored", "### Docs", "### Removed")) {
    if ($changelog -notmatch [regex]::Escape($section)) {
        Add-CheckWarning "CHANGELOG.md template section not found: $section"
    }
}

Write-Host ""
Write-Host "=== Release Docs Check ===" -ForegroundColor Cyan
$infos | ForEach-Object { Write-Host "INFO: $_" -ForegroundColor DarkCyan }
$warnings | ForEach-Object { Write-Host "WARN: $_" -ForegroundColor Yellow }
$errors | ForEach-Object { Write-Host "ERROR: $_" -ForegroundColor Red }

Write-Host ""
Write-Host ("Summary: {0} error(s), {1} warning(s)" -f $errors.Count, $warnings.Count)

if ($errors.Count -gt 0) {
    exit 1
}

exit 0
