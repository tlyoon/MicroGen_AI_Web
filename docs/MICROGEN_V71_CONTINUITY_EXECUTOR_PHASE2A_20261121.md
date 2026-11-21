# MicroGen_AI_Web: v7.1 continuity executor — Phase 2A

## Identity and authority

The project is MicroGen_AI_Web at github.com/tlyoon/MicroGen_AI_Web, NOT Bosla
or the separate MicroGen_AI repository.

Authoritative autonomous development v7.1 contract:
https://docs.google.com/document/d/17g84vOa3B0GNRgle294BzpR8HQfe48ev/edit

Mandatory handoff: checkpoint committed -> next action dispatched, with an
observable worker PID/result. A status report or recommendation is not
execution. A missing persistent runner must be reported as NOT RUNNING.

## Executable Phase 2A capabilities

Entry point: python -m selenium_pipeline.development_continuity_executor_v71
run --plan ABSOLUTE_PLAN_JSON --state-dir ABSOLUTE_STATE_DIR --repo-root
ABSOLUTE_CODE_ROOT

Supported actions are strictly: verify_file_sha256, pytest_suite (only bounded
repository test files), g2_source_reconciliation (read-only, no provider Send),
lecture_completion_readonly (existing integrity gates). Any arbitrary
shell, model Send, paid call, code edit, PR merge or student publication is
rejected before dispatch.

Plan and controller source SHA are version-pinned. OS-held file locks prevent
duplicate controllers. Each step persists an atomic fsynced checkpoint,
original worker token, actual PID and source-attributed result. The process
scans eligible tasks across workstreams rather than stopping after one pass.
Exhausted tasks are quarantined while independent authorized work advances.

Restart after crash BEFORE child start reuses the same original token.
Crash AFTER child start never launches a second child; it uses the saved
receipt or awaits that exact child while other independent work proceeds.
An exact executable allowlist in
selenium_pipeline/development_continuity_recovery_registry_v71.json limits
recoveries; modified/disabled/foreign rules fail closed with ZERO model Sends
and ZERO publication permissions.

The state contains checkpoint_committed, next_task_dispatched, worker_started,
task_accepted, task_quarantined, authorization_gate_held,
orphaned_worker_result_reconciled and uncertain_worker_pending_receipt events.
project_complete only describes the explicitly pinned offline plan, NOT
total MicroGen_AI_Web G2/G3/scientific/release completion.

## Real Dell-115 acceptance

Isolated workspace:
%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\CONTINUITY_EXECUTOR_V71_20261121

The actual on-demand execution automatically dispatched and completed FOUR
authorized tasks across different workstreams:

1. Exact source-PDF SHA for published Serway 8.2.
2. Independent original Serway 1.3 G2 evidence reconciliation (the reconciliation
   task passed; original source acceptance remains 26/85 with 59 pending).
3. Cross-PC figure, G2 no-Send, and project-status regression tests.
4. Actual Serway 8.2 source-bound completion and slide validation.

An explicitly unauthorized release task was held. Final roadmap status:
BLOCKED_OR_AWAITING_EVIDENCE, project_complete=false. Original source,
lecture files and both intentionally disabled Windows scheduled tasks were
not modified; no Gemini Send, no TTS, no media generation, no paid request.

Real local plan:
real_offline_roadmap_20261121.json
Real state: real_offline_state/state.json

## Mandatory regression and fault tests

Actual Python subprocess tests (not just mocked callbacks) cover:
- Success A -> B -> C within one supervisor run.
- Last task of a local workstream -> independent next queue.
- Quarantined exhausted task -> independent authorized action.
- Bounded retries (maximum 2).
- Crash after persisted claim and before child start -> original token once.
- Crash after real child starts -> reconcile original receipt, no second child.
- Unknown child outcome -> wait for receipt, fan out other work.
- Misattributed or forged result rejected.
- Unregistered Gemini Send rejected before dispatch.
- Authorization gate held; independent work still launches.
- No fake background-running state or global completion claims.
- Plan mutation, unknown dependency, cycle and recovery-registry tampering
  fail closed.

## Limits and next boundary

This is verified ON-DEMAND continuity, not yet a Windows boot-persistent
development service and not a self-authoring coding agent. No scheduled tasks
were enabled or created in this phase. Code authoring, source-scientific
G2/G3 acceptance, provider request recovery and authorized publication remain
separate gated workstreams.

Phase 2B must add an explicitly authorized real persistent process/launcher,
verify its live heartbeat/restart after loss of interactive control, and
extend next-action routing to independently eligible production QA tasks.
Do not infer active persistence from only this code, a status document or
a finite local roadmap.
