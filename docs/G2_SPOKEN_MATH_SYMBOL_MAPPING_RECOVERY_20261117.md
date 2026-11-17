# V6: Exact spoken-math / rendered-PDF operator candidate recovery

Date: 17 November 2026. Development runner: authorized Dell-115. MicroGen_AI_Web isolated draft PR #530.

## Actual original failure and root cause

A source-bound, provider-free G2 readiness audit of genuine Serway §1.3 (13 slides / 85 narrations) identified **seven** narrated utterances with *no ranked visible target candidate*, even though their slide PDFs contain physical text elements. Their narration uses ordinary mathematical English while the PDF extractor represents the corresponding formula in compact symbols. Examples verified by inspecting the actual original source and slide element inventory include:

- Slide 11: `So, n plus m equals one.` vs the rendered text `n + m = 1`.
- Slide 8: `position x is proportional to acceleration a times time t squared` vs physically rendered `Conclusion: x ∝at2`.
- Slide 9: `length divided by time` vs literal `L/T` in an original slide text block.

The existing `element_plan_autodraft.stable_recommendations` awarded zero lexical overlap for those exact notation equivalents. Simply picking the nearest element, assuming stacked fraction layout, or assigning generic words like `time` to a random equation would be unscientific.

## Reusable executable repair and strict limits

`element_plan_autodraft.py` adds `_exact_spoken_math_operator_hint` to produce a **review-ranking hint only** when the actual PDF text contains precisely the requested operands, operator and result. Three tightly scoped normalizations are allowed: `n plus m equals one` ↔ physically present `n + m = 1` (not reversed operands or another result); `x is proportional to a times t squared` ↔ physically present `x∝at²`; and `length divided by time` ↔ an explicit literal `L/T` ratio (never `L/T²` or missing fraction separators). An exact same-slide PDF text target is still mandatory. Existing incompatible sine/cosine exclusions and figure/visual-provenance guards remain in effect.

A new v6 recovery-registry signature `SPOKEN_LITERAL_OPERATOR_VS_RENDERED_MATH_SYMBOL` with mechanism `EXACT_PHYSICAL_PDF_OPERATOR_ALIAS_RANKING_HINT_ONLY` must be enabled and code-verified before the additional notation hint can contribute to `stable_recommendations`. Missing, changed or retired signatures simply disable this extra hint; ordinary ranking continues under its preexisting evidence and gates.

These suggestions are neither semantic equality proofs nor claims that the derived equation is physically correct. They do **not** mark scientific source agreement, resolve original source PDF ambiguity, authorize paid TTS/video, or publish any lecture.

## Real change after correction

A new, provider-free real `candidate_map` of the unchanged Serway §1.3 PDFs and original narration lowered the number of no-ranked-target utterances from **seven to four**. The remaining exact units are:

- slide 5 `s005.utterance.003`: an explanatory paraphrase about adding length to time, not a literal formula match;
- slide 6 `s006.utterance.006`: spoken `one half` in PDF text split across physical numerator/denominator glyph blocks;
- slide 9 `s009.utterance.005`: length/time² ratio whose PDF glyphs are split, not one literal safe slash representation;
- slide 11 `s011.utterance.003`: paraphrased left/right exponents whose equation matching requires a nonliteral interpretation.

Those four are **not auto-assigned**; they require exact visual/semantic independent review. Physical mapping candidates on the other three can be shown to reviewers, but their target identities are not scientifically accepted without source-grounded QA.

## Source/readiness cache invalidation

The concurrent v6 offline QA module now incorporates a SHA of the **actual six source/QA mapping algorithm files** (including itself, `element_plan_autodraft.py`, source-quote and scientific recheck code) into its content-addressed receipt identity. Any future change in ranker, source quote algorithm, geometry checker or consensus verifier invalidates the older offline preflight result and generates new source-locked technical evidence. A changed implementation cannot silently reuse the prior report with seven unranked cases. Crash-safety, finite resource bounds and no provider Send are preserved.

## Verification

- New `tests/test_spoken_operator_rank_hints.py`: positive physical literal examples and mismatched-operand/result, reversed/missing/squared expression, unsupported fraction/figure, trig conflict and retired-registry negative tests.
- Extended existing source-bound offline audit tests include algorithm-version-invalidation and still recheck original source+queue SHA; prior simulated provider-failure, crash, no-resend and scientific gates remain.
- Focused tests passed: **43 passed, 0 failed**; expanded local/historical tests and exact-head Windows CI must pass before this follow-up code can be reported as hosted-verified.

**G2 scientific state remains open** at **20 of 85 independently source-agreed**, 65 unresolved; slides 10/11 and the failed synthetic Gemini PDF request remain consumed and cannot be replayed. No new Gemini submission or paid operation is part of this source-target ranking fix.
