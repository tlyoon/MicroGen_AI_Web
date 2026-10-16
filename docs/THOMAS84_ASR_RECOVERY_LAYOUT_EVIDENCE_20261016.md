# Thomas Calculus 8.4 — ASR recovery and layout-only transcript evidence

16 October 2026. MicroGen_AI_Web. **REVIEW-ONLY.** This branch is
stacked on draft PR #98. It does not merge any earlier PR, change the original
source materials, replace the corrected preview MP4s, or publish to students.

## Durable, independently transcribed speech checks

The source of truth for the narration WAVs remains the original unmodified
48-clip, Gemini 3.8 Flash Lite TTS, Kore collection. A distinct Gemini
3.1 Flash Lite model receives **audio bytes only**, not the script, to
independently generate spoken-word transcription candidates. Matching
transcription to the intended narration script indicates model-level
consistency, **not** an independent-human pronunciation audit.

The existing ASR stage is resumable and limited to three bounded retries for
transient service errors. A service outage creates an explicit INCOMPLETE
receipt and leaves previously verified per-WAV SHA-256-bound transcripts
unaltered. It never invents remaining transcripts.

## Generic layout-only ASR migration

The added `selenium_pipeline.asr_layout_carryover` stage reuses **only
previously completed** machine-transcription evidence when the slide
PDF has been corrected but the voice-bound element narration is demonstrably
unchanged. The carried evidence must match:

- Full original and re-bound authored-plan exact byte SHA256,
- Corrected visual-only rebind receipt and source material hash,
- Each original narration text SHA256 and unchanged original WAV SHA256,
- Original ASR job's model identity and original authored-plan hash,
- Each original actual ASR transcript's SHA256 and original WAV hash.

It copies no WAVs, does not invoke any ASR model and never marks missing clips
verified. It writes a fresh model-bound, re-bound-plan-specific ASR receipt
directory, plus a separate provenance document listing the exact number of
transcribed and remaining clips. Existing directories are never overwritten.

Example:

```powershell
python -m selenium_pipeline.asr_layout_carryover `
  --original-plan ORIGINAL_VOICE_BOUND_PLAN.json `
  --rebound-plan CORRECTED_LAYOUT_VOICE_PLAN.json `
  --original-asr ORIGINAL_INDEPENDENT_ASR_DIRECTORY `
  --audio ORIGINAL_GEMINI_TTS_WAV_DIRECTORY `
  --layout-receipt CORRECTED_LAYOUT_ONLY_REBIND_RECEIPT.json `
  --out NEW_NONEXISTENT_ASR_REVIEW_DIRECTORY
```

To verify the output in the actual complete-lecture audit:

```powershell
python -m selenium_pipeline.element_series_audit `
  --source ORIGINAL_SOURCE.pdf --slides CORRECTED_SLIDES.pdf `
  --authored CORRECTED_LAYOUT_VOICE_PLAN.json `
  --audio ORIGINAL_GEMINI_TTS_WAV_DIRECTORY `
  --staged CORRECTED_STAGED_INPUT_DIRECTORY `
  --rendered CORRECTED_RENDER_DIRECTORY `
  --old-slides ORIGINAL_SLIDES.pdf `
  --previous-voice-plan ORIGINAL_VOICE_BOUND_PLAN.json `
  --rebind-receipt CORRECTED_LAYOUT_ONLY_REBIND_RECEIPT.json `
  --figure-resize-receipt FIGURE_RESIZE_RECEIPT.json `
  --asr-dir NEW_NONEXISTENT_ASR_REVIEW_DIRECTORY `
  --report NEW_NONEXISTENT_TECHNICAL_REVIEW_AUDIT.json
```

Without `--require-asr`, the report states `partial_or_flagged_requires_review`
until all 48 real clips have acceptable model transcripts. Running with
`--require-asr` continues to fail unless all exact matching real transcripts
are present and pass word-error checks. Even that is **not** human academic
and spoken-pronunciation approval.

## Outstanding academic approval

Earlier visual/structural and mathematical sample QA remains valid
*for the source/text it actually checked*. The user reserved independent
academic, spoken lecture and figure review. All these claims stay false
until that review happens:

`human_listening_review_complete=false`,
`audible_word_fidelity_certified=false`,
`academic_approval=false`,
`production_approved=false`,
`student_publication=false`.

No timetable for the overloaded Gemini speech provider can be promised.

## Latest real execution of speech QA (16 Oct 2026)

A resumed real Gemini 3.1 Flash Lite audio-only ASR run processed **14/48**
WAV clips before a new model-unavailable error. Eleven of those were processed
after the initial three prior receipts. At the 20% normalized word-error
review threshold:
- **13** independently generated transcripts are machine-consistent.
- **1** segment (`s05_e03.wav`) is flagged with WER **0.355**. The intended
  speech concerns inverse sine and the interval from negative pi/2 to positive
  pi/2. The ASR model returned symbolic notation (`-I?/2` and `+I?/2`)
  rather than those words, so the real audible phonemes and mathematics
  require independent listening; no normalization was used to pass it.
- **34** segments have no independent ASR evidence.

The exact prior WAV files remain unchanged. The corrected-slide authored plan
receives fresh review-only ASR receipts via SHA-bound migration. The technical
lecture audit reports `checked=14, matched=13, flagged=1` and
`production_eligible=false`. A separate
`selenium_pipeline.speech_review_matrix` now creates a full CSV and JSON
listing all 48 clips, intended spoken script, actual ASR transcript where
available and review status for future human listening and academic review.
It never marks reviewed/approved itself.

The generic migration/regression tests and review-matrix fault tests require
real byte hash match; fabricated, mismatched or missing ASR files cannot be
counted as verified. Repeated Gemini 503 errors remain an external provider
blocker. Do not assume that further retries are guaranteed to work.
