# MicroGen_AI_Web persistent autonomous code author — 26 November 2026

## Why this worker is necessary

The hourly ChatGPT development task repeatedly stopped at checkpoint inspection, while `MicroGen_AI_Web_v71_OfflineDevelopment` is a deliberate offline read-only dispatcher that **does not write source code**. The original Codex CLI has an immutable host-effectively-read-only capability-denial record; do not clear or bypass it.

A separately bounded, restart-safe Python **code-authoring worker** lives in `selenium_pipeline/development_persistent_selenium_author_v1.py`. It takes independent SHA-pinned development jobs from an authorized job inbox and invokes the previously existing, authenticated **Gemini Selenium browser** transport (NOT the paid Gemini API). The existing v7.1 lecture and scientific-review restrictions remain unchanged.

Each admission requires: an approved MicroGen project and one-Send policy, an isolated Git feature worktree based on the exact pinned Git SHA, an allowed new Python target, an immutable independently authored pytest module with SHA, an immutable contextual file with SHA, a bounded task description and wait cap, and a separate append-only state directory.

The worker claims the **one possible provider Send BEFORE opening the browser**, saves the exact original model reply, optionally recognizes the known literal `Gemini said` UI response and restores only line indentation within a named function, verifies restricted pure-Python AST, atomically applies the candidate source to the isolated Git branch, then runs the pinned independent pytest tests. The complete source file and original captured reply both retain SHA identities. On crash, it may reprocess the **same saved reply offline**; it never repeats an uncertain original browser request. Failed candidates are quarantined. Unrelated valid queued work can proceed after an individual failure. It never calls a paid API, changes the Codex host-policy gate, publishes to students, merges GitHub PRs, or claims independent G2/G3 science acceptance.

The source is deliberately restricted to pure Python modules, safe builtins, approved non-IO imports and narrow method names. This is a **bounded** code writer, not unconstrained autonomous privilege. Larger code changes must become new, independently reviewed task types before they can use the worker.

The executable recovery policy contains these two entries:

- `PERSISTENT_SELENIUM_CODE_AUTHOR_ONE_SEND_20261126`
- `PERSISTENT_BROWSER_SOURCE_INDENT_RECOVERY_20261126`

## Original live Dell-115 one-Send proof

The initial job `windows_pytest_result_v1.json` has immutable SHA `b8f8e01c8b19e4a062282f4155f343a6a9055740a40b55bc24cad4ba56d80a01`. A real authenticated Selenium Chrome session at port 9222 verified Hydrogen, selected Medium, and **registered one genuine Gemini user-turn** on 26 November at 21:15:36 Malaysia time. The original 345-byte captured reply SHA is `fc6a091d2821e4c6c3a4f26fc4faaad4e4436faf5f7ced955fcc2e8c933d5d05`.

The initial raw response was quarantined because Gemini's UI copy flattened the indentation. A targeted source recovery was tested and installed without any second model Send. Its offline reprocessing produced source `selenium_pipeline/windows_pytest_result_v1.py` with original model-generated SHA `40aaf792f48c97921f1a3005001c6d66d0be98a0f832438832356dde39ff1068`. **All six independent exit-code/SWIG-warning tests passed**; the original response SHA stayed unchanged. The signed code-job state is under `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\LONG_HORIZON_CODE_AUTHOR_V1_20261126\state\windows_pytest_result_v1\coding_state.json`.

Important distinction: this is a verified code-writing and offline-recovery cycle. It does **not** prove that the worker can autonomously select all future G3 physics-meaning acceptance tasks, author unrestricted modifications, pass their scientific review, or merge/deploy a PR without additional CI gates. A continuously running worker with no eligible inbox job still has nothing to code.

## Long-horizon startup and operating contract

Once protected GitHub CI certifies this change, the authorized Dell-115 installation may start `MicroGen_AI_Web_v1_PersistentCodeAuthor`, a Windows Task Scheduler task that starts the installed worker at user logon, auto-restarts after fault and monitors the dedicated backlog inbox. This **must run separately** from the read-only v7.1 daemon; never change its executable or historical checkpoints.

New source-pinned jobs can be staged on the exact latest GitHub main using an independent test first, an isolated branch, a unique job ID and a signed manifest. A new original job can be sent **once only**. Source candidate promotion to PR, exact-head Windows CI, guarded production code deployment and next-task selection remain separate protected stages until individually verified. No stored original model request may be replayed to create an appearance of progress.

### Verification criteria

1. Real Selenium one-Send model receipt, not a simulated function call.
2. Original response bytes and input SHAs unchanged.
3. Actual generated code file plus passing independent pytest.
4. Fault-injection for unauthorized imports, changed test SHA, altered job, tampered generated candidate, original reply crash/resume and committed branch no-replay.
5. Executable recovery registered, complete GitHub Windows CI on exact PR head, guarded Dell deployment.
6. Unattended Windows task must be observed executing at least one **new** eligible development job, not merely generating heartbeat entries.

Until item 6 is independently verified, do not describe the system as a fully proven unattended code-development service.
