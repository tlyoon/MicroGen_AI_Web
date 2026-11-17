# Automatic Recovery, Persistent Learning, and Autonomous Forward Progress Contract

**Version:** 6.1
**Scope:** Codebase-wide, across all development, execution, testing, recovery, scientific assessment, and QA stages.

**Mandatory v6.1 change:** See Section 14. Production recovery and critical-path progress must be proven by the actual failed operation, not inferred from tests or supporting improvements.

## 1. Primary Objective

Develop and maintain the codebase as a robust, self-recovering, and autonomously progressing system.

The system must automatically detect, diagnose, resolve, test, and learn from encountered blockers. Once a blocker has been successfully resolved, execution must automatically resume from the appropriate checkpoint and advance to the next eligible development or production milestone.

**The user must not need to repeatedly issue instructions such as "proceed", "continue", or "fix the next blocker".**

Automatic recovery and forward progress must be properties of the normal executable workflow, not merely promises, documentation, or one-off interventions by an AI assistant.

The objective is not only to solve the present problem but also to prevent previously encountered problems from repeatedly interrupting future execution.

All automation must respect existing scientific requirements, QA standards, finite resource limits, access permissions, and authorization boundaries.

---

## 2. Mandatory Recovery and Forward Progress Cycle

Whenever a blocker is encountered, execute the following cycle automatically.

### Step 1 — Detect, Diagnose, and Classify

1. Detect execution failures, stalled operations, unexpected outputs, missing artifacts, invalid states, and failed quality checks.
2. Distinguish genuine failures from slow but functioning operations.
3. Identify the affected component, operation, execution stage, and most recent valid checkpoint.
4. Collect relevant diagnostic evidence, including logs, exceptions, state information, output artifacts, and execution history.
5. Classify the problem into a consistent failure taxonomy, including:
   - Temporary infrastructure or network failures.
   - External API, browser, Selenium, or user-interface failures.
   - Authentication, session, or authorization failures.
   - Resource exhaustion, rate limits, or timeouts.
   - Missing, malformed, or inconsistent input/output data.
   - Software defects, dependency failures, or configuration changes.
   - Scientific, logical, or QA failures.
   - Workflow orchestration, concurrency, or checkpoint failures.
   - Previously unknown failures.
6. Identify the probable root cause rather than merely reacting to the immediate error message.

Use deterministic diagnostics whenever possible. Do not substitute repeated guesses for evidence-based diagnosis.

### Step 2 — Search Historical Failures and Reuse Proven Resolutions

Before developing a new resolution:

1. Search the project's persistent failure and recovery history.
2. Examine relevant past development records, existing code, test results, commits, and recovery mechanisms.
3. Identify whether the same or a substantially similar failure has occurred before.
4. Match the failure against known recovery signatures, considering the affected component, environment, symptoms, and root cause.
5. Prefer an existing, previously verified recovery mechanism when its applicability conditions remain valid.
6. Verify that the historical resolution is compatible with the current code, dependencies, configuration, and operating environment.

**Do not repeatedly reinvent solutions to previously resolved problems.**

Historical records must be incorporated into a persistent, version-controlled recovery knowledge base that the executable workflow can consult without requiring access to an earlier ChatGPT conversation.

Maintain sufficient information for every known failure:

- Stable failure identifier and classification.
- Observed symptoms and diagnostic signature.
- Confirmed or probable root cause.
- Applicable environment and software versions.
- Recovery procedure and safety preconditions.
- Verification and regression tests.
- Retry and escalation policy.
- Historical success and failure evidence.
- Date/version of the last successful validation.

A previously successful resolution is not automatically valid forever. Revalidate it when relevant conditions change.

### Step 3 — Develop a Resolution When None Exists

If no suitable verified recovery mechanism exists:

1. Investigate the root cause using available evidence.
2. Identify the smallest reliable correction.
3. Prefer general solutions that address an entire class of failures rather than special-case patches.
4. Preserve existing working functionality and compatibility.
5. Avoid introducing unnecessary dependencies or excessive complexity.
6. Implement explicit checks that distinguish successful recovery from apparent success.
7. Define appropriate fallback strategies when the preferred solution is unavailable.
8. Establish clear conditions under which recovery must stop rather than continue unsafely.

Where feasible, make the resolution reusable across the entire codebase.

Do not treat unsupported assumptions, silent exception handling, or arbitrary retries as valid repairs.

### Step 4 — Verify and Stress-Test the Resolution

Every new or modified recovery mechanism must be tested before being accepted.

Testing must include, where applicable:

1. Reproducing the original failure.
2. Demonstrating that the resolution corrects the failure.
3. Testing relevant historical regression cases.
4. Testing realistic environmental variations and common failure scenarios.
5. Testing failures that occur during recovery itself.
6. Testing interruption, process termination, and restart behavior.
7. Verifying that existing working functionality remains intact.
8. Confirming that scientific and QA requirements remain satisfied.

Use targeted tests first to minimize execution time and resource consumption, followed by representative integration or end-to-end tests when appropriate.

**Passing a synthetic unit test alone is insufficient when the failure depends on actual external-system behavior.** Perform a bounded real-environment validation whenever safe and available.

A recovery mechanism is accepted only when there is credible evidence that it solves the original problem without introducing unacceptable regressions.

### Step 5 — Integrate the Verified Resolution into Production

Once verified:

1. Integrate the resolution into the normal production execution path.
2. Ensure that failure detection automatically invokes the appropriate recovery handler.
3. Add or update automated regression tests.
4. Register the recovery mechanism in the persistent recovery knowledge base.
5. Record the applicable software version, recovery conditions, and verification evidence.
6. Preserve backward compatibility wherever necessary.
7. Ensure that the resolution remains available after application restarts and new AI conversation sessions.

**A solution is not considered complete if it works only when the AI manually executes a particular sequence of commands.**

The executable system itself must be capable of detecting and applying the resolution during future normal operation.

### Step 6 — Persist State and Resume Automatically

The system must maintain a durable execution state containing:

- Active project, workflow, and milestone.
- Current stage and operation.
- Last successfully completed checkpoint.
- Input and output artifact identities.
- Pending operations and their dependencies.
- Failure classification and recovery attempts.
- Applied recovery mechanism and verification result.
- Remaining retry allowance.
- Authorization and QA status.
- Next eligible operation.

Persist important state changes atomically or with equivalent crash-safe guarantees.

When a process is restarted, the workflow must recover its last verified state without unnecessarily repeating completed work.

Completed operations should be idempotent wherever possible. External operations that cannot be safely repeated must have reconciliation or duplicate-prevention mechanisms.

Do not mistake an interrupted, unconfirmed operation for either a successful completion or a definite failure.

### Step 7 — Automatically Continue to the Next Eligible Milestone

After successful recovery:

1. Verify that the interrupted operation is safe to resume.
2. Resume from the most recent consistent checkpoint.
3. Complete the interrupted stage.
4. Verify the stage's acceptance conditions.
5. Identify the next eligible stage from the workflow dependency structure.
6. Automatically begin that stage without requesting another "proceed" instruction.
7. Repeat the recovery and advancement cycle as further issues arise.

This automatic progression must continue until:

- All currently eligible objectives are completed.
- A genuine external dependency prevents further execution.
- A scientific or QA acceptance condition remains unresolved after bounded recovery.
- A required authorization is absent.
- A defined safety, resource, or retry limit is reached.

A successful repair must trigger execution advancement, not merely a success message.

---

## 3. Persistent Recovery Intelligence

The codebase must progressively become more resilient as failures are encountered.

Implement a **Persistent Recovery Registry** that enables:

**Failure recognition:** Previously encountered failures are recognized through stable diagnostic signatures.

**Resolution reuse:** Known recovery mechanisms are selected automatically when applicable.

**Recovery validation:** Every repair is verified against explicit success conditions.

**Historical learning:** New failure classes and verified resolutions are recorded for future reuse.

**Regression protection:** Previously solved failures are covered by automated tests.

**Resolution retirement:** Outdated or repeatedly unsuccessful remedies can be disabled, revised, or replaced.

**Cross-session persistence:** Recovery knowledge resides in the codebase or durable project storage, not solely in an AI assistant's conversational memory.

Prefer deterministic recovery logic over repeated LLM diagnosis for familiar failures. Reserve AI-assisted investigation for ambiguous or genuinely new problems.

A resolved failure should become a reusable engineering improvement.

---

## 4. Prevent Infinite Recovery Loops and Repeated Failures

The system must not become trapped in endless retry, repair, and re-execution cycles.

Implement:

1. Finite retry limits per operation and failure class.
2. Exponential backoff with jitter where appropriate.
3. Circuit breakers for repeatedly failing external services.
4. Detection of repeated unsuccessful use of the same remedy.
5. Escalation to a different recovery strategy when justified.
6. Maximum recovery time or resource budgets.
7. Detection of oscillation between incompatible recovery actions.
8. Explicit terminal or paused states when safe autonomous recovery is exhausted.

Reset retry counters only under well-defined conditions. Restarting the application must not silently reset exhausted failure budgets.

Avoid uncontrolled retries against external APIs, websites, and paid services.

If a failure cannot be resolved safely within the available limits, preserve the checkpoint, report the evidence, and continue with independent eligible work where possible.

---

## 5. Efficient Execution and Resource Management

Recovery must be reliable without becoming unnecessarily expensive or slow.

Apply the following principles:

- Prefer known, tested recovery mechanisms over exploratory troubleshooting.
- Reuse successful intermediate artifacts and valid checkpoints.
- Avoid regenerating completed outputs unless their inputs, dependencies, or acceptance conditions have changed.
- Use selective regression tests before broader testing.
- Cache validated intermediate results when scientifically and technically appropriate.
- Avoid redundant API requests, browser operations, and repeated model calls.
- Distinguish transient service failures from defects that require source-code changes.
- Apply bounded concurrency where it improves throughput.
- Prevent multiple workers from accidentally processing the same operation.
- Use execution locks or leases with expiry and safe recovery.
- Prioritize fixes that unblock multiple dependent tasks.
- Allow independent workstreams to advance while another workstream is blocked, provided shared-state integrity is maintained.

Efficiency improvements must not compromise result correctness, scientific reproducibility, or QA coverage.

---

## 6. Scientific Integrity and QA Requirements

Automatic recovery must never bypass required scientific or quality assessments simply to achieve progress.

In particular:

1. Preserve the scientific meaning and correctness of generated content.
2. Preserve input data integrity and provenance.
3. Maintain the required independent review and QA procedures.
4. Distinguish a technical execution failure from a genuine scientific defect.
5. Do not automatically reinterpret scientific failures as transient software errors.
6. Do not weaken acceptance thresholds merely because a stage repeatedly fails.
7. When the governing QA policy permits minor deviations, apply that policy consistently rather than inventing ad hoc exceptions.
8. Regenerate or repair defective artifacts and rerun the affected assessments.
9. Record meaningful changes to scientific outputs and their validation results.
10. Never mark a milestone complete without satisfying its actual acceptance criteria.

Any proposed change to scientific acceptance criteria must follow the project's existing authorization and change-control requirements.

**Forward progress means advancing through valid stages, not bypassing them.**

---

## 7. External Services, UI Changes, and Uncertain Operations

For workflows involving browsers, Selenium, external APIs, or LLM services, implement additional resilience.

The workflow should:

1. Detect session expiry, changed interfaces, missing controls, server errors, timeouts, and rate limits.
2. Prefer semantic, accessibility-based, or otherwise stable UI selectors over brittle positional assumptions.
3. Verify the actual selected model, setting, or application state after interaction.
4. Use bounded alternative interaction strategies when UI layouts change.
5. Distinguish a failed submission from an operation whose completion state is uncertain.
6. Reconcile uncertain operations before retrying them.
7. Preserve valid sessions and avoid unnecessary browser resets.
8. Respect provider usage restrictions and rate limits.
9. Never bypass authentication, access controls, or paid-operation authorization.
10. Avoid logging credentials, tokens, or other secrets.

When an external dependency is temporarily unavailable, suspend only the affected operation when possible. Continue independent work and retry the blocked operation under its established recovery policy.

---

## 8. Safe Changes, Rollback, and Concurrent Execution

All automatic fixes must preserve system integrity.

Require:

- Version-controlled code changes.
- A known working baseline or equivalent rollback mechanism.
- Pre-change validation of the affected component.
- Post-change verification before production promotion.
- Automatic rollback or quarantine when a fix fails its acceptance checks.
- Protection against simultaneous conflicting repairs.
- Durable, atomic checkpoint updates.
- Detection of corrupted or incomplete checkpoints.
- Recovery from process termination during a code change or deployment.
- Clear separation between experimental recovery strategies and verified production mechanisms.

Do not deploy an unverified speculative patch directly into production.

Do not delete or overwrite valuable artifacts as a routine recovery strategy unless safely authorized and recoverable.

---

## 9. Autonomous Decision-Making and Authorization Boundaries

The system is authorized to autonomously perform routine development, diagnosis, code repair, local testing, verification, checkpointing, and continuation within the existing project permissions.

It must not assume new authorization for:

- Paid API calls or additional expenditure beyond established limits.
- Destructive or irreversible operations.
- Changes to access permissions or security controls.
- External publication, submission, or distribution.
- Material changes to scientific goals or acceptance requirements.
- Actions outside the approved computing environment or project scope.

When authorization is required, preserve the state and continue other permitted work rather than blocking the entire development workflow unnecessarily.

Do not repeatedly request approval for actions already authorized by the applicable project contract.

---

## 10. Monitoring, Auditability, and Completion Evidence

Maintain a concise, structured, persistent execution record.

For each significant blocker, record:

1. What failed and where.
2. Whether it had occurred before.
3. Which historical or newly developed resolution was selected.
4. What changes were actually implemented.
5. Which tests were executed and their results.
6. Whether the fix was integrated into the normal production workflow.
7. Whether restart and checkpoint recovery were verified.
8. Whether execution resumed automatically.
9. Which milestone was subsequently completed or entered.
10. What remains blocked, with the precise reason.

Distinguish clearly between:

- A proposed fix.
- An implemented fix.
- A locally tested fix.
- A verified production-integrated fix.
- A successfully recovered operation.
- A completed and accepted milestone.

Do not report successful integration, stress testing, or milestone closure without corresponding execution evidence.

Reports should be concise and evidence-based. Routine success should not interrupt autonomous execution.

---

## 11. Mandatory End-to-End Acceptance Tests

The automatic recovery system itself must be tested.

At minimum, verify the following scenarios:

**Test A — Previously encountered failure:** Inject or reproduce a known failure. Confirm that its historical recovery mechanism is automatically selected, applied, verified, and followed by resumed execution.

**Test B — New failure:** Introduce a failure without a known remedy. Confirm that a new resolution can be developed, validated, registered, and reused during a subsequent occurrence.

**Test C — Recovery fails:** Make the selected recovery mechanism fail. Confirm that retry limits, alternative strategies, circuit breakers, and escalation function correctly.

**Test D — Crash during recovery:** Terminate the process during recovery. Restart it and verify that the workflow safely resumes or reconciles its incomplete operation.

**Test E — Crash after successful recovery:** Terminate the process immediately after recovery but before the next milestone. Confirm that the next eligible milestone is automatically scheduled after restart.

**Test F — Duplicate execution:** Attempt concurrent execution of the same operation. Verify that the system avoids duplicate processing and conflicting state updates.

**Test G — Scientific/QA failure:** Introduce a genuine content or QA defect. Confirm that the system does not bypass the relevant requirements and performs the appropriate corrective workflow.

**Test H — Authorization boundary:** Trigger an operation requiring additional authorization. Verify that the system stops that operation without exceeding permissions and continues independent authorized work.

**Test I — External service failure:** Simulate a timeout, rate limit, changing UI, or uncertain external response. Confirm bounded recovery without accidental duplicate submissions.

**Test J — Repeated historical regression:** Reintroduce multiple previously fixed failures. Confirm that the current recovery system still resolves them correctly.

A recovery system is production-ready only when all applicable acceptance tests pass and the results are recorded.

---

## 12. Operational Instructions for the Development Agent

When this contract is invoked:

1. Inspect the current project state, execution history, existing recovery mechanisms, and outstanding milestones.
2. Identify the currently blocking failures and any relevant historical resolutions.
3. Begin resolving the highest-priority actionable blocker.
4. Implement and verify the resolution against the real failure wherever feasible.
5. Integrate successful fixes into the executable production workflow.
6. Persist the recovery knowledge and execution checkpoint.
7. Automatically resume the interrupted workflow.
8. Advance consecutively through subsequent eligible milestones.
9. Repeat this process for newly encountered blockers within the authorized execution and resource limits.
10. Report the resulting verified state, completed milestones, unresolved dependencies, and next executable operation.

Do not stop merely because one repair has succeeded.

Do not ask the user to issue another "proceed" instruction when the next operation is already eligible and authorized.

Do not claim that autonomous continuation is occurring in the background unless an actual persistent runner, service, or scheduler has been configured and verified to execute it.

If the AI session or external execution environment ends, ensure the persistent workflow has the necessary durable state and a verified restart mechanism to continue independently when its runner resumes.

If a required execution tool, repository, or computer is inaccessible, clearly distinguish that limitation from an actual code failure. Do not claim changes or testing that have not been performed.

---

## 13. Definition of Done

A blocker is considered **permanently addressed for its verified operating conditions** only when:

1. Its root cause has been identified sufficiently to support a reliable repair.
2. The repair has been implemented in the codebase.
3. The original failure and relevant regression tests pass.
4. The repair is integrated into the normal execution path.
5. Its recovery signature and mechanism are stored persistently.
6. Checkpoint and restart behavior have been verified where applicable.
7. The interrupted operation has resumed successfully.
8. The workflow has automatically entered or completed its next eligible milestone.
9. There is traceable evidence supporting these outcomes.

A milestone is considered completed only when its required acceptance criteria are satisfied.

**Final governing principle:**

> Every encountered failure should improve the system's future resilience. Every verified recovery should become a reusable capability of the executable workflow. Every successful recovery should automatically trigger safe forward progress.
>
> The development process must progressively require less repeated human intervention, while preserving correctness, scientific integrity, safety, and authorization boundaries.

---

## 14. Critical-Path Recovery Proof and Anti-Loop Development (Mandatory v6.1 Amendment)

**Precedence:** This section strengthens Sections 1–13. When a prior section permits a weaker inference of success, use the stricter real-operation requirements below. No scientific, authorization, cost, source-provenance, one-Send, or finite-retry protection is relaxed.

### 14.1 Optimize for restoration of the actually blocked operation

Identify the primary critical-path operation and its measurable user-facing acceptance outcome **before** selecting a repair. Maintain the dependency chain from the failure to the blocked milestone, and label secondary improvements as *independently useful but non-unblocking* until they demonstrably restore that operation.

Do not substitute easy-to-test improvements, additional diagnostics, more registry entries, CI badges, or safe-stop behavior for the main outcome. Prioritize repairs using evidence that they address the actual failure; repeatedly fixing unrelated issues while the same P0 operation remains blocked is an explicit development-process failure. A diagnostic improvement is valuable, but must not be called a recovery.

### 14.2 Required recovery evidence states

Every blocker shall carry an explicit durable status, with no ambiguous "fixed"/"resolved" shortcut:

1. **DIAGNOSED** — symptoms and evidence recorded; cause may be uncertain.
2. **PATCH_INTEGRATED** — implementation wired into the normal executable code path; no success claim.
3. **TESTED_OFFLINE** — unit/regression/fault-injection tests passed; actual external operation not yet proven.
4. **LIVE_CAPABILITY_VERIFIED** — the actual required external modality and response capture were proven under an attributable live request. This alone does not imply scientific review acceptance.
5. **ORIGINAL_OPERATION_RECOVERED** — an *eligible new or safely reconciled* instance of the originally failed operation completed, its output is attributable/source-bound and persisted, and its real acceptance criteria passed.
6. **NEXT_MILESTONE_ADVANCED** — after original-operation recovery, the normal executable workflow automatically entered or completed the next eligible downstream milestone with persisted evidence.
7. **BLOCKED_EXTERNAL_DEPENDENCY** / **BLOCKED_QA** / **BLOCKED_AUTHORIZATION** — no eligible safe operation can establish steps 4–6; preserve the exact facts and do not relabel as resolved.

States 5 and 6 require independently checkable production evidence. A high test count, local mock, recorded Send, correct model picker, provider text-only canary, or inferred successful request is insufficient. Do not advance a blocker to a stronger state solely by editing its status field, adding a registry entry, or issuing another assistant instruction.

### 14.3 Real failure, real validation, unchanged identity

For each repair explicitly record: original failure signature; immutable operation/request/source identity; original failure reproduction or preserved incident proof; code change; regression results; one production invocation; attributable real output; acceptance verdict; automatic downstream continuation; and new blockers. The verified output must correspond to the operation being repaired, not to a different, easier test.

For source-grounded scientific work, retain original source hashes and independent review requirements. An offline candidate map, synthetic capability proof, source-free text reply, WAV/MP4 existence, or geometry check is not an independent scientific review and cannot increase the approved-unit count. Do not accept an unrelated successful test as a proxy for the originally blocked stage.

### 14.4 External LLM PDF-response transport: explicit positive proof

For the current Gemini/Selenium PDF blocker, independently distinguish these hypotheses:

- service/backend did not generate an attributable PDF-based response;
- the browser received/displayed an answer but Selenium's owned-response capture missed it;
- attachment ingestion or response ownership failed;
- model/Thinking selection or authentication was unverified.

Do not assert any hypothesis without evidence from the *same request and owned browser tab*. Before qualifying an external PDF-response path, require an authorized existing authenticated session and positively verified model/Thinking controls, then a bounded, **new, source-free, uniquely claimed** test attaching two distinct synthetic PDFs. Each PDF must contain a different unprompted challenge known only from its file bytes. Require a **single owned Send**, genuine attributable model response, correct readback of both secrets with request ownership, and persisted source-free proof; treat missing/ambiguous capture as failure, not a success or automatic resend permission. Retain finite per-incident probe limits.

Only after that *modality* proof may a separate eligible, unattempted source-bound scientific review be dispatched. Transport is considered **recovered** only after an attributable real academic PDF response completes the originally blocked operation and meets the pre-existing independent source/QA checks. Do not replay consumed or uncertain prior source Sends or retired synthetic incidents.

### 14.5 No endless cycles disguised as progress

If the same critical-path blocker persists across a development cycle, require a **new falsifiable hypothesis or independently obtained evidence** before authorizing another live experiment. Do not repeat the same model-selection attempt, attachment-bearing Send, or provider probe merely because a new ChatGPT conversation began or unrelated tests passed. Unchanged provider health and exhausted capability budget must remain blocked across process restarts.

Maintain a bounded **critical-path recovery budget** and a separate supporting-work budget. When safe new experiments are unavailable, report the precise dependency and advance only independently eligible work; never inflate that into source-review or G2/G3 completion. A code change may be merged as a tested improvement while its original provider blocker remains open.

### 14.6 Executable verification gate, not documentation alone

Implement an executable, fail-closed recovery acceptance gate invoked from normal workflow decisions. It must reject claims of **ORIGINAL_OPERATION_RECOVERED** or **NEXT_MILESTONE_ADVANCED** unless tied to the exact incident/source operation, the real accepted output, and validated downstream transition. Record separate fields for engineering test success, live modality proof, original-operation acceptance, critical-path unblocked, and next-stage advancement. Verify restart/idempotence, forged status/receipt, stale artifact, another-model/another-tab substitution, and false-positive progression in automated tests.

An individual remedy can remain installed and useful as **PATCH_INTEGRATED** or **TESTED_OFFLINE**, but it must never be labeled an end-to-end repair without steps 5–6. Where actual external proof cannot be obtained due to provider availability or authorization, do not pretend to pass that gate; leave the incident blocked.

### 14.7 Reporting and promotion criteria

Every update must start with the **critical-path gate**: originally failed operation, last real accepted output, measurable count/milestone change since last report, blocking cause/evidence, and next eligible action. Report secondary fixes in a separate section, clearly marked as such. CI passes must be attributed to the exact tested commit. Unmerged development-branch fixes are not deployed production changes. A one-launch controller is not an always-on service or a scheduled task.

Mark the primary blocker closed **only** when:
1. the real originally failed operation passed under the integrated remedy;
2. its source/request and model-owned response identities are independently verified;
3. the saved actual output passed unchanged acceptance checks;
4. at least one eligible downstream transition actually executed under the normal controller;
5. the proof survives a restart and is reflected in the durable recovery registry/ledger.

Until all five conditions hold, use a qualified state and preserve the unresolved critical-path status, regardless of the number of ancillary repairs completed.

**Governing measure:** Success means *the failed production operation now works and the pipeline genuinely advances*, not *we made more tests pass*.
