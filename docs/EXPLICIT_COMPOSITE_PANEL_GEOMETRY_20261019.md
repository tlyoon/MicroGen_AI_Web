# Explicit composite raster panel geometry — technical candidate

19 October 2026, stacked on draft PR #141.

## Scope

The source figure's exact embedded image identity (PR #140) and independent
unobstructed rendered visibility (PR #141) are first required. This stage
accepts an explicit horizontal or vertical partition in NATIVE integer pixels,
such as [0,300,600,900] for a 900px wide figure with three panels.

The verifier maps each declared segment to both the original textbook PDF
and slide PDF coordinates; checks full source-image pixel coverage, no gaps,
overlaps, duplicate/blank sections or tiny regions; independently compares
RGB decoded source/slide pixel bytes and emits per-region SHA-256 digests.
It reads files only and does not alter lecture content.

## Crucial limitation

A pixel-perfect geometric partition may still split a real subpanel in
half, or misassociate panel (a) with figure (b). A four-way split of a true
three-panel figure can pass pixel-coverage tests. No parser currently proves
the original scientific labels from bitmap content. This checker therefore
ALWAYS returns figure_panel_completeness_certified=false,
figure_semantics_certified=false,
declared_panel_labels_source_verified=false,
tts_or_video_authorized=false, and human_review_claimed=false.
It is NOT integrated with production automatic figure narration.

Allowed partitions: horizontal or vertical contiguous native-pixel
strips (2–6), explicit declared identifiers a through f, min sizes.
Irregular two-dimensional grids, rotated images, semantic source labels,
or panel caption associations are not inferred.

Tests cover real generated PDFs with visibly distinct three-panel artwork,
horizontal and vertical mappings, missing first/last edge, gaps, overlap,
bad identifiers, booleans/floats, blank panels, and changed pixels.
No paid Gemini/TTS, YouTube, Moodle, production asset changes.

## Next

Develop independent verification of actual pixel-space (a)/(b)/(c)
labels and complete source panel boundaries, with a read-only pilot on
real textbook figures. Never infer scientific review from geometry alone.
Preserve all original PC Drive working trees, sub-600 second encoded videos,
and the agreed Flash-Lite/Kore default TTS policy.
