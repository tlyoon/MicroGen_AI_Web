# PR511 — Exact GitHub CI / live main verification and engineering-only Windows closure

The native Dell-115 Windows pipeline has acquired a safe single-send
figures→slides→narration→script-QA controller (PR505), a separately approved
WAV→MP4 review handoff (PR506), and an explicit release-readiness board
(PR507–510). Previously, that board **hard-coded** the final-head GitHub CI
gate to false; its engineering progress could never be reflected even after
two real native Windows CI jobs passed.

PR511 adds a deliberately **optional, read-only online** verifier,
`selenium_pipeline.windows_exact_head_github_ci`, and exposes a separate
`engineering_technical_release_candidate_ready` gate. It does not
auto-promote academic, student release, user signoff, or Git merging.

## Actual exact-head verification

On Dell-115 the new module independently queried the GitHub HTTPS REST
API for PR510 HEAD
`e4b64125d6ce75c6af92d33dd076d21f2143f28f`.
The server reported successful run `41821739890` (attempt 1), both
`offline-regressions` and
`Full offline suite (Windows, Python 3.12)` completed successfully.
No local environment variables, Gemini keys, PDF content, or credentials
were sent to GitHub.

The verifier requires:
- A strictly valid public `owner/repo` name and lowercase exact 40-hex HEAD.
- The **latest** pull-request workflow run for that exact head SHA to be
  completed/successful and have the expected exact workflow path/name.
- Both required native Windows jobs to be completed/successful; missing,
  duplicated, failed or queued jobs block.
- Optional read-only live `refs/heads/main` from GitHub to match the
  checked-out locally tracked `origin/main`. Stale local main blocks the
  separate engineering gate even when the current PR's CI is green.
- All remote errors/timeouts fail closed without fetching/writing Git refs.

~~~powershell
$repo = Join-Path $env:LOCALAPPDATA 'MicroGen_PR511_20261104'
$py = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web\pr493_clean_pypi_20261104\Scripts\python.exe'
Set-Location $repo
$head = git rev-parse HEAD
$main = git rev-parse origin/main

# Online independent check. Default other commands never contact GitHub.
& $py -m selenium_pipeline.windows_exact_head_github_ci `
  --repository tlyoon/MicroGen_AI_Web `
  --head-sha $head --tracked-main-sha $main

# Full combined READ-ONLY board with online CI + current main and stack:
& $py -m selenium_pipeline.windows_release_readiness_board `
  --repo $repo `
  --jobs-dir 'EXACT_IMMUTABLE_MULTISOURCE_JOB_DIRECTORY' `
  --fresh-trial-dir 'EXACT_EXISTING_SOURCE_LOCKED_TRIAL' `
  --worker-python $py `
  --reuse-scoped-pr362 --include-stack-batches `
  --verify-exact-head-ci-online
~~~

The board's new `engineering_technical_release_candidate_ready` is
true only if native Windows, clean isolated Git checkout, no divergence,
Windows-only CI files, SHA-correct old source/job receipts, existing isolated
worker import/dependency/FFmpeg/TeX check, **exact HEAD green online CI**,
**fresh live main reference**, and a safe bounded historical review *plan*
are all verified. This is a technical engineering candidate, NOT a release.

Even a fully green engineering technical gate does not mean:
- Another newly generated independent academic original-source lecture
  passed visual/math/meaning QA.
- Its full spoken element audio passed independent human hearing, or
  final synchronized videos were reviewed/accepted.
- The 780+ historical commits/PRs received independent dependency review.
- The user authorized any release, student publication or unbounded
  Gemini/TTS model costs.

Those independent checks remain permanently separate and **blocked
until genuine evidence exists**. A green PR CI cannot override them.

## New distinct-source figures attempt and recovery

Following PR510's successful original-only stage on a separate source,
a single Selenium figures attempt was run on Serway §1.1. It timed out
after the finite 180-second one-shot deadline and wrote immutable started,
result and provider-health receipts:
`FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY`,
`model_browser_submission_outcome=UNVERIFIED`,
`UNKNOWN_SUBMISSION`.

Its raw log shows normal local figure extraction/copy, an active
Chrome remote-debugging session, and no independently confirmed
successful Gemini figure mapping response. This does **not** prove
Gemini service unavailability. The original request may have been sent
at an unknown point; do not re-send it, switch keys for the same task,
or repair this particular textbook as the next milestone.
The development continues at the code/release level.

The distinct genuine full lesson remains outstanding. Any future
new provider generation must use a separate unattempted source and
the prior one-send/cost-authority contract. No new paid API or TTS
requests occurred in this PR. No publisher originals, G: shared main,
previous source files or student distribution were modified.

## Test evidence

Synthetic Windows GitHub API fixtures cover exact vs stale SHA, newer
failure/queued run overruling older success, absent/failed/duplicate
jobs, unavailable network, untrusted repository input and actual
live-main SHA mismatch. The release board tests show an engineering
technical pass does **not** enable academic approval/publication.
Existing Windows-only CI uniqueness, stage and release tests remain.
