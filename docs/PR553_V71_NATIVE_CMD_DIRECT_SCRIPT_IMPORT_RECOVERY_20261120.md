# PR553 — Repair the actual Windows scheduled `.cmd` launcher import failure

**Host and date:** Dell-115, 20 November 2026 (Malaysia time). **Parent:** PR552 exact SHA `854d8529aecc1425e66ae9432cde5fd8ee33c3b1`, draft/unmerged. New PR553 code is maintained only in an isolated clean Git worktree.

## Historical failure review

PR552 completed 48/48 source-only historical tasks, six of six v7.1 stage results, independently confirmed zero-duplicate restart on exact HEAD and both hosted Windows CI jobs, hosted run `44544396874`. The first real recurring Task Scheduler installer created the limited-user task `MicroGen_AI_Web_v71_SourceOnly`. The external gate script then crashed when assigning to PowerShell's built-in read-only `$HOME` variable, and its fail-closed handler disabled the task. That script error did not invalidate PR552's CI/source-only engineering acceptance but left persistence **unverified and disabled**.

An independent audit of the Task Scheduler XML confirmed the task was **disabled**, configured for `InteractiveToken` of the existing authorized account, pointed at `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\v71_scheduled_resume_v1\sourceonly_v71.cmd` with **no extra arguments**, and its wrapper invoked `python.exe -B ...\selenium_pipeline\windows_v71_scheduled_resume.py --run --repo ...`. Running exactly that wrapper while the scheduled task remained disabled produced a **real native Python `ImportError: attempted relative import with no known parent package`** in `_audit_installed`. The root cause: direct `.py` execution has no package context, unlike `python -m ...` used by the local tests. This had not been detected by the previous scheduled action audit test.

## Targeted repair and executable recovery registration

Use the absolute `from selenium_pipeline.recovery_registry import lookup_mechanism` import in both the actual scheduled `_audit_installed` path and the installer, retaining the normal source-bound `__main__` bootstrap, model/source/paid operation safety, native Windows task audit and finite retry rules. Register `V71_NATIVE_CMD_DIRECT_SCRIPT_RELATIVE_IMPORT_CRASH` with `ABSOLUTE_REGISTRY_IMPORT_FOR_NATIVE_SCHEDULED_SCRIPT_ENTRY` in the executable recovery registry. If the registered repair mechanism is disabled, the task refuses before touching its action or source.

A new fault-injection test executes the *actual file through `runpy.run_path` in a separate Python process with no package context*, invokes its audit under a retired registry mechanism, and requires a clean fail-closed RuntimeError, not an import crash. The old independent path-alias recovery test was targeted to its own signature so both safeguards remain testable separately. First test batch **14/14 pytest**, **49/49 unittest**, Git patch check clean. Previous PR552 exact source and immutable original Gemini slide 10/11 incidents remain untouched.

## Exact acceptance gates

Before enabling the existing scheduled task or migrating it, require: a clean immutable committed PR553 SHA; hosted full Windows CI and offline jobs green; normal source-locked v7.1 controller 48/48 historical regression queue and 6/6 read-only stage results; independent fresh restart 6/6 with zero duplicate dispatch. The existing task is disabled and points to PR552, so no installer may silently overwrite or treat it as a verified running task.

For migration, first independently inspect the installed task identity, enabled state, user and exact action against the known original PR552 wrapper. Only a verified disabled **owned** prior-version task may be intentionally retired in a documented, reversible migration to the new SHA. Preserve all security boundaries. After installing the PR553 task, use the actual Task Scheduler trigger and verify a new source-only JSON receipt and zero duplicate providers/dispatches. If a scheduled invocation fails, disable the task and record the precise failure instead of asserting persistence.

Scientific boundaries are unchanged: original Serway §1.3 G2 20/85 source-agreed, 65 unresolved, old source Sends and synthetic probes ambiguous/consumed, G3 independent science/acoustic/video review incomplete, historical semantic review pending, student publication unauthorized, no automatic merge.
