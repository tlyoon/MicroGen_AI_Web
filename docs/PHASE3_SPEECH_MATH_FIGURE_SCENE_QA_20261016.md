# Phase 3: independent speech, mathematics, figure preflight and scene autodrafts

**Status: review-only, 16 October 2026.** This phase adds permanently reusable
quality gates. No legacy outputs or production branch are overwritten.
The changes are stacked on the still-draft Thomas 8.4 full-element pilot PR #95.

## Independent model-level speech recognition

`selenium_pipeline.independent_speech_audit` compares the actual synthesized
Gemini 3.8 Flash Lite TTS WAVs against transcripts created **without supplying
the intended spoken script** to a distinct recognition model, Gemini 3.1 Flash
Lite or Gemini 3.5 Flash.

The transcriber emits one immutable receipt per audio element with the WAV
SHA-256, original requested transcript SHA-256, ASR transcript SHA-256,
model identity, conservative word-error rate, and a review flag. All evidence
is kept outside the textbook/source folders. Changing the model within an
ongoing job or tampering with WAV/transcript blocks reuse.

Model independence is **not provider independence** (the models share the
Gemini vendor), and matching recognition is **not** word-perfect fidelity or
human listening review. The separate audit must continue to label it as
machine consistency only.

A resumable ASR command:

```powershell
python -m selenium_pipeline.independent_speech_audit --plan FULL_ELEMENT_TTS_PLAN_JSON --audio GEMINI_TTS_WAV_FOLDER --output NEW_ASR_REVIEW_FOLDER --model gemini-3.5-flash --confirm-live
```

The exact model, frozen plan and list of WAV IDs are bound to the job. The
call requires explicit `--confirm-live`, never occurs during ordinary tests,
and transient provider 503 errors trigger bounded retries and then a
**nonapproval/incomplete** outcome. Do not restart ASR in a new arbitrary
folder to conceal failures.

The completed scene acceptance audit exposes `--asr-dir` and optional
`--require-asr`; the latter **rejects** any missing, mismatched or altered
transcription. Without a complete matching ASR receipt, a complete lecture
may still pass technical video tests but **cannot pass speech acceptance**.

**Real Thomas 8.4 status:** 3/48 clips were independently transcribed and
compared with Gemini 3.1 Flash Lite (WER 0.15, 0.00 and 0.00). The remaining
45 were blocked by repeated Gemini 503 overload. The alternative Gemini 3.5
Flash returned a successful one-clip probe, but also became unavailable in
the bulk job. No full ASR or word-level human approval is claimed.

## Generalized scene authoring for arbitrary PDF pairs

`selenium_pipeline.scene_candidate_authoring` automatically reads a
source.pdf and corresponding slides.pdf, identifies individual visible text
blocks and full figures, records PDF coordinates, and ranks possible textbook
source pages using lexical overlap. It never hallucinates speeches or
certifies the suggested page references; its JSON deliberately has
`REVIEW_REQUIRED_NOT_TTS_READY` and cannot be handed straight into
the TTS production gate.

Observed use:
- Thomas 8.4: 17 slides, 121 candidate regions, five image candidates.
- Thomas 8.5: 20 slides, 139 candidate regions, no image candidates.

These are **raw candidates**; not every text fragment is a desirable
narration step. Figure panel counts remain unknown until source-grounded
verification, and mathematical equation fragments require thoughtful grouping.

```powershell
python -m selenium_pipeline.scene_candidate_authoring --source-pdf SOURCE_PDF --slides-pdf SLIDES_PDF --out NEW_SCENE_DRAFT_JSON
```

## PDF visual/figure QA and mathematics QA

`selenium_pipeline.academic_visual_preflight` detects PDF content clipping,
very small figures, math-sized text spans, and likely horizontally composite
figures requiring explicit panel coverage review. It does not certify image
correspondence to the source, true legibility, mathematical truth or human
approval. It never modifies PDF content.

Thomas 8.4 scan:
- **0** out-of-page content blockers.
- **1** small-width figure (slide 13, 15.5% of full slide width).
- **2** possible composite figures requiring explicit panel review
  (slides 4 and 5; preserved width approximately 73.3% and 79.9%).
- 60 small math-text spans flagged as review cues (not automatically defects).

Thomas 8.5 scan: 20 pages, 0 geometry blockers, 91 small-text-span review
cues. Treat all small math labels as potential false positives until reviewed.

`selenium_pipeline.math_identity_preflight` evaluates numeric consistency of
an explicitly declared antiderivative against its integrand at safe sample
points, with a restricted AST expression evaluator (no eval/exec or user
code). Four source-anchored Thomas 8.4 worked-example identities passed
at **20 selected points** total: tangent substitution, inverse hyperbolic
sine, sine substitution and secant substitution. Altered coefficients,
unsafe code and stale source SHA bindings fail the tests.

A numerical derivative agreement is not a symbolic proof, does not prove
the expressions were reproduced correctly in the actual slide, and covers
only the declared mathematical examples. Manual academic approval remains
separate.

## Next production blockers

1. Obtain 48/48 independent transcription evidence (the external ASR
   service is presently overloaded) or use another documented, separately
   validated ASR backend; do not invent missing transcripts.
2. Resolve figure 13 readability and independently confirm the multipart
   figure-panel contents and textbook source correspondence, with rerenders
   and narration if slide count/content changes.
3. Upgrade automatic scene candidate generation to an actually complete,
   source-verified per-element narration plan for arbitrary subchapters,
   including evidence for all mathematical derivations.
4. Wire the new safeguards into production fail-closed gates, rerun full
   three-PC QA, and only then consider merging draft PRs #91–#96.

The existing 17-slide Thomas 8.4 two-part videos remain **review-only**.
The user will independently inspect and listen to the videos later.
