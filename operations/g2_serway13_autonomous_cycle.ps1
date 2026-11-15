# Bounded source-bound G2 academic-to-media cycle on Dell-115.
# A Windows Interactive-only scheduled task may invoke this after sign-in.
# Failed/uncertain Gemini requests are never resubmitted.
param([switch]$ReadOnly)

$ErrorActionPreference = 'Stop'
$Repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$WorkRoot = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web_Checkpoints'
$Folder = Join-Path $WorkRoot 'auto_captionless_6528f3cfd9929c3706de\source_tree\1\1.3'
$Queue = Join-Path $WorkRoot 'G2_20261115_SERWAY13_AI_ACADEMIC_REVIEW'
$Python = Join-Path $env:LOCALAPPDATA 'miniconda3\python.exe'
$LogRoot = Join-Path $WorkRoot 'G2_SERWAY13_CONTINUATION_LOGS'

foreach ($directory in @($WorkRoot, $Folder, $Queue)) {
    if (-not (Test-Path -LiteralPath $directory -PathType Container)) {
        throw "Original source-bound G2 checkpoint missing; no work dispatched."
    }
}
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Installed local Python missing; no model request dispatched."
}
New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null
$stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ')
$Log = Join-Path $LogRoot ("g2_" + $stamp + ".log")
$argsList = @(
    '-u','-m','selenium_pipeline.windows_g2_autonomous_qa_supervisor',
    '--folder',$Folder,'--queue-root',$Queue,'--work-root',$WorkRoot,
    '--health-family','pro',
    '--max-units',($(if ($ReadOnly) { '0' } else { '1' }))
)
if (-not $ReadOnly) {
    $argsList += '--execute'
}
Push-Location $Repo
try {
    & $Python @argsList *> $Log
    $exitCode = $LASTEXITCODE
    if ($null -eq $exitCode) { $exitCode = 4 }
} finally {
    Pop-Location
}
# All provider claims, source-cited reviews and media are in separate
# immutable checkpoint directories. Logs are informational, not evidence
# of accepted academic QA or final video completion.
exit $exitCode
