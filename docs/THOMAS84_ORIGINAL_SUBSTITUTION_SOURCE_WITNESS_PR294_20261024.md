# PR294 — Three real substitution formulas with exact textbook provenance

24 October 2026 (Asia/Kuala_Lumpur); Dell-115 isolated draft stacked on CI-green PR293 head `01d20b1a1a7e7f475034de673d254ead0a6fb6e8`.

## Source-grounded evidence

Read the original Thomas Calculus 8.4 source.pdf, slides.pdf and script.txt without alteration. The physical textbook PDF page 1 contains a single, geometrically coherent sentence naming all three formulas: `x = a tan u`, `x = a sin u`, and `x = a sec u`. The full contextual sentence is unique on the physical page and passes the PR292 spatial quote witness. Its normalized quote SHA256 is `91d159ba56daf6fe948e548168fa55d3688b5c4f5f3cfb799800d4731f254b0c`.

The exact original narration bindings are s003.utterance.002 (tangent), s003.utterance.003 (sine) and s003.utterance.004 (secant), with original spoken SHA256 values recorded in the review-only CLI result. The prior source-hash-bound numeric pilot found 18 in-domain and 3 out-of-domain sign-branch cases PER form: 54 positive and 9 negative checks across the three source-linked formulas. Physical textbook PDF SHA256 is `b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`. The source quote describes the substitutions, not the complete derived radical identities or the figures' semantic panel assignments.

## Permanent correction to review workflow

Reusable read-only `selenium_pipeline.original_substitution_source_formula_witness` verifies immutable source/slides/script SHA identity, exact slide-3 narrator IDs and SHA anchors, unique physical-page contextual citation, exactly one occurrence per named textbook formula, and preexisting bounded numerical branch checks. Its output is a deterministic source-attribution candidate with machine-readable provenance. Unlike naive isolated formula searches, the complete contextual sentence has one genuine continuous physical source occurrence. This prevents ambiguous short formula matches from being promoted as source proof.

## Acceptance limits and tests

Dell-115 focused and neighboring regression run: **20 tests passed**, zero failed, plus existing SWIG deprecation warnings. Adversarial tests reject missing or duplicated source formula sentence, changed textbook SHA, wrong narrator ID, missing domain negative samples and an unexpected fourth formula case. Real immutable Thomas 8.4 Slide-3 execution returned three source quote bindings, source page 1, 54 positive and 9 negative numerical cases.

**Do not count these as independent academic agreements.** The real two-pass original AI-source acceptance remains 1 of 71 (the Slide-1 section title only), 70 pending or disputed, and zero substantive mathematical agreements. No independent human approval, source figure semantics, original Kore TTS or synchronized MP4 verification is claimed; no provider review request, paid API, original media edit or publication was performed. Next: obtain appropriate source/slide-specific review authorization and independently challenge the original three formula claims, or continue legitimate figure semantics and media QA without bypassing that gate.
