# Launch from a certified immutable GitHub-main checkout in logged-on Dell-115.
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
$backlog='C:\Users\tlyoon\AppData\Local\MicroGen_AI_Web_Checkpoints\LONG_HORIZON_CODE_AUTHOR_V1_20261126'
$python='C:\Users\tlyoon\AppData\Local\miniconda3\python.exe'
if(-not(Test-Path $python) -or -not(Test-Path (Join-Path $repo 'selenium_pipeline\development_persistent_selenium_author_v1.py')) -or -not(Test-Path (Join-Path $backlog 'inbox')) -or -not(Test-Path (Join-Path $backlog 'state'))){throw 'Code worker source or independent signed backlog unavailable'}
$sha=(git -C $repo rev-parse HEAD).Trim()
if($LASTEXITCODE -ne 0 -or $sha -notmatch '^[a-f0-9]{40}$'){throw 'Code writer checkout not pinned by Git'}
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONUTF8='1'
Set-Location $repo
& $python -B -m selenium_pipeline.development_persistent_selenium_author_v1 --root $backlog --poll-seconds 30
$exit=$LASTEXITCODE
if($exit -ne 0){throw ('Persistent Selenium development worker stopped with code '+$exit)}
