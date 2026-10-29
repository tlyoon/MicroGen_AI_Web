# PR299 — Exact symbolic squared identities with principal-root sign safeguards

25 October 2026, Asia/Kuala_Lumpur. Isolated Dell-115 draft stacked on PR298 exact head `6cf9877511957d57d8eea8475bdfbe9e89435e48` (GitHub CI green: offline regressions, full Ubuntu, full Windows).

## Original-source acceptance gap

Original Thomas Calculus 8.4 physical textbook page 1 and original lecture Slide 3 contain the three canonical substitutions:
- `x = a tan u`, corresponding squared radicand `a² + x²` and candidate `a / cos u`;
- `x = a sin u`, squared radicand `a² − x²` and candidate `a cos u`;
- `x = a sec u`, squared radicand `x² − a²` and candidate `a tan u`.

PR294 independently verified the unique original textbook substitution sentence and original Slide 3 narration IDs .002/.003/.004. PR298 established the original Figure 8.2 printed side-fragment positions against genuine vector right angles and faithful slide pixels. PR289 supplied 54 in-domain numerical comparisons and 9 deliberately out-of-domain counterexamples, but numerical agreement alone is not exact algebra.

**The actual radical/square-root glyph is imperfectly encoded in this source PDF**; source extraction often reports it as a quotation mark. Therefore it remains unjustified to assert complete original operator equivalence, general principal-root equality or independent academic consensus from those fragments.

## Permanent code and real-source proof

New read-only `selenium_pipeline.original_figure82_symbolic_branch_qa` cross-checks SHA256 of immutable textbook/slides/script, three unique original textbook substitution formula witnesses, exact narrator utterance IDs and original Figure 8.2 side-position candidate statements. On Dell-115, preinstalled SymPy 1.13.1 independently and exactly simplifies each **squared radicand minus the square of its proposed replacement** to 0 using exact trigonometric identities:

- `a² + (a tan u)² − (a/cos u)² = 0`
- `a² − (a sin u)² − (a cos u)² = 0`
- `(a/cos u)² − a² − (a tan u)² = 0`

These are exact **algebraic squared-identity results** on the defined-function domains. They do not prove the corresponding principal square-root identity in regions where the candidate replacement becomes negative. The module explicitly preserves the minimum sufficient sign restrictions and illustrative angle intervals:
- tangent: `a > 0, cos(u) > 0`, representative range `-π/2 < u < π/2`;
- sine: `a > 0, cos(u) >= 0`, range `-π/2 <= u <= π/2`;
- secant: `a > 0, cos(u)>0, tan(u)>=0`, range `0 <= u < π/2`.

The engine does **not** claim a machine-certified proof that every source utterance satisfies the interval/sign preconditions, nor complete original radical symbol fidelity. It cannot promote an ambiguous principal-root branch by squaring it. A changed formula, narrator ID, interval, source/slide hash, sign contract or academic approval flag fails closed. When SymPy is absent (for example on hosted CI environments), it reports `SYMPY_NOT_INSTALLED_EXACT_MATH_NOT_CHECKED`, never a substituted numerical success. Source contract validation still runs even without SymPy. SymPy is not installed or fetched on any unauthorized PC.

## Local validation and outstanding gates

Dell-115 with exact **original untouched** Thomas Calculus 8.4 source: `pytest -q tests/test_original_figure82_symbolic_branch_qa.py tests/test_original_substitution_source_formula_witness.py tests/test_original_trig_substitution_numeric_preflight.py tests/test_original_figure82_side_word_positions.py` — **31 passed**, zero failures, five preexisting third-party SWIG warnings. Mutations of each branch restriction, angle interval, formula/utterance identity, bogus automatic approval, duplicate/missing family and missing symbolic engine are covered. The actual source-bound CLI checked three identities exactly using SymPy.

Original 71-unit source-math consensus remains **1 independently AI-mapped title utterance, 70 pending/disputed, and 0 substantive mathematical agreements**. This module does not claim external academic/human signoff, real Kore TTS, source-bound narrator-element synchronization, encoded video <600 seconds or student publication authorization. No new Gemini request, paid API call, original textbook/slides/script/WAV/MP4 modifications, protected main merge, or YouTube/Moodle publication occurred.

Next priority: inspect GitHub CI for PR299, and then obtain a valid, explicitly scoped independent original academic review for the source mathematical statements and principal radical semantics. Independently verify narrated element-highlight timing without lowering academic publication gates.
