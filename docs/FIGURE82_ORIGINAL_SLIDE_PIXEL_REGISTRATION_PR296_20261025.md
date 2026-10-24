# PR296 — Independently register original Figure 8.2 source pixels to Slide 4

25 October 2026, Asia/Kuala_Lumpur. Dell-115 only. Isolated new draft stacked on PR295 exact head `8f9f25f34c03fed48fc54afef9378584fc4218ee` (all 3 GitHub CI checks green before development).

## Root cause and observed real-case acceptance gap

The Thomas Calculus 8.4 original source Figure 8.2 is **vector-drawn in the textbook PDF**, while the generated Slide 4 contains a **409×134-pixel embedded composite raster**. PR290 verified source-image visibility, PR291 found three image whitespace gutter candidates and PR295 associated the original printed formula labels to image strip order. None of these established that the **actual slide pixels** faithfully reproduced the source PDF's real illustration. A wrong drawing with the same layout/labels could have passed their technical checks.

This PR implements genuine cross-modal pixel registration against the unchanged original source PDF and original embedded Slide-4 bitmap, instead of treating matching text and geometry as pixel fidelity.

## Reproducible original-source evidence

Original source `source.pdf` SHA256:
`b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`

Original textbook physical page **1**, matched source PDF point bbox `[264.66667,506.66667,537.33333,596.0]`, source render scale **1.5**.

- Full source-vs-slide normalized grayscale correlation **0.922333**; mean pixel absolute difference **2.864595 / 255**.
- Slide region 1, printed source label tangent: correlation **0.917917**, mean difference **3.316542 / 255**.
- Slide region 2, printed label sine: correlation **0.924303**, difference **3.063611 / 255**.
- Slide region 3, printed label secant: correlation **0.924399**, difference **2.378033 / 255**.

All three values come from the actual native Slide-4 image with originally observed cut pixels 0, 120, 246, 409 and independently PDF-rendered Figure 8.2, not source PNG copied into test fixtures. The source and slide SHA hashes are rechecked at the end. Full per-strip registered pixel fingerprints are machine-reported by the CLI.

## Permanent guard

New reusable `selenium_pipeline.original_figure82_pixel_registration` requires PR295's **printed textbook label order** and PR291's original embedded source-image gutter witnesses to agree on exact source, slide and narration SHA, expected material bitmap count, strip crop hashes, and real native shape. It searches a small corridor adjacent to the independently located original Figure 8.2 caption at strictly bounded render scales 1.45, 1.5 and 1.55; **exactly one** bounded scale must pass. It uses OpenCV grayscale normalized-template correlation plus actual mean pixel error for the full image and every independently derived strip.

It rejects absent/corrupted/blank originals, missing or extra image content, mutated source hashes, uncorrelated matches, distorted material strips, overlapping/misaligned candidate bounds, excessive render dimensions and multiple matching scales. When local OpenCV/numpy is not installed it reports explicit unverified/dependency-blocked status rather than approving absent checks; hosted full regression jobs already install OpenCV.

The threshold is intentionally stringent for this source-grounded *visual* pilot: full correlation ≥0.90, mean difference ≤8/255, each source-to-slide strip correlation ≥0.88, strip difference ≤10/255. No hard-coded positive match location is passed to the registration algorithm.

## Tests and release boundaries

Dell-115 focused/neighbor suites with **real original source enabled**:
`python -m pytest -q tests/test_original_figure82_pixel_registration.py tests/test_original_figure82_source_label_order.py tests/test_original_composite_gutter_proposals.py tests/test_original_figure_raster_preflight.py` — **29 passed**, zero failures, preexisting SWIG deprecation warnings. Includes wrong/mirrored figure, one intentionally corrupted panel, blank figure, unrelated source region, invalid bounds, oversized buffers, valid synthetic registration and the real Thomas 8.4 source/slide registration. CI skips real private textbook case when unmounted but runs synthetic checks.

**Pixel resemblance is not mathematical truth.** This PR does not independently verify triangle side symbols, source-to-panel narration alignment, genuine Kore TTS, actual <600-second encoded production video, human listening/academic QA or student publication. Two-pass original mathematical source consensus remains **1/71 section-title metadata only**, **70 pending/disputed**, **0 substantive mathematical agreements**. No Gemini requests, paid APIs, original G: changes, historical WAV/MP4 replacement, Moodle or YouTube publication.
