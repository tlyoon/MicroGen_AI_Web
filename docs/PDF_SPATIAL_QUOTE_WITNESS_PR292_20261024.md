# PR292 - Prevent source quotation evidence fabricated by PDF column merging

24 October 2026, Dell-115 only. Isolated draft stacked on CI-green PR291 a987d3f863bc1125216e46dff7a9d4b3d5862c4b.

## Reproduced defect

The normal original textbook quote validator previously searched collapsed `page.get_text(sort=True)` output. PyMuPDF can combine distant PDF text into one extracted line or block. A synthetic PDF printed `The derivative is` at x=40 and `equal to cosine` at x=300, both at y=90. Old validator incorrectly ACCEPTED `The derivative is equal to cosine` as one exact page quote. Original source text never appeared visually as one continuous sentence. Ordinary get_text('blocks') likewise merged the distant components, so block membership alone is not sufficient.

## Integrated fail-closed correction

Added bounded `selenium_pipeline.quote_spatial_continuity` and called it in the normal `pdf_text_source_span_witness.prove_source_quote_occurrence` path. After the existing exact text match, the validator checks that the matching words occur in the actual geometric order and are adjacent on the same line or a nearby next line within one block, without a large horizontal jump into a different column. Physical token occurrence counts must match text occurrence counts; duplicate source quotes retain explicit index selection. Existing original source hash, physical PDF page and nonpublication checks remain in force. Unsupported/exotic extracted layout fails closed rather than fabricating source mathematical agreement.

## Verification

Dell-115 focused tests: 18 passed, no failures, with existing third-party SWIG deprecation warnings. The synthetic distant-column quote is now REJECTED, while a genuine contiguous quotation and ordinary wrapped paragraph remain accepted. Duplicate identical quotes require an explicit occurrence index. A genuine `8.4 Trigonometric Substitutions` quote from original textbook PDF page 1 remains accepted.

This strengthens attribution, not proof of source mathematical semantics, independent scholarly consensus, correct original diagram panels, element synchronization, actual Kore voice or publication. No original teaching files, historical WAV/MP4 or review receipts were changed. No Gemini request, paid API call or protected main merge occurred. GitHub Actions CI must be verified after the draft PR is opened.
