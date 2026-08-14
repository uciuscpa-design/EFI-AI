$ErrorActionPreference = 'Stop'

$repo = 'C:\Users\shannon\Documents\EFI-AI'
$port = 8765
$url = "http://127.0.0.1:$port/"
$healthUrl = "http://127.0.0.1:$port/health"
Set-Location $repo
$env:PYTHONPATH = $repo

$runDir = Join-Path $repo 'data\gexy\runtime'
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$pidFile = Join-Path $runDir 'gexy-ui.pid'
$stdoutLog = Join-Path $runDir 'gexy-ui.stdout.log'
$stderrLog = Join-Path $runDir 'gexy-ui.stderr.log'

function Test-GexyHealth {
    try {
        $response = Invoke-RestMethod -Method Get -Uri $healthUrl -TimeoutSec 2
        return $response.status -eq 'ok'
    } catch {
        return $false
    }
}

if (Test-GexyHealth) {
    Start-Process $url
    [pscustomobject]@{
        status = 'already_running'
        url = $url
        pid = if (Test-Path $pidFile) { (Get-Content $pidFile -Raw).Trim() } else { $null }
    } | ConvertTo-Json
    exit 0
}

$python = (Get-Command python -ErrorAction Stop).Source
$arguments = @(
    '-m', 'uvicorn',
    'apps.gexy_api.main:app',
    '--host', '127.0.0.1',
    '--port', "$port"
)
$process = Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $repo -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru
Set-Content -Path $pidFile -Value $process.Id -Encoding ascii

$healthy = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    Start-Sleep -Milliseconds 250
    if (Test-GexyHealth) {
        $healthy = $true
        break
    }
    if ($process.HasExited) {
        break
    }
}

if (-not $healthy) {
    $errorTail = if (Test-Path $stderrLog) { (Get-Content $stderrLog -Tail 20) -join "`n" } else { '' }
    throw "GEXY UI failed to start. $errorTail"
}

Start-Process $url
[pscustomobject]@{
    status = 'started'
    url = $url
    pid = $process.Id
    stdout_log = $stdoutLog
    stderr_log = $stderrLog
    research_only = $true
    execution_enabled = $false
} | ConvertTo-Json
