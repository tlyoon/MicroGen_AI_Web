# MicroGen_AI_Web — guarded Windows main-revision cutover auto-repair v1

Incident: the first PR #655 certified-main deployment on Dell-115 started a new scheduled daemon whose owner PID subsequently vanished; the previous live v7.1 revision was safely rolled back. The identical code revision ran a successful isolated offline cycle, and a second SHA-pinned guarded handoff succeeded. A transient Windows task handoff must not strand independent eligible development.

`selenium_pipeline.development_guarded_cutover_recovery_v1` is a bounded wrapper around the **existing guarded Windows cutover script**. It never writes the pinned `development_continuity_executor_v71.py` and never creates content, sends a model request, resets a campaign, changes payment permissions, or publishes lecture material.

Only run with a newly prepared, owner-approved JSON manifest whose exact `guard_script_sha256`, old/new checkout, original plan, original state, task name, and expected GitHub main SHA are pinned. The guard script must include its original OS-PID attestation, model-send and publication checks, and verified rollback behavior. GitHub main protection must still require the two Windows CI jobs, strict up-to-date checks and administrator enforcement. The candidate checkout must be clean and identical to the current GitHub main; both executors must have the same SHA. A changed executor requires the separate approved checkpoint migration procedure.

Execution is idempotent. If the new daemon is already independently attested, emit completed without invoking any task mutation. Otherwise require a live owned original daemon and run the existing guard script at most twice. After a failed/uncertain handoff, independently check Windows Scheduled Task state, running owner PID and command line, fresh heartbeat, unchanged task policy, zero provider sends and no publication; retry only when the original daemon has demonstrably recovered. If neither old nor new owner is attested, HOLD that deployment, retain original checkpoints, and continue unrelated work. A stale success string is never proof of a new running daemon. Each attempt creates an atomic, immutable-scope progress receipt.

Example read-only verification from a clean MicroGen checkout:

```
python -m selenium_pipeline.development_guarded_cutover_recovery_v1 --manifest C:\Users\tlyoon\AppData\Local\MicroGen_AI_Web_Checkpoints\RECONCILE_20261125\PR655_CUTOVER_RETRY_MANIFEST_20261126.json --report-root C:\Users\tlyoon\AppData\Local\MicroGen_AI_Web_Checkpoints\RECONCILE_20261125\cutover_recovery_readonly_witness --verify-only
```

Actual deployment uses the same command without `--verify-only`, but **only** for an audited manifest and source script SHA that refer to an undeployed certified main. Never run the same task with simultaneous independent deployers. This specialized recovery worker does not make the v7.1 offline daemon an autonomous code-writing agent; that remains a separate capability requiring a real permitted coding executor.

Regression coverage: `tests/test_development_guarded_cutover_recovery_v1.py` — first-failure/verified-rollback/retry success, missing new process, failure after both bounded attempts, idempotence, false success output, forged model sends, immutable source/plan drift, original code SHA mismatch, missing GitHub strict branch protection, and an actual Dell-115 read-only owner attestation. Integrate this into the project-wide recovery chain: historical failure review → targeted code repair → real safe test → fault-injection regression → registry → exact-head Windows CI → guarded deployment → next eligible task.
