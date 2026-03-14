param(
    [string]$Host = "127.0.0.1",
    [int]$Port = 8001
)

[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:ALLOW_MANUAL_RUNTIME_FALLBACK = "1"

$env:LOCAL_HOST = $Host
$env:LOCAL_PORT = [string]$Port

$pythonPath = if (Test-Path 'D:\HEIGOOA\.venv\Scripts\python.exe') { 'D:\HEIGOOA\.venv\Scripts\python.exe' } else { 'python' }
& $pythonPath D:\HEIGOOA\main1.py
