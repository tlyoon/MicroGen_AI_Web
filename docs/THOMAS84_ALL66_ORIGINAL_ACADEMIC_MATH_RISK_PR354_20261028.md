# PR354 — Academic mathematical risk audit for all 66 §8.4 source utterances

Only Dell-115 Windows real source work. Protected textbook original source
\`source.pdf\` (6 actual pages), generated source-preserved
\`slides.pdf\` (17 pages), original unaltered \`script_tts.json\`,
PR347 complete 66-cue original-WAV PCM plan, ten original PDF
composite mathematical source corrections PR350, flexible actual
historical audio PR353 and independent genuine corrected two-MP4
physical verification PR352 were all SHA-bound and rechecked.

**Real source-academic audit:**
- **66/66 historical utterances** have actual original-PDF text/rectangle
  source geometry reverified, with their original narration fragment hashes.
- **10/10** prior physically corrected mathematical source composites
  have their actual original PDF source block text/geometry reverified.
- Four actual original §8.4 worked formula families passed limited
  symbolic antiderivative/domain checks.
- **5** inequality/domain scope textual mismatches remain
  *uncertainties*; ASR alone does not prove a formula/voice error.
- **Slide 11** remains a single targeted historical audio recognition
  trig-function suspicion requiring actual independent audio evidence.
- **ONE actual blocking mathematical defect** confirmed in GENERATED
  slide17's final question (not a claim about the textbook itself):

  The source-generated question requests the resulting transformed
  **integrand** of an integral "containing sqrt(x²-16), with x>4"
  without specifying the complete original integrand/numerator.
  That is mathematically insufficient. Two true counterexamples under
  x=4sec u, 0<u<π/2:
  (A) integral dx/sqrt(x²-16) gives integral sec(u) du;
  (B) integral x dx/sqrt(x²-16) gives integral 4sec²(u) du.
  SymPy independently verified both and distinct transformed results.

**Precise candidate repair** (NOT yet synthesized/published):
"Evaluate the integral of dx over the square root of x squared minus
sixteen, for x greater than four. Set x equal to four secant u, with
zero less than u less than pi over two. Find dx and show that the
transformed integrand is secant u."

This REQUIRES an actual corrected slide and corrected speech together.
DO NOT merely update the picture while old audio continues describing
an unspecified integral; DO NOT mutate original source.pdf, old
slides.pdf, old WAVs or previously archived MP4s.

**Future-run defect prevention:** extended pre-existing
\`selenium_pipeline/automatic_math_semantic_qa.py\` with conservative
\`incomplete_integral_does_not_define_transformed_integrand\`
blocking rule *before TTS*. The rule triggers only when an
unspecified integral described as "with/containing" a radical
is used to demand a resulting/simplified trigonometric integrand,
unless the full integral is explicitly specified.
An adversarial test accepts a properly specified original integral
and blocks the exact malformed courseware pattern, without changing
benign math material. This is in the actual reusable production
academic-linting path, not merely a one-time report.

Source/model audit report saved privately and exclusively:
\`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261028_PR354_ALL66_REAL_ACADEMIC_MATH_RISK_AUDIT.json\`.
New source-bound original academic report module
\`selenium_pipeline/original_thomas84_66_academic_math_risk_audit.py\`
with regression tests, plus two new generic mathematical pre-TTS tests
in \`tests/test_automatic_math_semantic_qa.py\`.
Actual real original-source run PASS, 14 targeted Windows tests PASS.
No Linux/Ubuntu, HP/Yoga6/Zenbook, paid Gemini/TTS/Whisper, media
mutation, source overwrite, or student release.

**Full mathematical-semantic student acceptance remains FALSE**:
visible original source cue provenance and selected worked-math proofs
are not a complete independent proof of every spoken sentence, and the
generated source itself contains an under-specified mathematical task.
0 release-eligible original video replacements.

Next: generate **paired corrected question/slides AND matching
narration** in a versioned out-of-source bundle, verify its mathematical
and pronunciation accuracy, selectively rebuild both <600s MP4s,
and independently re-audit final media. Do not use a synthetic
prerecorded voice pretending to be the earlier actual Gemini source.
