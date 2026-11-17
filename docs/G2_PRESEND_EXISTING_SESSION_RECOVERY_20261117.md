# G2 pre-Send existing-session recovery guard — 17 Nov 2026

**Runner:** Dell-115. **Development:** isolated draft PR #530, not main.

## Actual regression and root cause

On the current authenticated-primary session, a fresh pre-Send Flash check found the requested full model unavailable (only Flash-Lite offered). A separate Pro/Medium pre-Send check also found Pro unavailable in that session. These probes made no academic request or PDF upload. After the probes, neither approved Chrome debugging endpoint was currently available. The historical two original source-bound PDF review claims and one synthetic dual-PDF claim remain exhausted and may not be resent.

Review of the production vendor launcher revealed a direct pre-Send safety gap: when no debugging port was listening, `GeminiSeleniumClient.start` created a new `C:\gemini_automation_profile_runs\run_<timestamp>` browser profile even though `use_persistent_chrome=True`. Academic preflight could therefore enter the wrong fresh Chrome session and fail to reuse the approved authenticated context. **This is an identified pre-Send launch defect, not proof of the cause of the already-consumed PDF-response failures.**

## Production remedy

- `academic_gemini_presend_preflight.inspect` now verifies the authenticated existing debugging endpoint under its per-port lock before allowing the vendor client's `start`. When absent, it returns `GEMINI_EXISTING_DEBUG_SESSION_UNAVAILABLE_NO_SEND` without starting Chrome, generating an academic claim, uploading files, or changing profiles.
- `select_ready_existing_session` may inspect port 9225 only when it is already live, exact-model/Thinking verification remains required, and a code-reviewed `PRIMARY_GEMINI_DEBUG_SESSION_DISAPPEARED_NO_SEND` registry remedy is active. No new login, browser launch, different family, downgrade or Send is authorized.
- This repair is wired into the ordinary academic preflight used before new scientific requests. It does not bypass the post-Send PDF capability circuit breaker or create any scheduled task.

## Regression and real observation

The first targeted test run was 24 passed, 1 failed because the new registry retry policy omitted the required literal `finite`. The registry wording was fixed without weakening the runtime. The following broader academic, incident-health, Gemini response DOM, recovery-registry and G2 forward tests returned **68 passed, 0 failed, 5 nonfatal dependency warnings** (`TEST_EXIT=0`).

A real no-Send Dell-115 preflight with the debugging endpoint absent returned exactly `GEMINI_EXISTING_DEBUG_SESSION_UNAVAILABLE_NO_SEND`. Timestamped temporary Chrome-profile directories counted **32 before / 32 after**, providing independent evidence that the repaired academic preflight did not start a disposable profile. Logs: `G2_SERWAY13_CONTINUATION_LOGS/presend_existing_only_live_20261117.log` and `presend_no_ephemeral_broad_tests_20261117.log`.

## Limitations / next eligibility

**P1 PDF-response transport not resolved; G2 20/85 scientific consensus, 65 unresolved; G3 open.** The fix corrects a recurring pre-Send session-classification/launch hazard only. The existing consumed Gemini requests remain immutable. New original academic review requires a freshly eligible, authenticated, verified full model and Thinking control, genuinely owned attachment-response evidence, strict two-pass science validation, and automatic next-stage journal advance. Paid TTS and student publication remain separately gated. No always-on runner or schedule is claimed.

Exact new branch commit/hosted Windows CI must be verified before claiming hosted engineering acceptance.

## Vendor-side time-of-check/time-of-use closure

Additional review found that the debugger could disappear *after* the academic preflight's `ready(port)` check but *before* `GeminiSeleniumClient.start`. This would again launch the vendor's temporary `run_*` profile. The production vendor `Config` now has an opt-in `existing_session_only` flag, set true by academic preflight. `GeminiSeleniumClient.start` checks this at the actual launch boundary, raises `EXISTING_GEMINI_DEBUG_SESSION_UNAVAILABLE_NO_SEND` before any Chrome spawn, and never calls force-kill for this case. All non-academic callers retain their previous defaults. The shared finite pre-Send recovery policy classifies this exact failure as `GEMINI_EXISTING_DEBUG_SESSION_UNAVAILABLE_NO_SEND` and does not retry the missing authenticated session blindly.

Additional regression tests simulated the port disappearing between checks, prohibited Chrome spawning, confirmed precise no-Send classification, and checked the finite pre-Send circuit breaker. Expanded real-code suites now **79 passed, 0 failed, six nonfatal warnings** (including one vendor legacy escape-sequence warning), `TEST_EXIT=0`, in `presend_vendor_lost_port_regressions_20261117.log`. Actual Gemini external PDF response remains unverified. No prior consumed claim was replayed.

## Shared figure/slide/narration model-request integration and actual G2 restart

The same `existing_session_only=True` guard has been enabled on the ordinary `series_gemini._browser_request` path, not just academic preflight. This prevents future genuine figure, slides, narration, and independently reviewed model work from accidentally launching a timestamped unauthenticated Chrome profile when the previously authorized browser is unavailable. The underlying vendor `Config` default remains `False` for intentionally isolated non-production/test browser runs. New `tests/test_series_existing_browser_profile_policy.py` verifies the normal source stage's exact configuration and compatibility default without any real model Send.

The expanded source-stage, academic/route, G2, Gemini DOM and recovery registry regression test returned **81 passed, 0 failed, 5 warnings**, `TEST_EXIT=0`, in `gemini_all_stages_existing_session_tests_20261117.log`.

A real normal `g2_forward_recovery_engine --execute --max-cycles 1 --no-auto-media` after the recovery-registry change returned `G2_FORWARD_STOPPED_AT_VERIFIED_ELIGIBILITY_BOUNDARY`, `critical_path_recovery_proof.status=BLOCKED_EXTERNAL_DEPENDENCY`, `original_operation_recovered=false`, `next_milestone_advanced=false`, **0 new stage cycles**, **20/85 accepted**, 65 unresolved, 0 missing visual-review candidates, 2 ambiguous fractions, 13 unrepaired historical PDF counter geometry blockers, 10 source quote candidates for untouched slide 12, and 0 new model requests. New immutable audit receipt `20435685d0858b5650865e6f958de8de7fefa77a432dccaac7793d0737f02031.json`, SHA256 `4ae9dbd3008a38be434283ccf62490a09572db58d47aeef3d3950f34ff808ee1`. Log `g2_actual_after_presend_fix_20261117.log`.

This is production wiring and real unchanged fail-closed G2 behavior, **not** restoration of Gemini PDF reading, independent science completion, paid TTS/media acceptance or release. Commit/CI verification pending at report creation.
