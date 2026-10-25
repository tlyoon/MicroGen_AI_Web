# PR298 — Original Figure 8.2 source printed side-label positions

25 October 2026, Asia/Kuala_Lumpur. Isolated Dell-115 draft stacked on CI-green PR297 head 44165854cb7f08d2ea8e7e2ec77d9e6bc8ddaea2.

## Real original textbook observations

Original Thomas Calculus 8.4 textbook physical page 1 Figure 8.2 has three source-right-angle triangles geometrically proved in PR297, whose actual source drawing is visually registered to Slide4 embedded bitmap by PR296. Vector paths and figure images alone do not confirm printed side-label positions.

The real original PDF word boxes show:
- Tangent panel (x=a tan u): base a, vertical edge x, diagonal-label square-term fragments a2 + x2.
- Sine panel (x=a sin u): diagonal a, vertical x, base-label square-term fragments a2 - x2.
- Secant panel (x=a sec u): diagonal x, base a, vertical-label square-term fragments x2 - a2.

All nine printed side-position candidates were observed beside their original vector edges, with exact per-word physical PDF bounding boxes returned by the CLI. Original source SHA b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068; source/slides/script unchanged.

## Permanent hardening

New source-bound original_figure82_side_word_positions CLI requires the same immutable textbook/slide/script hashes, all 3 original closed vector triangles and independently verified source-to-slide pixel similarity. It locates printed words in edge-relative geometric regions, normalizes square/minus character fragments, and sorts by physical PDF word x-position rather than relying on misleading PDF extraction text order. It requires adjacent word boxes and expected per-side fragment sequences, rejecting missing, duplicated, altered, displaced or disconnected printed labels.

Importantly, the source PDF does not reliably encode the original square-root glyph: text extraction sometimes represents it as a stray quotation mark. The auditor therefore reports square-term/sign FRAGMENTS, not verified full radical operators, academic source math, Pythagorean derivation, independently approved side meaning, audio synchronization or release.

## Validation and limits

Dell-115 focused and neighboring suites exercise real immutable original material and synthetic reordered, corrupted and displaced word boxes. The actual original Figure8.2 run passes all nine edge-relative physical label-position candidates. Dell-115 local pytest command (new side-word cases plus original triangle vector topology and actual pixel registration) completed with **27 passed, 0 failed** and 5 pre-existing SWIG deprecation warnings. The valid original-source case was included, not merely mocked.

The true two-pass original AI source agreement is still 1/71 section title only, 70 pending/disputed, 0 independently agreed substantive mathematics. No new Gemini review request, paid API, protected original teaching files, historical WAV/MP4 edits, or student publication.
