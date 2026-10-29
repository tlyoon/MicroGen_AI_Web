# Dell-115 TTS outage and Windows CI blocker recovery — 29 October 2026

## Original failure evidence
- A complete independently generated **17-slide** Thomas §8.4 deck contains textbook worked Examples 1–4 and passed the source-based narration/script gates.
- The source PDF and versioned corrected historical deliverables are preserved.
- New `20261029_WINDOWS_E2E_REPAIR_V2` checkpoint at 13:27 Malaysia time had `source_content=stage_pass`, `narrated_audio=stage_failed` return 124 at attempt 3.
- Gemini 3.8 Flash-Lite Kore generated **7 real candidate WAVs** (Slides 1–7); later slides timed out at ~195–240s. Earlier orchestration restarted the TTS subprocess three times, each with the locally numbered first round, and outer 2,100s deadline killed before the provider-fallback chain. The original source hashes match.
- A preexisting Windows CI test `tests/test_rfh_slides_transport.py` wrote fake text under `source.pdf`; this now fails the real source coverage gate under PyMuPDF. Updated test fixture writes a real single-page PDF and preserves the asserted API source bytes.

## Code-level recovery rather than single-file workaround
- `tts.py`: enable outage circuit breaker for **both normal and fallback** Gemini phases even when fallback is authorized. Stop requesting remaining slides after two consecutive transient failures per round; do NOT record skipped slides as provider failures. Three actual failed requests on one or more source-bound slides authorize a whole-batch next-tier fallback after append-only retry journal checks. None of the first seven successful WAVs are deleted. Inhomogeneous voices are never mixed: higher tier must generate entire batch in one engine/voice or fail safely. Correct final-round circuit breaker and classify skipped slides as unattempted rather than permanent errors. Default per-utterance hard timeout max 125s; still configurable by owner's Windows environment. Keep 3 attempts and Flash-Lite primary.
- `tts_attempt_evidence.py`: recognize three hash-chained *actual* failed provider calls across interrupted Windows subprocesses even if their local queue round counter starts again at 1; no fictitious calls or changes to source-bound SHA accepted.
- `windows_sourcebound_e2e_orchestrator.py`: extend overall audio-stage deadline to 5,400s for Lite/Flash/Cloud genuine fallback. Add explicit **one-time source-bound repair epoch** only after an observed exhausted 3-attempt transient TTS stage with original source-content pass. Preserve earlier logs and checkpoint receipts; new repair logs have new names; repeated unlocking is prohibited.
- `tests/test_dell_tts_outage_circuit_recovery.py`: offline observed three-round outage on an entire multi-slide source; confirms exactly six genuine failed provider interactions, no false skipped-slide failures, and single-voice batch fallback. Plus resumed hash-chain proof.
- `tests/test_dell_tts_repaired_resume.py`: fail-closed recovery gate and log preservation.
- GitHub CI remains **Windows-only**; no Ubuntu/Linux checks, HP/Yoga6/Zenbook work, Whisper, unauthorized publications or alterations to the shared dirty G-drive repository.

## QA / next execution
Focused Dell Conda test suite: 75 tests PASS. Next: run full Windows CI, recover existing §§8.4 WAV candidates (7/17) via one-time explicit repair, proceed to real soundalike audio QA and strict-duration genuinely highlighted multipart videos if successful, then generate §§8.5–8.6. Stop on genuinely unresolved model outage or missing Cloud credentials instead of falsely certifying completion.
