# G2/G3 source-checkpoint-derived coding tasks — v1

This mechanism extends the previously finite `approved_source_jobs_v1.json` queue. When all reviewed catalog IDs have been claimed, the source selector calls `development_g2g3_requirement_task_factory_v1.derive`. The compiler requires an exact clean GitHub `main` checkout and `development_specs/g2g3_technical_requirement_rules_v1.json` committed to that same reviewed revision.

The compiler reads the **live** G2/G3 daemon heartbeat at `RECONCILE_20261125/live_state_migrated_v1/daemon_heartbeat.json`, checks the actual open G2/G3 milestone status, and selects the next unclaimed technical rule. It builds the **independent** test program deterministically from the reviewed `set_coverage` or `ordered_alignment` oracle, writes a durable original evidence receipt, commits the test to a dedicated Git worktree, and atomically stages a SHA-pinned one-claim Selenium author job. It never uses an AI model to write its own acceptance tests.

All code-generation requests remain Selenium-only with one immutable Send claim. The separate original worker must pass its independent test, then the existing promotion controller requires GitHub Windows CI, strict merge verification and guarded dual-worker deployment. Failed, uncertain, or quarantined prior Sends are never recycled. No scientific, acoustic, visual-semantic, or student-publication acceptance is conferred by metadata parity.

## Current source-grounded technical requirements

- G3: original caption identifiers versus rendered LaTeX figure identifiers
- G3: source page indices versus narrated WAV segment indices
- G3: original page indices versus encoded MP4 segment page indices
- G2: original slide identifiers versus the reviewer evidence references

The current reviewed rule set is deliberately finite. Genuine additional engineering requirements may be added by changing the Git-reviewed requirement rules and/or adding audited deterministic oracle families; they will then be admitted automatically by the next running selector cycle after certified deployment. New scientific-acceptance tasks cannot be made valid by inventing tests or by counting metadata matching as independent physics review.

## Restart and fault-injection contract

Each generated job has its own never-reused ID, pinned test SHA, source gate, main SHA, independent test receipt and original model claim. The existing CI/deployment mechanisms must operate on the exact original source SHA. The test suite verifies clean-main provenance, closed/unknown gates, invalid catalog records, malformed checkpoints, non-replay, SHA integrity, and that incorrect generated code actually fails independent tests.

Inspect `autonomous_controller_heartbeat.json` for `SOURCE_GROUNDED_INDEPENDENT_TEST_JOB_STAGED`, `SOURCE_G2G3_REQUIREMENT_TEST_JOBS_EXHAUSTED`, or a failure status. The tasks are useful only when the source/checkpoint provenance is genuine; they do not themselves close G2/G3 scientific acceptance.
