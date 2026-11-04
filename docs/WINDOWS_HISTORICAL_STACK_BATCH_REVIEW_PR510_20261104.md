# PR510 — Native Windows read-only historical commit/PR-stack review batches

The codebase carries a long stack of development commits. PR507/508/509
close general workflow gaps but are NOT authorization to merge hundreds of
historic drafts or to publish student-facing lectures.

PR510 implements `selenium_pipeline.windows_historical_stack_batch_plan`,
a purely read-only, bounded Git inspection of an *isolated Windows checkout
under %LOCALAPPDATA%*, plus optional reporting from the existing read-only
release-readiness board.

## Commands (no network and no file modification)

~~~powershell
$repo = Join-Path $env:LOCALAPPDATA 'MicroGen_PR510_20261104'
$py = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web\pr493_clean_pypi_20261104\Scripts\python.exe'
Set-Location $repo

# Only local Git read operations, no provider APIs or checkout mutation.
& $py -m selenium_pipeline.windows_historical_stack_batch_plan `
  --repo $repo --batch-size 20 --max-commits 2500

# The normal release board can include the same unapproved batch plan:
& $py -m selenium_pipeline.windows_release_readiness_board `
  --repo $repo `
  --jobs-dir 'EXACT_EXISTING_IMMUTABLE_JOB_DIRECTORY' `
  --fresh-trial-dir 'EXACT_EXISTING_SOURCE_LOCKED_TRIAL' `
  --include-stack-batches --worker-python $py
~~~

The **local** `refs/remotes/origin/main` is a snapshot. It must be
independently refreshed/compared with the real remote before any acceptance,
because this command deliberately does NOT fetch GitHub data.

## What is inspected

- Require native Windows, an isolated local-app-data checkout, a real
  tracked `origin/main` and a valid exact Git HEAD SHA.
- Refuse a shallow or divergent local history rather than fabricating
  a valid dependency chain.
- Read exact Git commit ancestry with `git rev-list --topo-order --reverse`
  and divide it into up to 2,500 commits in independently inspectable
  windows of 1–40 commits (20 by default).
- For each batch record the exclusive predecessor, first SHA,
  inclusive last SHA, number of commits and changed-file scope.
- Flag risk classes from actual file paths: pipeline runtime, Windows
  CI, regression tests, documentation, packaging/launcher and source,
  audio or video assets.
- Set all PR dependencies, academic review and merge/publication
  authorizations to **false**. Grouping commits is not reviewing PRs.

If `--include-stack-batches` is selected, the release board exposes
`bounded_historical_stack_review_plan_available` separately from
`entire_historical_stack_dependency_and_review_completed`. A batch
plan may pass while historical review/release must remain blocked.

## Actual Dell-115 run, 4 November 2026

Using the PR509 checkpoint at SHA
`5a222156275050ea16e9172e140cf21b5d3e55e4`, local tracked main
`84cb105ff3a21411ac6b0de6665d6c832e11b6be`:
**782 commits ahead, zero behind**, divided into **40 bounded batches**
of 20 or fewer commits (last batch 2). The first batch has pipeline,
test, documentation and Windows CI changes. No Git refs or worktree
files were modified. These counts reflect **locally tracked main**,
not a claimed live GitHub main check.

The first batch is NOT already approved. The next review work is to
map each SHA segment to its actual draft PR, verify changed dependencies
and CI for that batch, and obtain independent scientific and voice
QA where those contracts are affected. Only after that should an
explicitly approved merge be considered.

## Release boundary

The second truly independently generated, human-reviewed original
multimedia lecture remains outstanding. The new technical source
catalog and review batches cannot substitute for it. No textbook
reprocessing, paid Gemini/TTS calls, FFmpeg generation, historical
mass merge, release tag or student publication occurs in PR510.

Dell-115 Windows only; no Ubuntu/HP/Yoga/local models or edits to
the G: shared dirty main/publisher originals.
