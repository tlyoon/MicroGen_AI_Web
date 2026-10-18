# PR #139 — Verified Multi-Element Spoken Text Anchors

**Development date:** 18 October 2026. Stacked draft PR on #138.
**Scope:** exact, readable, sequential source-grounded text elements; **not** semantically inferred images or arbitrary mathematical diagrams.

## Added capability

MicroGen_AI_Web previously accepted only a single slide narration block
equal to exactly one visible PDF text block. A narration spanning multiple
visible slide text blocks was rejected before TTS.

The automatic element narration planner can now process up to 12 distinct
vertically ordered text blocks per slide **only if all conditions hold**:

1. The existing script contains corresponding full spoken paragraphs
   separated by actual blank lines; there is no automatic speech/word splitting.
2. Each spoken paragraph is bounded, and its normalized text matches
   **exactly one** visible, measurable PDF slide text block.
3. The concatenated original paragraphs match the slide's narration **in
   full**, and the complete narration occurs verbatim on **exactly one**
   textbook source page.
4. The matched visual blocks are non-overlapping, unique, unclipped and
   ordered consistently from top to bottom; no inferred multi-column reading.
5. The slide has **no** embedded XObject images, inline raster blocks, or
   vector drawings. This avoids falsely treating PDF vector diagrams,
   equations rendered as paths, and multi-panel figures as ordinary text.
6. Every distinct paragraph is recorded with its own source-bound
   `text_block` anchor, sequential `sNNN_eXX.wav` filename and exact spoken
   text. Later accepted-media stages independently recompute this mapping
   from original PDFs and original narration.

The separate-element TTS batch uses the existing Flash-Lite/Kore primary,
bounded retries and conditional fallbacks. Each original distinct element
WAV has an independent SHA-256/PCM/timing/provenance record, is assigned to
exactly one highlight, and is verified together with all encoded pixels.
No separate human academic approval is invented or needed for automatic
technical progress.

**Safety:** Multipart cuts are on **whole slide boundaries**, computed
from real element-WAV durations, with a safe <540-second target and strict
**encoded <600-second per-part** acceptance. Any single slide exceeding the
safe budget is rejected rather than cut mid-narration without source anchors.
Existing source, slides, scripts, historical MP4s and all original three-PC
dirty working directories are preserved. No Whisper, Moodle, Zenbook or
Google Cloud distributed lease.

## Tests

Offline tests build genuine synthetic PDFs and an original mock TTS batch,
then produce a real H.264/AAC MP4 through the independent encoded-pixel
highlight renderer. The media path covers **six different spoken text
elements across three slides**. Adversarial checks reject reversed spoken
order, duplicated slide blocks, repeated source-page content, vector-only
figures, raster figures, mutated source PDFs, and overlong single slides.
No paid TTS or YouTube upload is made in this PR.

## Limitations

This is **not** a general solution for mathematical reasoning, narration
paraphrases, side-by-side columns, figure-panel recognition or missing
source text. Math expressed as accessible independent text blocks may be
eligible if it meets the exact matching requirements. Equations rendered
as vector artwork, composite figure panels and mathematical expressions
whose textual encodings differ from spoken words remain ineligible.

**Next:** build a separately independently verifiable, full-panel
source-grounded figure/diagram matcher; then pilot on a REAL complete
subchapter isolated from historical production, verify Flash-Lite and
actual source-to-video contracts, and only then test YouTube deployment.
Do not weaken this fail-closed gate merely to increase lecture coverage.
