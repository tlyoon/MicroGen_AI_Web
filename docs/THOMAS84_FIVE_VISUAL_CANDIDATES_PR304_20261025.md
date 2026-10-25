# PR304 — Five real original Slide-4 visual review candidates

Windows-only, Dell-115 isolated draft stacked on CI-green PR303 exact head `72c34b59153df2c65dc7adfac5b156739baac057`.

## Real source observation

Original Thomas Calculus 8.4 Slide 4 contains FIVE original source-bound narration units. PR300 proposed only three source-matched Figure8.2 raster-strip regions for tangent, sine and secant (utterances .002/.003/.004). Direct read-only source extraction of this same original slide establishes:
- The original introduction `s004.utterance.001` specifically discusses right triangles and their acute angle; original visible target `s004.text.002` displays a matching explanatory paragraph at PDF bbox **[10.909,57.794,339.762,82.252]**.
- The original principal-square-root / absolute-values utterance `s004.utterance.005` describes the displayed radical expressions. Original visible targets `s004.text.003` through `.006` occupy the combined PDF rectangle **[32.727,186.691,126.5,240.062]** and contain a square-root glyph and the displayed `a²+x²`, `a²−x²`, `x²−a²` expressions with visible absolute-value notation. PDF text encoding remains imperfect: these visually positioned claims are **NOT an academically verified mathematical source interpretation**.

## Permanent source-grounded improvement

New `selenium_pipeline.original_slide4_five_visual_candidates` binds exact original source/slides/script SHA256s and all five original narration identities to the previously source-pixel verified PR300 3-strip Figure8.2 candidate report. The two formerly unmapped utterances receive distinct review-only text regions, each anchored by exact extracted original visible text, target IDs, slide PDF geometry and original spoken phrase checks. The three already verified Figure8.2 candidates are preserved unchanged.

It fail-closes on missing/altered original slide text, root symbols, inconsistent math-word fragments, changed narration, altered source fingerprints, swapped/missing targets, invalid bounding boxes and fictitious prior triangle mappings. No speech/audio timestamps, real WAVs or encoded highlight frames are inferred.

**Result:** five of five **review candidates**, zero of five new independent scientific approvals, zero genuine utterance-aligned audio timing verified. Explicit `FIVE_ORIGINAL_SLIDE4_VISUAL_CANDIDATES_NOT_TIMED_OR_APPROVED` status cannot become production evidence or release authorization. The original review queue remains 0/71 two-pass source agreements; separate Slide-1 title-only review stays distinct.

## Evidence scope and next dependency

Original textbook/source.pdf SHA256 `b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`, original narration/script SHA256 `1744fc254bf7726f4953745c9f60caee93474ee34961fb684be030c815853807` are not modified.

This review-only improvement directly closes the **visual-candidate coverage** gap but leaves actual source math review, TTS provider/voice/speech content receipts, utterance timestamps and decoded MP4 element synchronization unverified. No Gemini sends, paid model calls, Whisper, source asset modifications, historical WAV/MP4 replacement, merges or student publication. Hosted GitHub CI uses Windows only by PR303's authoritative contract.
