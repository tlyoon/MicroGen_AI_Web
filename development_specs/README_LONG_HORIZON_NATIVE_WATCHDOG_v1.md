# Long-horizon Dell-115 development task recovery v1

## Observed failure, 27 November 2026

The original G2/G3 offline daemon and GitHub code-promotion controller both ended after the scheduler had exhausted its limited logon-trigger retry window. The daemon checkpoint became `STOPPED` at 16:13 MYT and Windows reported last task result 1. The independent Selenium coding worker kept running. The actual process exception cannot be reconstructed from Windows Task Scheduler's disabled Operational event log, so no specific exception is assumed.

The verified current GitHub `main` at `d886c3f` matched Dell-115's clean `post_pr673_main` checkout. No old owner process was active. A guarded native restart restored both tasks with a fresh daemon heartbeat at approximately 16:30 MYT.

## Durable remedy

The new **separate** native Task Scheduler entry, `MicroGen_AI_Web_v1_RecoveryWatchdog`, runs a bounded once-per-five-minutes watchdog for ten years (renew before 2036 if still required). It is a limited, interactive **current-user** task with `IgnoreNew` multiple-instance policy and restart-on-transient-failure settings. It does not replace or modify the original three developer jobs or their original one-claim model journals.

Each tick checks the actual native Task Scheduler owners, fixed original task actions, clean source tree, current protected GitHub `main`, and immutable no-publication G2/G3 heartbeat. It restarts **only** `MicroGen_AI_Web_v71_OfflineDevelopment` if stopped and stale. It does not start the dependent `MicroGen_AI_Web_v1_CodePromotionOrchestrator` until a genuine fresh daemon and process readback exists, or unless that daemon is already securely attested. It never restarts the independent Selenium worker, edits lecture source, repeats a model request, merges a pull request, issues paid Gemini API requests or publishes student material.

For an active task whose heartbeat is stale, or when source identity/ownership cannot be established, fail closed rather than creating a duplicate. The watchdog writes a small auditable `native_health_watchdog_v1.json` receipt in the existing promotion-control checkpoint folder.

The original logon tasks' finite retry policy remains intact. This **independent five-minute trigger** is the missing recurrence that restores source and promotion supervision even when the original logon retries are exhausted.

## Installing (exact protected main only)

After both GitHub Windows CI jobs and guarded deployment, run the reviewed `scripts/install_microgen_long_horizon_watchdog_v1.ps1` from the **current clean protected-main checkout** on Dell-115 under the current interactive user. It fails if an existing differently configured watchdog is found and will not overwrite that task. Native registration is checked for original-owner identity, five-minute repetition, strict one-task identity and limited privilege. The separate launcher `scripts/run_microgen_long_horizon_watchdog_v1.ps1` selects the current owner task's repository on every run, so later guarded Git revisions retain the watchdog.

## Scope boundary

The four approved derived technical tasks are already consumed. The watchdog fixes **availability and continuation**, not **task creation** or scientific acceptance. Three older ambiguous model replies remain quarantined. G2/G3 independent physics, audio, video, and second-subsection acceptance remain open and cannot be satisfied by metadata matching.

Tests: `tests/test_development_windows_autorestart_watchdog_v1.py`, existing native daemon/owner validation and historical stage-3 regression suite. Run from a clean isolated code-review branch, exact-head Windows CI, one-time guarded merge and dual-worker deployment, then native registration and restart-safe readback.
