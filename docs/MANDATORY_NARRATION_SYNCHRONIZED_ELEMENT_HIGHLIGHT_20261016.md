# Mandatory narration-synchronized element highlighting — integration

**16 October 2026 | development draft, no publication**

The MicroGen_AI_Web original contract requires the *currently narrated*
equation, sentence, figure, or constituent figure panel to be visually
highlighted at the same time as its spoken audio. This is element-level
synchronization, not a static page highlight and not automatic word-by-word
tracking. Every multipart lecture video must be **strictly shorter than
600 seconds**, and every original slide must be covered in sequence.

## What changed

The standard `selenium_pipeline.runner` previously **correctly refused**
its obsolete static-slide `video` stage. That prevented incorrect new MP4s
but also meant successful separately tested element-level rendering could
not be executed through the normal runner.

This development introduces a **safe, explicit REVIEW route** into the
standard runner: `--from-stage video --through-stage video`, together
with an authored element plan, original separate Gemini WAVs, optional
source-bound slides PDF, and a *fresh isolated* review directory. The runner
validates the configured source root and then calls
`selenium_pipeline.element_highlight_workflow.review`.

The new generic workflow:
1. Verifies source and slides PDF SHA-256 against a frozen author-specified
   narration/anchor plan; requires every slide in order exactly once.
2. Verifies at least one specific audio-highlight element per original slide,
   one original unique PCM WAV per element and exact same declared voice.
3. Rejects any audio part not **strictly below 590 seconds** before encoding
   (10-second safety margin) and each final encoded MP4 not below 600 seconds.
4. Reuses the already source/geometry-validated element stage and timed
   per-WAV, per-element H.264/AAC renderer, with no Gemini or TTS call.
5. Independently verifies the staged plan, WAV hashes, narration timestamps,
   actual MP4 streams and duration, per-event decoded active target pixel
   evidence and transition drift ≤0.15s; re-decodes all encoded pixel
   highlights rather than trusting a JSON count.
6. Saves `highlight_technical_review.json` with every video part duration
   and hash, slide and element coverage and explicit **false** flags for
   academic/semantic correctness, human listening, production and publishing.
7. Does **not** produce `lecture_completion.json`, overwrite
   `slides.mp4`, alter the original subchapter, merge a PR or update Moodle.

## Safe use

The source root remains the independently configured textbook tree. The
corrected slide deck and previously generated WAV folder can be read-only.
The author plan must be created and sourced to the current slide PDF **before**
running the video-review stage.

```powershell
python -m selenium_pipeline.runner `
  --source-root "G:\My Drive\Projects\Thomas_calculus_13ed" `
  --subchapter "8.4" `
  --from-stage video --through-stage video `
  --element-plan "PATH_TO_AUTHORED_ELEMENT_PLAN.json" `
  --element-audio "PATH_TO_ORIGINAL_PER_ELEMENT_GEMINI_WAVS" `
  --element-slides "PATH_TO_SOURCE_BOUND_SLIDES.pdf" `
  --element-review-root "PATH_TO_NEW_ISOLATED_REVIEW_FOLDER"
```

All four element options are deliberately explicit. There is no implicit
static-slide fallback. In particular, selecting `--from-stage figures`
with `--through-stage video` still **fails closed** instead of converting
a slide-level script into a falsely highlighted MP4. A complete source-bound
element plan and element-level WAVs are not currently automatically authored
by the normal upstream slide and TTS stages. This is the remaining generic
authoring/productization gap.

The independent technical audit can also be used on an existing correct
render (e.g., preserved Thomas 8.4 review) without rendering a new one:

```python
from selenium_pipeline.element_highlight_workflow import verify_rendered
technical_report = verify_rendered(
    source=source_pdf, slides=slides_pdf, authored=authored_plan,
    audio=recorded_audio, staged=staged_parts, rendered=rendered_parts,
    output=new_audit_file, recheck_pixels=True,
)
```

## Real Thomas 8.4 reference case

The source-bound corrected Thomas Calculus 8.4 plan has **17 slides and
48 distinct, narrated elements** split into two review videos:
slides 1–8, 291.40s/23 highlights; slides 9–17, 322.96s/25 highlights.
The generic preflight and independent audit passed. The previous real
element renderer on Dell-115, HP and Yoga6 independently demonstrated
decoded encoded highlights for 48/48 events at 0.00s timing drift.

A generic validation pass is **technical** evidence of synchronized
rendering; it does not prove mathematical meaning, accurate spoken words,
or independent lecturer approval. Thomas 8.4 has 14/48 genuine Gemini
transcripts from earlier evidence (13 machine-consistent, one flagged) and
34 without independent ASR. The required speech and academic release gates
therefore remain closed.

## Tests and release policy

The generic regression suite creates a new, unrelated 3-slide example
and checks valid 2-part source/audio coverage, missing/skipped/duplicate
slides, missing anchors and WAVs, source-hash drift, non-overwrite and the
normal runner's explicit video-review option. A separate original
no-Whisper dependency contract is always enforced. Do not merge or publish
until project-level QA and final human approval, even when all technical
highlight events are verified.
