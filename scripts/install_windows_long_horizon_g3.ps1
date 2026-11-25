param(
    [Parameter(Mandatory=$true)][string]$RepoPath,
    [Parameter(Mandatory=$true)][string]$OriginalReport,
    [Parameter(Mandatory=$true)][string]$ArchiveRoot,
    [Parameter(Mandatory=$true)][string]$StateRoot,
    [Parameter(Mandatory=$true)][string]$ReportRoot,
    [Parameter(Mandatory=$true)][string]$PythonExe,
    [string]$TaskName='MicroGen_AI_Web_G3_SourceLongHorizon',
    [switch]$Install
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath($RepoPath)
$report=[IO.Path]::GetFullPath($OriginalReport)
$archive=[IO.Path]::GetFullPath($ArchiveRoot)
$state=[IO.Path]::GetFullPath($StateRoot)
$output=[IO.Path]::GetFullPath($ReportRoot)
$python=[IO.Path]::GetFullPath($PythonExe)
$runner=Join-Path $repo 'scripts\run_windows_long_horizon_g3.ps1'
if($TaskName -ne 'MicroGen_AI_Web_G3_SourceLongHorizon'){
    throw 'Unexpected source-only task identity'
}
foreach($p in @($repo,$archive,$state,$python,$runner,$report)){
    if(-not (Test-Path -LiteralPath $p)){throw ('Missing pinned input '+$p)}
}
$head=(& git -C $repo rev-parse HEAD).Trim()
if($LASTEXITCODE -ne 0 -or $head -notmatch '^[0-9a-f]{40}$'){throw 'Unverified code revision'}
if((& git -C $repo status --porcelain).Count -gt 0){throw 'Source worker repo checkout is not clean'}
$expectedRemote=& git -C $repo ls-remote origin refs/heads/main
if($LASTEXITCODE -ne 0 -or -not $expectedRemote.StartsWith($head)){throw 'Worker must use GitHub-certified main'}
$configPath=Join-Path $output 'long_horizon_windows_task_config.json'
$config=[ordered]@{
    schema_version=1
    status='MICROGEN_G3_SOURCE_ONLY_LONG_HORIZON_WINDOWS_TASK'
    task_name=$TaskName
    repo_path=$repo
    code_revision=$head
    python_exe=$python
    original_report=$report
    archive_root=$archive
    state_root=$state
    report_root=$output
    no_provider_sends=$true
    student_publication_authorized=$false
}
$existing=Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if($existing){throw 'Refuse to modify an existing source task automatically'}
if(-not $Install){
    Write-Output ('PREFLIGHT_OK_SOURCE_ONLY revision='+$head+' task='+$TaskName)
    return
}
New-Item -ItemType Directory -Path $output -Force|Out-Null
if(Test-Path -LiteralPath $configPath){throw 'Refuse to overwrite existing source-only task configuration'}
# Write config before task registration; no credentials, textbook content or prompts.
$bytes=[Text.UTF8Encoding]::new($false).GetBytes(($config|ConvertTo-Json -Depth 4)+"`n")
$stream=[IO.File]::Open($configPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
$argument='-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$runner+'" -ConfigPath "'+$configPath+'"'
$action=New-ScheduledTaskAction -Execute (Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe') -Argument $argument -WorkingDirectory $repo
$trigger=New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) 
    -RepetitionInterval (New-TimeSpan -Minutes 15) 
    -RepetitionDuration (New-TimeSpan -Days 365)
$settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$principal=New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
try{
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal|Out-Null
}catch{
    # Never remove the source receipts or original evidence on an install failure.
    throw
}
$installed=Get-ScheduledTask -TaskName $TaskName
if($installed.Actions[0].WorkingDirectory -ne $repo -or $installed.Settings.MultipleInstances.ToString() -ne 'IgnoreNew'){
    throw 'Scheduled long-horizon source worker policy attestation failed'
}
Write-Output ('INSTALLED_SOURCE_ONLY_TASK '+$TaskName+' revision='+$head)
