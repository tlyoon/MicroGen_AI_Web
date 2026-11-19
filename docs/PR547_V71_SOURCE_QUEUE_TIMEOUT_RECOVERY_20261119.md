# PR547 — v7.1 long offline regression-stage timeout recovery

**Date:** 19 November 2026. **Host:** Dell-115. **Parent:** PR546 source SHA `539b7af613bc10952b04e57143ba806a4446a822`. Isolated checkout `%LOCALAPPDATA%\MicroGen_PR547_20261119`; no original source, shared Drive publisher, or student media edits.

## Historical failure and verified cause

The real PR546 normal v7.1 run launched its 48-task source-only queue at 19:21. The outer child stage reached its fixed **900-second timeout** while the inner code controller had already saved 47 passing source-test task receipts and started batch 48. Parent recorded `WORKER_DID_NOT_RECORD_OUTCOME`, exit 124, and quarantined the stage, then correctly continued independent Git-gap and read-only original G2 claim-reconciliation stages. It did **not** repeat the consumed original source request or falsely approve the failed source-test stage.

This is a supervisor allowance mismatch, not evidence of a failing source regression. The inner production controller still enforces one SHA-locked receipt per task, finite two source-only attempts, and a 150-second timeout for each test subprocess.

## Targeted executable recovery

- Increase only `curated_offline_source_regressions` outer timeout from 900 to a **finite 2400 seconds**; other stage timeouts remain intact.
- Register `V71_LONG_OFFLINE_QUEUE_PREMATURE_TIMEOUT` with `BOUNDED_LONG_OFFLINE_QUEUE_AND_DESCENDANT_CLEANUP` in the actual executable recovery registry. Fail closed before worker intent/dispatch if that mechanism is missing, disabled, or the allowance is 900 seconds.
- On genuine outer timeout, reuse existing Windows process-tree termination instead of killing only the wrapper PID. This prevents an orphaned offline test child from continuing after timeout.
- Do not replay any quarantined PR546 exact-head worker. The source-policy change must be committed to a **new exact SHA** with its own immutable task receipts.

No Gemini model Send, cloud API, paid TTS, academic promotion, auto-merge, student publication, or weakening of independent scientific review is added.

## Evidence and acceptance requirements

Focused native Dell registry/supervisor tests: **27 tests passed** (including new real launcher timeout propagation, missing/retired registry, old 900-second policy rejection, simulated timeout and descendant cleanup, and continuation to independent stages). Git local diff check passed. Broader history, normal controller, import and release tests, exact SHA commit and hosted CI, actual 48/48 run, separate-process receipt reuse, and release board must still be evaluated before declaring the repair fully accepted.

The original Serway §1.3 scientific G2 is still 20/85 source-agreed and 65 pending; no old uncertain two-PDF Gemini request may be resent.
