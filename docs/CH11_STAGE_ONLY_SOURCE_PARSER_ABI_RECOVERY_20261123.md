# Chapter 11 unreleased narrated-video stage source parser ABI recovery

23 November 2026, MicroGen_AI_Web, Dell-115. The verified test case uses
original Serway Chapter 11 sections 11.1, 11.3 and 11.5, not Serway 8.2 G3.

## Root cause and previously resolved remedy

A pre-existing original Chapter 11 technical video chain checked its source
with the *published-lecture* `slide_narration_sync.verify` guard, which
accepts no more than 10% changed derived text hashes and requires a
`.microgen_completion.json` fully completed receipt. The video-only chain
was deliberately **never** granted full completion, student publication or
source-grounded animated highlights. It holds a stage-only receipt instead.

The actual failure was reproduced on the unmodified upstream baseline, and
did not come from the journal/G3 patches. The exact byte identities of
`source.pdf`, `slides.pdf`, `script.txt`, all numbered WAVs and
`slide_narration_sync.json` match immutable QA/preview receipts; only
PyMuPDF-derived `page.get_text()` SHA lists differ:
- §11.1: pages 3–15, 13 of 15.
- §11.3: pages 2,3,4,6,14,15, 6 of 15.
- §11.5: pages 3,4,5,6,7,9, 6 of 10.

The existing published source/text ABI recovery correctly does NOT approve
this pattern because its 10% cap was exceeded and the full lecture completion
receipt does not exist. Broadening it would be an academic and publication
safety regression.

## Integrated correction

`selenium_pipeline.ch11_stage_only_pdf_text_parity_v1` is an **independent,
review-only, narrowly scoped original-source** recovery handler. Both its
cross-PC handler and normal executable recovery registry signatures must be
enabled. Only the original no-highlight
`narrated_video_chain._technical_input_proof` invokes it, and only when the
original strict sync verifier rejects evidence.

The new helper independently:
1. Recomputes the original page count, source PDF, authored PDF, numbered
   WAV, original narrator-script and narration SHA identities, and requires
   that every stored structural-sync property **except the derived
   `page_text_sha256` list** matches exactly.
2. Requires the original `slide_narration_sync.json` and its precise SHA
   in the independent preview manifest; validates source.pdf, slides.pdf,
   script.txt, audio QA summary and each numbered WAV SHA against the
   original unmodified video preview manifest.
3. Requires the original stage-only receipt and preview manifest explicitly
   affirm *not published*, *no highlights verified*, *no full G3 release*,
   and requires that **no** `.microgen_completion.json` exists.
4. Allows derived text SHA differences only for this stage-only technical
   preview, even when more than 10% of pages differ. The global lecture
   `slide_narration_sync.verify` remains unchanged and STRICT.
5. Returns the original byte-pinned, source-grounded structural-sync data to
   the existing no-highlight technical preview/media validation. It never
   writes any source, PDF, script, WAV, MP4, model or release receipt.

Any mutated PDF, script, WAV, source identity, published/QA flag, sync
receipt, slide count, original preview manifest or stage-only gate fails
closed. Scientific/audio/visual QA still need their full distinct original
acceptance. Neither the helper nor its registered recovery authorizes a
Gemini model Send, paid TTS, or student publication.

## Real-case proof

Dell-115 verified all three original sections and all original input
bytes. Its source-grounded original technical preview test passed after
repair, and the full original published-lecture validator still rejects all
three in its own scope. Original files and Drive data were not modified.

Regression and injected fault tests check source and QA mutations, WAV
tampering, forged full-completion and highlighted video claims, altered
narration, and no-drift dispatch. The repair is part of the executable
recovery registry, not a one-off manual artifact edit.

## Distinct unresolved work

This stage-only correction does not close independent G2 or G3 science,
audio, source-grounded highlighted MP4 or release acceptance. G3 still has
two genuinely uncertain original Selenium browser Sends; those require
historical attribution, never unguarded replay.
