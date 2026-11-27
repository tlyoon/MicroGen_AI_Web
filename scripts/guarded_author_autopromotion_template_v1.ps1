# Swap source-pinned persistent code worker to a certified new GitHub main.
$ErrorActionPreference='Stop'
$root='C:\Users\tlyoon\AppData\Local\MicroGen_AI_Web_Checkpoints\RECONCILE_20261125'
$backlog='C:\Users\tlyoon\AppData\Local\MicroGen_AI_Web_Checkpoints\LONG_HORIZON_CODE_AUTHOR_V1_20261126'
$taskName='MicroGen_AI_Web_v1_PersistentCodeAuthor'
$oldRepo=Join-Path $root '__OLD_REPO__'
$newRepo=Join-Path $root '__NEW_REPO__'
$newLauncher=Join-Path $newRepo 'scripts\start_microgen_persistent_selenium_author_v1.ps1'
$newHead=(git -C $newRepo rev-parse HEAD).Trim()
$mainHead=(gh api repos/tlyoon/MicroGen_AI_Web/commits/main --jq '.sha').Trim()
if($LASTEXITCODE -ne 0 -or $newHead -ne $mainHead -or $newHead -notmatch '^[a-f0-9]{40}$' -or @(git -C $newRepo status --porcelain).Count -ne 0){throw 'New author revision is not certified clean GitHub main'}
if(-not(Test-Path $newLauncher) -or -not(Test-Path (Join-Path $newRepo 'selenium_pipeline\development_persistent_selenium_author_v1.py'))){throw 'Certified worker source/launcher missing'}
$task=Get-ScheduledTask -TaskName $taskName
if($task.State.ToString() -ne 'Running' -or $task.Principal.LogonType.ToString() -ne 'Interactive' -or $task.Principal.RunLevel.ToString() -ne 'Limited' -or $task.Settings.MultipleInstances.ToString() -ne 'IgnoreNew' -or @($task.Actions).Count -ne 1){throw 'Old worker task authorization differs'}
$action=$task.Actions[0]
$oldArgs=$action.Arguments
if($action.WorkingDirectory -ne $oldRepo -or $oldArgs -notlike '*start_microgen_persistent_selenium_author_v1.ps1*' -or $oldArgs -notlike "*$oldRepo*" -or $action.Execute -notlike '*powershell*'){throw 'Original worker task not source-identical'}
$hbfile=Join-Path $backlog 'worker_heartbeat.json'
$before=Get-Content -Raw $hbfile|ConvertFrom-Json
$oldPid=[int]$before.worker_pid
$oldOwner=Get-CimInstance Win32_Process -Filter ("ProcessId="+$oldPid)
if($null -eq $oldOwner -or $oldOwner.CommandLine -notlike '*development_persistent_selenium_author_v1*' -or $before.new_paid_api_requests -ne 0 -or $before.student_publication_authorized -ne $false){throw 'Original worker PID/heartbeat not certified'}
$oldParent=Get-CimInstance Win32_Process -Filter ("ProcessId="+$oldOwner.ParentProcessId)
if($null -eq $oldParent -or $oldParent.CommandLine -notlike "*$oldRepo*"){throw 'Old author process parent not anchored to original repo'}
$seen=@(Get-ChildItem (Join-Path $backlog 'inbox') -Filter '*.json' -File)
if($seen.Count -lt 1 -or $seen.Count -gt 16){throw 'Original source job inventory invalid'}
$allowed=@('SOURCE_CANDIDATE_TESTED_NO_PUBLICATION','UNSAFE_MODEL_REPLY_QUARANTINED','SOURCE_TEST_FAILED_QUARANTINED','PROVIDER_SEND_UNCERTAIN_NO_REPLAY','SOURCE_INPUT_CHANGED_NO_SEND')
$originalHashes=@{}
foreach($item in $seen){
    $state=Join-Path $backlog ('state\'+$item.BaseName+'\coding_state.json')
    if(-not(Test-Path $state)){throw 'New source claim may still be running; no cutover'}
    $value=Get-Content -Raw $state|ConvertFrom-Json
    if($allowed -notcontains $value.status){throw 'Model Send may be in flight; no cutover'}
    $originalHashes[$state]=(Get-FileHash $state -Algorithm SHA256).Hash
}
$oldHBepoch=[double]$before.heartbeat_epoch
$oldArgsSnapshot=$oldArgs
$newArgs=$oldArgs.Replace($oldRepo,$newRepo)
if($newArgs -eq $oldArgs -or $newArgs -notlike "*$newRepo*"){throw 'Cannot construct next source-identical task'}
Export-ScheduledTask -TaskName $taskName|Set-Content (Join-Path $root '__TASK_BEFORE__') -Encoding UTF8
$stopped=$false
try{
    Stop-ScheduledTask -TaskName $taskName
    $stopped=$true
    $gone=$false
    for($i=0;$i -lt 30;$i++){
        if($null -eq (Get-CimInstance Win32_Process -Filter ("ProcessId="+$oldPid))){$gone=$true;break}
        Start-Sleep -Seconds 1
    }
    if(-not $gone){throw 'Original code worker still running: quarantine cutover'}
    foreach($state in $originalHashes.Keys){
        if((Get-FileHash $state -Algorithm SHA256).Hash -ne $originalHashes[$state]){throw 'Original model request checkpoint changed during cutover'}
    }
    $newAction=New-ScheduledTaskAction -Execute $action.Execute -Argument $newArgs -WorkingDirectory $newRepo
    Set-ScheduledTask -TaskName $taskName -Action $newAction|Out-Null
    $updated=Get-ScheduledTask -TaskName $taskName
    if($updated.Actions[0].WorkingDirectory -ne $newRepo -or $updated.Actions[0].Arguments -ne $newArgs -or $updated.Principal.RunLevel.ToString() -ne 'Limited'){throw 'New code worker policy drift'}
    Start-ScheduledTask -TaskName $taskName
    $ok=$false
    for($i=0;$i -lt 40;$i++){
        Start-Sleep -Seconds 1
        try{
            $h=Get-Content -Raw $hbfile|ConvertFrom-Json
            $newPid=[int]$h.worker_pid
            $p=Get-CimInstance Win32_Process -Filter ("ProcessId="+$newPid)
            if($newPid -ne $oldPid -and $h.heartbeat_epoch -gt $oldHBepoch -and $h.new_paid_api_requests -eq 0 -and $h.student_publication_authorized -eq $false -and $null -ne $p -and $p.CommandLine -like '*development_persistent_selenium_author_v1*'){$ok=$true;break}
        }catch{}
    }
    if(-not $ok){throw 'New persistent coding worker not independently attested'}
    $proof=[ordered]@{status='CERTIFIED_PERSISTENT_CODE_WRITER_CUTOVER';old_repo=$oldRepo;new_repo=$newRepo;new_commit=$newHead;old_pid=$oldPid;new_pid=$newPid;source_claims_unchanged=$true;new_paid_gemini_api_calls=0;student_publication_authorized=$false;timestamp_utc=[DateTime]::UtcNow.ToString('o')}
    $proof|ConvertTo-Json -Depth 5|Set-Content (Join-Path $root '__AUTHOR_RECEIPT__') -Encoding UTF8
    Write-Output 'PERSISTENT_WRITER_GUARDED_CUTOVER_SUCCESS'
    $proof|ConvertTo-Json -Depth 5
}catch{
    $message=$_.Exception.Message
    Write-Output ('PERSISTENT_WRITER_CUTOVER_ERROR '+$message)
    if($stopped){
        try{
            $restored=New-ScheduledTaskAction -Execute $action.Execute -Argument $oldArgsSnapshot -WorkingDirectory $oldRepo
            Set-ScheduledTask -TaskName $taskName -Action $restored|Out-Null
            Start-ScheduledTask -TaskName $taskName
            Write-Output 'PERSISTENT_WRITER_ROLLBACK_REQUESTED'
        }catch{Write-Output ('PERSISTENT_WRITER_ROLLBACK_ERROR '+$_.Exception.Message)}
    }
    throw $message
}
