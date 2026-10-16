# Thomas Calculus 8.4: complete element-narration REVIEW candidate

Date: 16 October 2026. Repository: MicroGen_AI_Web.
Development: stacked branch on the draft phase-2 implementation (PR #94).
**Do not use student publication or an accepted production completion receipt.**

## What this development branch adds

The existing 17-slide correction from Thomas Calculus 8.4 is read but never
modified. `thomas84_full_element_candidate.py` assembles a **48-element,
17-slide** explicitly authored scene plan. Original slide 5 contains three
separately addressed Figure 8.3 panels; slide 6 contains four independent
procedural steps. Other slides have independently selected narration anchors
representing their mathematical concept, figure or worked-example steps.

Two coherent parts are defined in advance:
- **Part 1: original slides 1–8**, 23 highlight/narration segments.
- **Part 2: original slides 9–17**, 25 highlight/narration segments.

Both exact durations are determined by the final recorded WAV samples, not
word-count estimates. The renderer fails closed if either encoded video
reaches 600 seconds. Per-element WAVs are synthesized with Gemini 3.8
Flash Lite TTS, named voice **Kore**; automatic provider mixing is forbidden.

The generic updated stage supports `image_whole` anchors to highlight small
figures without cropping, in addition to three independently highlighted
panels in a sufficiently wide composite figure. The original figure and
equations remain in their original Beamer-rendered slide appearance.

The generic `selenium_pipeline.element_series_audit` checks 17 ordered
slides, all 48 sourced narration chunks, content hashes, explicit
figure/source anchors, strict part duration, actual video encoding SHA,
and decoded MP4 frame target evidence. Fault tests deliberately corrupt
source digests, audio provenance, framed pixel evidence and video duration.

## Replay and safety controls

Use only new output locations outside the original source directory.
A complete candidate plan must be recreated if either original PDF changes;
staging validates source excerpts against the specified source PDF pages
and visually validates anchors against actual rendered PDF content.

```powershell
# In an isolated development clone with PYTHONPATH set to its root:
python thomas84_full_element_candidate.py --source SOURCE_PDF --slides VERIFIED_SLIDES_PDF --two-slide-plan PRIOR_FROZEN_REVIEW_PLAN --output NEW_FULL_PLAN_JSON

# Network/TTS calls occur only with explicit --confirm-live.
python -m selenium_pipeline.element_narration_gemini --authored-plan FULL_PLAN_JSON --output-folder NEW_TTS_DIR --voice Kore --model gemini-3.8-flash-lite-tts --confirm-live

# Resume a provider interruption using identical plan/model/voice.
# Previously completed files require cryptographic per-WAV attestations.
python -m selenium_pipeline.element_narration_gemini --authored-plan FULL_PLAN_JSON --output-folder EXISTING_UNFINISHED_TTS_DIR --voice Kore --model gemini-3.8-flash-lite-tts --confirm-live --resume

python -m selenium_pipeline.element_narration_cli --source-pdf SOURCE_PDF --slides-pdf VERIFIED_SLIDES_PDF --authored-json TTS_DIR/gemini_test_voice_plan.json --recorded-audio TTS_DIR --destination NEW_STAGED_DIR

python -m selenium_pipeline.series_review_cli --source-pdf SOURCE_PDF --prepared-parts STAGED_DIR --output-root NEW_RENDER_DIR

python -m selenium_pipeline.element_series_audit --source SOURCE_PDF --slides VERIFIED_SLIDES_PDF --authored TTS_DIR/gemini_test_voice_plan.json --audio TTS_DIR --staged STAGED_DIR --rendered RENDER_DIR --report NEW_TECHNICAL_REVIEW_REPORT_JSON
```

`FULL_PLAN_JSON` uses the exact same content as `TTS_DIR/gemini_test_voice_plan.json`
except the latter carries the frozen synthesized voice ID. The original
source files and historical MP4 must never be overwritten.

## What this DOES NOT verify

Even when all structural, video-duration, source SHA and pixel QA checks pass:
- Textual source evidence matching is **not** a proof of mathematical
  correctness, pedagogical appropriateness or faithful scholarly attribution.
- A generated WAV's hash does **not** verify the exact audible words or
  pronunciation. This needs separate audio-to-transcript confirmation.
- All chunks requested from the same named TTS voice do not, alone,
  constitute an independent listening or perceptual voice-consistency test.
- Original figures being intact does not guarantee they are perceptually
  legible at every student's video size, or that a source multi-panel figure
  is perfectly labelled in the narration.
- The user has reserved independent academic/video listening review for
  later. Do not falsely mark it completed.

Until those checks and full production integration pass, all output statuses
remain **REVIEW ONLY, NOT STUDENT APPROVED**. PRs #91–#94 and this new stacked
development PR must remain draft/unmerged.
