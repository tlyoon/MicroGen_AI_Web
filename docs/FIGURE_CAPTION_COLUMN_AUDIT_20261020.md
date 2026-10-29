# PR152 — independent Figure caption/neighboring-column evidence

20 October 2026; Dell-115 only. Stacked on draft PR151
`feature/source-vector-boundary-review-20261020`
at `bc0798792ab00463317a68e44f72dd0bb5098015`.

A source PDF text block can span both a figure caption and a separate
adjacent instructional column. Therefore a whole PDF text-block rectangle
MUST NOT be equated with exact figure caption bounds. The new
`figure_caption_column_audit.audit_caption_column_collision`
reads only an original source PDF with hash preservation, requires one
exact structured FIGURE heading line, and inventories substantial
parallel prose lines in the caption neighborhood. The heuristic
flags possible column collisions; it NEVER certifies caption extents,
source figure panel boundaries or video.

## Real Thomas Calculus 8.4, original source page 2

Independent heading: `FIGURE 8.3`,
bbox `[29.64,404.11,78.132,413.11]`.
PDF text block 36 also includes the adjacent procedure heading and
instructions at x216+ spanning y434–553. Eight substantial
parallel instructional lines share that same block.
Result `CAPTION_PARALLEL_PROSE_COLLISION_REVIEW_REQUIRED`
with 8 lines sharing the heading's text block. Source SHA256
`b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`
was unchanged. The original figure's complete graph geometry,
caption segmentation, scientific panel identities and narrated
highlight placement are NOT independently certified.

See PR151 for the earlier actual source error: drawing #37 is
the prose-filled substitution procedure box, not Figure 8.3.
This source audit does not invent a replacement figure rectangle.

All original teaching assets and G: tree files untouched; no
production, paid TTS, protected main merge, HP, Yoga6 or Zenbook.
Owner contract remains strict encoded parts <600 seconds,
source-ground synchronized highlighting, approved Flash-Lite/Kore,
actual retries and homogeneous voice, no Whisper/ASR or GCS lease.

Test evidence belongs in the PR body and checkpoint only after
exact-head test completion. Next: independent source graph
object inventory above the true caption followed by an integrated
read-only scientific evidence gate, never heuristic approval.
