# PR160 — automatic local source-vector to visible slide-raster correspondences

20 October 2026; only Dell-115, fresh isolated checkout stacked directly
on draft PR159 exact head `6a04ef71740ba74b407914c53bb9fbdf0cc59049`.
No changes to original source, lecture slide PDF, WAV or MP4,
any shared dirty G: repository or other isolated checkout.

The new *read-only, optional* `figure_local_feature_correspondence`
audit combines pre-existing original FIGURE heading / source corridor
and visibly rendered slide-bitmap checks, then uses local ORB
image features, nearest-neighbor descriptor ratio screening, and
separate RANSAC similarity-transform fits in **FOUR ARBITRARY
EQUAL-WIDTH SCAN BINS** on the displayed slide bitmap.
These bins are **NOT** intended panel divisions; splitting one
original panel into two bins is possible and observed.
For each bin, the report supplies descriptor match count,
geometric RANSAC inliers, source PDF keypoint extent,
slide-bitmap pixel keypoint extent and observed affine fit
when sufficient inlier coverage exists.
All geometry refers to **matched keypoints only**, not the
original author-intended full figure boundary or crop.
Repeated text and visual motifs can create false matches;
this is reproducible geometric candidate evidence only.
The optional cv2/numpy library import fails closed when not
installed, without triggering paid/remote services.
Every positive or negative result returns CLI exit 2 and all
scientific/semantic/narration/video/publication approval fields false.

## Real original Thomas Calculus 8.4, source page 2 / slide page 5

At read-only resolution 3x original source pre-caption left corridor
and actual slide embedded bitmap xref 136 (744x173):
- Original source grayscale ORB features: 1,999
- Slide bitmap grayscale ORB features: 733
- Tentative descriptor-ratio correspondences: 202
- Four arbitrary slide x-scan bins fit local transforms with
  **58, 18, 31 and 20 geometric RANSAC inliers**, respectively.
- Estimated source-render-to-slide scale in coherent scan bins
  is approximately 0.50; fitted translations differ by region,
  consistent with source artwork having been repositioned.
- Candidate matched **keypoint** source extents (PDF coordinates):
  bin 0: [51.840,92.897,118.245,161.050];
  bin 1: [75.247,202.383,102.021,249.628];
  bin 2: [105.339,199.757,154.276,251.818];
  bin 3: [90.774,320.717,152.285,348.365].
  In particular, bins 1 and 2 have overlapping original y-ranges
  and do not imply two independent original source panels.
- Source SHA256:
  `b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`
- Slides SHA256:
  `f6219ee18be4e347132d59be0d55e19765f325efed0b9d3d6544959a6dda68d1`
  Original hashes and source/slide files unchanged.

This is substantial independent evidence of source-page visual
material matching portions of the visible slide bitmap. It is
**not proof** that every Figure 8.3 original curve/axis/label
is present; source full-graph geometry, author-intended panel
labels and complete slide coverage remain unverified.
PR155 independently measured legacy Thomas 8.4 MP4 at 633.93s,
which fails the strict <600s rule; verified multipart highlighted
replacement still missing. No MP4/slide/TTS generated or promoted.

Generated-PDF adversarial testing exercises deliberately reflowed
multiple *vector-drawn* source regions, unrelated random bitmap,
single included panel, video/figure-approval flags, overlay and
wrong original figure heading. Tests must not infer scientific
meaning from geometric matching.

Contract: strictly <600s per encoded video part, genuinely
synchronized spoken-element slide highlights, Flash-Lite/Kore
primary with approved homogeneous fallback after three
genuine TTS failures, no Whisper/ASR, GCS distributed lease,
HP/Yoga6/Zenbook, unverified Moodle/YouTube/student publication,
or protected-main edits. Human academic/listening QA remains separate.
