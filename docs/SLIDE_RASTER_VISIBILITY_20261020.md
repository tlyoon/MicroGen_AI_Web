# PR156 — independently verify displayed slide bitmap, not original figure identity

20 October 2026, Dell-115-only isolated development, stacked on
draft PR155 head `f1bb4bf0acff712786e96fbf5aea4fe854e0d301`.
This new audit is deliberately separate from the untouched
`20261020_pr155_source_vector_visibility_0055` uncommitted checkout,
which examines **source** vector drawing render observations.
The new `figure_slide_raster_visibility.py` checks actual **slide**
embedded raster visibility only.

## What is independently checked

- Source and slide PDFs are original, link/junction-free, bound to
  independently reviewed source FIGURE heading and page identities.
- Every displayed slide image is inventoried. Tiny inline decorative
  raster glyphs are counted separately and not automatically
  treated as full figure images.
- Requires one substantive, normally placed, unmasked embedded slide
  raster reference at a unique location. Checks its intrinsic image
  dimensions, placement aspect, size and containment.
- Independently extracts that embedded image, builds an in-memory
  image-only PDF reference and compares **all rendered RGB pixels**
  in the original slide image rectangle at 2x resolution.
  Overlays and clipping that change the visible pixels fail closed.
- All original source and slide SHA256 values are rechecked after
  audit. Positive visible-image proof **never** certifies complete
  author-intended original figures, panel identity, scientific
  correctness, source-to-slide correspondence, spoken highlights,
  video duration or publication. CLI exits 2 even for visible image.

## Actual Thomas Calculus 8.4 source page 2 / slide page 5

- Source page contains **zero displayed raster images**. Its 23
  pre-caption source drawing objects remain independently unassigned
  to complete original scientific figure/panels.
- Slide page reports **4 displayed image instances**: 3 tiny inline
  6x6 / 6x7 decorative images and one substantive xref 136 bitmap
  with intrinsic size **744x173 px**, bbox approximately
  `[36.484,165.439,326.346,232.84]`.
- The substantive bitmap's current slide-visible rendered pixels
  match the extracted embedded original bitmap reference exactly
  at the bounded audit resolution. This is **slide display evidence
  only**, NOT evidence that the original textbook graphs were
  faithfully selected or reflowed.
- Source SHA256 `b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`.
  Slide SHA256 `f6219ee18be4e347132d59be0d55e19765f325efed0b9d3d6544959a6dda68d1`.
  Neither original file was modified.

## Remaining contract blocks

The exact original source figure groups/panel labels, source-to-slide
content equivalence, genuine per-element spoken narration highlights
and individual encoded MP4s strictly <600 seconds remain unverified.
The historical Thomas 8.4 `slides.mp4` is 633.93 seconds and
is not a publishable compliant part.

No historical PDF/slides/script/WAV/MP4, shared G: working trees,
older uncommitted checkouts, protected main, credentials, paid TTS,
Moodle/YouTube or other PCs touched. Flash-Lite/Kore primary and
approved homogeneous three-real-failure fallback remain unchanged.
No Whisper, ASR or GCS external lease. This audit never bypasses
independent academic/listening QA.
