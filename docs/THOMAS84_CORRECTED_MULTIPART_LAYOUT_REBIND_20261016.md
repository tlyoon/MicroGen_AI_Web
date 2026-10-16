# MicroGen_AI_Web — layout-only lecture correction and narration rebind

**16 October 2026 | Draft development | Technical review only**

This changes **only the visual layout** of an existing source-bound lecture.
It does **not** regenerate text or WAVs, certify the audible words, approve
mathematics, or publish student-facing content. All outputs are new, isolated,
non-overwriting review artifacts.

## Why these new fail-closed gates are necessary

The first attempt increased Thomas 8.4 slide 13's Figure 8.6 reference
triangle from 15.46% to 21.08% of slide width. That looked better visually
but pushed a narration-highlighted equation into the Beamer footer safety
band. A smaller enlargement without spacing adjustment also violated the
PDF figure/body-text clearance requirement (less than 8 PDF points).

The acceptance pathway MUST validate **all** of the following before
regenerating video:
1. Original source PDF and slide PDF SHA-256 are unchanged.
2. After an isolated LaTeX recompile, every slide except the explicitly
   corrected slide is pixel-identical to the original.
3. Extracted rendered mathematical text and actual embedded figure bytes
   are identical on **every** slide, including the corrected slide.
4. Every authored text/image/panel anchor still exists and passes the
   actual rendered-PDF positioning rules. Renumbering figures/text is not
   guessed or silently patched.
5. All 48 separately synthesized Gemini PCM narration WAVs retain the
   original SHA-256, requested-script SHA-256, named voice and model.
6. Both final MP4s remain strictly less than 600 seconds.
7. The encoded, decoded MP4 frames prove highlighting for every element;
   movement must align to the exact individual WAV duration.
8. A distinct receipt shows this was a layout-only rebind and records
   which original slide and semantic targets actually moved.
9. Production and academic acceptance remain **false** until separate
   speech and subject-content review passes.

## Actual Thomas 8.4 accepted technical review layout

One isolated Beamer source edit was permitted to resize Figure 8.6 on
**slide 13 only**:
- Existing `height=0.22\\textheight` changed to
  `height=0.27\\textheight`.
- Local in-frame layout tightened by 8pt before the image; the following
  procedural text is given 1.5pt of positive spacing.
- Result: Figure 8.6 width is **18.97%** of slide width, versus **15.46%**
  originally.
- 17 slides in both decks. **Only rendered slide 13 pixels changed**.
- Zero 8pt figure-body clearance violations across the corrected deck.
- The final narration-highlighted equation remains inside the required
  element boundary (bbox bottom 253.956pt; limit 255.126pt).
- All three targets on slide 13 were rebound from the original PDF,
  with every other narration element's geometry unchanged.
- All 48 input WAVs were cryptographically verified against the original
  voice-bound audio manifests; **no TTS calls and no voice mixing**.
- Corrected review MP4 Part 1: slides 1–8, **291.40s**, 23/23 decoded
  pixel highlights, measured transition drift 0.00s.
- Corrected review MP4 Part 2: slides 9–17, **322.96s**, 25/25 decoded
  pixel highlights, measured transition drift 0.00s.
- Reproduced with **identical technical results on Dell-115, HP and Yoga6**,
  using the same frozen, read-only staged inputs.

At first the renderer rejected a tightened-layout iteration due to inadequate
clearance between Figure 8.6 and a text block. This was diagnosed as
**the corrected slide 13 (page 5 of Part 2)**, not textbook slide 5.
The final source was corrected, **not the clearance threshold weakened**.

Canonical LaTeX implementation spells the following positive space as
`\\vspace{1.5pt}`. It was rendered independently and confirmed pixel-identical
to the earlier equivalent double-minus TeX test expression; this does not
authorize substituting a different PDF hash in an existing provenance receipt.

## Generic commands (fresh output destinations required)

```powershell
python -m selenium_pipeline.figure_resize_review `
  --source ORIGINAL_SUBCHAPTER_FOLDER `
  --destination NEW_CORRECTION_FOLDER `
  --image "Figure 8.6.png" `
  --old-height 0.22 --new-height 0.27 --slide 13 `
  --compact-before-image-pt 8 --compact-after-image-pt -1.5

python -m selenium_pipeline.layout_only_rebind `
  --source ORIGINAL_SOURCE_PDF --old-slides ORIGINAL_SLIDES_PDF `
  --new-slides NEW_CORRECTION_FOLDER/slides.pdf `
  --voice-plan ORIGINAL_GEMINI_VOICE_BOUND_PLAN `
  --audio ORIGINAL_GEMINI_WAV_DIRECTORY `
  --figure-receipt NEW_CORRECTION_FOLDER/figure_resize_receipt.json `
  --out-plan NEW_REBOUND_PLAN_JSON --out-receipt NEW_REBIND_RECEIPT_JSON

python -m selenium_pipeline.element_narration_cli `
  --source-pdf ORIGINAL_SOURCE_PDF --slides-pdf CORRECTED_SLIDES_PDF `
  --authored-json NEW_REBOUND_PLAN_JSON --recorded-audio ORIGINAL_WAV_DIR `
  --destination NEW_FROZEN_STAGED_INPUTS

python -m selenium_pipeline.series_review_cli `
  --source-pdf ORIGINAL_SOURCE_PDF `
  --prepared-parts NEW_FROZEN_STAGED_INPUTS `
  --output-root NEW_REVIEW_RENDER_DIR

python -m selenium_pipeline.element_series_audit `
  --source ORIGINAL_SOURCE_PDF --slides CORRECTED_SLIDES_PDF `
  --authored NEW_REBOUND_PLAN_JSON --audio ORIGINAL_WAV_DIR `
  --staged NEW_FROZEN_STAGED_INPUTS --rendered NEW_REVIEW_RENDER_DIR `
  --old-slides ORIGINAL_SLIDES_PDF `
  --previous-voice-plan ORIGINAL_GEMINI_VOICE_BOUND_PLAN `
  --rebind-receipt NEW_REBIND_RECEIPT_JSON `
  --figure-resize-receipt NEW_CORRECTION_FOLDER/figure_resize_receipt.json `
  --report NEW_TECHNICAL_REVIEW_REPORT
```

The full-series audit rejects a rebound plan that lacks *any* of the four
origin files, uses an altered previous voice plan, contains changed spoken
words, has stale audio provenance, or claims unverified academic approval.

## Artifacts and release status

The separate private Drive review folder contains two playable MP4s,
source-bound corrected slides.pdf, audio-provenance receipts, both original
and rebound authored scene plans, before/after figure screenshots,
the technical audit, and frozen reproducibility inputs.

**Not yet resolved:**
- Only three of 48 original spoken segments had earlier independent model-ASR
  review receipts. The other 45 remain untranscribed owing to ASR service
  outages. The rebind technical audit does **not** claim that those older
  transcripts cover its new authored-plan hash.
- Formal mathematical/academic approval and lecturer listening/viewing
  review have not been carried out.
- PR #91 and successors remain **draft/unmerged**.
- No student-facing file replacement, Moodle publication, production
  completion receipt or published corrected lecture is authorized.
