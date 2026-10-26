# PR315 — Reusable mathematical domain/sign QA and autonomous bounded narration repair

**26 October 2026 — Windows-only, Dell-115 only, stacked on successful PR314 head `ac6f559e2b638ee5b19deefeab0ca437f1623cc0`.** The owner explicitly requests that future lectures automatically identify and rectify defects similar to the Thomas 8.4 signed-angle mistake instead of repeatedly adding one-off textbook patches.

## Root cause and production fix

The previously deployed normal `script_qa` stage checked TTS pronunciation hazards but **not** rigorous mathematical sign/domain semantics. Consequently original Thomas8.4 Slide 4's "acute angle u" and signed `x` as positive triangle side survived to the original 45.295s WAV and >600s historical MP4.

Added standalone `selenium_pipeline.automatic_math_semantic_qa`, a pure offline stdlib first-line semantic risk detector. Unlike Thomas-specific source SHA guards, this applies to **any script**: it catches unqualified acute signed-angle trigonometric claims, signed x as an unsigned right-triangle leg, unqualified secant hypotenuse x, principal-root sign simplifications, and explicit division/cancellation of possibly-zero variables. Each finding records slide, rule, explanation, a suggested correction, and (where valid) an exact mathematical counterexample. No known findings only means *known rules did not fire*, NOT proof of all mathematics.

The CLI emits an immutable source+script hash report, and independent repair instructions, with `--strict` exit 2 on blocking defects; it never changes the script or calls an AI model. Genuine immutable original Thomas8.4 script was run on Dell, math hazards were identified, and TTS was refused. Review prompt and audit receipts are stored outside the protected source folder.

## Automatic self-correction when generating FUTURE lectures

The existing browser/Flash narration generator `vendor_template_v2/gen_script_selenium_v15.py` now includes source-hash-linked mathematical QA in `collect_all_warnings`; it already handles failed validation by preserving the rejected candidate and regenerating the **entire** narration with locally supplied corrective feedback using its existing bounded Selenium retry budget (up to the configured three attempts). There is no new API/service or separate unattended background process. It regenerates, revalidates each candidate, and will refuse acceptance when exhausted. This is **an actual normal production generation path**, not a standalone optional Thomas test.

The main `runner.py` `script_qa` step additionally runs the source-bound semantic CLI with strict failure **before TTS**, stores scientific report and revision prompt, makes mathematical QA part of the stage's required output/checkpoint signature, and rejects stale script/source/misleading receipts. The independent `series_bridge.stage_tts_job` is also guarded; its separate storyboard entrypoint cannot bypass this barrier.

This arrangement is generalizable to other mathematical cases by adding precise, counterexample-tested rule modules to the common detector, not by hardcoding individual PDF names. It does **not** self-certify academic correctness, fabricated source citations or model output. An unknown mathematical issue still needs genuinely independent source-grounded AI review; candidates with unresolved blocking findings do not reach narration TTS or publication.

## Evidence and remaining production milestones

Focused Dell-115 validation with genuine Thomas 8.4 and synthetic non-Thomas adversarial examples: **9 of 9 tests pass**, including real original QA stop, corrected input acceptance under limited rules, model retry feedback, source/hash-stale `runner.valid('script_qa')` refusal, and CLI refusal/no source mutation. GitHub hosted full Windows CI independently required prior to marking PR green; Windows workflows remain Windows-only and require no Ubuntu checks.

**Still NOT complete:** independent source-grounded two-pass corrected-Slide4 mathematical agreement, five newly synthesized correct Kore speech segments, sample-timed mapping to original Figure8.2 strips, 2 real accepted encoded synchronized MP4 parts each <600 seconds, publication. Original assets/legacy dirty G checkout and prior Gemini attempts untouched, no Whisper or paid API. No new Gemini or TTS request was made for PR315 test work. The previous Thomas pilot remains draft PR314, CI-green.

**Next:** verify hosted Windows CI for this generic normal-path QA integration; then proceed to corrected revised-script AI-source review and genuine five-segment TTS/encoded multipart production in an isolated review folder. Never bypass source citation, identity, timing, media or voice proof gates.
