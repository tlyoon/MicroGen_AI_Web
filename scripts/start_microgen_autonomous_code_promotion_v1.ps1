# Persistent restart-safe MicroGen promotion controller; no model Send here.
$ErrorActionPreference='Stop'
$python='C:\Users\tlyoon\AppData\Local\miniconda3\python.exe'
$base='C:\Users\tlyoon\AppData\Local\MicroGen_AI_Web_Checkpoints'
$backlog=Join-Path $base 'LONG_HORIZON_CODE_AUTHOR_V1_20261126'
$control=Join-Path $base 'AUTONOMOUS_CODE_PROMOTION_V1_20261127'
$cutover=Join-Path $base 'RECONCILE_20261125'
$catalog=Join-Path $backlog 'approved_source_jobs_v1.json'
if(-not(Test-Path $python) -or -not(Test-Path $catalog)){throw 'Python or approved source catalog unavailable'}
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
while($true){
    $task=Get-ScheduledTask -TaskName 'MicroGen_AI_Web_v71_OfflineDevelopment'
    if($task.State.ToString() -ne 'Running' -or @($task.Actions).Count -ne 1 -or $task.Principal.LogonType.ToString() -ne 'Interactive' -or $task.Principal.RunLevel.ToString() -ne 'Limited'){throw 'Production source owner not safely identified'}
    $repo=[string]$task.Actions[0].WorkingDirectory
    $current=(git -C $repo rev-parse HEAD).Trim()
    if($LASTEXITCODE -ne 0 -or $current -notmatch '^[a-f0-9]{40}$'){throw 'Original continuous development checkout changed'}
    Set-Location $repo
    & $python -B -m selenium_pipeline.development_autonomous_code_loop_v1 --backlog-root $backlog --control-root $control --catalog $catalog --template-root (Join-Path $repo 'scripts') --cutover-root $cutover --cycles 1 --poll-seconds 45
    if($LASTEXITCODE -ne 0){throw 'Protected code-deployment controller exited nonzero'}
    Start-Sleep -Seconds 45
}
