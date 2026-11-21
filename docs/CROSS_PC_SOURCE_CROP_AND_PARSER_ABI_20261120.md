# Source-bound cross-PC crop and PDF text extraction recovery (v1)

## Trigger and historical failure record

On 20 Nov 2026, HP published a v3 repaired Serway section 8.2 with five
printed source figures (8.2–8.6), nine lettered panels, 15-slide PDF,
15 reused QA-accepted WAVs and 2 MP4 parts. Its source PDF is unchanged
at SHA-256
f72422b7113d11a7adfe55c0fc9e7a85b2470bda84cd32b0add5f847f8f52fd1.

When a separately installed Dell-115 PyMuPDF/MuPDF version independently
checked the *same Google Drive files*, source_figure_chain_v1
SHA matched each PNG but freshly rendering source.pdf did NOT produce the
same PNG bytes. Exact raster comparisons showed at most 22 channel values
difference, at most ~1% changed content pixels, no grayscale difference
above 20, and no lost figure panels. The existing deterministic SHA gate
incorrectly rejected all figures based on renderer-dependent antialiasing.

Further, the HP-saved slide_narration_sync.json and Dell's live
slide_narration_sync.inspect() compared unequal on only **slide 9 page-text
digest**. Every *asset byte* SHA (original source, slide PDF, narration
script, 15 WAVs), page count, narration block identity and the saved
structural receipt SHA still matched. The completed_lecture gate returned
False solely due to parser version-specific extracted text.

## Production recovery mechanisms

1. The normal verified original PNG remains bound to the SHA-256 in
   source_figure_chain_v1.json. Original PDF source SHA, caption count and
   identity, crop bbox, panel letters, and source object/witness checks
   remain unchanged and mandatory.
2. If a fresh re-rendered crop has different PNG SHA, the executor invokes
   **registered** SOURCE_CROP_PIXELS_DIFFER_ACROSS_RENDERERS.
   Reconstructed and ledger PNGs must be valid color PNGs, equal dimensions,
   correct PNG IEND at the exact file end and valid CRCs. Byte-appending
   after PNG IEND and changed critical chunks fail closed.
3. Source pixel drift is accepted only within strict measured bounds:
   max RGB channel difference 24/255; luminance difference never above 20,
   changed fraction above grey 1 <=0.018, above grey 5 <=0.006, and
   the worst 4x4 tile fraction above grey 5 <=0.018. Changed source labels,
   significant overlays or missing panels fail tests and block pipeline.
4. The existing slide source-to-PDF image-object pixel provenance and
   final-page raster visibility checks are still required. No approval
   passes from crop parity alone.
5. If a saved slide/narration receipt differs ONLY in derived
   page_text_sha256 hashes, the normal slide_narration_sync.verify() invokes
   registered PUBLISHED_PDF_TEXT_HASH_DIFFERS_ACROSS_RENDERERS.
   It accepts only schema v1, matching PDF/script/WAV bytes and narration
   blocks, exactly matching page count, at most 10% or one changed
   page-text hash, and a real .microgen_completion.json whose source,
   final PDF/script and structural sync SHA match saved actual files.
   It returns the original approved structure without rewriting it.
6. The exact allowlisted cross_pc_artifact_recovery_registry_v1.json
   permits **zero model Sends, zero source/media publication edits, and
   zero student release approvals**. Unknown/disabled/modified mechanisms
   fail closed. The helper is not a Gemini retry mechanism.

## Actual Dell-115 verification

- Before repair: 8.2 source crop verifier rejected Figure 8.2 even though
  HP verified the same source SHA. PDF screenshot and source panel identity
  were intact.
- After bounded parity recovery: 5/5 figures, 9/9 lettered panels,
  visible slide positions 3,6,8,10,12, and normal runner.valid(slides)
  passed on Dell, with all real GDrive source/media files unchanged.
- Before slide-text ABI repair: slide_narration_sync differed on page 9
  only; original PDF/script/WAV hashes all matched.
- After source-locked parser parity: verify(8.2) and
  completed_lecture(8.2/source.pdf) accepted on Dell with **no receipt
  modification**, no new Gemini requests, and no media regeneration.
- Fault tests cover appended PNG data, altered label/overlay,
  unsupported schema, changed source, changed PDF/script/WAV,
  changed original completion receipt, too many changed text pages,
  disabled/foreign recovery handler, source crop geometry mismatch.

## Deployment/release boundaries

- CI on exact PR head and full modern main regression suite are required
  before merging. Do not revise the already published 8.2 files or change
  the older dirty main checkout.
- This is a version ABI/data-integrity repair. It does not independently
  approve source science, acoustic meaning, G2/G3 or student release.
- The original Dell Windows source-only and status monitor scheduled tasks
  remain intentionally disabled. No persistent autonomous code-development
  executor was verified or started.
