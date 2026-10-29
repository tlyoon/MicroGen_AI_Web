# PR147: Figure narration production promotion contract gate

2026-10-19; stacked on PR146 verified source/slide panel reflow.

## Implementation

The existing source-bound production bridge's `accept_candidate`
is a TECHNICAL production promotion boundary; reviewed previews may be
human-inspected but are not proof of actual textbook figure correctness.

New `figure_narration_promotion.check_production_anchor_provenance`
rejects all `image_whole`, `image_panel`, `vector_figure`, `figure`,
`figure_panel` and `diagram_region` anchors in an authored plan
BEFORE expensive decoded FFmpeg verification and before any production
candidate is created. It also rejects unknown anchor types and malformed
plans. The bridge rechecks the plan after expensive verification and
ensures its SHA has not changed before copying original media.

Self-declared flags such as `tts_or_video_authorized=true`,
`author_intended_complete_panel_boundaries_certified=true`,
`figure_semantics_certified=true` or a user-authored 'APPROVED'
label do NOT authorize a figure for production. Previous PR140-146
preflights expressly do not certify the author's complete panel crop or
scientific interpretation.

This is deliberately a **fail-closed production safeguard**, not a claim
to have created automatically grounded figure narration. It leaves
the author-specified review-only preview workflow intact, while text
anchors retain existing technically verified production paths.

## Tests

- HP focused direct gate tests: 6 passed / 16 parameterized cases passed.
  Covers all image/panel variants, bogus approval fields, unknown
  anchors, mixed text/figure plans, and absence of paid tools/output.
- Existing original source-bound FFmpeg production bridge regression
  plus new guard tests: 30 passed / 16 subtests passed. Actual video
  preview/production code still accepts source-grounded TEXT-only
  work after guard introduction.
- Other independent PC and full CI results need separately verified
  receipts on the exact resulting commit.

## Next

PR148 should implement a deterministic technical acceptance auditor
for the full chained draft stack and actual textbook pilot (including
duration <600s and decoded source-bound highlight evidence where a
genuine MP4 exists). The real Thomas Figure 8.3 remains not certified
for narration because its textbook panel labels cannot be independently
extracted/located in the source. Do NOT guess source geometry.
