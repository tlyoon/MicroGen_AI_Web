# 18 November 2026 — Active-head PR dependency audit recovers from unrelated historical branches

## Scope and historical failure
MicroGen_AI_Web, Dell-115 Windows, current isolated development ancestor f6af456 / draft PR #530. The mandatory live read-only PR audit of tlyoon/MicroGen_AI_Web returned OPEN_PR_STACK_INCOMPLETE_OR_REVIEW_REQUIRED despite a valid newest contiguous draft tranche. It enumerated 441 open PRs, 10 numeric-neighbor branch disagreements and 2 non-drafts. Those entries include older parallel workstreams, which must not be assumed to be parents of the newest recovery branch.

Historical code already included a read-only global audit, bounded GitHub pagination, head-SHA matching, explicit false merge/publication gates and a release board integration. This fix REUSES that code; it does not replace it or retroactively authorize any historical review.

## Targeted production remedy
The same normal windows_github_pr_stack_readonly_audit.audit now adds an independent `active_exact_head_dependency_chain` report. From the newest exact SHA-matched open PR, it follows **base.ref -> exactly one open head.ref** and also requires exact GitHub **base.sha == parent head.sha**. This uses the returned complete bounded live open PR catalog, not PR numeric adjacency.

It rejects stale head, incomplete pagination, missing/duplicate parents, modified base SHA, cycles, and any non-draft PR in the active chain. A root reached at `main` is reported separately from a root whose parent is absent from the open PR catalog. In every case code/QA review completed=false, may_merge_automatically=false and student_publication_authorized=false. Global audit status and old fields remain intact.

An exact enabled reusable `GITHUB_SCOPED_HEAD_CHAIN_RECOVERY` entry is in the ordinary `recovery_registry_v1.json` and `recovery_registry.py` handler map. Retiring the registry entry disables scoped acceptance. The normal read-only release board already invokes `audit` and therefore inherits the new scoped metadata without a parallel implementation. A CLI `--active-head-chain-only` mode checks exact active chain identity without forcing unrelated old-PR links to pass, and never approves a merge.

## Genuine live test, no Send
Using Dell-115 and the real GitHub API from the production audit, with head SHA f6af4563e31e9ef3b483b316ad6f69ff5ffd1759:
- Global catalog remained incomplete/review-required: 441 open PRs, 10 unrelated numeric adjacency disagreements.
- **Active development chain reached main**: 163 actual open draft PRs, **162 independently matching branch and SHA parent links**, no cycle or duplicate parent on the traversed path.
- All code/science/audio reviews, historical approval, auto-merge and student publication remain false.
- Zero Gemini, ChatGPT, API/TTS, PDF uploads, FFmpeg, source changes or original one-Send claims.

## Fault injection and regression
New tests `tests.test_windows_github_scoped_head_audit` reproduce the originally false-negative mixed historical stack and independently inject stale head, changed base SHA, duplicate parent, cycle, missing open base, non-draft current parent, incomplete pagination, retired registry, and CLI scope distinction. The new test is enrolled in the standard Windows reliability workflow.

Local Dell-115 selected legacy audit, release board, registry, CI and stack-plan suites: **56 passed, 0 failures** after correcting registry fixture order/policy. Existing first registry record is preserved for legacy positional tests. Python compile and git diff whitespace check passed.

## Boundary and continuation
This repairs active PR-chain metadata classification only. It **does not** review or merge 163 commits/PRs, certify a fresh lecture or recover the exhausted Gemini two-PDF response. Serway §1.3 G2 remains 20/85 accepted with 65 pending; G3 remains open. Keep the latest PR stacked and draft; exact-head hosted CI is required before code acceptance, while source-science/phonetic/media work remains behind existing independent QA and authorization gates.
