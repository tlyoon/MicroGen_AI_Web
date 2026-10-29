# Non-destructive real-textbook figure pilot and technical acceptance boundary

Date: 19 October 2026. Stacked on PR #144.

## Implemented

The new python -m selenium_pipeline.figure_textbook_pilot interface
performs a read-only bounded audit of specified original textbook and
lecture-slide PDF pages. It records exact SHA-256 before/after, page
counts, original source vector/raster image counts, slide figure media,
the requested figure identifier's extractable PDF text appearances and
candidate original source panel-label tokens.

Without independent explicit source-space and slide-space figure
rectangles, all panel boxes, a source-verified figure caption and panel
label mapping, the result is
PILOT_BLOCKED_MISSING_INDEPENDENT_FIGURE_GEOMETRY. It does not guess.

If an explicit source mapping is supplied, the full strict PR143/144
vector-source and gutter pipeline is replayed. A negative proof returns
PILOT_BLOCKED_SOURCE_PANEL_PROOF. A geometrically positive result is
PILOT_TECHNICAL_CANDIDATE_SEMANTIC_QA_BLOCKED: this still does not
certify original author-intended complete subpanels, scientific
semantics, valid synchronized figure narration, or student publishing.

## Actual read-only Thomas Calculus 8.4 pilot

Inputs inspected locally on authorized HP only:
G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4\source.pdf
G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4\slides.pdf

Parameters: figure_id 8.3; original PDF page 2; lecture slide page 5.

Observed original: 6 source PDF pages, 44 vector drawing paths and
zero embedded raster images on page 2; two Figure 8.3 text matches
across extracted source-page blocks; zero (a)/(b)/(c) tokens extracted.
Observed lecture: 17-slide PDF, slide 5 has four raster objects and
22 vector drawing paths, with zero Figure 8.3 extractable caption
block matches.

Exact source SHA-256:
b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068

Exact slides SHA-256:
f6219ee18be4e347132d59be0d55e19765f325efed0b9d3d6544959a6dda68d1

The pilot returned PILOT_BLOCKED_MISSING_INDEPENDENT_FIGURE_GEOMETRY
with figure_region_mapping_verified=false,
figure_panel_completeness_certified=false,
scientific_semantics_certified=false,
tts_or_video_authorized=false,
student_publication_authorized=false.

## Consequences and next task

The original source uses vector drawings rather than one embedded PNG.
Its figure labels could be part of non-extractable text/paths/graphics.
Slide 5 has multiple image objects but no unambiguous extractable
matching Figure 8.3 caption block. Exact source to slide figure and
full (a)/(b)/(c) panel geometry is therefore NOT independently
established. It would be incorrect to claim a figure-synchronized
lecture video is technically accepted from this evidence.

Next: independently identify and audit the complete source PDF figure
region(s), full original panel label shapes/positions, and map only
the exact corresponding rendered slide elements. Use a real-textbook
source-grounded pilot with no guessed semantic labels, not arbitrary
pixel-grid partitions. Keep automatic paid TTS/video publication blocked
for unsupported slides while advancing other proven stages.

All original textbook PDF/slide/script/WAV/MP4 remain untouched.
No Whisper, Zenbook, GCS lease, publication to Moodle or YouTube,
protected-main merge, or live Gemini/Cloud TTS was executed.
