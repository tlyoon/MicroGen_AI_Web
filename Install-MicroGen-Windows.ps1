# Optional native-Windows environment installation.
# Default mode performs diagnostics only; -Install deliberately opts into pip.
[CmdletBinding()]
param(
    [switch]$Install,
    [string]$Python = 'python'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'This installation is Windows-only.' }
$repo = $PSScriptRoot
$venv = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web\venv'
if (-not $Install) {
    Write-Output "Read-only inspection. To install an isolated environment in $venv, invoke -Install explicitly."
    & (Join-Path $repo 'MicroGen-Windows.ps1') -Mode Doctor -Python $Python
    exit $LASTEXITCODE
}
if (Test-Path -LiteralPath $venv) {
    throw "Existing environment is preserved; refusing to replace it: $venv"
}
New-Item -ItemType Directory -Path (Split-Path -Parent $venv) -Force | Out-Null
& $Python -m venv $venv
if ($LASTEXITCODE -ne 0) { throw 'Python virtual environment creation failed.' }
$venvPython = Join-Path $venv 'Scripts\python.exe'
& $venvPython -m pip install -r (Join-Path $repo 'requirements-worker.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed; review isolated environment.' }
& (Join-Path $repo 'MicroGen-Windows.ps1') -Mode Doctor -Python $venvPython
exit $LASTEXITCODE
