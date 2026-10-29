# PR172 — generalized multi-graph color/black-ink reflow (2–6)

Source-row / slide-column connected ink segmentation now accepts
two to six independently separable corresponding textbook graphs
instead of only exactly three. The blue-curve and red-asymptote
shape comparisons and the stricter independent black axis/label
ink geometry guard are all mandatory for every candidate graph.
Different counts, missing visual segments, and more than six
regions fail closed. Every auto match remains a layout-only
observation and does NOT certify author-original axes/labels,
graph semantics or narration highlights.

Adversarial synthetic tests use distinct graph shapes for
2, 3, 4, 5, and 6 vertically-stacked source vs horizontal
slide cases; seven is intentionally outside the bounded
supported range. 4-part fabricated source receipt must
contain four verified panel entries; otherwise fails closed.
Thomas original 8.4 Figure 8.3 still recognized as three.

Dell-115 ONLY; parent PR171 exact commit
`5a47dd7353b4f9b8b13c5d12b817f64e6a2f7838`.
This expansion does NOT guarantee arbitrary layouts,
grayscale drawings, overlapping plot panels, insets or
OCR/math characters. For those, retain source-bound review.
All G: source/slide/WAV/MP4 unchanged, dirty tree and
other-PC restrictions observed. Strict video parts <600 s,
real spoken-element highlight synchronization, academic
listening QA and approved TTS fallbacks unchanged.
