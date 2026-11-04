# Native Windows operator; self-locates its checkout, never accesses user secrets.
[CmdletBinding()]
param(
    [ValidateSet('Doctor', 'Inspect', 'BatchStatus', 'RenderPrepared', 'LectureStatus', 'LectureAdvance')]
    [string]$Mode = 'Doctor',
    [string]$Campaign = '',
    [string]$Section = '',
    [string]$JobsDir = '',
    [string]$SourceRoot = '',
    [string]$TrialDir = '',
    [ValidateSet('selenium','api')]
    [string]$CommunicationMode = 'selenium',
    [switch]$ConfirmContentApiCost,
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
if ($Mode -notin @('LectureStatus','LectureAdvance') -and (
    $SourceRoot -or $TrialDir -or $ConfirmContentApiCost -or
    $CommunicationMode -ne 'selenium'
)) { throw 'Lecture-only arguments are not valid in legacy operator modes.' }
switch ($Mode) {
    'Doctor' {
        if ($Campaign -or $Section -or $JobsDir) {
            throw 'Doctor cannot select campaign or jobs directory.'
        }
        $arguments += '--doctor'
    }
    'Inspect' {
        if (-not $Campaign -or $JobsDir) { throw 'Inspect requires only -Campaign.' }
        $arguments += @('--campaign', $Campaign)
        if ($Section) { $arguments += @('--section', $Section) }
    }
    'BatchStatus' {
        if (-not $Campaign -or -not $JobsDir) {
            throw 'BatchStatus requires both -Campaign and external -JobsDir.'
        }
        $arguments += @('--campaign', $Campaign, '--jobs-dir', $JobsDir)
        if ($Section) { $arguments += @('--section', $Section) }
    }
    'RenderPrepared' {
        if (-not $Campaign -or -not $Section -or $JobsDir) {
            throw 'RenderPrepared requires BOTH -Campaign and -Section, no jobs directory.'
        }
        $arguments += @('--campaign', $Campaign, '--section', $Section, '--execute-prepared')
    }
    'LectureStatus' {
        if (-not $SourceRoot -or -not $Section -or -not $TrialDir -or
            $Campaign -or $JobsDir -or $ConfirmContentApiCost -or
            $CommunicationMode -ne 'selenium') {
            throw 'LectureStatus requires only -SourceRoot, -Section and external -TrialDir.'
        }
        $arguments = @('-m', 'selenium_pipeline.windows_lecture_progression_coordinator',
            '--source-root', $SourceRoot, '--section', $Section, '--trial-dir', $TrialDir)
    }
    'LectureAdvance' {
        if (-not $SourceRoot -or -not $Section -or -not $TrialDir -or
            $Campaign -or $JobsDir) {
            throw 'LectureAdvance requires -SourceRoot, -Section, external -TrialDir.'
        }
        if ($CommunicationMode -eq 'api' -and -not $ConfirmContentApiCost) {
            throw 'Paid Gemini API needs explicit -ConfirmContentApiCost.'
        }
        if ($CommunicationMode -ne 'api' -and $ConfirmContentApiCost) {
            throw 'Paid API confirmation is invalid for Selenium mode.'
        }
        $arguments = @('-m', 'selenium_pipeline.windows_lecture_progression_coordinator',
            '--source-root', $SourceRoot, '--section', $Section, '--trial-dir', $TrialDir,
            '--execute-next-one-stage', '--communication-mode', $CommunicationMode)
        if ($ConfirmContentApiCost) { $arguments += '--confirm-content-api-cost' }
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
