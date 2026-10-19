# Source vector figure and labelled panel candidate (PR #143)

Date: 19 October 2026. Stacked on draft PR #142.

## Verification boundaries

The new read-only `selenium_pipeline.figure_vector_provenance.inspect_vector_figure_region`
accepts explicitly declared source and slide PDF pages, figure rectangles,
per-panel source rectangles, a numbered source caption, and 2–6 ordered
(a)/(b)/(c) identifiers.

It checks lexical symlink/junction safety, original SHA integrity, single
caption block on each page, exact source/slide figure aspect ratio, source
raster exclusion, presence of original vector paths, full contiguous
horizontal/vertical panel tiling and unique extractable original PDF
(a)/(b)/(c) labels inside their declared panel rectangles. Each vector path,
including zero-height lines, must lie wholly within exactly one panel.
It compares actual source-vector and slide-raster visible RGB pixels at
one explicitly bounded render resolution and rejects text/vector overlays.

The resulting evidence is strictly a technical candidate. A subtly shifted
panel boundary crossing neither a path nor label might still be wrong;
the declared figure crop could omit other author-intended content; and
equal rendered pixels do not validate physics semantics.

The following fields therefore always remain FALSE:
author_intended_crop_certified,
true_panel_boundary_semantics_certified,
figure_panel_completeness_certified,
figure_semantics_certified,
tts_or_video_authorized,
human_review_claimed.

No existing automatic narration is enabled for vector figure candidates.
No paid TTS, original textbook/lecture artifact modifications, public
publication or protected-main merges are part of this PR.

## Tests

The adversarial actual-PDF tests cover exact source-vector -> slide-raster
rendering, missing/duplicate/misordered original lettered labels, changed
caption, false crop/boundary confidence, vector paths crossing seams,
source-raster contamination, slide vector/text overlays and symlink handling.

Next PR should independently constrain *real* full-panel boundaries and
figure-label semantics against the textbook source. Another stacked draft
should conduct a nondestructive, source-verified actual-textbook pilot and
end-to-end technical QA. Never equate these preflights to academic approval.
