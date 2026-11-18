# PR534 — Restartable historical Git batch integrity execution

**Source:** MicroGen_AI_Web, Dell-115 native Windows; parent PR #533 commit `ff3da4a790bca926b2977ef7066ddfe54d5db189`. Date: 18 Nov 2026 MYT.

## Historical failure
The original 48-batch history planner in `windows_historical_stack_batch_plan` only enumerated commit windows. PR #532 repaired the risk inventory to retain 15 intermediate files omitted by final-state diffs in batches 45 and 46, but still stopped at **planning**. There was no executable, SHA-locked, checkpointed commit-integrity stage to advance across batches without a repeated user instruction. Draft PR topology checks and green hosted CI on the latest head do not independently inspect every historical commit.

## Integrated production remedy
`windows_historical_stack_batch_executor.execute_batches` REUSES `plan_stack` and its fixed per-commit touched-file inventory. It requires a clean authorized native Windows checkout, exact base/head/rev-list, finite batch numbers, and the enabled `HISTORICAL_RESTARTABLE_BATCH_EXECUTION` recovery registry entry. For each actual commit SHA it runs read-only `git show --no-ext-diff --no-renames --format= --check` with a hard timeout and bounded output. A nonzero Git patch-check result quarantines the exact batch and leaves later independent batches eligible; it never rewrites historical Git commits or claims full code review. Other infrastructure failures fail closed.

Each batch receives an immutable exact-head, exact member-commit, touched-path-digest and check-implementation-digest keyed receipt under user-local `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\historical_code_batch_execution_v1`, outside publisher assets. An unchanged receipt is verified and reused across process restarts. Source HEAD or tool changes invalidate the path and require new verification. Receipt discrepancies, symlinks and concurrent mutations fail closed. No model, TTS, media or provider access.

The normal historical stack planner has `--execute-offline-history-checks` and optional finite batch-range flags; the normal Windows release-readiness board exposes `--execute-historical-batch-checks` together with `--include-stack-batches`. The new run result is evidence only, not a code/academic review gate or student release approval.

## Real and fault-injection evidence
- Before integrating, read-only real Git inspections of source-bearing batches 45 and 46 checked 40 actual commit patches without whitespace errors.
- New synthetic native Windows Git tests: exact clean batches, bad intermediate whitespace later reverted (one quarantined while next continues), disabled recovery registry, dirty worktree, tampered persisted receipt, different exact HEAD, wrong finite batch bounds, resume without repeating per-commit checks, subprocess timeout, and normal CLI routing.
- Focused tests: 10/10 passed. Wider historical planner/registry/release-board test suite: **44/44 passed**. No paid operation or source-file change.

## Scope and remaining obligations
This validates patch-format integrity, not the meaning or correctness of all historical code. The PR chain has hundreds of linked draft PRs and remains unmerged without independent source, academic/acoustic/video, dependency and release checks. Original Serway §1.3 G2 remains 20/85 accepted and the two-PDF Gemini response source is externally blocked; Serway §6.4 has 67/74 unresolved source mappings. No exhausted request replay is allowed.

Post-commit genuine full-history execution and exact-head Windows CI must be recorded before this engineering scope can be considered closed. Git patch findings must remain auditable even if a later commit reverts them.
