# PR289 — Real source-hash-bound numerical substitution-domain pilot (Thomas 8.4 Slide 3)

24 Oct 2026, Asia/Kuala_Lumpur. Dell-115-only isolated draft, stacked on PR288 exact `4b52b8f2400b290cd589adbe300fa2ce37145e85`.

## Concrete original technical evidence

Original six-page Thomas Calculus 8.4 source textbook PDF, original slides and script remain immutable. The Slide 3 original five-unit narration yields EXACT unique anchored utterances:
- `s003.utterance.002`: positive sum-of-squares radical via `x=a tan(u)`.
- `s003.utterance.003`: positive difference-of-squares radical via `x=a sin(u)`.
- `s003.utterance.004`: `x^2-a^2` via `x=a sec(u)`.

All are bound to original SHA256 narration IDs and source/slides/script fingerprints; no independently cited textbook formula or figure semantics is inferred. Physical source PDF SHA256: `b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`.

For each of the three transformations, on three positive `a` values and six valid angles (18 test samples), numerical radical and signed trigonometric replacement values agree within floating point tolerance. On three deliberate outside-branch cases per formula, the signed shortcut is materially wrong due to `abs(cos u)`, `abs(sec u)` or `abs(tan u)` complications. Real Dell-115 checks:
- Tangent + form: 18 in-domain samples, worst scaled relative error ~1.83e-16; 3 outside errors >=2.
- Sine - form: 18 in-domain samples, worst ~3.27e-16; 3 outside errors >=1.00.
- Secant difference form: 18 in-domain samples, worst ~3.25e-15; 3 outside errors >=1.09.

The tool intentionally reports **0 source-cited/independently agreed mathematical reviews** from these numerical checks, no formal derivation proof, no human academic pass, no TTS/video/publication approval. The previously evidenced 1/71 two-pass original math mapping remains ONLY the Slide 1 title; these three numeric checks are strictly technical review-candidate evidence.

## Durable code and tests

Added reusable `selenium_pipeline.original_trig_substitution_numeric_preflight`: uses the existing safe mathematical AST evaluator, original source-hash-bound review job and unique specific original narrator phrases. Rejects changed teaching asset identities, absent/misbound original formula units, wrong signed branches, nonfinite calculations, missing negative/out-of-domain counterexamples and overlapping narration IDs. No execution on new Gemini tab, remote provider or paid voice.

Dell-115 focused and related `pytest` suites: **29 passed**, five existing SWIG deprecation warnings. Adversarial tests inject wrong sign, omitted domain counterexample, changed source hash, and missing original source-bound narrator unit. Actual full original Slide 3 run returned exactly the three canonical formula witnesses and 5 narration units, with all permissions false.

## Outstanding scientific and multimedia gates

Algebraic sample consistency is not textbook correspondence or general mathematical proof, and cannot serve as first/second independent Gemini review. A specifically approved, source-bound Slide 3 initial academic review and then a separate challenge are still required under existing contract. Figure geometry/right-triangle mapping and original element-level audio/render acceptance are independently missing. No prior retry limits, consent gates or protected source/output assets are changed.
