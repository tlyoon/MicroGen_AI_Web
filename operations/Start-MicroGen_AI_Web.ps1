<#
MicroGen_AI_Web Windows production launcher.
Local workstation configuration lives outside Git and outside teaching-material folders.
Requires an exact pinned GitHub release and refuses dirty checkouts.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9]+\.[0-9]+$')]
    [string]$Subchapter,

    [ValidateSet('figures','slides','narration','script_qa','tts','tts_qa','video')]
    [string]$FromStage = 'figures',

    [ValidateSet('figures','slides','narration','script_qa','tts','tts_qa','video')]
    [string]$ThroughStage = 'video',

    [ValidateSet('figures','slides','narration','script_qa','tts','tts_qa','video')]
    [string]$ForceFrom = '',

    [switch]$DryRun,

    [string]$ConfigurationFile = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $ConfigurationFile) {
    if (-not $env:LOCALAPPDATA) {
        throw 'LOCALAPPDATA is not set. This launcher requires a Windows user environment.'
    }
    $ConfigurationFile = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web_Production\worker.json'
}
if (-not (Test-Path -LiteralPath $ConfigurationFile -PathType Leaf)) {
    throw "Production worker configuration missing: $ConfigurationFile"
}
$config = Get-Content -LiteralPath $ConfigurationFile -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($property in @('release_sha','runtime_python','pipeline_python','work_root')) {
    $value = $config.PSObject.Properties[$property]
    if (-not $value -or [string]::IsNullOrWhiteSpace([string]$value.Value)) {
        throw "Missing required production configuration: $property"
    }
}
if ([string]$config.release_sha -notmatch '^[0-9a-fA-F]{40}$') {
    throw 'Production configuration release_sha must be an exact 40-character Git commit.'
}
$repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
if (-not (Test-Path -LiteralPath (Join-Path $repo '.git'))) {
    throw "Launcher is not inside a Git checkout: $repo"
}
$origin = (& git -C $repo remote get-url origin | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $origin -ne 'https://github.com/tlyoon/MicroGen_AI_Web.git') {
    throw "Refusing to run non-MicroGen_AI_Web checkout: $origin"
}
$release = (& git -C $repo rev-parse HEAD | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $release -ne [string]$config.release_sha) {
    throw "Release mismatch: expected $($config.release_sha), found $release"
}
$changed = @(& git -C $repo status --porcelain)
if ($LASTEXITCODE -ne 0 -or $changed.Count -gt 0) {
    throw 'Production checkout is dirty; use a clean pinned release, not a shared Drive working copy.'
}
$source = (Resolve-Path -LiteralPath $SourceRoot).ProviderPath
if (-not (Test-Path -LiteralPath (Join-Path (Join-Path $source ($Subchapter.Split('.')[0])) (Join-Path $Subchapter 'source.pdf')) -PathType Leaf)) {
    throw "Missing source.pdf for subchapter $Subchapter below $source"
}
foreach ($program in @([string]$config.runtime_python, [string]$config.pipeline_python)) {
    if (-not (Test-Path -LiteralPath $program -PathType Leaf)) {
        throw "Configured Python interpreter missing: $program"
    }
}
$work = [string]$config.work_root
if (-not [System.IO.Path]::IsPathRooted($work)) {
    throw "Configured work_root must be an absolute local path: $work"
}
$fullWork = [System.IO.Path]::GetFullPath($work).TrimEnd('\')
$fullSource = [System.IO.Path]::GetFullPath($source).TrimEnd('\')
if ($fullWork.StartsWith($fullSource + '\', [System.StringComparison]::OrdinalIgnoreCase) -or
    $fullSource.StartsWith($fullWork + '\', [System.StringComparison]::OrdinalIgnoreCase) -or
    $fullWork.Equals($fullSource, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Local work_root and published source root must be separate, non-nested directories.'
}
New-Item -ItemType Directory -Path $work -Force | Out-Null

$env:MICROGEN_GEMINI_UI_MODE = 'flash'
$env:MICROGEN_LLM_MODEL = 'gemini-3.8-flash'
$env:MICROGEN_FIGURE_MAPPING_BACKEND = 'api'
$env:MICROGEN_PIPELINE_PYTHON = [string]$config.pipeline_python
$env:MICROGEN_TTS_PYTHON = [string]$config.runtime_python
$env:PYTHONNOUSERSITE = '1'
$env:PYTHONUNBUFFERED = '1'

$pipelineArgs = @(
    '-m', 'selenium_pipeline.runner',
    '--source-root', $source,
    '--subchapter', $Subchapter,
    '--work-root', $work,
    '--from-stage', $FromStage,
    '--through-stage', $ThroughStage
)
if ($ForceFrom) {
    $pipelineArgs += @('--force-from', $ForceFrom)
}
if ($DryRun) {
    $pipelineArgs += '--dry-run'
}
Write-Output "[MicroGen_AI_Web] release=$release subchapter=$Subchapter root=$source work=$work flash=enabled dry_run=$DryRun"
Push-Location $repo
try {
    & ([string]$config.runtime_python) @pipelineArgs
    $status = $LASTEXITCODE
} finally {
    Pop-Location
}
if ($status -ne 0) {
    throw "MicroGen_AI_Web stage failed with exit code $status; inspect per-stage logs for $Subchapter"
}
Write-Output "[MicroGen_AI_Web] completed successfully subchapter=$Subchapter"
