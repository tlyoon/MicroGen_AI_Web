# Native Windows operator; self-locates its checkout, never accesses user secrets.
[CmdletBinding()]
param(
    [ValidateSet('Doctor', 'Inspect', 'BatchStatus', 'RenderPrepared', 'LectureStatus', 'LectureAdvance', 'LectureMediaReview', 'LectureCandidates')]
    [string]$Mode = 'Doctor',
    [string]$Campaign = '',
    [string]$Section = '',
    [string]$JobsDir = '',
    [string]$SourceRoot = '',
    [string]$TrialRegistryRoot = '',
    [string]$TrialDir = '',
    [ValidateSet('selenium','api')]
    [string]$CommunicationMode = 'selenium',
    [switch]$ConfirmContentApiCost,
    [string]$ReviewDraft = '',
    [string]$ReviewSelection = '',
    [string]$TtsRequest = '',
    [string]$AudioDir = '',
    [string]$ReviewOutDir = '',
    [switch]$ConfirmMediaReviewRender,
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
if ($Mode -notin @('LectureStatus','LectureAdvance','LectureMediaReview','LectureCandidates') -and (
    $SourceRoot -or $TrialDir -or $ConfirmContentApiCost -or
    $CommunicationMode -ne 'selenium'
)) { throw 'Lecture-only arguments are not valid in legacy operator modes.' }
if ($Mode -ne 'LectureMediaReview' -and (
    $ReviewDraft -or $ReviewSelection -or $TtsRequest -or $AudioDir -or
    $ReviewOutDir -or $ConfirmMediaReviewRender
)) { throw 'Reviewed media inputs and FFmpeg consent require LectureMediaReview.' }
if ($Mode -ne 'LectureCandidates' -and $TrialRegistryRoot) {
    throw 'TrialRegistryRoot requires read-only LectureCandidates mode.'
}
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
    'LectureCandidates' {
        if (-not $SourceRoot -or -not $TrialRegistryRoot -or
            $TrialDir -or $Section -or $Campaign -or $JobsDir -or
            $ConfirmContentApiCost -or $CommunicationMode -ne 'selenium') {
            throw 'LectureCandidates requires only -SourceRoot and -TrialRegistryRoot.'
        }
        $arguments = @('-m',
            'selenium_pipeline.windows_original_source_candidate_inventory',
            '--publisher-root', $SourceRoot, '--trial-registry-root',
            $TrialRegistryRoot)
    }
    'LectureMediaReview' {
        if (-not $SourceRoot -or -not $Section -or -not $TrialDir -or
            -not $ReviewDraft -or -not $ReviewSelection -or
            -not $TtsRequest -or -not $AudioDir -or -not $ReviewOutDir -or
            $Campaign -or $JobsDir -or $ConfirmContentApiCost -or
            $CommunicationMode -ne 'selenium') {
            throw 'LectureMediaReview requires source/trial and reviewed input paths, no Gemini API flags.'
        }
        $arguments = @('-m', 'selenium_pipeline.windows_lecture_media_handoff',
            '--source-root', $SourceRoot, '--section', $Section,
            '--trial-dir', $TrialDir,
            '--draft', $ReviewDraft, '--selection', $ReviewSelection,
            '--tts-request', $TtsRequest, '--audio', $AudioDir,
            '--outdir', $ReviewOutDir)
        if ($ConfirmMediaReviewRender) {
            $arguments += '--render-reviewed-media-once'
        }
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
