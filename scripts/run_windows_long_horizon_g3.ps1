param(
    [Parameter(Mandatory=$true)][string]$ConfigPath
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$configPath=[IO.Path]::GetFullPath($ConfigPath)
if(-not (Test-Path -LiteralPath $configPath -PathType Leaf)){throw 'Pinned source-worker config missing'}
$config=Get-Content -LiteralPath $configPath -Raw|ConvertFrom-Json
if($config.schema_version -ne 1 -or
   $config.status -ne 'MICROGEN_G3_SOURCE_ONLY_LONG_HORIZON_WINDOWS_TASK' -or
   $config.no_provider_sends -ne $true -or
   $config.student_publication_authorized -ne $false){
    throw 'Source worker task config cannot authorize model Sends or publication'
}
$repo=[IO.Path]::GetFullPath([string]$config.repo_path)
if(-not (Test-Path -LiteralPath (Join-Path $repo 'selenium_pipeline\long_horizon_g3_source_worker_v1.py'))){
    throw 'Missing versioned G3 source-only code'
}
if(-not (Test-Path -LiteralPath ([string]$config.python_exe) -PathType Leaf)){
    throw 'Python interpreter not available'
}
$progress=Join-Path ([string]$config.report_root) 'g3_long_horizon_progress.json'
$log=Join-Path ([string]$config.report_root) 'windows_long_horizon_worker.log'
Set-Location -LiteralPath $repo
$env:PYTHONPATH=$repo
# This executable invokes only the registered historical textbook-PDF
# witness. It has no Gemini, TTS, YouTube, API or publication permission.
$env:MICROGEN_COMMUNICATION_MODE='selenium'
$env:MICROGEN_API_ATTEMPTS='0'
$stamp=(Get-Date).ToString('o')
Add-Content -LiteralPath $log -Value ("BEGIN "+$stamp)
& ([string]$config.python_exe) -u -m selenium_pipeline.long_horizon_g3_source_worker_v1 --original-report ([string]$config.original_report) --archive-root ([string]$config.archive_root) --state-root ([string]$config.state_root) --report-root ([string]$config.report_root) --max-rounds 2 *>> $log
$exitCode=$LASTEXITCODE
Add-Content -LiteralPath $log -Value ("EXIT "+[string]$exitCode+" "+(Get-Date).ToString('o'))
if($exitCode -notin @(0,2)){throw "Source-only worker execution failed, exit=$exitCode"}
if(-not (Test-Path -LiteralPath $progress -PathType Leaf)){throw 'Source worker progress receipt absent'}
$result=Get-Content -LiteralPath $progress -Raw|ConvertFrom-Json
if($result.new_browser_sends -ne 0 -or $result.new_paid_gemini_API_calls -ne 0 -or
   $result.student_publication_authorized -ne $false -or
   $result.source_scientific_QA_complete -ne $false){
    throw 'Source-only task reported a forbidden model Send or academic acceptance'
}
$sections=@($result.source_sections.PSObject.Properties)
if($sections.Count -ne 2){throw 'Expected both original source scope receipts'}
$pending=@($sections|Where-Object {$_.Value.status -eq 'SOURCE_SCOPE_PENDING'})
if($result.source_only_completed -eq $true -or $pending.Count -eq 0){
    Disable-ScheduledTask -TaskName ([string]$config.task_name)|Out-Null
    Add-Content -LiteralPath $log -Value 'TASK_SELF_DISABLED_AT_SOURCE_ONLY_TERMINAL_STATE'
}
exit 0
