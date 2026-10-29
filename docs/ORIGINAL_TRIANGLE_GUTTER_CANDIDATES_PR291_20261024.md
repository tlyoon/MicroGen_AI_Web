# PR291 - Original composite triangle gutter proposals

Original Thomas 8.4 slide 4 source-bound pixel scan detects gutters at 112-128 and 238-255, with candidate boundaries x=120 and x=246. This is structural evidence only; math semantics and source labels remain unverified.

## Source evidence

Real original image is 409x134 native pixels, embedded in the unchanged Slide 4 PDF. A full-height near-white column analysis found two separator runs, 112-128 and 238-255. Resulting contiguous candidate strips are [0,120], [120,246], [246,409]. Slide PDF x-coordinate boundaries are 48.421, 126.4618, 208.4046 and 314.4101 points. Every strip has a different exact decoded pixel SHA256. Original textbook SHA256 b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068 remains unchanged.

## Integrated implementation and safety

The reusable read-only original_composite_gutter_proposals CLI requires the existing original figure raster QA to pass. It verifies the source, slides and script hashes before and after; extracts exactly one material native raster; measures actual pixel gutters instead of imposing equal thirds; rejects too many, missing, bridged or narrow candidates; and records crop identity, ink coverage and proposed slide PDF coordinates. It never assigns author panel labels or mathematical correctness. All science, TTS, timing, human review and publication permissions remain false. No Gemini request, paid API call, source edit, protected merge or production-media replacement occurred.

## Validation

Dell-115 focused and neighboring pytest run: 20 passed, no failed tests. Adversarial fixtures cover bridged and extra gutters, blank image, impossible panel count, too-small image and too-narrow strips. The real original Slide4 source check passed with two internal gutters and three distinct hash-bound candidate crops. Further independent validation is required for author-intended panel count, textbook labels, right-triangle semantics and narration-to-panel timing. See continuation checkpoint and failure-to-fix ledger.
