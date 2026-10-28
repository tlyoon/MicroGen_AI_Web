# PR350 — Fix ten incomplete or wrong-context original-PDF source cue selections

The original §8.4 lecture narration and actual 17-page PDF were
revisited after the PR349 independent two-part H264/AAC pass.
The prior mapping selected valid physical blocks but sometimes
highlighted only part of a split mathematical equation, or
an unrelated summary block with coincidentally similar words.

**Ten original PDF mathematical-source focus corrections, actual
source proof PASS**. Each corrected cue now retains explicitly
enumerated real original PDF block IDs, exact visible source
text, actual separate source rectangles and one genuine
rectangular group envelope. No synthetic mathematical symbols
or images have been created.

Corrected slide/sentence focus cases:
- Slide 5/sentence 4: secant-domain line and its x/a>=1 qualifier.
- Slide 7/sentence 1: actual integral and x=2tan u source
  substitution rather than only the substitution statement.
- Slide 8/sentence 2: tan u ratio and the adjacent source
  triangle-construction line.
- Slide 9/sentence 2: inverse-hyperbolic-sine antiderivative
  statement plus its source square-root term.
- Slide 10/sentence 3: the source sin²u transformed integral
  across physically fragmented equation blocks rather than
  only the procedural heading.
- Slide 12/sentence 2: original factorization equation
  rather than just its instructional heading.
- Slide 13/sentence 1: source secant/tangent cancellation
  across actual integral fragments.
- Slide 15/sentence 2: BOTH mathematical goals
  (invertibility AND radical simplification), not only one.
- Slide 16/sentence 1: original **Identity Alignment**
  summary rather than the unrelated algebra-preparation bullet.
- Slide 17/sentence 2: original complete sqrt(x²−16)
  problem text across two PDF blocks.

**Limited independent mathematical checks PASS:** SymPy symbolic
tangent derivative / secant radicand-square identities,
and representative source-domain signs for sine, tangent,
nonnegative secant-branch tangent and strict positive secant
branch. These domain samples are NOT themselves a formal proof
across every real value or full source mathematics approval.

Protected input original textbook SHA
`b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`,
PR347 exact sample plan and PR349 independently audited real
review media receipts reverified. Five targeted Windows-only
Python3.12 tests PASS, actual source-PDF block/geometry/SymPy
verification PASS. No source files or older media overwritten,
no paid Gemini/TTS, Whisper, Ubuntu, HP/Yoga/Zenbook.
**Release remains false.**

Private new correction receipt:
`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261028_PR350_SOURCE_COMPOSITE_MATH_FOCUS_REVIEW.json`

Source code:
`selenium_pipeline/original_thomas84_composite_source_semantic_corrections.py`.
Unit tests:
`tests/test_original_thomas84_composite_source_semantic_corrections.py`.
Windows-only GitHub Actions regression and syntax lists updated.

**Important:** PR348's two real MP4s still show the PRE-CORRECTION
cue images. Do NOT accept them as the corrected media. A new
render must overlay the true original composite PDF geometry
at actual source word times and be independently decoded/re-audited
before it is claimed to contain the ten fixes. Final academic
speech-to-visible element release approval is still missing.
