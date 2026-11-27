# Safe switch to the CI-certified new main, reusing the exact same v7.1 executor pin.
$ErrorActionPreference='Stop'
$taskName='MicroGen_AI_Web_v71_OfflineDevelopment'
$root='C:\Users\tlyoon\AppData\Local\MicroGen_AI_Web_Checkpoints\RECONCILE_20261125'
$oldRepo=Join-Path $root '__OLD_REPO__'
$newRepo=Join-Path $root '__NEW_REPO__'
$state=Join-Path $root 'live_state_migrated_v1'
$plan='C:\Users\tlyoon\AppData\Local\MicroGen_AI_Web_Checkpoints\CONTINUITY_EXECUTOR_V71_20261121\real_offline_roadmap_20261121.json'
$planSha=(Get-FileHash -Algorithm SHA256 $plan).Hash.ToLowerInvariant()
if($planSha -ne '4c2eec283acb3d34526c6b5a00c93d135c81c082678af2dd2f9b811381bac8c6'){throw 'Plan SHA drift'}
$remote=@(git -C $newRepo ls-remote origin refs/heads/main)
$head=(git -C $newRepo rev-parse HEAD).Trim()
if($LASTEXITCODE -ne 0 -or $remote.Count -ne 1 -or $remote[0] -notmatch '^([0-9a-f]{40})\s+refs/heads/main$' -or $Matches[1] -ne $head){throw 'Candidate does not equal GitHub current main'}
if(@(git -C $newRepo status --porcelain).Count -ne 0){throw 'Candidate dirty'}
$exeRelative='selenium_pipeline\development_continuity_executor_v71.py'
$oldExe=(Get-FileHash -Algorithm SHA256 (Join-Path $oldRepo $exeRelative)).Hash.ToLowerInvariant()
$newExe=(Get-FileHash -Algorithm SHA256 (Join-Path $newRepo $exeRelative)).Hash.ToLowerInvariant()
if($newExe -ne $oldExe){throw 'Executor changed; requires explicit audited checkpoint migration instead'}
$pin=Get-Content -Raw (Join-Path $state 'state.json')|ConvertFrom-Json
if($pin.executor_sha256 -ne $newExe -or $pin.plan_sha256 -ne $planSha){throw 'Saved checkpoint does not match new code or plan'}
$t=Get-ScheduledTask -TaskName $taskName
if($t.State.ToString() -ne 'Running' -or $t.Principal.LogonType.ToString() -ne 'Interactive' -or $t.Principal.RunLevel.ToString() -ne 'Limited' -or $t.Settings.MultipleInstances.ToString() -ne 'IgnoreNew' -or @($t.Actions).Count -ne 1){throw 'Scheduled task policy changed'}
$a=$t.Actions[0]
if($a.WorkingDirectory -ne $oldRepo -or $a.Arguments -notlike "*$oldRepo*" -or $a.Arguments -notlike "*$state*" -or $a.Arguments -notlike '*development_continuity_daemon_v71*'){throw 'Old task not source-identical'}
$hb=Get-Content -Raw (Join-Path $state 'daemon_heartbeat.json')|ConvertFrom-Json
$oldPid=[int]$hb.owner_pid
$oldRun=$hb.run_id
$proc=Get-CimInstance Win32_Process -Filter "ProcessId=$oldPid"
if($hb.running -ne $true -or $hb.provider_sends -ne 0 -or $hb.student_publication_authorized -ne $false -or $null -eq $proc -or $proc.CommandLine -notlike "*$oldRepo*"){throw 'Original daemon live PID is unverified'}
$stateHash=(Get-FileHash -Algorithm SHA256 (Join-Path $state 'state.json')).Hash.ToLowerInvariant()
Export-ScheduledTask -TaskName $taskName|Set-Content (Join-Path $root '__TASK_BEFORE__') -Encoding UTF8
$newArgs=$a.Arguments.Replace($oldRepo,$newRepo)
if($newArgs -eq $a.Arguments){throw 'New args missing'}
$stopped=$false
try{
    Stop-ScheduledTask -TaskName $taskName
    $stopped=$true
    $gone=$false
    for($i=0;$i -lt 30;$i++){if($null -eq (Get-CimInstance Win32_Process -Filter "ProcessId=$oldPid")){$gone=$true;break};Start-Sleep -Seconds 1}
    if(-not $gone){throw 'Old process still running'}
    if((Get-FileHash -Algorithm SHA256 (Join-Path $state 'state.json')).Hash.ToLowerInvariant() -ne $stateHash){throw 'Checkpoint changed during cutover'}
    $action=New-ScheduledTaskAction -Execute $a.Execute -Argument $newArgs -WorkingDirectory $newRepo
    Set-ScheduledTask -TaskName $taskName -Action $action|Out-Null
    $after=Get-ScheduledTask -TaskName $taskName
    if($after.Actions[0].WorkingDirectory -ne $newRepo -or $after.Actions[0].Arguments -ne $newArgs -or $after.Principal.RunLevel.ToString() -ne 'Limited' -or $after.Principal.LogonType.ToString() -ne 'Interactive' -or $after.Settings.MultipleInstances.ToString() -ne 'IgnoreNew'){throw 'Task policy mutation'}
    Start-ScheduledTask -TaskName $taskName
    $verified=$false
    for($i=0;$i -lt 45;$i++){
        Start-Sleep -Seconds 1
        try{
          $n=Get-Content -Raw (Join-Path $state 'daemon_heartbeat.json')|ConvertFrom-Json
          $newPid=[int]$n.owner_pid
          $owner=Get-CimInstance Win32_Process -Filter "ProcessId=$newPid"
          if($n.running -eq $true -and $newPid -ne $oldPid -and $n.run_id -ne $oldRun -and $n.provider_sends -eq 0 -and $n.student_publication_authorized -eq $false -and $n.plan_sha256 -eq $planSha -and $null -ne $owner -and $owner.CommandLine -like "*$newRepo*"){$verified=$true;break}
        }catch{}
    }
    if(-not $verified){throw 'New daemon owner not independently attested'}
    $result=[ordered]@{status='G2_G3_SOURCE_RECOVERY_REVISION_DEPLOYED';new_commit=$head;old_repo=$oldRepo;new_repo=$newRepo;preserved_state=$state;old_pid=$oldPid;new_pid=$newPid;old_run=$oldRun;new_run=$n.run_id;checkpoint_pin_unchanged=$true;provider_sends=0;student_publication_authorized=$false;timestamp_utc=[DateTime]::UtcNow.ToString('o')}
    $result|ConvertTo-Json -Depth 6|Set-Content (Join-Path $root '__MAIN_RECEIPT__') -Encoding UTF8
    Write-Output 'GUARDED_CUTOVER_SUCCESS'
    $result|ConvertTo-Json -Depth 6
}catch{
    $problem=$_.Exception.Message
    Write-Output ('CUTOVER_ERROR '+$problem)
    if($stopped){
       try{
          $action=New-ScheduledTaskAction -Execute $a.Execute -Argument $a.Arguments -WorkingDirectory $oldRepo
          Set-ScheduledTask -TaskName $taskName -Action $action|Out-Null
          Start-ScheduledTask -TaskName $taskName
          Write-Output 'ORIGINAL_DAEMON_RESTART_REQUESTED'
       }catch{Write-Output ('ROLLBACK_ERROR '+$_.Exception.Message)}
    }
    throw $problem
}
