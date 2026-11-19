# PR552 — Fix Windows short-path alias in scheduled-runner test without changing runtime gates

**Host:** Dell-115, 19 Nov 2026. **Parent:** PR551 exact clean SHA `d167a6f44911081ef15a309ff963a27d36cb7d49`. This code change is independently isolated in `%LOCALAPPDATA%\MicroGen_PR552_20261119` and does not edit PR551 while its normal source-only worker is active.

## Historical failure and reused mechanism

Exact-HEAD PR551 hosted Windows Python 3.12 CI run `44542448177` stopped after 3,419 passing and 83 skipped pytest tests (at 89%). The sole failing test was `test_real_source_only_runner_invokes_actual_normal_cli_with_no_gui`: a raw `kwargs["cwd"] == self.repo` assertion compared `WindowsPath('C:/Users/runneradmin/AppData/Local/Temp/...')` against the same physically resolved `WindowsPath('C:/Users/RUNNER~1/AppData/Local/Temp/...')`. This is a test-side lexical alias false-negative, **not** a scheduler permission, source integrity or scientific QA failure. It is an exact recurrence of historical GitHub Windows temporary directory alias behavior previously repaired in `tests/test_windows_offline_development_forward_controller.py`, plus the same class covered by the PR551 executable registry path-alias signature `V71_WINDOWS_SCHEDULE_TASK_ACTION_PATH_ALIAS_UNVERIFIED`.

## Targeted repair

Preserve the production code's physically canonical clean-source handoff. Change only the test's working-directory expectation to compare `kwargs["cwd"].resolve()` with `self.repo.resolve()`. Add a real local synthetic test passing an alias path `source_alias/..` into the normal scheduled-runner entrypoint and confirming that it invokes exactly the canonical source-bound six-stage v7.1 CLI under `MICROGEN_V71_BACKGROUND_SOURCE_ONLY=1` with no Gemini/paid model Send, writes a bounded receipt, and does not assert academic or student release. Existing forged action/disabled task/replayed request safeguards remain unchanged.

## Evidence and acceptance

Native Windows isolated scheduler `pytest` passed 13/13; relevant native tests including supervisor and recovery registry passed 48/48, and Git source patch check was clean. Next mandatory: clean exact-HEAD commit, stacked draft PR552, hosted full Windows pytest (not only targeted), normal source-locked six-stage run and independent restart, followed only after acceptance by actual authenticated limited-user scheduler installation with verified Task Scheduler execution. Do not merge PR stack or publish original G2/G3 work. Prior original Serway §1.3 G2 source acceptance remains 20/85 and 65 pending, no duplicate Gemini source Send.
