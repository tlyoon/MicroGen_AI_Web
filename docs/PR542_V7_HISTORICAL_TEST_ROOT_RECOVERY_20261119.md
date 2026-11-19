# PR542 — Guard both historical regression-test roots in normal source review

**Date:** 19 November 2026 (MYT). **Authorized host:** Dell-115. **Parent:** draft PR541 exact HEAD `c794e2d81477a262cb18116db10ff2495f61512b`. This is a source-only repair in an isolated Windows worktree; no change to G: publisher/main or original academic media.

## Historical failure, review and classification

The first cross-session historical gap report over batches 22–36 examined original Git test files only beneath `tests/`, missing a second established root, `selenium_pipeline/tests/`. It incorrectly reported that original batches 34 and 35 had no changed test files and the statement propagated into draft PR541 documentation. The corrected exact-Git v2 audit of the original commits proved **18 historically touched test paths in batch 34 and 21 in batch 35**, all found in the nested root. Preserve the original flawed v1 audit as failure evidence. This was a source-audit and reporting failure, **not** proof that the live G2/science/media pipeline malfunctioned or that PR541's current-code tests failed.

The existing normal planner's `_risk_paths` already classified both roots generally, and its exact-commit touched-path inventory already prevented disappearing/reverted file changes. Reuse that existing source-verification logic rather than writing a second Git history parser.

## Targeted executable repair

The normal `selenium_pipeline.windows_historical_stack_batch_plan.plan_stack` now exposes for every SHA-anchored history window:
- historically touched regression-test path count across `tests/` **and** `selenium_pipeline/tests/`;
- exact count per root, first 15 source paths, and SHA256 of the sorted complete list;
- a separate explicit false academic/semantic acceptance boundary.

All fields use the original committed `git log -m --name-only` evidence already verified against `rev-list`, not a manually written list or filenames from only the current working tree. Deleted/reverted historical test paths remain included. The existing executable recovery registry now recognizes exactly one new `history_test_root_inventory` handler mapped only to `NORMAL_WINDOWS_HISTORICAL_STACK_BATCH_PLANNER`, and the normal planner refuses disabled, missing or forged registry admission. All other registry validation remains strict.

## Failure injection, regression, and normal restart

- Synthetic genuine Windows Git tests: root and nested tests in one history; a misleading `selenium_pipeline/test_not_a_test.py` excluded; test created then deleted retained; disabled only-new registry mechanism refuses source plan.
- Source syntax and JSON parse, `git diff --check` and the targeted existing history/recovery registry tests remain required.
- A live, read-only recheck against the actual original batch34 and batch35 Git history must show 18 and 21 respectively; then commit/push a draft stacked on PR541, verify hosted Windows exact-head CI, and restart the normal read-only release board. **These are pending until independently verified.**
- No `--advance-offline-development` model Sends are necessary to test this source-only historical inventory; if a new committed HEAD is tested through that controller, all 30 new exact-HEAD task receipts must be reverified with zero unsafe replay.

## Scope

This repairs test-path inventory and source review evidence. It **does not prove** the historical commits semantically correct, complete the independent original mathematics/source QA, supply a second distinct original lecture, pass G2/G3 acoustic/video review, approve all stacked draft PRs, merge into `main` or publish student media. The v7 contract continues to require actual forward progress through the next safely eligible milestone; across-session execution still needs an authorized persistent runner.
