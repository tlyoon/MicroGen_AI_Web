# Stage one genuinely distinct next offline source-development job after CI merge.
# The persistent Windows worker, not this script, will perform the model Send.
$ErrorActionPreference='Stop'
$main=Split-Path -Parent $PSScriptRoot
$root='C:\Users\tlyoon\AppData\Local\MicroGen_AI_Web_Checkpoints\LONG_HORIZON_CODE_AUTHOR_V1_20261126'
$spec='C:\Users\tlyoon\AppData\Local\MicroGen_AI_Web_Checkpoints\RECONCILE_20261125\G3_AUDIO_VIDEO_PAGE_TIMING_INDEPENDENT_TEST_SPEC_20261126.py'
$specSHA='91880b006c887ce9bbb2c3c6113cb83686d464578fd8765e291d27540a49e29e'
$jobRepo='C:\Users\tlyoon\mg_g3_timing_code_job_1126'
$branch='feature/g3-audio-video-timing-autogen-20261126'
$jobFile=Join-Path $root 'inbox\g3_page_timing_v1.json'
$mainSHA=(git -C $main rev-parse HEAD).Trim()
$remoteSHA=(gh api repos/tlyoon/MicroGen_AI_Web/commits/main --jq '.sha').Trim()
if($LASTEXITCODE -ne 0 -or $mainSHA -ne $remoteSHA){throw 'Only independently certified latest GitHub main can stage next work'}
if(-not(Test-Path $spec) -or (Get-FileHash $spec -Algorithm SHA256).Hash.ToLowerInvariant() -ne $specSHA){throw 'Original independently authored G3 test changed'}
if((Test-Path $jobRepo) -or (Test-Path $jobFile)){throw 'Next source-pinned model job was already claimed; do not overwrite'}
git -C $main worktree add -b $branch $jobRepo HEAD
if($LASTEXITCODE -ne 0){throw 'Second independent worktree creation failed'}
$test='tests/test_g3_audio_video_page_timing_v1.py'
Copy-Item $spec (Join-Path $jobRepo $test)
if((Get-FileHash (Join-Path $jobRepo $test) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $specSHA){throw 'Independent test copy mismatched'}
git -C $jobRepo add $test
if($LASTEXITCODE -ne 0){throw 'Cannot register independent test'}
git -C $jobRepo commit -m 'Pin independent G3 audio-video page-timing regression'
if($LASTEXITCODE -ne 0){throw 'Trusted test-only commit failed'}
$base=(git -C $jobRepo rev-parse HEAD).Trim()
$job=[ordered]@{
 schema_version=1;project='MicroGen_AI_Web';job_id='g3_page_timing_v1';authorized=$true
 repo=$jobRepo;base_sha=$base;branch=$branch
 target='selenium_pipeline/g3_audio_video_page_timing_v1.py';target_original_sha256=$null
 test=$test;test_sha256=$specSHA;context_path=$test;context_sha256=$specSHA
 instruction='Create compare_g3_audio_video_page_durations(wav_durations_ms, frame_durations_ms, tolerance_ms) as a pure function. Input lists contain page durations. Return dictionary with technical_timing_match, mismatched_pages as 1-based page indices, independent_scientific_acceptance=False, independent_acoustic_acceptance=False, independent_video_highlight_acceptance=False, and student_publication_authorized=False. Reject bool, negative, missing and invalid duration/tolerance values. Favor a single-function implementation with comprehensions rather than nested blocks. Never treat mere timing match as independent physics or audiovisual acceptance.'
 selenium_mode='hydrogen';max_wait_seconds=150;browser_model_claims=1;paid_api=$false;student_publication=$false
}
[IO.File]::WriteAllText($jobFile,($job|ConvertTo-Json -Depth 6),[Text.UTF8Encoding]::new($false))
$env:PYTHONIOENCODING='utf-8'
Set-Location $main
python -B -c 'import sys;from pathlib import Path;from selenium_pipeline.development_persistent_selenium_author_v1 import validate_job;print(validate_job(root=Path(sys.argv[1]),file=Path(sys.argv[2]))["job_id"])' $root $jobFile
if($LASTEXITCODE -ne 0){throw 'New immutable G3 job not eligible'}
Write-Output ('NEW_G3_CODE_JOB_STAGED job=g3_page_timing_v1 git_head='+$base+' manifest_sha='+(Get-FileHash $jobFile -Algorithm SHA256).Hash.ToLowerInvariant())
