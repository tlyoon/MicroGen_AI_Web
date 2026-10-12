# RFH Phase 3A — multipart figure mapping safety guard

**Status:** isolated implementation candidate; not a production release.
**Scope:** `tlyoon/MicroGen_AI_Web` figure/caption mapping only.

## Reproduced failure mechanism

The older vendor mapper accepted repeated target names for separate Docling
`fig_*.png` crops, overwrote earlier files, and then concatenated the
crops horizontally. Source geometry was not retained, so this could corrupt
multipart figures such as Thomas Calculus Figure 2.10 (a)/(b)/(c).
A separately mapped panel could also be named as the complete parent.

## Changes

- Normalize all proposed output names **before any copies** and reject
  post-normalization filename collisions.
- Reject disagreement between figure or panel numbers in captions and targets.
- Reject ambiguous mixtures of parent-figure and separately identified panels.
- Never infer spatial layout or merge separate panels horizontally.
- Reject mismatching existing images instead of overwriting them; identical
  outputs can be reused without touching timestamps.
- Do not conceal figure-copy or root-publication errors and mark the page done.
- On a composite-rejected mapping, leave original crops alone and create a
  source/page/crop SHA256-bound `page_N_composite_review.json` for inspection.
  No generated image is promoted as verified by this report.

## Explicit limits and next acceptance gates

This change catches obvious *mapping-induced* multipart corruption.
It does **not** prove that a single crop already named `Figure 2.10.png`
visually includes every subpanel. The later full Phase 3 gate must use
source-page coordinates, source figure group and caption relationships,
synthetic three-panel layout fixtures, and inspection of rendered slide 7.
A second gate must enforce LaTeX width **and** height constraints with
`keepaspectratio`; compiling alone does not demonstrate no clipping.
Any ambiguous case must remain `review_required`, not `passed`.

Testing must include isolated mapper unit regressions, existing Phase 1
transport tests, Windows cross-PC validation, and a source-authorized Thomas
2.2 controlled pilot before rollout. Do not automatically regenerate
narration, MP4s, or accepted figures in any production source directory.

## Rollback

Revert the Phase 3A commit in a clean branch. The main source PDF and
published teaching assets are intentionally not modified by the tests.
Review JSON artifacts remain diagnostic only.
