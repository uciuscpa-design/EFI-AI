$ErrorActionPreference = 'Stop'

$repo = 'C:\Users\shannon\Documents\EFI-AI'
$pidFile = Join-Path $repo 'data\gexy\runtime\gexy-ui.pid'

if (-not (Test-Path $pidFile)) {
    [pscustomobject]@{ status = 'not_running'; reason = 'pid_file_missing' } | ConvertTo-Json
    exit 0
}

$pidText = (Get-Content $pidFile -Raw).Trim()
$serverPid = 0
if (-not [int]::TryParse($pidText, [ref]$serverPid)) {
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    [pscustomobject]@{ status = 'not_running'; reason = 'invalid_pid_file' } | ConvertTo-Json
    exit 0
}

$process = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
if ($process) {
    Stop-Process -Id $serverPid -Force
}
Remove-Item $pidFile -Force -ErrorAction SilentlyContinue

[pscustomobject]@{
    status = 'stopped'
    pid = $serverPid
} | ConvertTo-Json
