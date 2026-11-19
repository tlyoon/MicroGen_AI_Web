# PR551 — Recover Windows Task Scheduler action path aliases without relaxing audit

**Date:** 19 November 2026 MYT. **Host:** Dell-115. **Parent exact SHA:** PR550 `bdc995816bbb30af3f5d9a2002f1e3706fbd9b97`. New isolated clean worktree `%LOCALAPPDATA%\MicroGen_PR551_20261119`; PR550 and previous source/academic checkpoints untouched.

## Historical failure → targeted cause

PR550's actual hosted Windows Python 3.12 full suite run `44536871058` failed at 89%, after 3,412 passing and 83 skipped pytest tests, only at `SourceOnlyWindowsSchedulerTests.test_corrupt_normal_result_cannot_promote_science_or_release`. The previous action audit used a raw substring of the expected wrapper path inside `schtasks /Query /V /FO LIST` text. Yet the scheduler and Windows temporary test directories may represent the *same executable* with different lexical path aliases. A historical analogous Windows temp lexical path failure had already been fixed in the source-locked development test path validation, documented in `tests/test_windows_offline_development_forward_controller.py::test_git_root_containing_dotdot_is_canonicalized_for_source_boundary`. Reapplying a canonical-path comparison is appropriate; suppressing or bypassing action audit is not.

## Registered reusable repair

In the normal `windows_v71_scheduled_resume._audit_installed` path, check the *enabled* scheduler state and exact TaskName, require **exactly one** distinct `Task To Run` value, strip only an optional pair of outer quotes, then demand an absolute, not-symlinked action whose `Path.resolve()` matches the exact source-bound private `sourceonly_v71.cmd`. Extra arguments or an unrelated executable cannot match. The wrapper's original bytes, exact Python/entrypoint and source path are still verified. A new enabled executable registry entry `V71_WINDOWS_SCHEDULE_TASK_ACTION_PATH_ALIAS_UNVERIFIED` / `RESOLVE_EXACT_SCHEDULE_ACTION_PATH_WITH_NO_ARGUMENTS` must pass before the audit; disabling it stops the scheduler, without new provider operations or guessed success.

## Test results and release conditions

The source-local ten-case pytest scheduler suite with temporary path isolation passed (10/10), and native targeted supervisor, registry, history queue and scheduler regressions passed (80/80). New fault injection includes same-wrapper `subdir/../` alias, forged task action, trailing `--send`, duplicated `Task To Run`, disabled task, and retired registry. Compile, Git patch, committed clean SHA, hosted *full* Windows pytest (not only unittest), live normal six-stage source-only queue, CI-gated release board, independent no-duplicate restart, and actual registered Dell-115 scheduler installation/trigger remain required before acceptance.

**No G2 scientific or G3 acoustic/video acceptance, original provider replay, paid TTS, automatic PR merge or student publication is asserted.** The same originally consumed Gemini source claims remain immutable (original Serway §1.3: 20/85 source-agreed, 65 pending).
