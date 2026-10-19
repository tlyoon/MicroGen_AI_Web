# Caption-anchored vector figure discovery candidate — PR #149

Date: 19 October 2026. Target branch is stacked on draft PR #148.
Owner amendment: **Dell-115 ONLY** for PC development and testing,
no HP, Yoga6 or Zenbook. Existing GitHub Actions CI remains permitted.

## New isolated preflight

`selenium_pipeline.figure_vector_region_discovery.discover_vector_figure_candidate`
accepts a specific original textbook source PDF, one-based source page,
and numeric chapter.figure ID. It is read-only and prevents symlink/junction
input paths. An extractable, unique, exact FIGURE heading is required.
Drawing candidates must be page-contained, larger than small mathematical
strokes, and strictly bounded to the caption-heading neighborhood.
Pagewide drawings, decorations, off-page shapes, and tiny mathematical
paths are rejected. Missing or MULTIPLE plausible vector paths block.

The result is only VECTOR_REGION_CANDIDATE_REVIEW_REQUIRED. It does
not infer the author's intended complete figure crop, panels, figure
labels, scientific interpretation, narrated highlight locations, audio
timing or production eligibility. No image or video is generated.
All approval fields are explicitly false.

## Actual Thomas Calculus 8.4 source-only read-only pilot

Input is the original `8.4/source.pdf` on Dell-115,
source page 2, Figure 8.3.
Original SHA256:
`b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`.

Detected figure text block rectangle:
`[29.638, 404.110, 534.450, 553.190]`.
Sole admissible vector path:
index 37, `[197.890, 424.406, 557.390, 562.906]`.
44 PDF drawing objects were observed, with 43 excluded, including
pagewide vector paths. This is a reproducible **candidate**, NOT
certification of author-intended figure extent, complete a/b/c panels,
caption semantics or source-to-slide equivalence.

## Tests, safety and next acceptance gate

Real generated PDF adversarial tests exercise unique candidate,
ambiguous multiple large figures, missing/incorrect heading, no
figure, math-only strokes, invalid pages/IDs and disallowed symlink
when supported by the OS. SHA before/after is checked for the fixture.
No original teaching material writes, no billable TTS calls, no
Moodle/YouTube publication or protected-main merge.

Next PR #150 must independently ground the source figure's full
panel region and original panel labels/caption, not treat the new
candidate rectangle or a heuristic axis partition as authoritative.
PR #151+ must respect audio/visual source equivalence and every
encoded part strictly <600 seconds, with synchronized narrated
highlights and the agreed Flash-Lite/Kore TTS retry/fallback policy.
