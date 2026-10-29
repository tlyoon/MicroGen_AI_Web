# PR #141 — Rendered whole-raster equivalence safety preflight

Date: 19 October 2026 (Malaysia). Stacked on draft PR #140, exact parent commit
ecd23081b4ffd49c4bc5315e5b6bc6bf1a66ee7c.

## What changes

New read-only module selenium_pipeline.figure_render_equivalence provides
inspect_rendered_whole_raster_candidate. It runs the existing PR140 source/slide
raster hash, caption, unique placement, geometry and path-safety guards first.
It then independently rasterizes actual PDF source and slide figure rectangles
and compares each RGB pixel at scale 2–4 against a separate PDF containing
only the same extracted bitmap at the original rectangle and page location.

The check rejects page-level PDF clipping paths hiding part of a figure,
text drawn across a figure, colored annotation overlays, and any other pixels
different from an unobstructed image-only reference. Strict bit-for-bit
equality is required (no similarity threshold). Incompatible color profiles
or renderer differences may cause conservative rejections.

The record only claims rendered_raster_equivalence_verified=true, with
scale and actual compared bounds. Source and slide SHA-256 are rechecked
before and after inspection.

## What is NOT established

Image pixel identity cannot prove that the embedded textbook bitmap was
correctly extracted from a larger scientific figure, or certify subpanels
(a)/(b)/(c) and their boundaries. Rendering at one finite scale also cannot
establish mathematically absolute visibility at unobserved subpixel
resolution or clipping over pixels identical to the page background.
The record therefore explicitly retains these false values:

- image_visible_completeness_certified=false
- figure_panel_completeness_certified=false
- figure_semantics_certified=false
- tts_or_video_authorized=false
- human_review_claimed=false

This module is NOT wired to automatic narration or video production. It does
not authorize paid Gemini TTS, human approval claims, production replacement,
Moodle, or YouTube publication. It weakens no existing contract gate.

## Tests and continuation

Tests in tests/test_figure_render_equivalence.py create real PDFs,
including adversarial content-stream clipping, red foreground text and
annotation overlays retaining the same embedded source-image digest,
plus altered bitmap, caption and panel-labelled negative cases.

Next: independently establish source-space complete composite figure/panel
boundaries with caption and panel-label evidence and real textbook examples.
Only then bind proven elements to original per-element TTS, synchronized
highlights, strictly <600 s encoded parts and existing publication guards.
