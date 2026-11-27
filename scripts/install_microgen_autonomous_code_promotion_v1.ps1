# Provision independently restartable long-horizon PR/CI/guarded-deploy Windows task.
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$main=(gh api repos/tlyoon/MicroGen_AI_Web/commits/main --jq '.sha').Trim()
$head=(git -C $repo rev-parse HEAD).Trim()
if($LASTEXITCODE -ne 0 -or $head -ne $main -or @(git -C $repo status --porcelain).Count -ne 0){throw 'Installer only allowed from clean GitHub-certified latest main'}
$base='C:\Users\tlyoon\AppData\Local\MicroGen_AI_Web_Checkpoints'
$backlog=Join-Path $base 'LONG_HORIZON_CODE_AUTHOR_V1_20261126'
$control=Join-Path $base 'AUTONOMOUS_CODE_PROMOTION_V1_20261127'
$worktrees=Join-Path $base 'MICROGEN_AUTONOMOUS_CODE_WORKTREES_V1'
$catalogSource=Join-Path $repo 'development_specs\approved_source_jobs_v1.json'
$catalogDest=Join-Path $backlog 'approved_source_jobs_v1.json'
$tests=@('g3_captioned_png_asset_coverage_v1.py','g3_narration_segment_page_index_v1.py')
foreach($required in @($catalogSource,(Join-Path $backlog 'worker_heartbeat.json'),(Join-Path $repo 'selenium_pipeline\development_autonomous_code_loop_v1.py'))){if(-not(Test-Path $required)){throw 'Required source or original worker heartbeat missing'}}
foreach($name in @('MicroGen_AI_Web_v71_OfflineDevelopment','MicroGen_AI_Web_v1_PersistentCodeAuthor')){$task=Get-ScheduledTask -TaskName $name;if($task.State.ToString() -ne 'Running' -or $task.Principal.RunLevel.ToString() -ne 'Limited'){throw ('Existing authorized worker not running '+$name)}}
foreach($path in @($control,(Join-Path $control 'promotions'),(Join-Path $control 'promotions\worktrees'),$worktrees,(Join-Path $backlog 'specs'))){if(-not(Test-Path $path)){New-Item -ItemType Directory $path|Out-Null};if((Get-Item $path).Attributes.HasFlag([IO.FileAttributes]::ReparsePoint)){throw ('Unexpected redirected recovery directory '+$path)}}
foreach($name in $tests){
    $source=Join-Path $repo ('development_specs\'+$name)
    $dest=Join-Path $backlog ('specs\'+$name)
    if(Test-Path $dest){if((Get-FileHash $source -Algorithm SHA256).Hash -ne (Get-FileHash $dest -Algorithm SHA256).Hash){throw 'Existing original independent spec changed'}}
    else{Copy-Item $source $dest -ErrorAction Stop}
}
if(Test-Path $catalogDest){
    if((Get-FileHash $catalogSource -Algorithm SHA256).Hash -ne (Get-FileHash $catalogDest -Algorithm SHA256).Hash){throw 'Approved original catalogue immutable; do not overwrite'}
}else{Copy-Item $catalogSource $catalogDest}
$taskName='MicroGen_AI_Web_v1_CodePromotionOrchestrator'
$launcher=Join-Path $PSScriptRoot 'start_microgen_autonomous_code_promotion_v1.ps1'
$args='-NoProfile -ExecutionPolicy Bypass -File "'+$launcher+'"'
$found=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if($found){
    if(@($found.Actions).Count -ne 1 -or $found.Actions[0].Arguments -ne $args -or $found.Actions[0].WorkingDirectory -ne $repo){throw 'Existing original promotion task different; no overwrite'}
}else{
    $action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $args -WorkingDirectory $repo
    $trigger=New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $principal=New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    $settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings |Out-Null
}
Start-ScheduledTask -TaskName $taskName
if((Get-ScheduledTask -TaskName $taskName).State.ToString() -ne 'Running'){throw 'Continuous code promotion task did not start'}
Write-Output ('MICROGEN_AUTONOMOUS_CODE_PROMOTION_STARTED source='+$head+' job_catalog_sha256='+(Get-FileHash $catalogDest -Algorithm SHA256).Hash.ToLowerInvariant())
