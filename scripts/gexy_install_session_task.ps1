$ErrorActionPreference = 'Stop'

$repo = 'C:\Users\shannon\Documents\EFI-AI'
$launcher = Join-Path $repo 'scripts\gexy_collect_session.ps1'
if (-not (Test-Path $launcher)) { throw "GEXY launcher not found: $launcher" }

$taskName = 'GEXY Session Collector'
$powerShell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$action = New-ScheduledTaskAction -Execute $powerShell -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$launcher`"" -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Weekly -WeeksInterval 1 -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 6:20am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 10)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null

$task = Get-ScheduledTask -TaskName $taskName
$info = Get-ScheduledTaskInfo -TaskName $taskName
[pscustomobject]@{
    task_name = $task.TaskName
    state = $task.State.ToString()
    next_run_time = $info.NextRunTime
    last_run_time = $info.LastRunTime
    launcher = $launcher
} | ConvertTo-Json
