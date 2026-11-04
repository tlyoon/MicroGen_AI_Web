# PR492 - Native Windows safe stack integration and release readiness

This milestone is **release engineering**, not another Thomas single-PDF
scientific perfection campaign. It provides a reusable, read-only Windows
release gate; it does NOT merge, tag, ship, render, bill a model/TTS provider,
overwrite source files, or authorize publication.

## Operator command (Dell-115, isolated Windows worktree)

```powershell
$base = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web_Checkpoints'
python -m selenium_pipeline.windows_release_readiness_board `
  --jobs-dir (Join-Path $base '20261104_PR489_WINDOWS_MULTISOURCE_JOBS_V1') `
  --fresh-trial-dir (Join-Path $base '20261104_PR490_FRESH_SERWAY22_1_V1')
```

The board checks exact current Git branch/HEAD, clean worktree, last-fetched
`origin/main` ancestry/commit distance, local-main mismatch with tracked main,
Windows-only workflow runner declarations,
SHA-pinned original two-section PR489 job recovery and the PR490 independently
staged Serway original publisher SHA plus ambiguous one-shot model attempt.
It is informational and fails closed for any actual tampered source evidence.

## The actual inherited Git history (not yet integrated)

On 4 November 2026 the predecessor PR491 branch was **763 commits ahead of
GitHub main, zero behind**, from remote main SHA
`84cb105ff3a21411ac6b0de6665d6c832e11b6be`.
Dell-115's *local* `main` differs: `9e1a0ff6f27a1d9644b208c12a87f9717eac4042`.
A fresh `git fetch origin main` (read-only against worktrees) reconciled
`origin/main` to actual GitHub main; the board now compares HEAD against the
last-fetched `origin/main` and **explicitly shows local-main divergence**.
Do not merge to stale local main or interpret a stale tracked remote ref as
current without fetching first. These are draft stacked development commits,
NOT 763 approved patches. The board never infers permission to merge them.

Required safe integration workflow: review exact branch dependency graph,
audit protected files and the three pre-existing user-local edits in the
shared G: main checkout, confirm every relevant Windows CI check for exact
SHAs, break cumulative changes into justified reviewable batches, and merge
only after independent sourcebound functional release acceptance. No reset
of the shared G: checkout; use isolated Windows worktrees.

## Explicit outstanding release blockers

- PR488 launcher and PR489 source-job reuse are functional and physically
  tested, but Windows installation was not yet qualified in a clean target
  user environment.
- PR490 genuine new Serway §22.1 seven-stage dry-run passed. Its ONE
  figures-only authenticated Selenium attempt **timed out after 180s**
  without accepted output; model submission outcome remains uncertain.
  No automatic resend; its immutable attempt ledger remains authoritative.
- PR491 physically confirmed two unchanged original Thomas section job
  receipts and immutable Serway staged source integrity. These are not
  complete new generated lectures.
- A fully new original-source academic/materials/audio/source-bound
  synchronized <600s multipart MP4 **does not yet exist** for this release
  campaign. A second distinct fully qualified source is also missing.
- Exact latest branch Windows CI, cumulative PR review, clean install,
  final student publication authority are separately required.

Existing PR362 historical Thomas §8.4 accepted multimedia evidence must be
reused only in its proven source/version scope; it does not certify a new
independent original-source complete generation. Per-input unreviewed
math/figure mappings from Thomas §8.4–8.6 are recorded as blocked inputs;
they do NOT block general codebase application readiness engineering.

Formal status should be **WINDOWS_RELEASE_CANDIDATE_BLOCKED** until all
independent obligations genuinely pass. No student-facing release, no
automatic model/TTS spending and no unsafe merge.
