# PR285 — Prevent title agreement being confused with mathematical verification

24 October 2026. Dell-115 only. Stacked on exact GitHub CI-passing PR284 head `55e6df0212a7852cf63cad5057f0dc54342c8019`.

## Retrospective fault and root cause

The source-hash-bound AI consensus in PR284 correctly accepted 1/71 original Thomas Calculus 8.4 narration elements. The **sole accepted unit was the Slide 1 topic title** `8.4 Trigonometric Substitutions`, which both saved independent model passes cited against the original textbook title and visible slide title. The report lacked any classification between metadata-only alignment and mathematics. A user interpreting **1/71 independently agreed source math** as evidence of substantive verified integration could infer false mathematical progress even though no mathematical identity, substitution or Figure 8.3 diagram was reviewed in those passes.

This is an **acceptance-evidence classification defect**, not a failure of source PDF hashing, text target matching or historical checkpoint recovery. The original two AI reviews are preserved and valid for the narrower title-only scope.

## Permanent, fail-closed correction

Modify the existing read-only `selenium_pipeline.scoped_original_math_consensus` **normal audit path**, not a one-off report. A unit is explicitly `ORIGINAL_SECTION_TITLE_METADATA_ONLY` only when:
- It belongs to **slide 1**.
- Its original spoken text is an explicit numbered section heading (e.g. 8.4 followed by a descriptive title).
- The original spoken heading exactly matches the real PDF visible element selected by both source reviews.
- Both source-witnessed verbatim book quotes exactly match the same original spoken title.

Every other unit remains `UNCLASSIFIED_DOMAIN_CLAIM`: a lexical agreement alone never certifies a mathematical identity, proof, equation, figure semantics, or human mathematical review. Report the count of title-only AI agreements separately from other source agreements and formally proven mathematical derivations. Preserve the true **combined source-mapping consensus** numerator and denominator, original source SHA, source report receipts, and nonpublication gates.

The denominator remains **71**; never silently exclude metadata, disputes, or unknowns from total original narration units. Do not retroactively mutate Oct22 original queue records, Oct23 failed challenges or Oct24 actual independent successful response.

## Real acceptance and limits

Against actual original Thomas 8.4 evidence, the expected result is:
- **1/71 source-witnessed two-pass AI element agreements**
- **1 section-title metadata-only agreement**
- **0 independently classified substantive mathematical agreements**
- **70 unresolved/undisputed-in-source-consensus original elements**
- **0 formal mathematical derivations proven**, 0 human academic or listening approvals, no source-faithful Kore element TTS or publishable MP4

This classification has no influence on provider requests, quotas, backoff, approval/consent, source files or production release.

## Tests

Local Dell-115 regression suite:
`python -m pytest -q tests/test_scoped_original_math_claim_kind.py tests/test_scoped_original_math_consensus.py tests/test_scoped_original_math_review_capture.py tests/test_ai_academic_review_consensus.py tests/test_original_math_review_recovery.py`
— **27 passed** (existing third-party SWIG deprecation warnings only). New negative tests reject wrong source quote, wrong slide, missing target, mismatched visible text, unverified mathematical speech, and even a formula on the title slide. Existing source consensus and review-window tests also passed.

## Remaining risks and next step

The evidence that two language-model passes independently phrase the same explanation is not a formal proof and does not validate unseen figure semantics. The next vertical-slice priority is to obtain **approved, source-bound original mathematical derivation** reviews for slide 3 or the smallest mathematically substantive slide using the project's actual authorization and retry policy, then validate figure geometry and element-level narration before authorizing genuine production TTS/media. Retain the already captured Slide 1 response as immutable source evidence. Do not open a new mathematical reviewer window by borrowing the original Slide 1 consent.
