# Automatic figure reflow triage integrated into source-to-slide acceptance

20 October 2026; Dell-115 only. Stacked PR170 on corrected PR169
commit `5491175d4b35ebead557a3410be8727ab49dc804`.

The independent source figure / slide audit now checks for exactly
one substantial displayed slide bitmap, then invokes the optional
3-graph layout detector only when an original pre-caption figure
geometry candidate is present. Crucial recursion guard:
`figure_slide_raster_visibility` invokes the parent
`assess_real_source_slide_figure(automatic_layout_review=False)`
so the nested pixel audit does not repeatedly invoke itself.

For the original Thomas Calculus 8.4 source page 2 Figure 8.3
and slide 5, the automatic triage locates the three original
vertically stacked blue/pink-graph shapes versus three horizontally
placed slide shapes. It returns
`THREE_GRAPH_REFLOW_DETECTED_SEMANTIC_REVIEW_PENDING`.
The **previous single whole-crop aspect mismatch is
automatically reclassified as an EXPECTED LAYOUT CHANGE**
rather than a missing entire graph. Neither original PDF nor
slide/media is overwritten.

The joint figure+original encoded video acceptance gate is
now wired to use this diagnostic. For real 8.4 the gate reports:
- `UNVERIFIED_MATH_AXES_LABELS_AND_WHOLE_FIGURE_CONTENT`
  instead of the old undifferentiated source-versus-slide
  geometry blocker
- `SOURCE_CAPTION_OVERLAPS_UNRELATED_PROSE`
- `MEASURED_ENCODED_VIDEO_AT_OR_ABOVE_600_SECONDS`
  (existing slides.mp4 approximately 633.93 sec)
- `UNVERIFIED_SPEECH_TIMED_MULTIPART_HIGHLIGHTS`

Other source figures may contain one graph, four panels, no
colored traces, gray strokes, rotated/overlaid components, altered
aspect, image-embedded original art or other layouts; **no
automatic semantic approval** is claimed for them. The optional
detector may be unavailable on systems without OpenCV; its
failure returns an explicit review-required status rather than
silently treating a missing figure as correct.

Only safe automatic 'rectification' implemented: correct the
**false detection/QA interpretation** of a legitimate
three-graph vertical-to-horizontal arrangement. For a
genuinely missing/wrong/unmatched figure, create a source-bound
review/repair candidate using existing figure recovery tools;
do not edit originals, substitute a guessed crop or promote
media. Mathematical axes/labels, complete original figure
provenance, element-level spoken highlights, encoded per-part
duration strictly below 600 seconds, and academic/listening
review remain independent mandatory acceptance gates.

PR169 CI issue was due to `cv2` missing in GitHub Windows
and Ubuntu runners, and has been fixed with the optional
`opencv-python-headless` full-suite dependency. PR169 exact
new head `5491175d4b35ebead557a3410be8727ab49dc804`
passed GitHub CI. Separate new automatic QA integration
code and tests here are stacked on that fixed head.

All source, slide, WAV and MP4 hashes preserved; no original
G: lecture folder, older dirty clone, HP, Yoga6, Zenbook,
paid TTS, Whisper/ASR, GCS distributed lease, protected main,
student publication or academic sign-off performed.
Flash-Lite/Kore default, voice-consistent approved fallback
after three genuine failures is unchanged.
