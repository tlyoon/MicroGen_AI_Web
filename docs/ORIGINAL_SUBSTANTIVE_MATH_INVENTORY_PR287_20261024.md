# PR287 — Actual original-source mathematical-claim inventory and next vertical-slice selection

Date: 24 October 2026, Asia/Kuala_Lumpur. Owner hardware policy: Dell-115 only. Stacked on GitHub CI-green PR286 head `5a9ec6eff475129377e594e8ee3779d6858052b8`.

## Verified original material

Used original teaching assets under `G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4`, without writing to that folder. Original source.pdf SHA256: `b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`. Source textbook PDF physical pages: **6**; slide PDF pages: **17**; exact narration utterances: **71**.

The independent read-only inventory built on the normal original text/slide/WAV source map and covered all 71 unique ID/SHA-linked utterances:
- 1 slide-1 numbered section-title metadata candidate.
- 52 substitution/identity cues.
- 7 geometry/radical cues.
- 6 integration/derivation cues.
- 5 general-prose/unknown cues.

These are **nonexclusive semantic cue categories collapsed to a deterministic first-match priority**; a lexical match is never a verified mathematical theorem, source quote, element mapping, independent academic consensus, approval, paid voice authorization, nor evidence of real source/figure fidelity.

The first candidate with multiple explicit original algebraic narration phrases is **Slide 3 — The Three Basic Substitutions**. Its original five narration units reference Pythagorean identities and the tangent and sine substitutions. Slide 2 is an introductory roadmap, not the desired first detailed mathematical pilot. Original worked integrations appear in Slides 7–13. No new source-math window or Gemini request has been created; the sole genuine independently compared review remains the existing Slide 1 heading, 1/71 AI source agreements, **0 substantive mathematical agreements, 70 pending/disputed**.

## Permanent robustness change

Introduced `selenium_pipeline.original_math_claim_inventory`, read-only by default; optional new `--out` JSON is permitted only outside original teaching assets. It cross-checks immutable original textbook, slide and narration SHA256 against the existing real element candidate inventory, physical PDF page count, source slide and unit numbering, total counts and before/after input identity. It emits stable utterance IDs, spoken hashes, cue classes and prior-review status **without dumping textbook pages or unpublished narration into public repository docs**.

First real run exposed an overly broad ranking issue: simply counting words like 'substitution' falsely prioritized the introductory roadmap. Added distinct explicit algebraic phrase cues and regression to rank the first slide with two or more such statements. The real second run correctly selected **Slide 3**. This is planning evidence only; that slide's initial independent review still needs actual source-grounded scope and appropriate authorization.

Private real inventory output, not version-controlled, is `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261024_pr287_original_math_inventory_formula_priority.json`; no original-file edits or remote submissions.

## Validation

Dell-115 `python -m pytest -q tests/test_original_math_claim_inventory.py tests/test_incremental_element_candidate_map.py tests/test_ai_academic_web_review.py tests/test_scoped_original_math_consensus.py`: **20 passed**, five existing third-party SWIG deprecation warnings. Adversarial tests verify original PDF hash drift, bad utterance IDs, denominator drift, exact title/prose/identity separation, and no artificial science/publishing authority. Exact real original run succeeded with all 71 units and the original source SHA shown above.

## Subsequent work

PR288 should turn the selected slide-3 review into a **read-only, source-bound authorization and attempt-preflight plan**, not silently borrow the user approval for the previously exhausted slide-1 independent challenge. It must trace the current source ledger, historic receipts, stage-specific permission and worker ownership, and remain no-send without explicit applicable scope. PR289+ may harden source validation independently while scope is awaited. No protected main merge, YouTube/Moodle release, paid API, voice synthesis or replacement of historical videos is authorized by the inventory.
