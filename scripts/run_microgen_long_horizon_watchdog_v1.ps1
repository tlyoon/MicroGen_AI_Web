# This stable source-reviewed launcher executes one bounded watchdog tick.
# It never sends a model request, modifies source, merges a PR, or publishes.
$ErrorActionPreference = 'Stop'
if ($env:COMPUTERNAME -ine 'DELL-115') { throw 'Dell-115-only native controller' }
$t = Get-ScheduledTask -TaskName 'MicroGen_AI_Web_v71_OfflineDevelopment' -ErrorAction Stop
if (@($t.Actions).Count -ne 1) { throw 'Original daemon action not unique' }
$repo = [string]$t.Actions[0].WorkingDirectory
$python = [string]$t.Actions[0].Execute
if (-not (Test-Path -LiteralPath $repo -PathType Container) -or
    -not (Test-Path -LiteralPath $python -PathType Leaf) -or
    [System.IO.Path]::GetFileName($python) -ine 'python.exe' -or
    -not $repo.EndsWith('_main')) { throw 'Unverified original daemon executable' }
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
Push-Location -LiteralPath $repo
try {
    & $python -B -m selenium_pipeline.development_windows_autorestart_watchdog_v1 --tick
    if ($LASTEXITCODE -ne 0) { throw 'Reviewed watchdog refused native recovery' }
}
finally { Pop-Location }
