# 13 November 2026 — Fresh Serway §1.2 source generation stress, reusable model-route repair, and real §6.4 acoustic preflight

**Project:** MicroGen_AI_Web (Dell-115 only), draft PR #528 derivative, based on code commit `8c0a095230ffe2834dd7af88160c46e7e6b5575c`.
**Incident family:** MG-NEW-SOURCE-GEMINI-ROUTE-HEALTH-INCONSISTENCY-20261113
**Status:** Real new original-source SHA/7-stage dry-run PASS. Real source-bearing Gemini generation **not admissible** under the current SHA-backed browser-health evidence. Model requests **0**; TTS/FFmpeg/publishing requests **0**.

## 1. Fresh distinct source — real physical test, no PDF overwrite

Publisher source: `G:\My Drive\Serway\Serway_1_7\1\1.2\source.pdf`.
Exact SHA-256: `814ce3e174b730271b04bbec4284bb4a15930d5026a2fcbb5148e0cf5ec018cb`; 482307 bytes.

New isolated, versioned external trial:
`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261113_PR528_SERWAY1_2_FRESH_STRESS_V1`.
A bounded source inventory discovered this SHA absent from the specified historic immutable trial registry (24 source contracts, 35 send-intent receipts, 18 unique trial SHA), but **absence is not proof of globally unattempted content**. The original source was copied into its own immutable `source_tree\1\1.2\source.pdf`, with hash verified identical. `windows_fresh_source_trial` dry run returned `FRESH_SOURCE_SEVEN_STAGE_DRY_RUN_READY` and `dry_run_exit_code=0`, without model calls.

## 2. Recurring route defect reproduced in normal execution

The old `windows_lecture_progression_coordinator.inspect_progress` and direct figures/slides/narration stage adapters only consulted the temporary `windows_gemini_provider_halt.inspect_halt` circuit. It currently returned `NO_PROVIDER_HALT` and `new_generation_dispatch_allowed_by_health_policy=true`. It ignored independent, immutable negative source-free model-routing evidence from historical PR #512 canary and a SHA-authenticated owned Gemini UI error. The separate `windows_provider_route_evidence_preflight` already reported `gemini_browser_auto_selection_suppressed_by_prior_evidence=true` and `GEMINI_SELENIUM_TEMPORARY_FAILURE_STOP`. A cooldown's expiry **does not** prove a source-bearing model response can be attributed.

Later history was checked too: the Nov 10 genuine 1973-character source-sized Gemini V3 canary `20261110_PR528_G1_SOURCE_SIZED_V3_POST_LATE_FIX_ONESHOT` has a SHA-backed `VALID_CANARY_RESPONSE`, but its immutable receipt has `gemini_new_user_turn_verified=null` and `gemini_send_registration_status=null`. A valid JSON response **cannot** be promoted to independently attributed model-turn proof. A Nov 7 canary also returned valid JSON but lacked turn registration; Nov 9 had repeated unaccepted results. The currently authenticated composer alone does not authorize or certify a fresh source request.

## 3. Permanent generic normal-pipeline remedy

Added `selenium_pipeline/windows_new_source_browser_admission.py`:
- Read-only, bounded, canonical `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints` enumeration of **latest** previous source-free browser claim/result (not merely a favorable older result); use the existing `windows_gemini_differential_probe._read` to check immutable model/prompt profile and SHA-bound send-intent identity.
- Require a complete source-sized real canary (1200–3000 chars), actual `VALID_CANARY_RESPONSE`, explicit `gemini_new_user_turn_verified=true`, no source PDF, one Send, authenticated Gemini composer and healthy provider capacity. Absent, untrusted, stale, malformed or non-attributed evidence returns `NEW_SOURCE_GEMINI_ROUTE_UNVERIFIED_STOP_NO_SEND`.
- No ChatGPT, API fallback, account switching, cache clearing, source retransmission or paid generation. A new genuine **independently registered** source-free canary can make a **new distinct** source eligible on a later normal invocation without a code patch; it never permits replay of any previously consumed original claim.
- Wired it **before the immutable Send-intent record and before Selenium** to the ordinary `windows_fresh_source_trial.run_trial` (figures) and `windows_original_stage_sequence.run_stage` (slides and narration), plus the read-only `windows_lecture_progression_coordinator.inspect_progress` and operator `advance_one`. The existing explicit one-stage execution cap, original source SHA checks, scoped prior request ledger and finite stop rules remain binding.
- The **same gate is reused automatically after restarts and new chat sessions**, because it reads durable verified source-free model history from the on-machine checkpoint registry; this is not a one-off assistant fix.

### Actual source §1.2 post-fix observation

Normal read-only coordinator returned `HALTED_UNVERIFIED_GEMINI_BROWSER_ROUTE_NO_SEND`, `next_stage=figures`. Direct normal figures attempt admission returned `GEMINI_SOURCE_ROUTE_UNVERIFIED_NO_SUBMISSION`, `new_model_or_tts_calls=false`, `historical_canary_claim_verified=true`, `owned_new_user_turn_verified=false`. **No figures Send-intent or figures result** was created in the new §1.2 trial. The publisher source SHA remained unchanged. This is a verified fail-closed recovery, **not** successful text/slides/video creation. We must not fake new generation when Gemini's model-turn ownership is unverified.

### Regression coverage

`tests/test_windows_new_source_browser_admission.py` adds independent source-free immutable canary tests: genuine-looking source-sized JSON lacking Send registration must not qualify; later failure overrides earlier positive; positive attributable long canary + authenticated editor + health makes a new-stage candidate eligible; a short canary cannot qualify; SHA tampering fails; coordinator and direct figure stage block before send journal; a legitimately qualified new stage can run once and never replay. `tests/test_windows_original_stage_sequence.py` also tests direct slide-stage admission; older mock stage tests now explicitly inject verified route evidence, preserving historical inner-attempt coverage.

New module is explicitly listed alongside `test_windows_fresh_source_trial` in `.github/workflows/microgen-reliability-tests.yml` — full discovery is not the only recurrence safeguard. Each historical remedy remains on the real production entrypoint rather than being invoked by ChatGPT alone.

## 4. Independent real scientific and acoustic QA status — **do not conflate**

Reused the historic actual Serway §6.4 14-slide, 74-utterance original; prior independent source-citation review produced 72 source-valid results, 23 supported, 49 unresolved, 2 untrusted. Latest source quotation retrieval physically proved 90 source literal candidates for all 74 narrated units, but this is **quote-candidate discovery**, not independent physical/mathematical acceptance. 41 element/visual mapping ambiguities remained unresolved in the original rich QA campaign.

Read-only real PCM acoustic preflight using existing `windows_slide_audio_timing_review.inspect`, actual SHA-bound 14 `slideN.wav` files, original source/slides/script and provider-attempt journal:
- `objective_pcm_signal_integrity_verified=true`; exactly **14** genuine WAV segments; sum **833.471 seconds**; bounded slide-level review would group into **2** parts.
- `independent_voice_listening_verified=false`, `audio_pronunciation_independently_verified=false`, `per_element_sync_verified=false`.
- An independent *deterministic* source-bound mathematical lint was rerun through the existing shared `automatic_math_semantic_qa --strict` pipeline against the physical Serway 6.4 source and all 14 original narration blocks (script SHA `7806b3e006b6727cec1acf9a0c9aeda2318c6e50f6821269fbae5c440223ee59`). It returned `NO_KNOWN_DOMAIN_SIGN_HAZARDS_IN_LIMITED_RULESET`, `blocking_count=0` and an independently proven restricted drag-law analytical identity set (linear terminal velocity/time constant, 90% time, quadratic terminal-speed positive root and selected numeric consistency checks). The contract explicitly records `all_mathematics_verified=false`, `independent_source_math_ai_review_approved=false`, `automatic_tts_authorized=false`, and `source_script_math_equations_all_semantically_verified=false`. New receipt saved outside Git in `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261113_PR528_G2_SERWAY64_REPEAT_MATH_TECHNICAL_QA_V1`.
- These checks verify source/PCM **technical and limited math identity integrity only**, not complete source utterance-to-audio ASR, correctness of all spoken mathematical expressions, Figure/panel meaning, independent vocal identity, element-level visible highlight or encoded synchronized MP4.
- **No TTS, ASR/LLM, video encode, overwrite or publication was performed** during the preflight. Existing 14 real WAVs and their original source provenance remain untouched.

Thus the requested independent science/acoustic QA **remains NOT_COMPLETE_WITH_NAMED_BLOCKERS**. Avoid looping one PDF; proceed with new generic recovery and evidence-acceptance tests only when a genuinely new safe mechanism exists.

## 5. Next legal progression and invariants

On Dell-115, the **normal** next-stage routing checks first re-read source SHA and immutable original Send-intent history, consult durable source-free model attribution (not merely cooldown) and then determine whether a *new* figure stage is eligible. If a distinct model-turn qualification becomes trustworthy, the pre-existing one-shot bounded stage runner proceeds and verifies real outputs. If not, stop provider work and continue independent deterministic QA/test development. No automatic replay of ambiguous model calls, paid API fallback, Google credential exports, old source overwrites, student publishing or unsound scientific/acoustic PASS.

Successful code tests/CI alone do not mean the new PDF has been converted to slides/WAV/MP4. No independent scientific/acoustic acceptance has been fabricated.
