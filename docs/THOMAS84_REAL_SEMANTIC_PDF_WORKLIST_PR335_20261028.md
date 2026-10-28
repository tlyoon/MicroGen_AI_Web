# Thomas §8.4 — PR335 candidate: mathematical-word / original-PDF review worklist (28 Oct 2026)

## Goal and observed result

Advance genuine spoken-element linking beyond PR334's four provisionally word-timed
historical slide PDF targets without calling Gemini or regenerating voice/media.
All work was performed on **Dell-115, Windows**, using one isolated branch.
The original protected source remains at
`G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4` (read only).

Re-read the **original source.pdf, slides.pdf, script.txt, script_tts.json, and all 16 historical WAVs**
with SHA-256 comparison against the original protected receipt. Recreated actual
rendered PDF text rectangles using the existing source/slide mapping code and
cross-checked all real Vosk sentence timestamps against their exact original
TTS text digests. Re-ranked real visible text blocks with math-name, procedure,
step-number, and lexical indicators. Trigonometric single-function conflicts
are excluded, composite figures are excluded, and any source-hash, missing
sentence or nonsensical timing fails closed.

Real original-data run on Dell-115:

- **16 historical slides** examined (Slide4 corrected audio remains independent).
- **66 original per-slide narration sentences**, **65 with real ASR word-timed hypotheses**.
- **29 uniquely prioritized review-only candidate PDF elements**, across the
  actual measured acoustic sentence intervals; previously four word-timed
  PDF visual candidates had satisfied the stricter lexical worklist threshold.
- **Zero** academic/math semantic approvals, **zero** complete slide
  synchronization approvals and **zero** student release approvals.
- **Zero** paid API calls, TTS re-generation, Whisper, Linux testing, extra PCs
  or protected source/media modification.

These 29 are NOT 29 confirmed correct spoken-element highlights: they are
a source-bound, time-grounded *candidate shortlist*. At least some may be
semantically wrong because matching words and PDF text do not prove the
mathematical meaning of a highlighted element. They must not be automatically
promoted or rendered as accepted final highlights.

The output receipt is intentionally external to the protected source and
excluded from GitHub (it carries original source text evidence):

`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261028_PR335_REAL_THOMAS84_PDF_SEMANTIC_TARGET_WORKLIST_UNAPPROVED_V2.json`

Saved receipt SHA-256:
`a3eba8daa81ae5cf86bf493a27d2877be7f2d96f85c7480dc39148350103cf2c`.

## Code and checks

- `selenium_pipeline/original_thomas84_semantic_mapping_review.py`: read-only
  original-data integrity verification and provisional PDF rectangle ranking.
- `tests/test_original_thomas84_semantic_mapping_review.py`: negative and
  positive tests for step-number targets, sine/cosine conflict, composite-figure
  exclusion, malformed PDF rectangles and absent-source/no-false-receipt.
- Hosted CI remains **Windows-only**; the focused regression and syntax-check
  lists now include the new module/test.
- Dell-115 Python 3.12 `unittest`: **17 related tests PASS**; syntax compilation PASS.
- New independent actual original-data run: **PASS**, 29 review-target
  priorities, 65 measured acoustic intervals, all approval flags FALSE.
  GitHub-hosted CI must be verified on the resulting final PR head.

## Remaining critical path

1. Independently validate mathematical semantics and actual spoken-to-visible
   element correspondence for the shortlisted real PDF boxes, especially
   adjacent formula lines, sign/domain cases, and partial multiline text.
   An ambiguous candidate remains unapproved; do not fabricate reviewer votes.
2. Extend true, sample-timed source-visible element coverage to the
   remaining narration spans of all 16 original historical slides. Source-ground
   and independently check speech meaning, math correctness and voice continuity.
3. Create **new** complete corrected Thomas §8.4 two-part MP4s, each
   **strictly less than 600 seconds**, with decoded audio/visual sync proof,
   independent source math acceptance, and only then consider release eligibility.
   Keep all PR333/334 real review media intact.
4. Replicate the successfully accepted path for Thomas §§8.5 and 8.6,
   retaining automatic splitting and exact PDF figure math integrity.
5. Do not merge draft stack or publish Moodle/YouTube while contractual gates
   are missing. Maintain the flexible sound-alike TTS screening (hard-reject
   `c` pronounced `circa` and material mathematical errors).

No manual academic sign-off is required to keep internal evidence gathering
and software hardening running; absence of verified academic proof does
prevent release classification.
