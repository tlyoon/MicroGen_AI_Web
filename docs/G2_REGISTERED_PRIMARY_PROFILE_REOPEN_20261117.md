# Reopen only the existing authorized primary Gemini profile — 17 November 2026

**System:** MicroGen_AI_Web / Dell-115 / draft PR #530. **Purpose:** close a repeatable pre-Send recovery defect without circumventing the original two-PDF Gemini response gate.

## Root-cause evidence

Previously the vendor Gemini Selenium start routine silently generated a disposable `C:\gemini_automation_profile_runs\run_<timestamp>` Chrome whenever port 9222 disappeared. The new earlier guard corrected this danger but ended at the missing port even though an authorized persistent primary profile already existed and could be reopened without credentials. Disposable-profile checks in the earlier session displayed Flash-Lite alone; they are NOT authoritative capabilities of the prior authorized primary account.

The real pre-existing `%LOCALAPPDATA%\gemini_automation_Dell-115` profile was safely reopened through existing `launch_gemini.launch(None)`, without submitting a model request, uploading a document, typing credentials or creating a fresh profile. **The actual authenticated primary then offered Flash-Lite and Pro; Flash was unavailable.** The model-level owned-tab preflight on this same persistent session positively selected **Pro / Medium** after New Chat and independently verified Medium Thinking. Recorded in `G2_SERWAY13_CONTINUATION_LOGS/existing_primary_chrome_relaunch_20261117.log`, `persistent_primary_flash_medium_probe_20261117.log`, and `persistent_primary_pro_medium_probe_20261117.log`.

## Ordinary executable repair

- New `selenium_pipeline/gemini_existing_primary_recovery.py` recognizes the exact failed pre-Send debug-port condition. It strictly requires port 9222, the previous primary profile directory with real `Local State` and `Default` markers, no symlinks, and a code-reviewed enabled registry entry `AUTHORIZED_PRIMARY_PERSISTENT_DEBUG_SESSION_LOST_NO_SEND`. It makes at most one restoration invocation via the existing profile launcher and positively checks the resulting port and same on-disk profile identity.
- The original `academic_gemini_presend_preflight.inspect` calls this within the per-port lock before academic client preparation. The vendor `GeminiSeleniumClient.start`, when `existing_session_only=True`, invokes it again only if the port vanished between the first check and its final attach boundary; it NEVER creates its old disposable `run_*` profile in that mode. `series_gemini._browser_request` uses the same vendor flag for normal figure, slide, narration and model stages. Intentional isolated clients retain the default `False`.
- **Only the exact previously initialized primary** may be automatically reopened. The alternate authorized account B on port 9225 is not launched automatically and still requires an already-running session. No sign-in, prompt, PDF Send, prior claim replay, API fallback, paid TTS or scientific approval is performed by this mechanism.
- Source/slide/script SHA validation, one-Send circuit breakers, model and Medium control verification, finite retry caps, independent academic/acoustic/video QA, and release gates all remain mandatory.

## Fault-injection and live observations

Regression suite `tests/test_gemini_existing_primary_recovery.py` covers positive same-profile reattach, existing-port reuse, wrong ports, missing state, missing Default, registry disabled, wrong profile, port race after launch, launcher exception and unsafe symlinks. The broader source/G2/Gemini suite returned **90 passed, 1 skipped, 0 failed**, six warnings, `TEST_EXIT=0`, in `primary_persisted_profile_autorecovery_tests_20261117.log`. The skipped Windows symlink case requires symlink permissions and other cases cover all remaining negative paths. The real currently live port verified `ready(9222)=True`, `recover(9222)=True`, `recover(9225)=False` with zero model Sends. The documented real manual pre-existing-profile restart was successful; **this particular new automatic missing-port branch is validated by fault injection, not falsely claimed to have been exercised by intentionally shutting down the user's Chrome session**.

## Critical-path status

The original source-bound Serway 1.3 two-pass scientific review remains **20/85 accepted, 65 unresolved**. Previously claimed source slide 10/11 and synthetic two-PDF requests have no attributable response and must not be replayed. The new pre-Send repair does NOT establish that Gemini now successfully reads/responds to both PDFs. G2/G3 remain open. Next genuine model request must pass the existing live owned two-PDF capability gate and original independent science and QA checks. Hosted exact-head CI and immutable checkpoint status must be independently verified.

## Final repeat live pre-Send proof and genuine forward journal

After integrating the actual automatic primary-profile handler, independent live `select_ready_existing_session` on authenticated port 9222 returned `EXACT_OWNED_GEMINI_MODEL_AND_THINKING_READY_NO_SEND`, `model_family=pro`, `thinking_level=medium`, `verified_port=9222`, `gemini_requests_submitted=0`, `files_uploaded=0`, `G2_approved=false`. Saved in `G2_SERWAY13_CONTINUATION_LOGS/final_pro_medium_existing_profile_proof_20261117.log` with `PROOF_EXIT=0`.

The latest normal source-bound `g2_forward_recovery_engine --execute --max-cycles 1 --no-auto-media` returned `BLOCKED_EXTERNAL_DEPENDENCY`, `original_operation_recovered=false`, `next_milestone_advanced=false`, no journal stage, 20/85 independent scientific accepted, 65 unresolved, zero Gemini requests, 0 unmatched visual-review candidates, two tied fraction options and 13 original PDF geometry blockers. Immutable offline worklist receipt `90005b26b6efe39b95c0def5cce2c596aa53b5b0ab64a72e2dbf7886b673e5dd.json`, SHA256 `b77bcbd5f9ec5e7e7a33c93dd295dc62435fb030416d4217c3268b08ae0b4fab`. Detailed log `G2_SERWAY13_CONTINUATION_LOGS/g2_after_persistent_primary_recovery_20261117.log`, `ENGINE_EXIT=0`.

This confirms that the new mechanism is harmless in the actual real currently owned Pro/Medium session, and that the normal G2 workflow *honestly* preserves the mandatory external PDF response boundary. It does not claim that the missing-port branch itself was live-triggered by interrupting Chrome. No model Send, paid media, scheduled runner or external release.
