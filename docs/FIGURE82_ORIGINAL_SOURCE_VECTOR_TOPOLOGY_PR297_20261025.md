# PR297 — Verify original Figure 8.2 triangle vector topology

25 October 2026 (Asia/Kuala_Lumpur). Isolated Dell-115 development, stacked on CI-green PR296 exact head `8960fd105fdeea4cbc18eda567333bac9ad1b418`.

## Actual original scientific-figure evidence

On the unchanged Thomas Calculus 8.4 textbook physical page 1, Figure 8.2 has three reference triangles under printed tangent/sine/secant labels. PR295 established label order; PR296 established full source-to-slide bitmap pixel similarity. Neither proved actual geometric *edges* were present.

A first exploratory diagnostic printed only the first few line items from each PDF drawing object. This truncated listing misleadingly suggested that the second and third triangles might be missing one right-angle leg. Re-examining **all original vector line segments**, including separate segments inside the same drawing objects, corrected that conclusion. All three have one horizontal, one vertical and one diagonally sloped segment. They form closed right-angle corners in the source PDF. The diagonal displacement spans 66 PDF points horizontally and 48 vertically in each panel, with the expected upward-right orientation.

This is a reusable diagnostic lesson: **never treat a truncated PDF vector-object listing as a complete geometric shape**. A PNG that looks similar, a text label in the right order, or a partial set of drawing objects is not sufficient proof of right-angle triangle topology.

## Reusable, normal codepath

Added `selenium_pipeline.original_figure82_triangle_vector_topology`. The read-only original-source CLI:
- Requires PR296's real source-to-slide pixel fidelity and PR295's physical printed-label identification to pass with the exact same source/slide/script SHA256.
- Extracts actual PDF **line items** from all relevant drawing objects in the original Figure 8.2 diagram region, classifies horizontal, vertical and rising diagonal geometry, groups segments by source formula-label x position, and rejects wrong dimensions, flipped diagonals, duplicate lines, disconnected/phantom corners and missing diagonal paths.
- Tests closed triangles **without assuming line endpoints have consistent direction**; a previously initially failed check revealed the first original vertical path is stored in the reverse endpoint order.
- Reports each panel's explicit source vector right-angle/corner evidence independently from the semantic meaning of its side labels.
- Verifies original teaching source SHA identity after the inspection, with no original writes.

The confirmed real-original output is **3 source vector triangle candidates, all 3 with three complete edges and right-angle corners**, each 66×48 PDF points. `source_to_slide_pixel_similarity_verified=true` remains bound to PR296 evidence.

The tool does **not** prove how textbook side-length symbols correspond to those vectors, correctness of trigonometric sign/domain derivation, independent two-pass original mathematical review, video highlight timing, Kore TTS, human listening approval or YouTube student publication. Every such approval remains false.

## Acceptance/testing

Dell-115 `python -m pytest -q tests/test_original_figure82_triangle_vector_topology.py tests/test_original_figure82_pixel_registration.py tests/test_original_figure82_source_label_order.py` with `MICROGEN_ORIGINAL_THOMAS84_FOLDER` set to original user-owned source root: **24 passed**, 0 failed, five preexisting SWIG warnings. Synthetic adversarial regression tests cover flipped diagonal, disconnected and missing edges, wrong dimensions, duplicated path, endpoint reversal, synthetic three-panel grouping, and the real unchanged original source case. Hosted GitHub CI is a separate stage.

Original source PDF SHA256 `b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`, unchanged. Two-pass original AI source agreement remains **1/71 title metadata only, 70 pending/disputed, 0 independently approved substantive math**. No paid API or Gemini academic request, protected tree/source/media edits, main merge or publication.

## Next meaningful dependency

Triangle geometry and pixel fidelity are now technically evidenced. Next establish **the actual mathematical relation between each printed side-length label, radical expression and triangle edge** under the original source, retaining separate AI/human approval requirements. An original slide-3 academic review must remain blocked until scope-specific consent and transport/attempt conditions are independently verified. Genuine narrated synchronized MP4 production is conditional on those domain gates.
