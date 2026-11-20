# Source-to-rendered-slide figure verification (main integration v1)

## Implementation
This is a selective port of the tested PR564 source-caption chain onto PR565's
already-merged main. Unrelated stacked G2/supervisor changes were not copied.

1. Inventory printed original Figure captions, excluding prose-only mentions.
2. Render all source vector and raster figures from PDF at 3x, verify source SHA,
   crop pixels, panel letters and edge clipping. Persist isolated candidate
   evidence and the source_figure_chain_v1.json ledger.
3. An executable figure_recovery_registry_v1.json entry enforces at most two
   source-only attempts, no new provider send, source integrity, safe promotion
   and a fail-closed disabled/tampered registry.
4. Normal slide generation requires literal unguarded includegraphics for every
   printed captioned figure and rejects missing figures early.
5. runner.valid(figures) verifies the full source crop set; runner.valid(slides)
   checks source PNGs, explicit LaTeX references, matching PDF image XObject RGB
   pixels AND the actual final-page raster at 2x (including 4x4 content tiles).
6. Graphics manifest, stage output copying and cleanup enforce the same chain.
   Cached stages revalidate before reuse. The published figure ledger is retained.
7. Missing, altered, covered, clipped or too-small figures fail closed rather
   than permitting narration or MP4 acceptance.

## Dell-115 real test, 20 November 2026
- Input source: G:\My Drive\Serway\Serway_8_14\8\8.2\source.pdf.
- Verified isolated source crops:
  %LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\PR563_SOURCE_FIGURE_CANDIDATES_FULLPANELS_20261120.
- Tested isolated compiled 20-page PDF:
  %LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\PR564_8_2_BEAMER_CANDIDATE_20261120.
- Staged read-only test copy:
  %LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\PR566_8_2_VALIDATION_20261120.
- Figures 8.2-8.6, 5 of 5, with nine lettered panels passed source crop,
  unguarded LaTeX and rasterized PDF visibility checks.
- An independent opaque rectangle covering much of Figure 8.6 was injected
  into a SEPARATE copy; normal runner.valid(slides) rejected it. A missing
  source-figure reference also failed. The original candidate passed.
- 49 existing source-figure and retroactive repair regression tests passed;
  five new main-integration tests also passed. No provider sends, source
  changes or scheduler restart.

## Limits and release gates
Pixel provenance and gross rendered-page appearance do not prove source
scientific meaning, all small-text legibility, audio synchronization, G2/G3
independent acceptance or permission to publish lectures to students.
These remain separate, mandatory gates. Known or uncertain PDFs fail closed.

Integrate and deploy only via verified branch, CI and authorized workstation.
No intentional Task Scheduler changes are part of this modification.
