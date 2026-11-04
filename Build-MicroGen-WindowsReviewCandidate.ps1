# Review candidate only: never tag, merge, run model/TTS or publish.
[CmdletBinding()]
param(
    [string]$OutputDir = '',
    [string]$WorkerPython = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Native Windows-only portable review candidate.' }
$repo = $PSScriptRoot
$local = [IO.Path]::GetFullPath($env:LOCALAPPDATA)
if (-not $OutputDir) {
    $OutputDir = Join-Path $local 'MicroGen_AI_Web_Checkpoints\WINDOWS_SOURCE_REVIEW_CANDIDATE'
}
if (-not $WorkerPython) {
    $WorkerPython = Join-Path $local 'MicroGen_AI_Web\pr493_clean_pypi_20261104\Scripts\python.exe'
}
$out = [IO.Path]::GetFullPath($OutputDir)
$worker = [IO.Path]::GetFullPath($WorkerPython)
$prefix = $local.TrimEnd('\') + '\'
if (-not $out.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Candidate root must be a new folder inside LOCALAPPDATA.'
}
if (-not $worker.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Worker Python must be a previously verified LOCALAPPDATA virtual environment.'
}
if (-not (Test-Path -LiteralPath $worker -PathType Leaf)) {
    throw 'No prior verified isolated Python worker; install through PR493 first.'
}
if (Test-Path -LiteralPath $out) { throw 'Output folder already exists; never overwrite evidence.' }
$dirty = @(& git -C $repo status --porcelain)
if ($LASTEXITCODE -ne 0 -or $dirty.Count -gt 0) {
    throw 'Cannot package an uncommitted/dirty Windows source checkout.'
}
$head = (& git -C $repo rev-parse HEAD).Trim()
$originMain = (& git -C $repo rev-parse origin/main).Trim()
$behind = (& git -C $repo rev-list --count HEAD..origin/main).Trim()
if ($LASTEXITCODE -ne 0 -or $behind -ne '0') {
    throw 'Git source branch diverged behind tracked main; refuse candidate.'
}
$names = @(& git -C $repo ls-files)
if ($LASTEXITCODE -ne 0 -or $names.Count -lt 100) {
    throw 'Missing tracked Windows source code.'
}
foreach ($name in $names) {
    $path = $name.Replace('\','/')
    if ($path -match '(?i)(^|/)(source\.pdf|\.env|credentials\.json|secrets\.json)$' -or
        $path -match '(?i)\.(wav|mp4|pem|p12|pfx|key)$' -or
        $path -match '(?i)(^|/)\.microgen_work(/|$)') {
        throw "Tracked source archive includes prohibited private material: $path"
    }
}
# Never include user source PDF, audio, private credentials, or .git itself.
New-Item -ItemType Directory -Path $out -ErrorAction Stop | Out-Null
$zip = Join-Path $out 'MicroGen_AI_Web_Windows_SOURCE_REVIEW_ONLY.zip'
$unzip = Join-Path $out 'extracted_readonly_smoke'
& git -C $repo archive --format=zip --output=$zip HEAD
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $zip)) {
    throw 'Immutable Git HEAD archive failed; candidate not accepted.'
}
Expand-Archive -LiteralPath $zip -DestinationPath $unzip -ErrorAction Stop
if (-not (Test-Path -LiteralPath (Join-Path $unzip 'MicroGen-Windows.ps1'))) {
    throw 'Extracted candidate lacks Windows launcher.'
}
Push-Location -LiteralPath $unzip
try {
    & $worker -m selenium_pipeline.windows_install_smoke | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Clean extracted-package worker installation smoke failed.'
    }
    & $worker -m selenium_pipeline.windows_operator --doctor | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Clean extracted-package source launcher smoke failed.'
    }
} finally {
    Pop-Location
}
$hash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
$manifest = @{
    schema_version = 1
    status = 'CLEAN_EXTRACTED_WINDOWS_SOURCE_REVIEW_CANDIDATE_ONLY'
    source_commit_sha = $head
    last_fetched_origin_main_sha = $originMain
    tracked_files = $names.Count
    zip_sha256 = $hash
    zip_bytes = (Get-Item $zip).Length
    clean_extracted_isolated_windows_smoke = $true
    source_originals_or_private_credentials_in_archive = $false
    full_second_original_lecture_certified = $false
    cumulative_historical_stack_review_completed = $false
    github_ci_exact_candidate_sha_accepted = $false
    student_publication_authorized = $false
    release_candidate_approved = $false
}
$manifestPath = Join-Path $out 'source_review_candidate_manifest.json'
[IO.File]::WriteAllText($manifestPath,
    (($manifest | ConvertTo-Json -Depth 4) + [Environment]::NewLine),
    [Text.UTF8Encoding]::new($false))
Write-Output ($manifest | ConvertTo-Json -Depth 4)
