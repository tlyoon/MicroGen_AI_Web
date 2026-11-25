# MicroGen_AI_Web — Windows-only development and regression contract

**Effective:** 25 November 2026
**Status:** Binding forward-looking platform and CI amendment to the Autonomous Continuous Development, Recovery and Forward Progress Contract v7.1.
**Authoritative v7.1 contract:** [Original Google Drive Markdown contract](https://docs.google.com/document/d/17g84vOa3B0GNRgle294BzpR8HQfe48ev/edit); the source document's Section 12 contains this Windows-only decision and was independently read back from Google Drive on 25 November 2026. Keep both copies consistent.
**Scope:** The tlyoon/MicroGen_AI_Web repository and all routine code-development, repair, regression, release and continuous-integration workflows. This is **not** a change to the separate Bosla project.

## 1. Supported platform and precedence

**Windows is the only supported execution and development-test operating system for this codebase.** Development uses the authorized Windows machines, with Dell-115 as the primary development/production validation host. Supported hosted CI runners use **windows-latest** (Python 3.12 unless later explicitly revised). Cross-PC operations must use authorized Windows machines.

This platform decision takes precedence over any older generic "cross-platform", "OS-agnostic", Ubuntu/Linux CI matrix, or Linux-hosted development-testing expectation in historical reports, prompts, docs and workflow files. Keep historical audit records unaltered, but do not treat historical Linux successes or failures as acceptance gates for new work.

**Linux regression suites are not required and must not be scheduled, dispatched, waited for, or treated as blockers** in the normal MicroGen code-development, PR approval, bug-fix recovery or release process. This includes hosted Ubuntu runners, Linux-only test matrices, local Linux environments, WSL-based Linux regression campaigns and reruns of historical Linux CI failures. A future explicit user instruction is required to introduce a non-Windows platform requirement.

## 2. Required Windows-only development loop

1. Derive changes from the current authoritative GitHub main branch in an isolated Windows worktree; do not silently modify another active development checkout.
2. Inspect relevant historical errors and existing recovery mechanisms, then implement a targeted, source-grounded repair. Retain original physics, source fidelity, QA, copyright/authorization and replay safeguards.
3. Run focused unit and integration tests on Windows. Run historical failure, fault-injection and broad regression suites on Windows whenever required by the change or applicable acceptance gate.
4. Validate production-specific behavior on the authorized Windows host, including real source files/devices when relevant and safe. Check Windows paths, process lifetime, Python environment, Selenium/Chrome, FFmpeg, LaTeX, Drive mounts and native Task Scheduler where applicable.
5. Push a reviewed, tested PR and require the Windows-only GitHub Actions checks. Preserve failure evidence and make a targeted tested repair rather than disabling a failing Windows acceptance gate.
6. Merge into GitHub main only after required Windows checks and existing academic/production safety gates pass. Verify merged code revision and actual CI status. Advance to other eligible tasks under the existing v7.1 continuous-progress and authorization rules.

**Not permitted:** substituting Linux tests for required Windows tests; skipping Windows checks because Linux once passed; requiring both Windows and Linux suites; running an Ubuntu job only to satisfy an obsolete status or matrix; declaring code complete from test success without separate scientific, media and release acceptance.

## 3. Authoritative executable CI implementation

The only required repository-hosted regression suites are:

- .github/workflows/microgen-reliability-tests.yml: Windows-only quick offline historical protections and the full historical/Stage 3 fault-injection pytest suite on Windows/Python 3.12.
- .github/workflows/source-adjacent-output-tests.yml: Windows-only publication path, video assembler and syntax checks when applicable.

Every active runs-on entry in those files must resolve to **windows-latest**. Do not add ubuntu-latest, macos-latest or a mixed-OS matrix. Keep the relevant tests and functional QA; this is a **platform-only change, not a relaxation of test coverage or quality thresholds**.

Local offline tests on Dell-115 and hosted Windows CI are sufficient for the operating-system dimension of development acceptance. Hardware/browser/Gemini integration tests and G2/G3 scientific/acoustic/visual gates remain subject to their independent, previously established Windows production-specific criteria.

## 4. Persistence and historical failure recovery

The Windows-only selection must survive new branches, GitHub Actions changes, scheduled development jobs, PR creation, rebases, restarts and cross-session handoffs. The repository tests in tests/test_windows_only_ci_contract_v1.py are the guard against accidental reintroduction of Linux runners or regression requirements.

If old automation assumes Linux CI is mandatory, fix its host/matrix selection and CI-status reconciliation to count **only actual, required Windows checks**. Do not quarantine a development item solely because a removed historical Ubuntu check is missing or failed. Never mask a genuine failure of a required Windows check.

Any change to this operating-system contract needs explicit new user authorization and accompanying tests/CI changes, not merely a model suggestion or generated code rewrite.

## 5. Non-goals

This amendment does not rewrite historic evidence or claim that an entire software stack is portable across operating systems. It does not authorize new paid Gemini calls, model sends, scheduler changes, destructive operations or student publication; the established v7.1, G2/G3, source-fidelity and handoff contracts remain intact. Older shell utility files in the repository are legacy artifacts, not an obligation to run Linux regression suites.
