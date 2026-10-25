# PR300 — Real original Slide4 narration to Figure8.2 highlight *candidates*

25 October 2026, Asia/Kuala_Lumpur; isolated Dell-115-only draft based on **CI-green PR299** head `6cd62666ae904db6446e2e68a08fa92cb3d152ff`.

## Real pilot and bottleneck

The actual original Thomas Calculus 8.4, physical lecture Slide 4, has **five** narration utterances. The actual embedded 409×134 composite of original textbook Figure8.2 contains **three independently bounded and source-pixel-matched regions** (tangent, sine, secant). Until now, figure QA did not bind the original speech/utterance SHA to those source-authenticated candidate rectangles. A naive global image highlight or an invented equal-time division into three panels could incorrectly claim that visually highlighted speech matched the intended mathematical object.

The read-only real-original pilot now retains all five narration IDs, exact original speech SHA256s, unchanged original source/slides/script SHA256s, and the actual geometric/pixel provenance inherited from PR291, PR295–298. It proposes figure strip rectangle mappings ONLY for utterances 002–004:

| Original speech ID | Printed source formula | Candidate original Slide4 rectangle (PDF pt) |
|---|---|---|
| `s004.utterance.002` | `x = a tan u` | `[48.421,91.9534,126.4618,179.099]` |
| `s004.utterance.003` | `x = a sin u` | `[126.4618,91.9534,208.4046,179.099]` |
| `s004.utterance.004` | `x = a sec u` | `[208.4046,91.9534,314.4101,179.099]` |

These regions retain actual original bitmap strip SHA256s and immutable original narration SHA256s. **Utterance 001 (general triangle introduction) and utterance 005 (principal-root/absolute-values statement) are deliberately UNMAPPED**: assigning them a single triangle panel would be speculative. No timestamp, fabricated audio segment, or timed highlight cue is emitted.

## Permanent engineering correction

Added `selenium_pipeline.original_slide4_figure_highlight_candidates` (CLI and reusable pure function). The read-only source audit requires:

1. Exact immutable original Thomas source/slides/script hashes and all five original narration units in order, with original utterance SHA256.
2. Original Figure8.2 source text/printed-formula order and physical side-label evidence, full original source-to-slide pixel fidelity, and actual source-native raster-strip fingerprints.
3. Three physically contiguous non-overlapping, within-slide candidate rectangles, with the expected printed source formula associated to each ordered strip.
4. Each of the three selected narration utterances must uniquely mention the corresponding tangent/sine/secant term; competing, changed, missing or duplicated terms fail closed.
5. Preserve both unassigned utterances in the denominator; set mathematical approval, actual word timestamps, audio rendering, highlight synchronization, Kore voice acceptance, and publication **all false**.

The output intentionally says `ORIGINAL_SLIDE4_THREE_RASTER_REGION_CANDIDATES_REVIEW_ONLY`, never an academic/pass/video-ready status. The added regression suite tests missing/reordered speech, ambiguous terms, inverted panel order, changed source strip hash, malformed overlapping/off-page rectangles, and genuine original-source audit.

## Acceptance, safety and next dependency

Original review baseline remains **1/71 title-only AI source agreements, 70 outstanding, and zero substantive independent mathematical agreements**. This increment raises real, source-bound **review candidate** coverage to 3/5 utterances for Slide4, not verified highlight timing, approved mathematical semantics, or completed/student-ready production. The original PDF radical glyph remains lossy and principal-root sign applicability is not independently approved.

The next meaningful step is to verify and record **genuine, consent-authorized original audio timing/voice** for all five exact utterances, then verify actual decoded MP4 frames alongside the audible speech. Keep the strict video duration below 600 seconds and identical voice through all video parts. If genuine authorized audio cannot be established, do not invent timestamps, spend on unapproved model calls, reuse a different voice, or claim synchronized final video.

Source originals, historical WAV/MP4 and model receipts remained untouched; **no new Gemini requests, paid API calls, protected branch merge, Moodle/YouTube publication, or HP/Yoga6/Zenbook access**.
