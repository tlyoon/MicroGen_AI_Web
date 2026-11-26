# MicroGen_AI_Web G2 historic owned-response reconciliation — 26 November 2026

## Historical source and actual blocker

PR #658 deployed a safe, persistent G2/G3 zero-Send source-preflight dispatcher to Dell-115. Its live v7.1 daemon discovered slides **3, 4, 10, 11** as incomplete original G2 review scopes and started four valid offline preflight workers. These are not scientific approvals.

A later independent inspection of the *original* G2 queue, request windows, attempt receipts, original source hashes and the explicitly configured Gemini recovery directory established:

- **slide 3, initial review**: original `SUBMITTED_OR_UNCERTAIN` claim and exact per-window dispatch marker. Existing original capture and matching metadata verify **0 bytes**, no retrievable model reply, no provider outage proof.
- **slide 4, independent challenge**: original initial review has source-validated one-pass evidence. The challenge request has `SUBMITTED_OR_UNCERTAIN` and a durable send claim, with no original independently validated challenge result.
- **slides 10 and 11, initial review**: identical conservative disposition to slide 3, each with its own original claimed request and distinct matching verified zero-byte quarantine.

The historical states **are not proof the provider never received the requests**. A zero-byte capture file only proves no recoverable response was saved in that quarantine. Reissuing the same request would violate the one-send contract.

## Integrated recovery

`selenium_pipeline/g2_owned_request_outcome_reconciliation_v1.py` accepts only the original queue, PDF, slide PDF, narration script and prior SHA-pinned `source_backlog_v1.json`, plus the explicitly selected original quarantine root and an isolated receipt location. It verifies exact original owned-claim SHA, request stage and source association, the original attempt receipts, matching recovery raw/meta SHA through the existing historical quarantine handler, and after-work source immutability.

The handler produces a deterministic SHA-addressed immutable receipt. An identical restart reuses the same bytes. It cannot initiate a browser/model/API Send, reset a budget, manufacture scientific acceptance or authorize student release. The production v7.1 daemon is extended to call `auto_audit_completed_handoff` immediately after a genuinely verified source-preflight handoff and to expose `last_historical_g2_disposition`, immutable receipt SHA and lane-specific failure class in the heartbeat; a fault in this evidence-only lane cannot strand other eligible work. Every recurring daemon poll reuses the same output, rather than replaying work.

The executable recovery is registered as `G2_HISTORICAL_OWNED_REQUEST_ZERO_CAPTURE_20261126` in `recovery_registry_v1.json` and `recovery_registry.py`. Its targeted regression suite includes changed original queue/source/G3 SHA, a forged request claim, missing historic window, corrupted attempt JSON, changed capture bytes, unauthorized backlog configuration, mutated immutable output and restart idempotence.

The direct real original Dell proof is at `C:\Users\tlyoon\AppData\Local\MicroGen_AI_Web_Checkpoints\RECONCILE_20261125\G2_OWNED_SEND_NO_REPLAY_EVIDENCE_20261126\ef8545ae95aa93ce8ce042158451013f637ce4c98f470b61856c572f9a335260.json`. A two-cycle real v7.1 daemon proof against an isolated copy of the production checkpoint verified automatic original 4-slide disposition, unchanged source hashes, zero restarts of existing workers and one idempotent receipt; its receipt is in `RECONCILE_20261125\PR659_G2_OWNED_EVIDENCE_REAL_DAEMON_PROBE_20261126_v2\verified_original_g2_owned_no_replay_daemon_2cycle_receipt.json`.

## Long-horizon continuation rule

The standing hourly agent must **not** attempt the same old model requests merely because G2 is still at 29/85. Continue with independent source-specific evidence collection and science review only when new identities, genuinely available existing replies and immutable authorizations support them, with Selenium-only scientific reviewer transport. Meanwhile continue other eligible code development (source-to-slide semantics, independently evaluated spoken WAV content and actual element synchronized video acceptance). The offline daemon remains read-only; the scheduled ChatGPT development automation must author/test/integrate changes, not merely poll.

Merging requires both protected exact-head Windows GitHub checks to pass, then guarded source-identity-preserving Dell deployment. The G2/G3 acceptance gates remain open and no student materials are published.
