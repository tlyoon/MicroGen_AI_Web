# Thomas Calculus 8.4 — Gemini Flash Lite element-narration pilot

**Date:** 16 October 2026. **Scope:** two source slides (#5 and #6) out of 17.
**Status:** technical review only, NOT academically approved / NOT production accepted.

## Measured technical results

- 8 individual narration segments synthesized with **Gemini 3.8 Flash Lite TTS,
  voice Kore**. One model and voice was used throughout, without switching
  providers. No original whole-slide narration was reused.
- 8 separate source-linked highlight targets in the already corrected
  Thomas 8.4 slides:
  1. The domain-restriction explanation,
  2. The first, second and third panels of Figure 8.3,
  3. The four individual substitution procedure steps.
- Input is the corrected, SHA-256-checked source.pdf/slides.pdf, without
  modification, figure crop or alteration to the historical published videos.
- Actual final narration PCM WAV durations total 91.36 seconds.
- Encoded H.264/AAC MP4 duration 91.36 seconds, strictly under 600 seconds.
- Decoder verified all 8 visual target highlights in actual MP4 frames,
  with maximum reported transition-frame drift of 0.00 seconds on Dell-115.
- Full source coverage is deliberately FALSE; only two slides are shown.

## Important limitations

The upstream narration text was explicitly written for the correct element,
and the actual separately generated PCM WAV sample counts fix the timing.
However, a text SHA-256 bound to a requested TTS segment does **not prove**
that every generated spoken word precisely matches the supplied script.
Voice continuity is a declared same-model/same-voice configuration, not
a human perceptual proof. The source quote matching protects provenance,
not mathematical truth. Academic review and pronunciation listening are
not claimed.

The code and renderer return review-only receipts and do not create a
lecture completion certificate, Moodle publication, or student-facing output.

## Private review contents

- `thomas84_slides5_6_Gemini_Kore_REVIEW_ONLY.mp4` — playable preview
- `tts_synthesis_receipt.json` — exact voice/model and per-WAV hashes
- `authored_element_plan.json` — original source-grounded narration mappings
- `element_stage_receipt.json` — exact source hash, coverage flags
- `part_review_receipt.json` and `encoded_pixel_qa.json` — decoded QA proof
- `frozen_inputs/` — read-only replay inputs for HP/Yoga 6 tests

## Next requirements for full Thomas 8.4 compliance

Build and verify a complete, source-faithful element narration plan for
all 17 slides and every required worked-example step. Regenerate the
entire lesson with the same Gemini voice; split at coherent boundaries so
every part stays below 600 seconds. Verify all element-target pixels,
word-to-audio fidelity, figures and equations, cross-PC acceptance,
complete coverage and safe atomic production publication.

Maintain PR #91–#94 as drafts until this release boundary passes.
Manual lecturer academic/audio signoff may follow later independently.
