# PR501 - Portable native Windows source-distribution review candidate

This is a **real packaged Windows source review candidate**, not a production
release, and it does not merge the 772-commit historical draft stack into
`main` or overwrite any user-authored multimedia/source files.

## Builder (run only on authorized Dell-115)

```powershell
$repo = Join-Path $env:LOCALAPPDATA 'MicroGen_PR501_20261104'
$dest = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web_Checkpoints\20261104_PR501_WINDOWS_SOURCE_REVIEW_CANDIDATE_V1'
$py = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web\pr493_clean_pypi_20261104\Scripts\python.exe'
powershell -NoProfile -ExecutionPolicy Bypass `
  -File (Join-Path $repo 'Build-MicroGen-WindowsReviewCandidate.ps1') `
  -OutputDir $dest -WorkerPython $py
```

The builder fails closed if native Windows isn't active, the source worktree
is dirty, `origin/main` isn't an ancestor, the output already exists,
the worker is not an existing isolated LOCALAPPDATA Python, or the Git HEAD
contains tracked original `source.pdf`, WAV/MP4, `.env`, credentials
JSON, secrets or private microgen workspaces.

It uses **`git archive HEAD`** (only tracked immutable committed source,
no `.git`, user PDFs, profile credentials, output video or historical
checkpoints), then expands into a fresh external folder and actually invokes
both `selenium_pipeline.windows_install_smoke` and
`selenium_pipeline.windows_operator --doctor` under the clean extracted
checkout using the PR493 verified standalone Python worker. Zero Gemini,
paid TTS, video, internet installation or student publication.

A `source_review_candidate_manifest.json` is written next to the ZIP with
the exact commit SHA, ZIP SHA, file count, worker and launcher smoke and
**explicit release-blocked flags**. Tests additionally run a real Git archive
and confirm operator modules are included and private originals excluded.

The artifact is **nonpublic and local**. Do not upload it to a distribution
site or call it a student release. Even if packaging passes, missing
independent second original complete media, full historical PR review,
exact final-head CI and formal release authorization remain outstanding.

The other project commitment remains in force: do not endlessly re-open
Thomas Figure8.3 or Serway §24.4 mapping/Beamer response defects; preserve
their exact SHA receipts, fix only universal code when justified, and advance
the application.
