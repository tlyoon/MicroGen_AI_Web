# PR159 — multi-crop original vector → slide raster tile comparison

20 Oct 2026, Dell-115 only, new isolated checkout
`20261020_pr159_declared_panel_reflow_1000`; parent PR158
HEAD `c5fe0a397809bfdec987baf54a9a63ef72802ceb`.

`figure_declared_panel_reflow.audit_declared_panel_reflow`
checks **two to twelve explicitly declared** candidate original
textbook vector crop rectangles against specified pixel tile
rectangles in the ONE independently visibly verified slide
material bitmap. Checks independent original source caption heading,
source+slide exact SHA-256, PDF crop containment above heading,
image pixel bounds and no overlapping source/tile selections,
bounded render geometry, RGB reference and pixel exact equality.
Each tile is independently rendered from original textbook page
at the declared target bitmap resolution; rows of original
decoded slide RGB pixels are independently compared. No original
PDF, slide or media is rewritten.

The test fixture deliberately arranges two separate source graph
areas vertically on a textbook page and combines those into
two horizontal slide bitmap tiles, demonstrating that a whole-source
aspect mismatch need not rule out a valid *reflowed raster
hypothesis*. Adversarial tests reject tampered tile content,
missing panel, overlays, overlapping/malformed crop declarations,
source rectangles below heading and single-tile declarations.

**Crucial source-of-truth limit:** caller-supplied source/tile
rectangles are NOT independent author-proven source figures,
panels or label mapping; matching all tiles is only RGB equality
at a declared sampling scale. It cannot prove the selected panels
are the author's entire intended Figure 8.3, that ordering and
semantic labels are mathematically correct, or that every slide
pixel is covered. Therefore every semantic panel, source-to-slide
scientific, narrated-highlight, strict encoded <600s MP4, listening
and publication authorization remains false; CLI exit 2.
The actual Thomas Calculus 8.4 original FIGURE 8.3 panel boxes
and slide tile mapping remain UNDETERMINED and are not invented
in this real-source pilot. PR157 found no extractable standalone
pre-caption (a)-(f) labels; PR158 whole-region aspect mismatch
alone is not enough to reject separate panel reflow. Further
independent figure evidence is needed before mapping any real
textbook panel and advancing video work.

Original Thomas source/slides/script/WAV/MP4 and three dirty G:
worktrees untouched. Older uncommitted raster-visibility checkout
preserved. No other PC, paid TTS, unauthorized publication,
Whisper/ASR or GCS external lease. Owner contract: subtopic
MP4 parts strictly below 600s, spoken-element highlighted
visuals, Flash-Lite/Kore primary and approved homogeneous fallback
after 3 actual failures; academic/listening QA independent.
