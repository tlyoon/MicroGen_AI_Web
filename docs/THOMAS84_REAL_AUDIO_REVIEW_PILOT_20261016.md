# Thomas Calculus 8.4: real-audio REVIEW-ONLY pilot (16 October 2026)

Status: **TECHNICAL_REVIEW_ONLY_PASS.** Not an approved source-specific
production lecture. Do not merge this experiment as a production renderer.

## What was actually demonstrated

- Isolated checkout of MicroGen_AI_Web PR #92 at `97399d0`.
- Input from a separately verified/corrected `MicroGen_AI` 8.4 bundle,
  preserving its source, slide PDF, all 17 slide-level narration WAVs and SHA receipts.
- Two ordered review-only H.264/AAC MP4s produced by the *Web* renderer:
  - Part 1, original slides 1–8, **321.89 seconds**, eight encoded highlights.
  - Part 2, original slides 9–17, **310.82 seconds**, nine encoded highlights.
- Encoded-pixel verification: 17/17 registered highlight events passed.
- Independent audio/source/figure audit: both WAV streams had nonzero RMS;
  SHA-256 source hashes unchanged; Figure 8.3 correction covers ~289.87 pt
  of the 362.83 pt page (~80% of page width).
- Neither video is classified as production-approved or student-published.
- All output media and audit were copied to a **private** Drive folder:
  https://drive.google.com/drive/folders/1gbEQ-BF7rRt2A_sVGk9QyqkACc7_mWL8

## Critical limitation: the video contract is NOT fully satisfied

Each reused WAV narrates its whole slide; the prototype highlights only
one selected content rectangle during that slide's complete narration.
That is **not** guaranteed to be the equation, graphic or derivation step
being spoken about at each instant. The `tts_text` hash is bound to the
recorded sidecar, not a proved audio transcription. Voice ID is unverified.
The source-page marker is a placeholder, not a factual source reference.

The pilot proves real spoken audio can be joined, displayed, encoded, and
pixel-checked in multiple strictly sub-600-second preview videos. It does
**not** establish semantic narration-to-element accuracy, word fidelity,
pedagogical completeness, or full mathematical correctness. Do not generate
production completion receipts from it.

## How to reproduce (without editing originals)

From an isolated checkout of the stacked review renderer PR #92:

```powershell
python thomas84_real_speech_pilot.py --source-dir PATH_TO_VERIFIED_8_4_FOLDER --destination PATH_TO_NEW_EMPTY_PARENT/84-prepared
python -m selenium_pipeline.series_review_cli --source-pdf PATH_TO_VERIFIED_8_4_FOLDER/source.pdf --prepared-parts PATH_TO_NEW_EMPTY_PARENT/84-prepared --output-root PATH_TO_NEW_EMPTY_PARENT/84-rendered
python thomas84_real_speech_audit.py --source-dir PATH_TO_VERIFIED_8_4_FOLDER --prepared PATH_TO_NEW_EMPTY_PARENT/84-prepared --rendered PATH_TO_NEW_EMPTY_PARENT/84-rendered --handoff PATH_TO_NEW_EMPTY_PARENT/84-review
```

Use real paths without renaming the originals. The destination directories
must **not exist**. Creation never overwrites files. All inputs are verified
against their existing hashes before staging; rerun protection applies.
No calls to Gemini or TTS occur; no paid services or course publication.

## What to implement next

1. Source-review a real concept/part outline, with verified textbook page
   references and all required equations, derivations and figure panels.
2. Create *per-element* spoken segments, rather than reusing whole-slide
   audio. Generate each segment using one consistent voice, with frozen
   spoken-text hashes and measured final WAV sample counts.
3. Bind segments to precise Beamer PDF elements (equations, subgraph panels,
   intermediate steps). Produce uninstrumented pixel-identical static PDFs.
4. Render end-to-end, decode actual MP4 frames, and verify every highlight
   against the contemporaneous spoken segment plus math/figure QA.
5. Add fail-closed production receipt and atomic publishing only after
   all contract checks; keep PR #91/#92 draft until then.

No human scientific or pronunciation approval was issued. Manual lecture
review may occur later independently, as instructed.
