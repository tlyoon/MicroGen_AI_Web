# PR163 — original source vector objects outside matched visual regions

20 October 2026; Dell-115 only, isolated checkout stacked
on PR162 exact head ed1591bff62f9a5332485dd9e98adce6e3dda286.
Read-only original source vector proximity auditor examines
source PDF drawing-object bounding boxes against the
independently measured PR161 matched-keypoint source extents.
It allows a small, bounded 8-point observation margin.
A source object near a group does NOT prove its rendered
pixels actually occur in the slide; missing correspondence
does NOT prove an object was omitted from the bitmap.
Rejects duplicate indices, invalid extents, nonfinite
input and excessive padding. Retains real PDF zero-area
horizontal/vertical vector strokes by using a tiny
observation-width enlargement for intersection.

Real original Thomas Calculus 8.4 source.pdf page 2
Figure 8.3 (23 pre-caption vector objects):
- 13 nearby exactly one measured transform group;
- 2 geometrically near more than one transform group;
- 8 outside all measured correspondences.
The 8 are **source drawing objects lacking nearby visual
feature evidence**, NOT certified missing figure strokes.
They could belong to other page material, or be included
in visually feature-poor graph regions.
No original complete author figure or panel/axis/curve/label
classification is inferred. Original textbook/slide hashes,
historical scripts/WAV/MP4, dirty G: trees unchanged.
Legacy slides.mp4 at 633.93s remains noncompliant.
No student publication or academic/audio approval. CLI exit 2.

Only Dell-115; old independent uncommitted work preserved.
No HP/Yoga6/Zenbook, paid TTS, Whisper/ASR, GCS lease,
protected main or Moodle/YouTube publishing. Actual
element-highlight sync, strict MP4 parts <600s,
default Flash-Lite/Kore with 3 true failures prior
to homogeneous approved voice fallback remain mandatory.
