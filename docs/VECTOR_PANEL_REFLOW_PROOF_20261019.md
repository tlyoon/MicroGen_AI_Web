# PR #146 — source-bound vector-panel reflow verification

**Date:** 19 October 2026. Stack parent: draft PR #145,
feature/read-only-real-textbook-figure-pilot-20261019,
commit 285b649f8a80bab21a70328b3de91a5514a468bb.

## Technical improvement

Existing PR143/144 used exact source-to-slide pixel comparison of ONE
declared figure rectangle. This fails when the original textbook figure
is arranged in vertically stacked vector panels but slides arrange
independently rasterized panels horizontally. This new read-only
`inspect_reflowed_vector_panels` checks explicit independent source
and destination page-space rectangles for each panel and exactly
matches rendered RGB pixels of each vector-source region with the
corresponding slide raster region. Thus simple panel reordering is
allowed WITHOUT inventing source identity.

It requires unique original textbook Figure N.N caption directly below
the declared complete source figure region, genuine original
extractable (a)/(b)/(c) labels in their own region, no unassigned
original source vector paths or PDF words, absence of overlapping
source/slide panel boxes, non-distorting source-to-slide aspect ratio,
one real identifiable covering slide raster per panel, no interfering
slide vector paths, exact bounded pixel grids, and full SHA-256
integrity of each original PDF before/after the operation.

## Explicit scientific boundary

All rectangles are DECLARED by the caller. Even if panel content
matches exactly, the source crop could omit a meaningful external
diagram, or the author's interpretation of (a)/(b)/(c) could be
misunderstood. The following flags remain FALSE:
`author_intended_complete_panel_boundaries_certified`,
`figure_semantics_certified`, `tts_or_video_authorized`,
`human_review_claimed`.

No production render/TTS stage uses this candidate automatically.
Unsupported source PDF text labels, combined annotations,
non-identical rasterized drawing, custom panels or ambiguous figure
identity must FAIL CLOSED. The original Thomas Calculus 8.4 Figure
8.3 has no extractable (a)/(b)/(c) panel labels and slide 5 does not
contain an exact PDF-text Figure 8.3 caption; this tool must not
declare it verified based on synthetic demonstrations.

## Verification

Isolated generated actual PyMuPDF PDFs with three vertically stacked
source-vector panels and three independently embedded horizontal
slide-raster panels: tests verify correct exact reflow acceptance;
swapped slide panel, missing/duplicate source labels, crossing source
stroke, omitted source art, wrong ratios, shifted panel boundaries,
unexpected original source raster, missing slide image, duplicate
panels and malformed inputs fail closed. 12 focused HP tests
passed plus four parameterized subtests. No paid model calls, editing
source files, student-visible publication, or protected-main merge.

## Next proposed stages

PR147: source-grounded spoken-panel highlight contract gate and strictly
technical staging integration, WITHOUT auto-approving unverifiable
scientific content. PR148: deterministic full pipeline acceptance
harness with real textbook negative regression and auditable reason
for unresolved Figure 8.3; only proven cases may advance.
