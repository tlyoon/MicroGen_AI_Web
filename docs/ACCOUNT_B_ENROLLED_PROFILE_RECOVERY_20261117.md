# 17 November 2026 — Previously enrolled Account B browser recovery

## Critical-path verdict

**P1 BLOCKED_EXTERNAL_DEPENDENCY.** Original Serway §1.3 two-PDF Gemini academic review remains 20/85 scientifically accepted; 65 pending, next untouched slide 12. Original failed slide-10/11 source-bound Sends and the two prior v1/v2 source-free synthetic two-PDF incidents remain exhausted and immutable. G2/G3, acoustic/video and student release are not accepted. No new Gemini model request, PDF upload, paid API call or source request replay was used to validate this repair.

## New independent, falsifiable route

Before this repair, port 9225 (Account B) was absent and the pre-Send selector would use only an already-running alternate browser. Read-only filesystem checks on Dell-115 established that the *previously user-enrolled* AccountB Chrome profile remained initialized, containing its real Chrome `Local State` and `Default` directory. This is a previously authorized identity, not an instruction to create or sign into a new profile.

The existing `launch_gemini.launch` now has an explicitly opt-in `existing_profile_only=True` guard; it checks those existing markers and refuses to create the profile if absent. A new registered handler `gemini_existing_alternate_recovery.recover_existing_alternate_debug_session` applies this guard to the **exact** authorized `AccountB` persistent profile on port **9225** only. It is called from the normal `academic_gemini_presend_preflight.inspect` path before any Send. The selector may inspect this old enrolled profile if the primary is unavailable or cannot satisfy the requested model/Thinking; it never invents a different model or weakens pre-Send source-claim policy.

A new local `enrolled_alternate_port_owned` predicate verifies that a listening port 9225 belongs to a Chrome process with matching `--user-data-dir` and port arguments for this exact enrolled profile. A port alone, an arbitrary Chrome account or an uninitialized directory is not sufficient. If the process cannot be independently verified, preflight fails closed. The real authenticated browser tab still must positively pass exact model and Medium Thinking checks; Chrome login cannot substitute for either.

## Live Dell-115 result (zero Send)

The registered recovery successfully reopened the existing Account B Chrome profile on port 9225 with no password, no prompt and no PDF upload. The ordinary Selenium vendor detected an existing authenticated Gemini login and positively selected and verified **Pro** on the owned tab. It then reported **`GEMINI_THINKING_LEVEL_UNAVAILABLE_NO_SEND`** for requested **Medium Thinking**. Therefore `EXACT_OWNED_GEMINI_MODEL_AND_THINKING_READY_NO_SEND` was **NOT** established and **no** source-bound or synthetic PDF request was eligible.

The saved source-free receipt is `%LOCALAPPDATA%/MicroGen_AI_Web_Checkpoints/accountB_enrolled_real_presend_receipt_20261117.json`. A separate local identity check showed both `port9225_listening=true` and `port_belongs_to_enrolled_accountB=true`. Neither proves Gemini's PDF-response capability. This is **verified recovery of the old browser process only**, not restored original operation.

## Tests and restrictions

Focused regression: **51 passed, 2 skipped**, zero failures, including missing/unknown/symlinked identity, wrong debug ports, absent ownership, no-profile-creation launcher behavior, fresh/consumed source claim barriers, and the registered no-Send preflight fallback. The two Windows skips are local symlink privilege limitations. Broad regression and new exact-commit CI must be checked separately.

- No replay of previous original or v1/v2 two-PDF claims, and no new health probe based only on Chrome readiness.
- Do not silently downgrade Medium/Pro or assume a login implies model response.
- Do not enable paid Gemini API/TTS or a scheduler without their existing authorizations.
- A future new, source-free two-PDF capability challenge needs a genuinely distinct, independently verified and permitted route, finite unique claim, attributable response with both hidden PDF tokens, and normal G2 source-bound review before any milestone may close.

**Stop reason:** Account B remains a real, separately authorized browser that can now reopen automatically, but cannot yet pass the requested Thinking level. Original P1, G2, G3 remain blocked.

## Hosted Windows path-alias regression and permanent correction

The first commit's hosted full Windows suite failed at the simulated Chrome ownership test after **960 passing tests**: CI's temporary profile path resolved through a Windows alias different from the raw `--user-data-dir` launcher argument. The first handler compared only the canonicalized string; it was overly restrictive, not an actual unauthorized login or provider error. The corrected local Chrome ownership predicate accepts exactly the two representations of the **same enrolled Account B path** (literal launcher argument and its `Path.resolve()` canonical form), while still rejecting unrelated directories, wrong ports or profiles. New regression explicitly forces a different junction alias; the local focused rerun passed **52 tests, 2 Windows symlink skips, 0 failures**. This repair changes no source/model claim and creates no Gemini Send. Full hosted CI must be independently rechecked on the new commit; do not report the earlier failing commit as green.
