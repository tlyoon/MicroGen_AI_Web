# Phase 2D — actual Codex no-diff failure and executable v7.1 recovery

## Actual Dell-115 failure, 21 November 2026

After PR #583 merged as main 452a0d9, we admitted a real, source-bound
coding job in a newly cloned disposable feature branch:
  PHASE2D_REAL_CODING_PROOF_20261121\repo
  branch feature/pr585-bounded-coding-real-proof-20261121
  original_main_sha 452a0d9f29d8f6d6d3bd14942fceb1ffd24710d2.
The manifest allowed a **single** new pytest test file and 480 seconds
maximum. Its current-user Codex CLI wrapper SHA was pinned; workspace-write
sandbox and network-off command execution were applied.

The actual Codex process returned exit code 0 and an attributable text
response (267 output characters, SHA
e990d85671bb4da61e47fa16d761343c3cdec459f0e51300a7b47e05c69fd00b),
but it created NO source changes. The coding verifier correctly refused to
approve the candidate, which had no Git diff and no new regression test.
The pre-Send checkpoint had recorded model_invocations_claimed=1 and
MODEL_RESPONDED_UNVERIFIED. No push, CI, publication or further model send
was attempted for the original job.

A nonempty model text response is not evidence of a code repair. Blindly
resending the original request risks duplicate paid/provider operations.

## Executable recovery path

- The normal coding candidate now imports an exact allowlisted
  development_coding_recovery_registry_v71.json. Supported handlers:
  MODEL_RESPONDED_NO_SOURCE_DIFF -> quarantine no-op, preserve the
  consumed response and advance independent work; no new provider calls.
  MODEL_MODIFIED_UNAPPROVED_FILES -> quarantine untrusted diff, never push;
  MODEL_RESPONDED_TEST_FAILED -> retry verification of already returned
  code without sending another model request.
- If the verified model response produces no source changes, the normal
  run_once now persists MODEL_NO_SOURCE_DIFF_QUARANTINED with the original
  job SHA, main SHA, model response SHA, one claimed invocation, false PR
  push and release flags, and independent work eligible.
- If modified files appear outside the exact source allowlist or are
  malformed, persist MODEL_SOURCE_CHANGE_QUARANTINED, no push.
- If tests fail on an otherwise allowed source diff, persist
  MODEL_RESPONDED_UNVERIFIED with the registry recovery action for a
  no-model-replay regression retest.
- A separate --reconcile-only command is permitted exclusively when an
  original source-bound model response already exists. It cannot send
  a model request, and can reconcile an older clean main/branch SHA
  without requiring current remote main if no external model is dispatched.
  Uncertain result claimed without an attributable returned response
  remains blocked. This is a historical evidence reconciliation, not a
  permission to run a fresh coding job on stale source.

## Real verification

Run from independent source checkout using
  python -m selenium_pipeline.development_coding_job_v71
  --reconcile-only --job <ORIGINAL_JOB>
  --repo <ORIGINAL_CLEAN_BRANCH> --state-dir <ORIGINAL_STATE>
  --checkpoint-root <ORIGINAL_CHECKPOINT_ROOT> --codex <PINNED_CLI>

On Dell-115, the original provider result was reconciled in place with
no new model invocation. Its state now reads:
  status MODEL_NO_SOURCE_DIFF_QUARANTINED
  failure_class MODEL_RESPONDED_NO_SOURCE_DIFF
  recovery_action QUARANTINE_NOOP_PRESERVE_RESPONSE_AND_ADVANCE_OFFLINE_BACKLOG
  model_invocations_claimed 1
  candidate_pr_pushed false
  next_independent_workstream_eligible true
The original feature branch remained clean (no changes), and no paid
Gemini/Codex call was repeated.

## Fault injection and remaining work

33 focused tests passed, covering the above original no-op, restart
with zero replay, changed model response, unauthorized changes, exact
registry tampering, test failure and recovery, source identity and
release/PR refusal.

Full repository tests plus GitHub Windows, Ubuntu and offline CI are
required before this mechanism may be merged. After merge, new independent
coding jobs can be admitted only with fresh unique job manifests and
original source/authorization checks; the original failed request must
remain quarantined.

This recovery is not proof of real successful Codex code modification or
a persistent self-authoring development agent. Those remain separate
Phase 2D boundaries. Phase 2C offline daemon continues to run with
zero code-authoring rights. Original G2 remains 26/85 accepted, 59 pending
and G3 plus final release remain unaccepted.
