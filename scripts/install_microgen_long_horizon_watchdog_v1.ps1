# Register one recurring Dell-115 source-attested watchdog, never overwrite.
# Installation requires this source-reviewed script in the current clean
# protected GitHub main and the original two tasks under the same user.
$ErrorActionPreference = 'Stop'
$watch = 'MicroGen_AI_Web_v1_RecoveryWatchdog'
$daemon = 'MicroGen_AI_Web_v71_OfflineDevelopment'
$controller = 'MicroGen_AI_Web_v1_CodePromotionOrchestrator'
if ($env:COMPUTERNAME -ine 'DELL-115') { throw 'Only Dell-115 may own this schedule' }
$repo = (Get-Location).Path
$h = (git -C $repo rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $h -notmatch '^[0-9a-f]{40}$') {
    throw 'Unverified Git repository' }
$remote = (gh api repos/tlyoon/MicroGen_AI_Web/commits/main --jq .sha).Trim()
if ($LASTEXITCODE -ne 0 -or $remote -ne $h) { throw 'Not current protected main' }
$dirty = @(git -C $repo status --porcelain)
if ($LASTEXITCODE -ne 0 -or ($dirty | Where-Object { $_ -ne '' }).Count) {
    throw 'Source tree not clean' }
$script = Join-Path $repo 'scripts\run_microgen_long_horizon_watchdog_v1.ps1'
if (-not (Test-Path -LiteralPath $script -PathType Leaf)) {
    throw 'Reviewed watchdog launcher not present' }
$tracked = (git -C $repo ls-files --error-unmatch -- scripts/run_microgen_long_horizon_watchdog_v1.ps1).Trim()
if ($LASTEXITCODE -ne 0 -or $tracked -ne 'scripts/run_microgen_long_horizon_watchdog_v1.ps1') {
    throw 'Launcher not tracked on verified main' }
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$who = [Security.Principal.WindowsIdentity]::GetCurrent().Name
foreach ($name in @($daemon,$controller)) {
    $t = Get-ScheduledTask -TaskName $name -ErrorAction Stop
    if (-not $t.Settings.Enabled -or @($t.Actions).Count -ne 1 -or
        $t.Principal.LogonType.ToString() -ne 'Interactive' -or
        $t.Principal.RunLevel.ToString() -ne 'Limited' -or
        $t.Settings.MultipleInstances.ToString() -ne 'IgnoreNew') {
        throw 'Native original task policy does not match reviewed scope'
    }
    $owner = (New-Object Security.Principal.NTAccount($t.Principal.UserId)).Translate(
        [Security.Principal.SecurityIdentifier]).Value
    if ($sid -ne $owner) { throw 'Native task not owned by current account' }
}
$d = Get-ScheduledTask -TaskName $daemon
if ([string]$d.Actions[0].WorkingDirectory -ne $repo) {
    throw 'Cannot install from non-owner historical Git checkout' }
$existing = Get-ScheduledTask -TaskName $watch -ErrorAction SilentlyContinue
if ($null -ne $existing) {
    if (@($existing.Actions).Count -ne 1 -or
        $existing.Actions[0].Arguments -notlike '*run_microgen_long_horizon_watchdog_v1.ps1*' -or
        $existing.Actions[0].WorkingDirectory -ne $repo -or
        -not $existing.Settings.Enabled -or
        $existing.Principal.LogonType.ToString() -ne 'Interactive' -or
        $existing.Principal.RunLevel.ToString() -ne 'Limited' -or
        $existing.Settings.MultipleInstances.ToString() -ne 'IgnoreNew' -or
        @($existing.Triggers).Count -ne 1 -or
        $existing.Triggers[0].Repetition.Interval -ne 'PT5M') {
        throw 'Existing differently configured watchdog must not be overwritten'
    }
    Write-Output 'EXACT_EXISTING_REVIEWED_WATCHDOG_PRESERVED'
    exit 0
}
$act = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $script + '"') `
    -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 5) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
    -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
$principal = New-ScheduledTaskPrincipal -UserId $who `
    -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $watch -Action $act -Trigger $trigger `
    -Settings $settings -Principal $principal `
    -Description 'Source-attested 5-min MicroGen G2/G3 restart watchdog. Only offline and promotion task starts; no Gemini Send or publication.' `
    -ErrorAction Stop | Out-Null
$got = Get-ScheduledTask -TaskName $watch -ErrorAction Stop
$owner = (New-Object Security.Principal.NTAccount($got.Principal.UserId)).Translate(
    [Security.Principal.SecurityIdentifier]).Value
if (-not $got.Settings.Enabled -or $got.Actions[0].WorkingDirectory -ne $repo -or
    $got.Settings.MultipleInstances.ToString() -ne 'IgnoreNew' -or
    $got.Principal.LogonType.ToString() -ne 'Interactive' -or
    $got.Principal.RunLevel.ToString() -ne 'Limited' -or
    $got.Triggers[0].Repetition.Interval -ne 'PT5M' -or
    $owner -ne $sid) { throw 'New native repeating watchdog readback failed' }
Write-Output 'GUARDED_FIVE_MINUTE_WATCHDOG_INSTALLED_AND_NATIVE_VERIFIED'
