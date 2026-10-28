# PR358 — Five actual original §8.4 trig source/domain cases investigated

Actual Dell-115 Windows original source source.pdf SHA
\`b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068\`,
17-page original generated slides.pdf, all 66 source-narration cue SHA
recorded in PR347, five earlier source text-scope flags recorded
in PR354, and true new corrected one-shot Kore WAV independent
offline phonetic QA PR357 were independently rechecked.

**Five previously flagged spoken source mathematical domain statements
received explicit source-branch checking**:
1. Slide5/sentence3: principal arcsine \(-\pi/2\le u\le\pi/2\),
   \(\cos u\ge0\) (endpoints included for inverse sine; the
   presence of a denominator may require extra exclusions in a
   particular integration).
2. Slide5/sentence4: principal positive secant
   \(x/a\ge1,\ 0\le u<\pi/2,\ a>0\); \(\tan u\ge0\).
   **Upper endpoint π/2 is excluded**, although source spoken
   "zero to pi over two" may be more precise if stated as
   "including zero but excluding pi over two".
3. Slide12/sentence3: strict \(x>2/5,\ x=(2/5)\sec u\) maps
   \(0<u<\pi/2\), \(\tan u>0\), so principal radical
   \(\sqrt{x^2-(2/5)^2}=(2/5)\tan u\).
4. Slide14/sentence2: tangent principal inverse branch
   \(-\pi/2<u<\pi/2\), \(\cos u>0,\ \sec u>0\).
5. Slide15/sentence2: the same tangent principal branch,
   with both reversibility and correct removal of absolute
   value from positive secant.

**Offline SymPy** confirmed squared-radicand and substitution
derivative identities for sine/tangent/secant; exact representative
angle values confirmed branch sign and endpoint behavior. Do not
mistake finite samples alone for an analytical proof over every
continuous real angle; the mathematical branch statements combine
classical monotonicity/sign facts of standard trig functions with
these exact symbolic identities. Exact spoken text hashes and
PDF block rectangles confirmed; no opposite-sign or single
trig-function term contradictions from the limited comparator.
Source branch uncertainty was mathematical-scope *triaged*,
not evidence that the recorded voice is fully correct.

**Output**:
\`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261028_PR358_FIVE_EXPLICIT_ORIGINAL_TRIG_DOMAIN_PROOFS.json\`.
New module
\`selenium_pipeline/original_thomas84_five_source_domain_proofs.py\`
and three Windows-only tests under
\`tests/test_original_thomas84_five_source_domain_proofs.py\`.
Real source audit PASS, three targeted tests PASS. Windows CI
tests/syntax included; no paid API, Whisper, Ubuntu, HP/Yoga6/Zenbook,
new Gemini TTS, source overwrite or publication.

**Strict remaining blocker:** all 66 speech-to-visual academic
semantic equivalences still not verified independently; Slide11
historical sound recording has prior ASR-only trig suspicion, no
independent audible confirmation; several contextual PDF cues have
low lexical specificity, and one secant-branch narration endpoint
could be made more explicit. Student-release remains forbidden,
zero approved replacement videos.
