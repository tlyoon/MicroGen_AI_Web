# fix_images_v3 source-verified split-panel acceptance

A printed Figure N.N remains mandatory. A historical lecture may show one
large source figure across two or more slides. The full original source image
is still retained as a SHA-bound canonical reference, but it need not be
duplicated as an additional slide when complete split coverage is proven.

## Deterministic evidence

1. The existing source_caption_figure_chain_v1.verify_figure_crops verifies
   every printed caption, canonical complete crop, source hash and panel ID.
2. The new source_split_figure_chain_v1.prepare_split_figure_chain runs
   **only in isolated retrofit staging** when original LaTeX has split assets
   instead of the full canonical image. Old source provenance is a candidate
   rectangle map, never evidence of acceptance by itself.
3. Each part must be an original-source PNG: independently render the exact
   source-page region at 3x, compare shape and strict image pixels. Tiny
   renderer-version variation of at most 1/255 per channel and 0.1% differing
   pixels can pass; missing content or altered images never can.
4. The union of panel rectangles must cover all original raster objects,
   significant vector paths, annotations and lettered-panel witnesses.
5. The split ledger records original source and legacy provenance hashes,
   per-part original crop regions and PNG hashes, per-panel object coverage,
   and explicit False scientific/student-release approval flags.
6. Every part must be included as a live, unguarded LaTeX reference and
   present as exact RGB pixels and as visible content on the rendered PDF.
   Separate source parts can appear on nonadjacent slides.
7. The normal runner.valid("slides"), figure manifest, conservative retrofit
   and cleanup gates enforce the complete source-to-final-raster chain.
8. Scientific interpretation, minuscule text readability, acoustic acceptance,
   video and student publication remain separate mandatory checks.

## Conservative retrofit

Keep a previously accepted 15-slide sequence with 15 accepted WAVs when all
source parts are already visible, semantically compatible, and synchronized.
Bootstrap both source ledgers from the original PDF inside staged work.
Regenerate and inspect corrected PDF and affected video; reuse scripts and
audio only when per-slide identity, hashes and QA prove compatibility.
If slide count/order or meaning changes, use the full downstream TTS/QA route.
Publication still requires the transactional --publish action after a
STAGED_ACCEPTED source/audio/video receipt; do not silently publish partial
results or enable a previously disabled scheduled task.

## Real Zenbook Serway 8.1 regression (20 November 2026)

The textbook has one printed Figure 8.1 with six source panels a-f.
Original lecture already shows a-c on slide 4 (Figure_8_1_upper.png) and d-f
on slide 6 (Figure_8_1_lower.png). Source reconstruction confirmed all 6
raster objects and 24 significant vector paths; old PNG pixels differed
from a fresh source render by at most one 8-bit level on a few pixels.
Both embedded image objects and final slide rasters passed, with visible
source parts on the correct pages. The original 15 slides and all 15 WAVs
remained aligned.

The isolated retrofitter compiled the 15-slide deck, bootstrapped both
ledgers, passed source/PDF/LaTeX/legibility/narration/WAV/sync checks and
re-encoded MP4 parts of 406.02s and 391.36s. Decoded frame comparisons for
slides 1, 4, 6 and 15 matched the PDF well. The stage produced the
STAGED_ACCEPTED receipt, including verified deliverables and hashes.
No original Drive files were overwritten, no paid Gemini Send occurred and
no scheduler or Zenbook Chapter 9 task was modified.

Fault-injection tests reject missing/changed PNGs, comment-hidden LaTeX
parts, missing/covered PDF parts and altered source provenance and ledgers.
The existing normal figure path and its older tests remain in force.

This document describes verified local staging behavior. GitHub merges and
deployed runtime updates must be checked independently.
