# PR548 — v7.1 automatic original Git integrity checks after curated B1–B48

**Date:** 19 November 2026, MYT. **Authorized host:** Dell-115. **Parent:** PR547 exact committed source `348515ed8a0e3d2c83c0b461f353634070edce9b`. This is an isolated source-only development worktree, not a merged production main or student media publisher.

## Historical failure and review of existing mechanism

The registered v7.1 supervisor dispatches (1) a finite curated 48 historical source-regression batch roadmap, (2) the source history gap inventory, (3) CI-gated read-only release board, and (4) the original G2 read-only no-resend claim reconciliation. The historical gap stage reports original commit windows after B48, but the project-wide controller does **not** execute the existing source-only Git patch checker for those later windows. New development commits continue to add windows and require another manual code check unless this independent eligible downstream work is registered.

Real PR547 exact-head `plan_stack` read-only check identified **49 windows (966 commits)**; B49 has **six** later commits, 17 touched paths, three originally touched test paths. The existing normal `windows_historical_stack_batch_executor.execute_batches(first_batch=49,last_batch=49)` ran successfully on Dell-115 and returned `OFFLINE_BATCH_PATCH_CHECKS_COMPLETE_CODE_REVIEW_PENDING`, with a pinned LOCALAPPDATA receipt; this is original Git patch integrity only, **not** semantic code review. See `pr547_exact_head_batch49_git_source_checks_20261119.json`.

## Reuse the normal source-bound mechanism, not a second Git history parser

Added the fifth global supervisor stage `recent_uncovered_historical_patch_checks`, depending only on independently accepted `global_historical_source_gap_inventory`. It calculates exact original Git windows outside the source-bound 48-task curated roadmap from the existing verified `plan_stack`, requires that uncovered windows be consecutive **after B48**, and permits at most **four** new windows per source-head invocation. An empty gap returns a true no-op receipt; an unbounded/nonconsecutive range is quarantined rather than blindly reviewed.

For eligible windows, reuse the current SHA-anchored `windows_historical_stack_batch_executor.execute_batches`, retaining its immutable source/checker-version receipts and explicit patch warning quarantine. Require the exact current source head, batch boundaries, count, zero model/TTS calls, no merge/release powers and semantic review false. A batch with findings is recorded as **quarantined**, never promoted to a pass or rewritten. This stage is independent of the original G2 provider blocker and can proceed even if CI-gated release-board acceptance is blocked. The registered `V71_UNCOVERED_GIT_SOURCE_PATCH_HANDOFF` signature is checked through the existing allowlisted v7.1 `global_checkpoint_handoff` handler. Missing/retired registry, source SHA drift, mismatched receipt, unsafe count or false scientific acceptance must fail closed.

The existing normal historical CLI `--supervise-project-v71` derives its finite dispatch budget from the declared `STAGES`, so this new fifth stage automatically runs under the usual source-bound v7.1 supervisor with real PIDs and hash-chained `next_task_dispatched` / `checkpoint_committed` evidence. This is **not** an always-on scheduler or permission to resend ambiguous Gemini/PDF claims.

## Regression and acceptance policy

- Targeted synthetic tests: original B49 source gap invokes the existing exact-Git executor once with the right range; deliberately forged model/TTS activity fails closed; no gaps performs no additional check; five-window overflow and disabled registry fail closed; normal default CLI includes all five stages.
- Outer supervisor anti-stall tests: passed stages cause next real dispatch, quarantined curated worker cannot block independent source/G2 work, finite source timeout and descendant cleanup still apply, and independent restart does not replay already-received stages.
- Focused source/supervisor/registry tests and syntax check passed, then broader local source/recovery CI tests and genuine clean-Git stage invocation must pass before engineer acceptance.
- Final acceptance requires a **new committed exact head**, hosted Windows CI successful, real five-stage normal supervisor run including actual patch-integrity stage, independent new-process zero-duplicate restart, source-bound read-only release board, and a durable checkpoint.

## Scientific and release boundaries

Nothing in this patch confirms all historical commits semantically, accepts an original Serway lecture, resolves the unverified dual-PDF Gemini response or 65 pending G2 science units, completes G3 acoustic/video QA, authorizes charges, merges any draft PR, or publishes student media. All original G2 no-resend and scientific, media, source, QA, security and authorization gates remain authoritative.
