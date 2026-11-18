# MicroGen_AI_Web v6 — physically witnessed fraction review candidates

Date: 17 November 2026, MYT. Authorized runner: Dell-115. Draft PR #530.

## Failure class and true root cause

The source-locked Serway §1.3 slide/utterance matcher initially had seven utterances without any ranked visible target. Prior exact spoken operator matching reduced this to three; two of those three were caused by PyMuPDF extracting actual numerator, denominator and superscript symbols as **separate physical text spans**. An ordinary literal text-block ranker could not read a stacked LaTeX fraction as a normal `1/2` or `L/T²` text string.

The original Serway §1.3 slide 6 contains two independent visually stacked `1` above `2` candidates:
- proposed equation near PDF x147 pt, numerator y107.8–115.8, denominator y115.85–123.82;
- right-hand expression's `1/2` near x138 pt, numerator about y168–179, denominator about y183–194.
The original slide 9 contains a physically stacked `L/T²` expression with numerator `L` near x181–192 pt, denominator `T` near x182–190 pt, and smaller raised `2` near x191–196 pt. These are directly inspected original PDF text-span bounds, not OCR or model-derived semantics.

## General production repair integrated into the normal mapper

New `selenium_pipeline/physical_fraction_review_targets.py` reads the original PDF's text-span geometry and accepts only two exact bounded patterns: same-x and correctly ordered `1` over `2`, and same-x `L` over `T` with correctly sized/positioned raised `2`. It stores original glyph indices and a SHA of exact physical glyph text, bounds and locations. It rejects reversed, distant, clipped, missing-exponent, and wrong-exponent glyphs. It limits candidate count.

`selenium_pipeline/incremental_element_candidate_map.py` calls this physical detector within its existing source-PDF, slide-PDF and narration-SHA-bound normal production mapping. It is enabled only by the version-controlled `SPLIT_PDF_NUMERATOR_DENOMINATOR_OR_SUPERSCRIPT_UNRANKED` recovery registry signature, mapped to mechanism `ORIGINAL_PDF_LITERAL_STACKED_FRACTION_REVIEW_TARGET_ONLY`. Disabled/retired mechanism cannot emit the new candidate type.

`selenium_pipeline/element_plan_autodraft.stable_recommendations` admits the candidate only with full original-PDF-geometry evidence, exact visible-glyph string `1/2` or `L/T^2`, no negation/contradiction, and exact spoken phrase `one half` or `length divided by time squared`. It emits a **review-only** target ranking score (not mathematical, scientific, highlighting or media approval). It does not invent a slash from separated or missing glyphs and does not certify a physics derivation.

The normal `selenium_pipeline/g2_offline_source_readiness.py` code-fingerprint incorporates the new detector and changed registry, generating new source/implementation-bound checkpoints rather than reusing stale ranking evidence. It *also* persists `ambiguous_fraction_review_worklist` for two tied high-ranked physically valid fraction targets, with null selected target, independent semantic-choice requirement, no paid TTS or source approval. The receipt verifier rejects tampering with chosen target or review counts.

## Genuine live and regression evidence

On the untouched 13-page Serway §1.3 original, the actual normal candidate-map test observed:
- slide 6 `s006.utterance.006` `The number one half is dimensionless` now has two equally ranked physical `1/2` review locations;
- slide 9 `s009.utterance.005` `The dimension of acceleration is length divided by time squared` has one physically supported `L/T²` review target.
- Only slide 5 `s005.utterance.003` `You cannot add a length to a time` remains **unranked** as a conceptual paraphrase.

The actual one-launch G2 forward engine and its full native offline audit found **1 unranked utterance**, **2 distinct slide-6 utterances with tied fraction target choices** (`s006.utterance.003` and `s006.utterance.006`), **20 of 85** independent source-science units accepted, **65 pending**, **13 original slide page-counter geometry blockers**, and 10 physically observed citation candidates for unchanged unattempted slide 12. It made **zero** new model requests, zero new journal stage intents, zero paid TTS/video calls, and no academic/publication approval.

Source+queue+code+registry identified no-overwrite offline receipt:
`%LOCALAPPDATA%/MicroGen_AI_Web_Checkpoints/g2_offline_source_readiness_v1/e1d7ee33b393f5274080c46fcd27d470dd55b23c52095f591f7e118895287d20.json`, SHA256 `274b70d672693c73db8f7daf85387e51da9d2f98b360c782437410763fae8014`.

Local test results: focused **54 passed**, expanded independent academic, source, visual and G2 regressions **207 passed, zero failed** (5 nonfatal warnings). New `tests/test_physical_fraction_review_targets.py` proves positive, negative, and forged origin claims; `tests/test_g2_offline_source_readiness.py` checks tied-choice worklist tampering. Exact-head GitHub Windows hosted tests to be run after the next commit.

## Safe boundary and next work

**Do not equate a review candidate with an approved highlight.** Both slide-6 ties and the semantic slide-5 paraphrase require independent evidence. The Gemini Pro PDF-response failure remains consumed/no-repeat, full Flash unavailable in preflight, alternate Pro without positively verified Medium/High Thinking. No source-cited second-pass consensus can be fabricated, so G2/G3 media acceptance remains blocked. The repaired future slide-layout code from prior commits continues to function; the original historical PDF remains immutable and its 13 page-counter geometry defects are not silently hidden.
