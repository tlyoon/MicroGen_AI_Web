# PR290 — Original teaching-figure structural and raster integrity, without inventing triangle semantics

24 Oct 2026, Asia/Kuala_Lumpur. Dell-115 isolated draft stacked on PR289 exact `4e728c8`.

## Verified real Thomas Calculus 8.4 evidence

Read-only original textbook/slide/script hash-bound inspection of **Slide 4: Geometric Reference Triangles**, with original five narration units. Original textbook `source.pdf` SHA256 `b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`.

The ORIGINAL `slides.pdf` page has **one material 409 × 134 pixel composite triangle raster**, displayed within page bounds at `[48.421,91.953,314.410,179.099]` PDF points. Actual image displayed aspect ratio and raster intrinsic aspect ratio both **3.05224** (0 relative distortion). Decoded grayscale cropped region contrast **193**, nonwhite ink occupancy approximately **12.584%**, indicating a real visibly nonblank figure. Cropped decoded pixel SHA256:
`f722f4e36c5a8d9a2b6d9f5432a1ae3d64e8c6b736419738a41f8b714b9518a6`.

Three tiny 6×6 decorative/placeholder rasters are **excluded** from material figure count; do not inflate figure content with them. Original textbook source file and slide/script assets remained unchanged.

## Generalizable safety code

Add reusable `selenium_pipeline.original_figure_raster_preflight` for one source-bound slide. It verifies original textbook/slide/script fingerprints against the genuine original narration job, material image intrinsic width/height, original PDF page-bound coordinates, distortion of image aspect ratio, decoded crop pixel hash/contrast/nonblank ink. It denies missing material figures, empty or clipped bounding boxes, visually blank material image regions, and disproportionate stretching. It reports actual visual image fingerprint for reproducibility.

**Important scientific and release boundary:** Passing this test is purely technical; the original figure contains **multiple reference triangles inside ONE composite raster**, so this tool does not infer their individual panel bounding boxes, side lengths, axis labels, correct right-angle direction, relationship to the original textbook illustration, narration-to-panel timing, independently agreed mathematics or human academic listening QA. Those fields remain false, as do paid voice and publication authorizations.

## Validation

Dell-115 focused and neighboring suite:
`pytest -q tests/test_original_figure_raster_preflight.py tests/test_original_trig_substitution_numeric_preflight.py tests/test_incremental_element_candidate_map.py tests/test_source_review_eligibility_preflight.py`: **25 passed**, five existing third-party SWIG deprecation warnings. Adversarial cases cover blank raster, missing material image, cropped out-of-page geometry, wrong displayed ratio, changed SHA, tiny image misclassified as real figure; real unchanged Slide 4 passes geometric/raster QA.

## Next milestone

A subsequent independently authorized original textbook review must validate substantive mathematical formulas/figure interpretation, not only numerical samples or visual crop health. Need independent segmentation of the three real right-triangle panels (with reliable proof of correct layout/labels), source-to-element mapping and permitted real Kore utterance TTS/render/decoded video QA. Preserve all historical source/WAV/MP4; no Moodle publication or protected branch merge.
