# PR169 — alternative three-graph layout-aware reflow algorithm

20 October 2026; Dell-115 only; stacked DRAFT on PR168
exact head `529dc56ae0a1bf5cf99299c9f08e600044a4253a`.
The **original Figure 8.3 is three vertically stacked,
UNLETTERED** graphs: arctangent, arcsine, and arcsecant
of `x/a`. The existing PDF slide page 5 embeds them
HORIZONTALLY in a single 744x173 bitmap. Comparing
one full source rectangle to the slide bitmap necessarily
fails geometrically even when the plotted curves are present;
trying to find explicit printed (a),(b),(c) panel markers
does not fit the original artwork.

New independent technique:
- Original textbook PDF page 2 is rendered RGB at 3x in
  a bounded left figure corridor ending above the
  independently verified FIGURE 8.3 caption heading.
- Pixel-ink row projection finds three separated ORIGINAL
  graph regions (no PDF vector-drawing index used for panel
  ownership or bounding boxes).
- Independently, column-ink projection of the ONE separately
  verified visible slide bitmap finds three horizontal regions.
- HSV blue curves and red-magenta asymptote lines are matched
  in original/source order using an independent normalized
  symmetric two-direction distance-to-ink (Chamfer) score.
  Very thin third-panel horizontal pink asymptote uses a
  separate normalized position/length comparison relative
  to its blue-curve bbox.
- Black text/axes/labels ink geometry is measured as a
  **diagnostic only**; mathematical character identity and
  label, axis or curve scientific correctness are not
  inferred from a black pixel overlap metric.

**Actual original Thomas Calculus 8.4 / Figure 8.3 results:**
- Three original vertical graph scan bands in source render
  pixel y: [226,497], [550,886], [933,1180].
- Three slide horizontal graph scan bands in embedded bitmap
  pixel x: [2,230], [307,447], [514,743].
- Ordered blue-curve symmetric normalized Chamfer differences:
  0.001526, 0.001110, 0.001405.
- Magenta-red: 0.000534, absent from both middle graphs,
  0.003858 for a thin horizontal line at the third.
- Black axis/label ink geometric diagnostics:
  0.020170, 0.004777, 0.035422.
- Real technical status:
  `THREE_GRAPH_COLORED_CURVES_REFLOW_CORROBORATED_REVIEW_REQUIRED`.
  These numerical thresholds empirically fit this figure
  and MUST NOT be treated as universal acceptance criteria.
- Original source SHA256
  `b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`;
  actual slide PDF SHA256
  `f6219ee18be4e347132d59be0d55e19765f325efed0b9d3d6544959a6dda68d1`.
  Both originals remain unchanged.

Synthetic adversarial tests include three same-order curves,
wrong graph order, deleted blue curve, missing red asymptote,
missing whole graph, erased black axes, invalid pixel types/
bounds, empty curves, and gutter detection. Black axes
erasure can leave colored shape agreement intact, so **no
semantic/complete graph/axis/label approval can come from
this algorithm alone**. This measured evidence resolves the
specific prior *whole-region/aspect and nonexistent lettered
panel* false blockers, but NOT full content QA.

CLI deliberately exits 2. No original textbook/slides/
narration/WAV/MP4 changed; no automatic PDF restoration,
real textbook publication or media generation. Historical
8.4 original MP4 ~633.93s is still over the strict 600s
upper bound. Per-part encoded length <600 seconds,
genuine narration-synchronized element highlights and
human academic/listening QA stay separate blockers.
Flash-Lite/Kore primary TTS, voice-consistent approved
fallback only after three real failed attempts; no paid
calls, Whisper/ASR, GCS distributed lease, main merge,
HP, Yoga6, Zenbook or unverified Moodle publication.
Older uncommitted Dell source-vector checkout preserved.
