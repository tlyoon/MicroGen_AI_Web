# PR346 — Independent mathematical verification of four real §8.4 worked formula families

The protected original Thomas §8.4 PDF identity SHA
`b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`
was checked on Dell-115 Windows before and after running independent
offline SymPy symbolic mathematics.

**Four of four worked formula families PASS** targeted differentiation,
zero-integration-constant or domain-sampled sign checks:

1. Example 1: `∫dx/√(4+x²) = ln((x+√(4+x²))/2)+C`,
   derivative matches for all real x.
2. Example 2: `asinh(x/a) = ln((x+√(a²+x²))/a)`
   for a>0; derivatives agree and both sides vanish at x=0.
3. Example 3: `∫x² dx/√(9−x²) =
   (9/2)asin(x/3) − (x/2)√(9−x²)+C`,
   on −3<x<3.
4. Example 4: `∫dx/√(25x²−4) =
   (1/5)ln((5x+√(25x²−4))/2)+C`,
   for x>2/5.

The actual original PDF source slides 7/8, 9, 10/11 and 12/13
were reopened and **16 matching visible formula/procedure text
fragments physically found** with original PDF geometry/sha.

**Limits:** PDF mathematical equations are frequently fragmented
by the PDF extractor; presence of 16 source fragments alone does not
prove every whole visually printed equation. Four correct symbolic
formulas DO NOT certify the exact wording/placement of all 66
historical spoken sentences, nor any source-to-visible-element
semantic mapping. All final academic/media student release gates
remain FALSE, 0 accepted videos, original G PDFs/WAVs/MP4s untouched.

Four new focused Windows/Dell Python tests PASS, including wrong
coefficient/sign/source refusal; actual original-source mathematical
proof PASS. No paid Gemini/TTS, Whisper, other PCs or Ubuntu CI.

Private external SHA/geometry source evidence:
`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261028_PR346_FOUR_WORKED_EXAMPLES_LIMITED_MATH_PROOF.json`.
Code `selenium_pipeline/original_thomas84_worked_examples_math_proof.py`,
tests `tests/test_original_thomas84_worked_examples_math_proof.py`.
Next: source- and mathematical-term crosscheck every 66 original acoustic
candidate source cue, then source-preserving full real 66-cue review
video re-encode with independent physical audit.
