# Phase 2 element-level narration pilot — Thomas Calculus 8.4 (16 October 2026)

**DRAFT/REVIEW ONLY.** This is not an approved or published lecture.
It is intentionally limited to two slides and one locally generated test voice.

## Real evidence obtained

- MicroGen_AI_Web source: stacked draft PR #93, base commit `91fd33e`.
- Input: previously corrected verified Thomas 8.4 `slides.pdf` and original `source.pdf`,
  read-only from the separate MicroGen_AI lecture folder.
- A new author-specified plan anchors eight real narration chunks to eight
  *different* existing PDF regions on original slides 5 and 6.
- Slide 5: explanatory text and the three separate original Figure 8.3 graph panels.
- Slide 6: each of the four source-slide procedural steps.
- Source evidence for the lesson is checked verbatim against original source
  textbook PDF page 2; text anchors are verified on actual rendered PDF blocks.
- The original composite Figure 8.3 is never cropped or removed; its three
  panel-highlight rectangles are independently located inside the original
  full-width figure. No image is reconstructed from the panels.
- One PCM WAV per element is generated with local Windows SAPI voice
  `Microsoft Zira Desktop`. **SAPI is for offline technical demonstration only.**
  It is not the intended default production Gemini Flash Lite TTS voice.
- Distinct final WAV segment durations determine highlight switching;
  no arbitrary timing estimates or whole-slide WAV subdivisions.
- Rendered MP4: 89.31 sec, 8 verified timed highlight events, measured
  maximum frame-transition deviation 0.02 sec.
- The video renderer decoded encoded MP4 frames and confirmed target pixels
  for all eight events, not only a declared storyboard.
- Seven new source/staging regression tests passed locally on Dell-115.

## Design boundary

New generic `selenium_pipeline/element_narration_stage.py`:

1. Requires an **explicit authored scene plan**. It never assigns mathematical
   meaning to equation regions by guessing from nearby text.
2. Fails if source/slide SHA changes, textbook source-page evidence cannot
   be found, the indicated visual block is wrong, original multi-panel figure
   is implausible, any segment WAV is missing/duplicated, or input/output
   trees are unsafe.
3. Requires physically separate PCM narration files for every element.
4. Produces actual `instrumented.pdf`, `storyboard.json`, `tts_chunks.json`,
   `series_inputs.json` consumable by the existing reviewed MP4 renderer.
5. Keeps proof scopes separate: true measured WAV boundaries and exact
   encoded highlight pixels are checked; audible-text fidelity, narrated
   meaning, voice identity authenticity, scientific correctness, and
   academic review are **not** thereby proven.
6. Its receipt explicitly records whether every source slide is covered.
   This pilot covers 2 of 17, so `complete_lecture_coverage=false`.
7. Never creates production completion/publication certificates or modifies
   any textbook or legacy lecture output.

## Reproduce safely in an isolated checkout

Set the correct absolute source paths and choose three *new* nonexistent
output paths. Do **not** place any output in the textbook source folder.

```powershell
python thomas84_element_demo.py --source PATH_TO_SOURCE_PDF --slides PATH_TO_SLIDES_PDF --output PATH_TO_NEW_PLAN_JSON
powershell -File .\generate_windows_sapi_review.ps1 -Plan PATH_TO_PLAN_JSON -OutputFolder PATH_TO_NEW_AUDIO_FOLDER
python -m selenium_pipeline.element_narration_cli --source-pdf PATH_TO_SOURCE_PDF --slides-pdf PATH_TO_SLIDES_PDF --authored-json PATH_TO_PLAN_JSON --recorded-audio PATH_TO_AUDIO_FOLDER --destination PATH_TO_NEW_STAGED_FOLDER
python -m selenium_pipeline.series_review_cli --source-pdf PATH_TO_SOURCE_PDF --prepared-parts PATH_TO_STAGED_FOLDER --output-root PATH_TO_NEW_REVIEW_MP4_FOLDER
```

## Full contract blockers and next development

- Author/source-validate true element-level structure for **all 17 slides**,
  including worked integration equations, captions and every figure panel.
- Generate coherent per-element narration with the configured Gemini
  Flash Lite TTS voice (or documented single-voice fallback), not SAPI.
- Verify audible spoken content matches the authored segment text; a
  text hash alone cannot prove that a WAV contains those words.
- Independently evaluate math, source mapping and each slide figure; keep
  final academic signoff separate for later lecturer review.
- Confirm all multipart videos strictly under 600.0 seconds, every source
  element covered, and all encoded highlight events mapped correctly.
- Only then connect to production acceptance and atomic publication; keep
  PR #91/#92/#93 and this stacked Phase 2 work in draft meanwhile.

This experiment is not equivalent to rebuilding the full Thomas 8.4 lesson.
