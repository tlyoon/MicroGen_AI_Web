# PR513 — Live GitHub historical open-PR dependency topology, read-only

MicroGen_AI_Web Windows-only release engineering has passed its PR511
isolated technical package, but this is NOT enough to merge the long
historical development stack or approve academic media release.

## Real live GitHub inventory (4 November 2026, Dell-115)

The new read-only Windows audit made bounded unauthenticated GET requests
to GitHub's public `/pulls?state=open&per_page=100&page=N` endpoint
(up to seven pages; actual five pages). Observations at the time:

- **423 open pull requests** from #40 to #512, fetched completely.
- **421 drafts, two non-drafts**. Draft vs non-draft is NOT review approval.
- **10 open-PR branch adjacency breaks**, which can be legitimate
  separate roots / prior changes to `main` and must be reconciled.
- Newest **142 open draft PRs form one contiguous head/base chain**
  from #512 backward to #370 (the missing #479 number is an Issue).
- The earlier full-history relationship is **not** a single provable
  open-draft chain. One confirmed independent main-based boundary is #363.
- Exact latest open PR HEAD matched the supplied pinned PR512 SHA
  `92978f74e3c0605ff4dbf31a7c46a7e4cb0db525`.
- Neither the code nor this report mutated any Git/PR refs, merged a
  change, re-requested generation, or published student material.

The earlier PR510 Git **commit** topology reported ~782 SHA commits
ahead of last tracked main. That is different from open PR count:
one PR can contain multiple commits, and older merged/closed PRs are
not covered by an open-only search. Never infer 423 independent complete
code reviews or a full PR-to-commit reconciliation from these counts.

## New global mechanism

`selenium_pipeline.windows_github_pr_stack_readonly_audit`:

- Fetches 1–10 bounded pages of GitHub open-PR metadata, never tokens,
  account secrets, or original-source PDFs.
- Verifies unique numeric PR identity, open state, current draft boolean,
  exactly pinned SHA-format head, head/base branch labels, and optional
  **exact latest HEAD SHA**.
- Detects GitHub pagination truncation, duplicate PR numbers and
  explicitly flags adjacent open-PR base/head inconsistencies.
- Identifies the newest *contiguous draft review tranche*, rather than
  incorrectly treating every open PR as one linear stack.
- Never labels branch adjacency as a conflict automatically: a missing
  adjacent open head can be a legitimately merged/closed predecessor.
- Returns `historical_stack_fully_reviewed_or_approved=false` and
  `may_merge_automatically=false` even when every open PR link matches.

The existing `windows_release_readiness_board` has an optional
`--audit-open-pr-stack-online` flag and displays the catalog
independently of its separate historic review, academic acceptance and
production release approval gates.

~~~powershell
$repo = Join-Path $env:LOCALAPPDATA 'MicroGen_PR513_20261104'
$py = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web\pr493_clean_pypi_20261104\Scripts\python.exe'
Set-Location $repo

# Read-only direct GitHub PR inventory:
& $py -m selenium_pipeline.windows_github_pr_stack_readonly_audit `
    --repository tlyoon/MicroGen_AI_Web --max-pages 7

# Optional read-only release-board inclusion:
& $py -m selenium_pipeline.windows_release_readiness_board `
    --repo $repo `
    --jobs-dir 'EXACT_PREVIOUSLY_LOCKED_JOBS' `
    --fresh-trial-dir 'EXACT_PREVIOUSLY_LOCKED_TRIAL' `
    --worker-python $py --include-stack-batches `
    --verify-exact-head-ci-online `
    --audit-open-pr-stack-online
~~~

Note: an audit with mismatches rightly returns an unsuccessful status
(exit 2) to prevent mistakenly treating an incomplete topology as
approval; the printed JSON remains independently useful and gives
the precise review boundaries.

## Next safe integration step

Reconcile the 10 historical branch boundaries against *closed and
merged* PR histories and local Git ancestry, one bounded group at a
time. Independently review science/voice/pipeline/Windows CI changes,
and do not merge until those reviews and exact-final-head CI pass.
The 142-member recent draft chain is a **review tranche**, not an
authorization for a 142-PR bulk merge.

The second independent real original lecture is still blocked by
Gemini browser response/capture uncertainty. PR512 records two
source-independent browser observations and safe model API metadata,
not a proved global Gemini outage. It does not justify retrying an
ambiguous source, conducting billable API generation without explicit
authorization, or returning to a single-PDF fixing loop.

All PR513 actions are read-only GitHub metadata and offline Windows
tests; no PDF edits, AI content/TTS calls, unsafe main merge, non-Windows
requirements, or student publication.
