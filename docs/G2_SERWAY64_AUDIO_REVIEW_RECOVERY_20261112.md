# MicroGen_AI_Web — 6.4 audio, source-quote and review continuation (12 Nov 2026)

**Project:** `tlyoon/MicroGen_AI_Web` / PR #528. **Device:** Dell-115 only. **Status:** real source/text pipeline completed; real audio pilot in progress; source-grounded per-element acceptance and G2/G3 release NOT complete.

## Immutable source evidence

- Publisher PDF: `G:\My Drive\Serway\Serway_1_7\6\6.4\source.pdf`
- SHA-256: `64b748468e6bdb12ddb127f1d8bea90a7f3f63d270fbb5378ba1d3ddeeb955fd`.
- Latest verified source stage: `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261112_PR528_G2_SERWAY6_4_NARRATION_SOURCE_REUSE_V7`.
- 14 `slides.pdf` pages, SHA `814fdbe054f09a3073e3d7c82bd5929d48c46a18255fdd5aeac3f7adcd4d1e72`; 14 narration blocks, 1,962 words, `script.txt` SHA `7806b3e006b6727cec1acf9a0c9aeda2318c6e50f6821269fbae5c440223ee59`.
- Deterministic script-QA stage SHA receipts accepted; no released lecture WAV/MP4 previously existed.

## General source-review blocker and correction

The original `element_plan_autodraft` reported 74 utterances and 45 ambiguous visual-target links. Exact text-only per-element pipeline refused because the actual slide PDF contains imagery and vector elements; these results **do not** authorize audio-element synchronization.

The strict source-citation reviewer originally exceeded its 13,000-character evidence packet cap for four slides. New `source_citation_batch_planner.py` reduces 1–4 slide batches without cropping, replacing, fabricating or losing independently witnessed source quotations. Genuine Serway 6.4 test produced 6 safe jobs covering all 14 slides and 74 utterances, no unresolved planning slots and **no model requests during planning**. Saved under `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261112_SERWAY64_AUTO_BOUND_SOURCE_REVIEW_JOBS_V1`.

A first original Gemini Selenium reviewer request for slide 14 was positively registered. Its four-row JSON text was captured fully but initially rejected: `academic_review_checkpoint.validate_saved` used `Path.read_text()` on Windows, silently normalizing 40 CRLF pairs and corrupting the stored SHA and recorded character count. The reusable fix reads the original response as **bytes**, decodes without newline translation, and preserves the actual existing one-Send claim. Two adversarial CRLF/collision regression tests were added. Revalidation accepted the exact old reply with **zero further Gemini Sends**.

Actual slide-14 first-pass AI review: 4/4 rows source-valid, 0 SUPPORTED, 4 UNRESOLVED, 0 INCORRECT. The lack of usable original quotations is a genuine academic evidence gap. No formal scientific or release approval is inferred. Result `20261112_SERWAY64_AI_REVIEW_SL14_ONE_PASS.json`, original claimed checkpoint unchanged except its valid model-source QA state. `source_citation_review_dispatch.py` provides bounded first-pass one-Send and separately safe `--recover-only` replay.

## Routine slide-level PCM candidate and fallback

- `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261112_SERWAY64_ROUTINE_GEMINI_AUDIO_CANDIDATE_V1` is a **distinct** source/slide/script copy with immutable SHA-256 staging manifest, exact 14-slide narration, and existing standing routine Gemini Flash-Lite TTS/Kore authorization.
- Real primary Gemini TTS queue started on Dell-115 with normal 3-round retry. Slide 13 suffered provider timeouts, including its short segmented retry; preserve genuine candidate WAVs and do not claim completion until complete manifest, effective provider identity, exact 14 WAV coverage, PCM decode and listening QA.
- New `windows_slide_audio_timing_review.py` is a separately classified real FFmpeg **slide-level timing review only** from a completed TTS batch; it splits by **measured WAV length into parts strictly under 600s**, source/verifies all original SHA and actual PCM 24kHz/16-bit/mono WAVs, rejects fallback speech without independent voice evidence, probes encoded real audio/video durations and marks per-element highlight and release NOT VERIFIED. It never submits a model request, generates TTS or overwrites a prior file.
- Genuine audio-video acceptance requires exact source-bound *element* highlighting, robust acoustic QA, independent figure/math source review and final release checks; coarse slide-level timing video is **not** a substitute.

## Non-destructive testing and next action

- Native Windows isolated **real FFmpeg smoke**: succeeded with decoded audio/video duration exact to 3.25s.
- Synthetic full source/audio-review positive and invalid-WAV/tamper/no-overwrite regressions passed.
- Academic-review checkpoint CRLF regression and source-citation adaptive batching regression passed.
- No API key values, provider prompts or personal credentials should be committed.
- Continue the existing bounded slide-13 TTS queue **only**; do not resubmit any ambiguous Gemini web request or duplicate the 14-slide batch. If the source's physical figure/element correspondence stays unverifiable, record G2/G3 as blocked and advance general codebase work, not per-PDF perfection loops.


## Completion checkpoint — all six real academic batches

The 14-slide, 74-utterance first-pass Gemini academic campaign finished **all six batches** with independently checked source-citation input, one durable Gemini Send per batch and no resubmissions. Two original whole-batch responses (slides 1–3 and 8–10) contained one inadmissible source quotation each; `source_citation_partial_rescue.py` recovered the remaining individually verified rows without rewriting or re-sending the original replies.

**Final immutable ledger:** `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261112_SERWAY64_SOURCE_REVIEW_COVERAGE_LEDGER_V2.json`. Genuine results: 74/74 reviewed in six batches; 72 source-valid rows, 2 untrusted rows rejected, 23 supported, 49 unresolved, 0 incorrect, 0 missing review. The 49 unresolved and 2 untrusted records remain **blocking evidence gaps**. This is one source-cited AI review pass, not independent scientific verification or a learner-release permit.

**Codebase reusability:** New `source_citation_partial_rescue.py` and `source_review_coverage_ledger.py`, with no-Send regression tests, validate individually source-grounded rows, catch source/response SHA tampering, account for each utterance exactly once, disallow duplicated results and never invent missing academic proof. The normal original source and old failed stages are untouched.

**Whole-batch fallback hardening:** Gemini Flash TTS/Kore recovered the difficult genuine slide 13 after Flash-Lite/Kore timed out. The slide-level FFmpeg review now accepts a homogeneous fallback as **review-only** only with actual SHA-bound provider failure journal (`AttemptEvidence.verify_saved`), while recording `independent_voice_listening_verified=false`; no false speaker-equivalence assertion. The slide-14 provider request remains finite/retry-bound at this checkpoint, not accepted as complete until the actual terminal result.
