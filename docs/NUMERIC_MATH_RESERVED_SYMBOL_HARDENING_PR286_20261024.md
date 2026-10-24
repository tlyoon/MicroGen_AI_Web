# PR286 — Prevent false-pass mathematical verification through sample-variable shadowing

24 October 2026 (Asia/Kuala_Lumpur). Dell-115 isolated stacked draft based on CI-passing PR285 head `6f255bcdca3a12f3ec62bb1c2fcb1f6cdc48d09b`.

## Proven reproducible bug and severity

The existing source-hash-bound `math_identity_preflight.verify` assembled sample values as `{"x": sample_x, **constants}`. If an untrusted explicit formula-check manifest included `constants: {"x": 2}`, it silently replaced **the integrand's x** with 2. The derivative expression was evaluated at genuine sample x values due to a later x override. An objectively WRONG antiderivative `F(x)=2x` for `f(x)=x` would therefore pass every numerical point (both reported 2), creating a **false mathematical acceptance test**. This is an actual code-level failure mechanism, independently reproduced in an adversarial test fixture; it is not a Gemini model problem or an observed historical source file modification.

## Permanent integrated fix

Use a single `checked_constants` validator in normal mathematics preflight, before any expression evaluation. Reject:
- reserved differentiation and built-in symbol names `x`, `pi`, `sin`, `cos`, `tan`, `sqrt`, etc.,
- malicious or malformed identifier keys, non-real values including booleans and strings,
- nonfinite, excessively large, and excessively numerous fixed constants,
- repeated, nonfinite or excessively large sample x coordinates that weaken regression evidence.

The normal valid `a`-parameter derivative check continues to pass. Bounded numerical sampling is **not** symbolic proof, verified source equivalence, human academic approval, permission for TTS, or student publication; those flags remain unchanged.

## Tests

Dell-115 direct Python pytest command:
`python -m pytest -q tests/test_math_preflight_reserved_symbols.py tests/test_math_identity_preflight.py tests/test_scoped_original_math_claim_kind.py tests/test_scoped_original_math_consensus.py`

**28 passed, 0 failed**, five existing SWIG deprecation warnings. Added eight adversarial/protective tests: historical wrong integral false-positive reproduction, valid parameterized derivative, restricted built-in or `x` names, malformed/nonfinite/huge constants, excessive constant count, repeated/nonfinite sampled points, and genuinely incorrect math failing normally. Original historical tests continue to pass.

## Safety & acceptance

Only code, tests, and docs in a new isolated Dell-115 worktree are changed. No original textbook PDF, slide, script, WAV/MP4, review/health receipt, protected main tree or external provider call is affected. Source-bound Thomas Calculus 8.4 acceptance remains exactly 1/71 **title-only** AI element agreement, 70 pending/disputed, no substantive mathematical derivation verified or publishable lesson.

## Next

Subject to PR286 GitHub CI, prioritize a genuine original-source mathematical derivation/figure case with approved independent-review scope, and keep the numerical identity preflight an extra safety check rather than a substitute for scholarly or release acceptance.
