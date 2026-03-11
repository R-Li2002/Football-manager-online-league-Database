param(
    [string]$Host = "127.0.0.1",
    [int]$Port = 8001
)

[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$env:LOCAL_HOST = $Host
$env:LOCAL_PORT = [string]$Port

python D:\HEIGOOA\main1.py
