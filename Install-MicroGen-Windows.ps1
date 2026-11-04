# Windows-only, isolated worker environment. Never modify an existing install.
# Default is read-only. Installation is an explicit -Install operation.
[CmdletBinding()]
param(
    [switch]$Install,
    [switch]$SmokeOnly,
    [string]$Python = 'python',
    [string]$TargetVenv = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Windows-only installation.' }
if ($Install -and $SmokeOnly) { throw 'Select -Install OR -SmokeOnly.' }
$repo = $PSScriptRoot
$localBase = [IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web'))
if (-not $TargetVenv) {
    $TargetVenv = Join-Path $localBase 'venv'
}
$venv = [IO.Path]::GetFullPath($TargetVenv)
$allowed = [IO.Path]::GetFullPath($env:LOCALAPPDATA).TrimEnd('\') + '\'
if (-not $venv.StartsWith($allowed, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Target virtual environment must stay inside LOCALAPPDATA.'
}
if ($venv -eq $localBase -or $venv -eq [IO.Path]::GetFullPath($env:LOCALAPPDATA)) {
    throw 'Refuse installation over an existing parent directory.'
}
$venvPython = Join-Path $venv 'Scripts\python.exe'
if ($SmokeOnly) {
    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        throw 'Cannot smoke-test a missing isolated virtual environment.'
    }
    Push-Location -LiteralPath $repo
    try {
        & $venvPython -m selenium_pipeline.windows_install_smoke
        exit $LASTEXITCODE
    } finally {
        Pop-Location
    }
}
if (-not $Install) {
    Write-Output 'Read-only diagnostics; no environment was created.'
    & (Join-Path $repo 'MicroGen-Windows.ps1') -Mode Doctor -Python $Python
    exit $LASTEXITCODE
}
if (Test-Path -LiteralPath $venv) {
    throw "Existing virtual environment is preserved, never overwritten: $venv"
}
New-Item -ItemType Directory -Path (Split-Path -Parent $venv) -Force | Out-Null
& $Python -m venv $venv
if ($LASTEXITCODE -ne 0) { throw 'Isolated Python venv creation failed.' }
if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    throw 'Isolated Python executable missing after venv creation.'
}
# Ignore machine-global auxiliary indexes (e.g. unavailable NVIDIA index).
# Pip's special lowercase 'nul' config filename disables ALL pip config on
# Windows; never modify the user's global or personal pip.ini settings.
$previousPipConfig = $env:PIP_CONFIG_FILE
try {
    $env:PIP_CONFIG_FILE = 'nul'
    & $venvPython -m pip install --index-url https://pypi.org/simple --retries 1 --timeout 15 --disable-pip-version-check -r (Join-Path $repo 'requirements-worker.txt')
    $installExitCode = $LASTEXITCODE
} finally {
    $env:PIP_CONFIG_FILE = $previousPipConfig
}
if ($installExitCode -ne 0) {
    throw "Installation incomplete; retained exact venv for diagnosis: $venv"
}
Push-Location -LiteralPath $repo
try {
    & $venvPython -m selenium_pipeline.windows_install_smoke
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
