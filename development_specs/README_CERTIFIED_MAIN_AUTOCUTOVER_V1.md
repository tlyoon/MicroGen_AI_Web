# Dell-115: automatic catch-up after an unrelated Windows-CI-certified GitHub merge

## Real failure and root cause

On 28 November 2026, Dell-115's original G2/G3 development daemon,
Selenium code author and promotion controller were running against
`post_pr677_main` (SHA `7a68e965...`). Independently approved
MicroGen/Serway changes on GitHub advanced protected `main` to PR #684
(SHA `a174c92f...`). The source-pinned selector correctly refused to stage
work from the stale old checkout, reporting `NEW_SOURCE_JOB_ADMISSION_HELD`.
The original watchdog also returned exit code 1 because it required
exact-current protected main. Manual guarded source deployment restored
Dell-115 to PR #684, but that alone was not persistent recurrence repair.

## Executable repair

The independent `development_ci_merged_main_autocutover_v1` repair is
integrated into `development_autonomous_code_loop_v1.cycle`, after any
previously claimed model-code PR deployment and before new job selection.
It performs read-only verification of the original old checkout and the
actual protected GitHub remote source. If they match it is a no-op.
Otherwise it requires:

1. Original clean Dell source checkout, finite forward-only ancestry (at
   most 50 GitHub commits), and the latest merge attributed to exactly one
   repository-owned, merged main-branch PR.
2. Its original PR head and squash-merge tree both uniquely identified;
   the exact latest matching PR-head Windows CI workflow and its two
   mandatory Windows jobs must succeed; other matching workflows must
   not have pending/failed latest results.
3. Model-author heartbeat is quiescent with no new paid API requests,
   both original native developer task owners are independently running,
   and no student-facing publication has been authorized.
4. Only the existing versioned guarded deployment may switch the original
   daemon and Selenium worker to that exact certified main source. The
   original cutover receipt prevents blind replay of uncertain native
   task mutations.

If any check fails, only the source catch-up is held. No new coding job
may be admitted against the stale source; no arbitrary GitHub PR, model
Send, paid Gemini API call, scientific approval or publication occurs.

## Verification

- `tests/test_development_ci_merged_main_autocutover_v1.py` covers
  forward ancestry, PR attribution, exact-head CI, protected-main movement,
  dirty source, pending original model sends, native owner failure, and
  actual controller dispatch sequencing.
- Original Dell-115 incident reproduced with a **read-only live proof**:
  old `7a68e9658ec25e47ffd9ab60647845554e892f98`, current certified
  main `a174c92f207df2ae523041337ab49d422e10d077`, PR #684 head
  `153a6e143eeaa9487f94b2acadcf1064d8322d81`, Windows CI run
  `46117253332`, **six forward GitHub commits**. Returned
  `LATEST_MAIN_CI_CERTIFIED_GUARDED_CUTOVER_ELIGIBLE`; no writes,
  provider Sends or publication.

This is **engineering/source-continuity work**, not G2/G3 academic,
acoustic, video or second-subsection acceptance.
