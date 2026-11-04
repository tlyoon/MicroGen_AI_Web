# Native Windows operator; self-locates its checkout, never accesses user secrets.
[CmdletBinding()]
param(
    [ValidateSet('Doctor', 'Inspect', 'RenderPrepared')]
    [string]$Mode = 'Doctor',
    [string]$Campaign = '',
    [string]$Section = '',
    [string]$Python = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repo = $PSScriptRoot
$localPython = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web\venv\Scripts\python.exe'
if (-not $Python) {
    if (Test-Path -LiteralPath $localPython) { $Python = $localPython }
    else { $Python = 'python' }
}
$arguments = @('-m', 'selenium_pipeline.windows_operator')
switch ($Mode) {
    'Doctor' {
        if ($Campaign -or $Section) { throw 'Doctor cannot select an original campaign.' }
        $arguments += '--doctor'
    }
    'Inspect' {
        if (-not $Campaign) { throw 'Inspect requires -Campaign.' }
        $arguments += @('--campaign', $Campaign)
        if ($Section) { $arguments += @('--section', $Section) }
    }
    'RenderPrepared' {
        if (-not $Campaign -or -not $Section) {
            throw 'RenderPrepared requires BOTH -Campaign and -Section.'
        }
        $arguments += @('--campaign', $Campaign, '--section', $Section, '--execute-prepared')
    }
}
Push-Location -LiteralPath $repo
try {
    & $Python @arguments
    if ($null -eq $LASTEXITCODE) { exit 2 }
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
