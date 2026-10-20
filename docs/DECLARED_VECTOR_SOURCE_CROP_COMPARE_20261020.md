# PR158 — bounded declared source-crop pixel comparison

20 Oct 2026, Dell-115 isolated new checkout, stacked on PR157 exact
HEAD `3bad1a505a7afc45ec8612f12db35cdf898e0c01`.
`figure_declared_crop_slide_comparison.py` checks an *explicit,
untrusted* four-coordinate source-PDF crop hypothesis. It requires
the candidate rectangle be within the original textbook page and
above the independently located FIGURE caption heading; verifies
the single material slide bitmap itself is visible (PR156), checks
source region vs slide encoded bitmap aspect, then, only for plausible
aspect, uses a bounded PyMuPDF rendering grid to compare exact RGB
bytes. The outcome is **hypothesis testing only**. Any matching
rect may be deliberately selected from the wrong textbook figure,
may omit unseen panels, labels or source semantic context. Even
a byte-perfect match NEVER certifies original author-selected complete
figure or allows slide highlighting, MP4 promotion or publication.
CLI always exits 2 for review.

Real Thomas Calculus 8.4 source page 2 Figure 8.3:
a hypothetical coarse pre-caption source region [30,85,180,381]
has width:height ratio 0.506757; actual slide page 5 material
744x173 bitmap ratio 4.300578. Direct whole-region unmodified
copy is geometrically inconsistent; reflow or a different subset
remains possible. This bbox is **not verified original source figure
geometry** and no source-panel-to-slide mapping was asserted.
Original source SHA256 b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068
and slides SHA256 f6219ee18be4e347132d59be0d55e19765f325efed0b9d3d6544959a6dda68d1
preserved. Strict encoded video length <600 s, audio synchronized
highlighting, Flash-Lite/Kore primary with approved 3-real-failure
homogeneous fallback, academic listening QA distinct.
No original teaching assets or G: repo changes; no other PCs,
uncommitted historical checkout changes, Whisper/ASR/GCS lease,
paid calls or publication.
