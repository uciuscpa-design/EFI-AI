$ErrorActionPreference = 'Stop'

$repo = 'C:\Users\shannon\Documents\EFI-AI'
Set-Location $repo

$envFile = Join-Path $repo '.env'
if (-not (Test-Path $envFile)) { throw '.env not found in EFI-AI repo' }

foreach ($line in Get-Content $envFile) {
    if ($line -match '^APCA_API_KEY_ID=(.*)$') {
        $env:APCA_API_KEY_ID = $Matches[1].Trim().Trim('"').Trim("'")
    }
    elseif ($line -match '^APCA_API_SECRET_KEY=(.*)$') {
        $env:APCA_API_SECRET_KEY = $Matches[1].Trim().Trim('"').Trim("'")
    }
}
if (-not $env:APCA_API_KEY_ID -or -not $env:APCA_API_SECRET_KEY) {
    throw 'Alpaca credentials missing from .env'
}

$env:PYTHONPATH = $repo
$logDir = Join-Path $repo 'data\gexy\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format 'yyyy-MM-dd'
$logFile = Join-Path $logDir "session-$stamp.log"

"[$(Get-Date -Format o)] GEXY session collector starting" | Tee-Object -FilePath $logFile -Append
& python scripts\gexy_session_collector.py --interval-seconds 60 --tolerance-seconds 90 2>&1 |
    Tee-Object -FilePath $logFile -Append
$exitCode = $LASTEXITCODE
"[$(Get-Date -Format o)] GEXY session collector exited code=$exitCode" | Tee-Object -FilePath $logFile -Append
exit $exitCode
