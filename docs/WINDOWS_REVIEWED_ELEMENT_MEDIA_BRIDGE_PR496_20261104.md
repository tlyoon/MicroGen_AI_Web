# PR496 - One original-source reviewed-element MP4 review operator

**Integration of already existing production capabilities**, not an alternative
renderer and not a new round of per-PDF figure/mathematical defects.

The sourcebound element-voice review pipeline was already implemented
separately in `element_plan_review_bridge`, `element_narration_gemini`,
`element_highlight_workflow` and their production counterparts. PR496
adds ONE reusable Windows operator linking existing separately reviewed
source, authored slides, original script and SHA-pinned recorded element WAVs
to genuine decoded H264/AAC synchronized highlighted review media.

## General interface

```powershell
python -m selenium_pipeline.windows_reviewed_element_media_bridge `
  --source SOURCE_LESSON\source.pdf `
  --slides SOURCE_LESSON\slides.pdf `
  --script SOURCE_LESSON\script.txt `
  --draft SHA_FROZEN_AUTO_ELEMENT_DRAFT.json `
  --selection INDEPENDENTLY_REVIEWED_SELECTION.json `
  --tts-request SOURCE_VERIFIED_TTS_REQUEST.json `
  --audio FROZEN_ELEMENT_PCM_AND_PROOFS_DIRECTORY `
  --outdir BRAND_NEW_EXTERNAL_REVIEW_DIRECTORY
```

Required inputs must already exist. This command never invokes Gemini,
ChatGPT, paid TTS or a source-generation stage. In particular it does
NOT split original slide-WAVs to invent element-level speech. It calls
existing `element_plan_review_bridge.promoted` with the immutable
pre-synthesis TTS request and actual per-element recorded PCM proofs;
that gate independently verifies all original source/author/script
fragments and source-specific PDF geometry, model/voice identity and WAV
hashes. **Only after that preflight** does it create a new external
review directory, store an exact authored plan, and call the existing
`element_highlight_workflow.review` true FFmpeg renderer with complete
decoded pixel and audio-timing QA. Final receipt pins the original
publisher/author/script and reviewed selection, TTS request, all WAV,
and encoded MP4 SHA hashes. It cannot overwrite source, audio or prior
review, and refuses modified/tampered words, figures and audio provenance.

Review status remains strictly **REVIEW-ONLY**. This is proof of an actual
encoded synchronized multimedia review, NOT proof of human-reviewed source
mathematics or acoustic fidelity, not the final approved production MP4,
and never authorization to publish students' videos. Existing production
component `sourcebound_production_video` retains independent original
source and figure-meaning gates.

## Dell-115 qualification

Offline fixture tests use synthetic textbook/author PDFs plus deterministic
mocked Gemini PCM audio (zero paid/provider calls), but **real original
FFmpeg** and freshly decoded image pixel/voice-timing QA are executed by
the maintained renderer. Tests also modify a source PDF and a recorded
WAV receipt deliberately; each must fail before any media output.
This establishes generic integration, not a newly generated real
publisher original-source production lesson. Real Thomas/Serway original
sources remain source-bound blocked until genuine approved element
mappings and recorded PCM are available, and are not resubmitted.

Only Dell-115 native Windows, no Ubuntu, HP/Yoga, local language model,
student release or touching protected user dirty G: main worktree.
