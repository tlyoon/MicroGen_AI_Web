# PR #140: Exact whole-raster source-identity preflight

Date: 18 October 2026. Stacked on draft PR #139, commit
`4db850f205030d9a764f86dc34f790d8502e1667`.

## Technical scope

`selenium_pipeline.figure_source_identity.inspect_whole_raster_candidate`
performs a read-only, explicitly scoped PDF image identity preflight.
It requires an exact figure caption appearing once as a text block on
the selected source page and slide, a single ordinary embedded raster
image per selected page, one visible unmasked placement, valid
page-contained geometry, matching decoded image-pixel MD5, matching
pixel dimensions, undistorted image placement, and unique image
occurrence across both PDF documents.

The function produces an **identity candidate only**. It does not
authorize element narration, figure highlights, paid TTS, video
publication, or a claim of scientific correctness. It is deliberately
not wired into `automatic_element_narration` or any production stage.

## Known limitations and contract guards

Exact decoded pixel identity is necessary, not sufficient, to prove
that a source figure is completely visible. PDF clipping paths,
composite panel geometry, source mathematical semantics, OCR text
inside bitmaps, and captions that do not have an exact extracted
text block remain outside this proof. The returned record explicitly
sets `image_visible_completeness_certified=false`,
`figure_panel_completeness_certified=false`,
`figure_semantics_certified=false`, and
`tts_or_video_authorized=false`.

Before any PDF is opened, the preflight rejects symbolic-link or Windows junction path components on both input paths; it also rejects identical source/slide paths. This repairs a previous resolve-before-check weakness. Deterministic mocked path tests exercise both leaf and parent links even when Windows symlink creation is not permitted. This is a preflight check, not a claim to prevent concurrent filesystem replacement or all possible TOCTOU races.

The preflight rejects vector artwork, masks, inline images without
a source xref, multiple/reused images, different decoded pixels,
re-encoded partial crops, mismatched captions, visibly clipped/off-page
or too-small figures, and panel-labelled captions. It does not
silently infer a/b/c panel boundaries.

## Tests and next step

The synthetic actual-PDF test module
`tests/test_figure_source_identity.py` covers identity success and
fail-closed adversarial cases, preserving all source files. Tests do
not call Gemini, Cloud TTS, YouTube or Moodle.

Next: add an independent source-space panel completeness validator
that proves full-panel boundaries and pixel-visible completeness
before allowing any figure element to become a production TTS target.
Only after independent checks pass should an isolated real-textbook
pilot be attempted. Do not weaken PR #139's text-only safety gate
to make figure narration appear to work.

Never merge stacked PRs out of order, alter historical lecture
materials or three original dirty PC worktrees.
