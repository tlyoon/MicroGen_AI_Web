# PR345 — Original §8.4 PDF physical anchor coverage for all 37 missing speech units

**Genuine original source/PDF inspected on Dell-115 Windows.**
Prior PR344 source-bound ledger contained 66 historic source narration
sentences: 29 provisionally acoustic-linked PDF blocks, and 37 lacking
any uniquely proposed source visual target. This milestone independently
read every ORIGINAL slide PDF page text block and assigned one
physically existing, text/geometry-validated source cue to **each of
those 37 missing sentences**. No generated diagrams, guessed PDF
coordinates or invented source text were used.

- **37/37** previously missing source speech units have a
  candidate original-PDF text block rectangle.
- **36** use real original Vosk word start/end intervals, tied to
  untouched source `slideN.wav`.
- **1 opening title** has physical source-PDF text but no reliable
  word-level timing; nothing is invented.
- Among the 37 physical candidates, **19 directly mention the
  relevant source mathematical/procedure term**; **18 contextual
  anchors** represent relevant slide text but may not fully state
  the spoken mathematical reasoning.
- The 29 prior acoustic/PDF hypotheses remain distinct and
  provisional; source geometry counts must not be equated with
  independent mathematical-semantic acceptance.
- **ZERO** mathematical-semantic full approvals or student-release
  permissions. Review-only.

A concrete problematic example was discovered: the prior numeric
PDF representation `sin2 u = 1 − cos 2u` was incorrectly classified
as a cosine-only visual when narration says sine. This was a
**false positive** trig-function mismatch caused by ignoring PDF
exponent notation `sin2`. The general mathematical-comparison
logic and tests now recognize `sin2`, `cos2`, `tan2`, etc. and
retain actual sine-vs-cosine contradictions as errors.

New source-only code:
`selenium_pipeline/original_thomas84_37_contextual_cues.py`;
tests `tests/test_original_thomas84_37_contextual_cues.py`,
plus two added false-positive/true-positive math regression tests
in `tests/test_original_thomas84_math_domain_crosscheck.py`.
Real original-data run PASSED; 11 focused Dell tests PASS.
The Windows-only GitHub Actions workflow registers the new
source proof and tests. No Ubuntu, HP/Yoga/Zenbook, Whisper, TTS
regeneration, paid API or mutations to original G media.

Private protected evidence only:
`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261028_PR345_ORIGINAL_PDF_37_CONTEXTUAL_CUES_UNAPPROVED.json`

**Next acceptance task:** independent mathematical/speech/source
equivalence for all 66 candidates, with conservative handling of
multi-block formulas, domain signs and contextual descriptions;
then actual PCM-anchored full source video re-encode.
The already produced pair (420.85s, 312.13s) remains intact and
release-blocked, despite the verified final H264/AAC decoding.
