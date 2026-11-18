# PR532 — Restore transient changes to normal historical stack review inventory

**Date:** 18 November 2026 (MYT) · **Machine:** Dell-115 (native Windows) · **Repository:** MicroGen_AI_Web · **Parent:** draft PR #531 / `d858e0f667f8c587c97c4de054bd02757c31ae2b`.

## Historical failure and root cause
The existing `windows_historical_stack_batch_plan.plan_stack` generated finite SHA windows but inspected the changed files using only `git diff --name-only <prior-batch-end> <batch-end>`. This describes a net endpoint difference, not all code or metadata touched during the batch. A file modified and then reverted could disappear. The existing plan explicitly did not approve academic QA, merge or release, but its risk inventory could still be incomplete.

The original Dell-115 plan for 945 feature commits ahead of the tracked main comprised 48 batches of at most 20 commits. Comparing its endpoint-change files with genuine commit-by-commit Git history exposed **15 omitted paths** across exactly two batches:
- **Batch 45**: net 71, touched 80; nine intermediate paths including `windows_new_source_browser_admission.py`, `windows_fresh_source_trial.py`, `windows_original_stage_sequence.py`, the coordinator and source-admission regression tests.
- **Batch 46**: net 83, touched 89; six intermediate paths including `academic_source_microbatch.py`, `gemini_stage_policy.py`, `gemini_ui_adaptive_protocol.py`, `original_source_e2e_acceptance.py` and two relevant tests.

This was a **real historical inventory false negative**, not proof that those files were scientifically correct or contained defects.

## Code-level remedy in the normal production planner
- Reuse the existing native Windows `plan_stack` entrypoint, its exact `origin/main..HEAD` rev-list, finite 1–40 commit batch windows, isolated LOCALAPPDATA worktree gate and no-merge/no-publication contract.
- Query Git once using `git log -m --no-renames --format=MICROGEN_COMMIT_SHA:%H --name-only origin/main..HEAD` and require every exact SHA of the previously verified `rev-list` to occur in that stream.
- Build each batch's review path inventory from the **union of all paths touched by its actual member commits**, conservatively unioned with the original endpoint diff. `-m` conservatively includes merge-parent changes. The first and last SHA of the existing batch remain unchanged.
- Preserve `changed_path_count` as the revised inclusive count, and add the original `net_diff_path_count`, `historical_touched_path_count`, `transient_or_reverted_path_count`, up to 12 illustrative paths, and a deterministic inventory digest for auditing.
- Fail closed on absent/unrecognized commit identifiers, missing historical paths before a commit header, unsafe path records, or a disabled/missing registry mechanism.
- Register `HISTORICAL_BATCH_COMMIT_PATH_INVENTORY` / `HISTORICAL_BATCH_NET_DIFF_HIDES_REVERTED_PATHS` in the actual versioned `recovery_registry_v1.json` and handler whitelist. Normal release-board batch planning uses the same improved source; no parallel processor or Send/retry system was created.

## Real test, fault injection and regression
- Genuine unchanged Git repo on Dell-115: **945 commits, 48 bounded batches**, with **15 recovered omitted paths** across batches 45 and 46. All other 46 batches have no such observed difference.
- A separate synthetic Windows Git repository created a source-like PDF, committed it, deleted it in a subsequent commit, and verified that normal planner still marked its file and SOURCE_OR_AUDIO_MEDIA_ASSET risk despite zero net PDF at the batch end.
- Injected malformed/missing exact-commit markers, unanchored Git paths and disabled registry mapping all failed closed.
- **62 selected regression tests passed**, including historical batch planner, recovery registry, release readiness board, exact GitHub CI and PR-chain audit. Existing safeguards that historical reviews cannot auto-merge or publish remain true; compilation and diff whitespace checks also passed.

## Remaining boundaries
The static code-file history inventory is repaired, but **not a complete semantic per-commit code review**. The 48 historical batches remain queued for independent bounded review. No automatic merge of 164 draft PRs is authorized. P1 Serway §1.3 Gemini two-PDF response transport remains BLOCKED_EXTERNAL_DEPENDENCY; G2 20/85 independently accepted, 65 unresolved, G3 and independent acoustic/video acceptance still open. No original request replay, textbook source modification, paid API/TTS, new WAV/MP4, or student publication occurred.

Next steps: commit to isolated draft PR stacked on #531; verify latest-head hosted Windows CI; rerun actual normal batch planner under that committed SHA and inspect remaining batches using corrected inventory.
