# MicroGen hardening acceptance report — 12 October 2026

**Repository:** [tlyoon/MicroGen_AI_Web](https://github.com/tlyoon/MicroGen_AI_Web)
**Reliability PR:** [#28](https://github.com/tlyoon/MicroGen_AI_Web/pull/28)
**Merged GitHub main:** `3616b7658a1df3feb227bd31bb126bd8e4201682`
**Status:** **Offline hardening accepted; final three-PC full-production certification remains open.**

This report distinguishes demonstrably completed work from outstanding live/semantic acceptance. No simulation, unit test or worker start is described as a completed lecture.

## Phases and evidence

| Phase | Evidence | Status |
|---|---|---|
| 1 — Failure and fix audit | Historical incident-to-protection matrix, root-cause limitations and closeout rule in `MicroGen_Historical_Failure_and_Fix_Audit.md` | Delivered; additional unknown historical incidents may emerge |
| 2 — Pipeline hardening | Gemini Flash fresh-tab safe recovery; per-port local browser lock; strict source/hash/stage checks; zero-pending-review TTS QA; durable downstream invalidation; protected MP4s, WAVs, `.history`; missing-source-figure previews | Merged PR #28 |
| 3 — Multi-PC portability | Independent clones on HP, Dell-115, Yoga6; separate Python environments; merged main source tree verified identical to tested candidate; disjoint chapter assignments and local browser locks | Targeted tests passed; full unattended cross-PC certification pending |
| 4 — Regression suite | **213 tests passed**, 8 non-fatal legacy/third-party warnings in HP candidate environment; **33 targeted tests passed each** on Dell-115 and Yoga6 | Passed local offline tests |
| 5 — End-to-end validation | Real Serway 12.1 source PDF missing-figure preview/fail-closed test; isolated 2-slide PDF+WAV to H.264/AAC MP4, missing-WAV failure without video loss; actual Dell-115 Flash High generation stage start | Partial: whole lecture fresh generation, semantic narration/figure review and interruption recovery on all PCs still needed |
| 6 — Release, documentation, distribution | Merged #28 to `main`; README, historical audit, operations runbook, GitHub Actions regression workflow in repository | Code and docs merged; GitHub Actions execution status not independently confirmed |

## Safeguards now in main

The repository has permanent regression-backed protections for the already observed Gemini composer and mode-picker changes, account-safe Flash checking, pipeline stage evidence, missing figure source-page review candidates, paper/audio/video dependencies, per-PC competing-browser processes, incomplete TTS QA, history and WAV preservation, and source/output completion-receipt verification. It **does not** automatically certify a proposed physics figure solely from a caption or filename.

The stage watchdog remains 900 seconds of output silence and 3,600 seconds hard timeout, with deferral and a second pass. Google Drive virtual-ticket files are **not atomic locking primitives**, and the lock only coordinates updated local clients that cooperate with the browser lock.

## Independent acceptance commands

HP full offline test suite (test-only Pytest installed separately, no production package changes):

```powershell
$env:PYTHONPATH="C:\Users\tlyoo\AppData\Local\MicroGenRecovery\hardening_test_dependencies_20261012"
python -m pytest -q tests selenium_pipeline/tests
```

Each Dell-115 and Yoga6 candidate clone ran the same 33 selected no-account regression tests (`test_browser_port_lock`, `test_gemini_mode_recovery`, `test_hardening_regressions`, `test_figure_recovery_candidates`, `test_reliability_audit`, `test_downstream_invalidation`, `test_env_key_conflicts`). Dell-115 needed isolated PyMuPDF for these tests; the live environment was left unchanged.

The actual Serway source root was read-only audited as of **2026-10-11 16:53 UTC**: 46 source PDFs, 6 receipt-verified lectures, 7 partial decks, 33 without published slides. This is a **historical snapshot**. Re-run `python -m selenium_pipeline.reliability_audit --source-root <root> --expected 46` to obtain live status; do not infer new completion from these numbers.

## Deployment and production separation

- **Dell-115:** An unrelated Calculus 3.8 MicroGen process finished before restarting Serway. A merged-code isolated checkout was pinned at `3616b765`, Gemini Flash High verified, duplicate-worker check passed and recovery worker launched as PID `16208`; first observed at 8.1 figures. Its subsequent progress must be independently checked.
- **HP and Yoga6:** Original Serway recovery workers were **not hot-upgraded**. They continue on the preceding isolated checkout `4bb1da9` until safe process exit, then should receive a clean update to the merged version. This is not an end-to-end acceptance of the new code on those workers.
- The old shared production repository and historical campaign checkpoint were not overwritten. Validated lecture output and source-PDF files were not modified by the hardening development/test cycle.

## Unresolved, explicitly tracked release limitations

1. A textbook PDF page preview is **not** a scientifically verified figure crop; approving, publishing and narrating image corrections may still require semantic review.
2. A normal full-length Serway lecture generation plus controlled interruption and resumption on **all three PCs with the merged code** has not yet been certified.
3. Late-stage TTS, paid API quota, authentication and true browser service outages remain possible, even when the software defers without data loss.
4. The newly added GitHub Actions workflow is configured to run on `main` and PRs, but this report does **not** claim a successful remote GitHub Actions run without direct check evidence.
5. The historic campaign still contains outstanding partial jobs; the recovery worker's `finished` phase is not sufficient to declare 46 complete.

**Result:** PR #28 is an implemented, tested hardening release. Full end-to-end multi-PC reliability certification and 46-lecture campaign completion remain separate milestones.
