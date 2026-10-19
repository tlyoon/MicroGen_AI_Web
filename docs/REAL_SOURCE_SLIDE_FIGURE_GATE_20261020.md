# PR154 actual source-to-slide figure acceptance blocker

20 Oct 2026; Dell-115 only; stacked on PR153 exact
`7ebda8d20427bbc1ba30e1f389820379b6f08bc6`.

New read-only `figure_real_source_slide_gate` independently
runs the PR152 source caption collision and PR153 pre-caption
vector inventory, then inspects an original slide PDF page. It
records immutable SHA256 identities, source collision indicators,
candidate ungrouped source drawing-object count, slide exact
Figure N.N text matches, embedded raster count and slide PDF
drawing count. It **never** declares complete source figure
boundaries, author-intended panels, semantic mapping, source-to-slide
equivalence, narration alignment, video duration or publication
readiness. CLI always exits **2 for blocked evidence** so automation
cannot confuse a successful PDF read with technical acceptance.

## Real Thomas Calculus 8.4 / Figure 8.3, read-only Dell-115

- Original source `source.pdf` page 2 SHA256
  `b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`.
- Original `slides.pdf` page 5 SHA256
  `f6219ee18be4e347132d59be0d55e19765f325efed0b9d3d6544959a6dda68d1`.
- Original Figure heading `FIGURE 8.3`; eight lines of adjacent
  substitution instruction text share PDF caption text block.
- Source pre-caption left corridor has 23 individual, **unassigned**
  PDF drawing objects. The false previously selected source vector
  path #37 is not part of that pre-caption inventory.
- Slide page 5 has zero extractable exact Figure 8.3 caption
  text matches, one embedded raster image reference, 22 PDF vector
  drawing paths. These are object counts, not original figure
  equivalence evidence.
- Return `REAL_SOURCE_SLIDE_FIGURE_EVIDENCE_BLOCKED` and CLI exit
  `2`, all production and human academic approval flags false.

For production, original-source complete graphics/panel identity,
source-to-slide figure correspondence, timed audible highlights and
strict encoded <600s multipart video must be independently proven.
Old source/slides/scripts/WAV/MP4 and shared G: worktrees
were untouched; no paid Gemini calls, publication, protected
main merge or HP/Yoga6/Zenbook use. Approved Flash-Lite/Kore,
three genuine failures before homogeneous-voice fallback,
no Whisper/ASR/GCS external lease remains the owner contract.
