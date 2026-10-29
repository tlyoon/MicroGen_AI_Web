# PR302 — Exact conditional principal-root branch verification on original Thomas 8.4

25 October 2026; Dell-115 isolated draft stacked on PR301 `0eafea73bc418a17df462bdd67e6e6dde0d1a793`, **only after confirming its parent CI**.

## Specific observed problem

PR299 proved the THREE **squared** identities in original Thomas Calculus 8.4 Slide3, but equality of squares does not imply a principal-root equality without nonnegativity. Nine previous out-of-domain counterexamples proved that global shortcuts can have the wrong sign. PR298 also found that PDF text extraction loses portions of the square-root glyph. A general statement like `sqrt((a tan u)^2) = a tan u` is false if the right side is negative.

## Exact interval/branch evidence

New source-bound, read-only `selenium_pipeline.original_principal_root_interval_qa` combines PR299's exact algebra with SymPy 1.13.1's exact `function_range` calculations under the **explicit hypothesis a>0**:

| Canonical substitution family | Angle interval | Exact calculated range | Nonnegative replacement |
|---|---|---|---|
| `x=a tan(u)` / `a²+x²` | `-π/2<u<π/2` | `cos(u) in (0,1]` | `a/cos(u) > 0` |
| `x=a sin(u)` / `a²−x²` | `-π/2<=u<=π/2` | `cos(u) in [0,1]` | `a cos(u) >= 0` |
| `x=a sec(u)` / `x²−a²` | `0<=u<π/2` | `cos(u) in (0,1]`, `tan(u) in [0,∞)` | `a tan(u) >= 0` |

For real expressions, the program verifies the algebraic lemma `sqrt(z²)=abs(z)` with SymPy and establishes nonnegative replacement over those exact intervals. Therefore the three *candidate* principal-root equalities are valid **conditionally on exactly those domains and positive a**. A different interval, sign assumption, source formula, narration ID or missing SymPy must not be promoted as proven. The secant branch for negative `u` is intentionally excluded.

The verifier rechecks the unchanged physical source.pdf, slides.pdf, script.txt SHA256s and original Slide3 narrator identities after PR299's Figure8.2 source-linked math checks. This is stronger than finite sampling, but it is not independent confirmation that the user's textbook/narration has the intended radical operator, is pedagogically correct, or has a second AI/human scientific approval.

## Real original results and limitations

Dell-115 real original source audit returned **three exact conditional principal-root branch lemmas** with nonzero denominator and required sign domains, original textbook source SHA `b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`, original Slide3 narration IDs .002/.003/.004, no source changes and zero new provider calls. Actual independent academic approval remains 0 substantive mathematical utterances. Do not silently combine the independently scoped Slide1 title-only proof with the full 71-unit source-review queue (which presently records 0/71 two-pass agreements).

All source-figure radical glyph fidelity, scientific second-pass AI/human approval, original Slide4 audio timing, actual encoded highlighted MP4, and strict under-600-second student publication remain unverified. No Gemini requests, paid TTS, historical WAV/MP4 edits, protected branch merge, or external publication.

## Tests and handoff

Dell-115 local test command `python -m pytest -q tests/test_original_principal_root_interval_qa.py tests/test_original_figure82_symbolic_branch_qa.py tests/test_original_substitution_source_formula_witness.py` with genuine original source enabled: **24 passed, no failures**; five pre-existing SWIG deprecation warnings. Cases verify interval endpoints (including open vs closed), changed utterance IDs or theorem conditions, altered expected trig function ranges, absent symbolic engine and real source lineage. Optional SymPy-unavailable hosts must SKIP positivity-proof tests and mark proof unverified, never claim a pass without the engine. Hosted CI to be verified separately.

Follow-on PR303/304 video production is blocked pending actual independent math agreement, authoritative two currently unmapped Slide4 targets, genuine same-voice per-utterance TTS receipts/WAV samples, measured timeline and decoded audio-to-highlight fidelity. Working on future unsafe deliverables before those gates pass would fabricate progress.
