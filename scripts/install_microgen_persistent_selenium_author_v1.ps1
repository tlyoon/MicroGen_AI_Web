# Install exactly one interactive, restartable development writer.
# Run only AFTER protected GitHub main merge and guarded certified deployment.
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$root='C:\Users\tlyoon\AppData\Local\MicroGen_AI_Web_Checkpoints\RECONCILE_20261125'
$backlog='C:\Users\tlyoon\AppData\Local\MicroGen_AI_Web_Checkpoints\LONG_HORIZON_CODE_AUTHOR_V1_20261126'
$task='MicroGen_AI_Web_v1_PersistentCodeAuthor'
$sha=(git -C $repo rev-parse HEAD).Trim()
$main=(gh api repos/tlyoon/MicroGen_AI_Web/commits/main --jq '.sha').Trim()
if($LASTEXITCODE -ne 0 -or $sha -ne $main){throw 'Refuse to install author from non-certified GitHub main'}
$old=Join-Path $root 'live_state_migrated_v1\daemon_heartbeat.json'
if(-not(Test-Path $old)){throw 'Original read-only daemon checkpoint missing'}
$state=Get-Content -Raw $old|ConvertFrom-Json
if($state.provider_sends -ne 0 -or $state.running -ne $true){throw 'Original offline daemon invariant changed'}
if(-not(Test-Path (Join-Path $backlog 'inbox')) -or -not(Test-Path (Join-Path $backlog 'state'))){throw 'Isolated code backlog missing'}
$launcher=Join-Path $PSScriptRoot 'start_microgen_persistent_selenium_author_v1.ps1'
$argument='-NoProfile -ExecutionPolicy Bypass -File "'+$launcher+'"'
$action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $argument -WorkingDirectory $repo
$trigger=New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$principal=New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$existing=Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue
if($existing){
    if($existing.Actions.Count -ne 1 -or $existing.Actions[0].Execute -notlike '*powershell*' -or $existing.Actions[0].Arguments -ne $argument -or $existing.Actions[0].WorkingDirectory -ne $repo){throw 'Existing unattended writer task differs: do not overwrite'}
}else{
    Register-ScheduledTask -TaskName $task -Action $action -Trigger $trigger -Principal $principal -Settings $settings |Out-Null
}
Start-ScheduledTask -TaskName $task
$found=Get-ScheduledTask -TaskName $task
if($found.State -ne 'Running'){throw 'Autonomous code writer did not enter RUNNING state'}
Write-Output ('PERSISTENT_CODE_WRITER_STARTED task='+$task+' source='+$sha+' repo='+$repo)
