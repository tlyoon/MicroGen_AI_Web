> **PR #139 EXTENSION:** The formerly one-block-only requirement below now extends to multiple distinct, explicitly paragraph-delimited, verbatim source-grounded text blocks per slide. No images, vector figures or ambiguous math are permitted. See [verified multi-element narration](VERIFIED_MULTI_ELEMENT_NARRATION_20261018.md).

# MicroGen_AI_Web — automatic exact-text element narration & TTS

**18 October 2026. Draft source-grounded upstream bridge, stacked on PR #137.**

The owner has authorized **automatic internal-stage progression without routine
human academic approval**. The stage uses the current approved paid Gemini
Flash-Lite/Kore speech generator and inherits its exact 3-attempt primary,
Flash/Kore secondary and conditional Cloud Chirp3 HD/Corey full-batch policy.

## Strict supported case: one complete narration per visible text element

The new modules `automatic_element_narration.py` and
`automatic_element_audio_stage.py` create the missing prerequisite for
production highlighted multipart video **only for an unambiguous case**:

- Each slide has a single distinctive visible body text block whose content
  matches its complete existing narration block **exactly**, not a generated
  paraphrase; the verbatim words must occur on exactly one textbook page.
- No figures or image panels occur on those slides. Any composite images,
  images, drawings or ambiguous text/source mappings require further source-
  grounded design; their meaning cannot be correctly inferred from lexical
  matching. **No paid TTS call** occurs when this preflight fails.
- Each text block has a valid rendered non-clipped rectangle verified by the
  existing `element_narration_stage.rectangle` gate.
- The source PDF, slide PDF and existing narration script are SHA-256-bound.
  Exactly one distinct TTS narration WAV is requested for each source-bound
  text element using the existing Flash-Lite/Kore batch engine, without
  changing the text.
- The *actual* TTS batch manifest is checked with
  `tts_effective_identity.verify_effective_identity`; when a fallback
  occurred, the original observed chained `AttemptEvidence` is verified,
  never fabricated. Full-batch effective model/voice identity must be uniform.
- Each WAV must be mono, 16-bit, uncompressed PCM, 0.2–120s. Coherent
  multipart boundaries are calculated **after measuring real WAV durations**,
  targeting less than 540 spoken seconds per part (an additional encoding
  safety margin below the mandatory 600-second ceiling).
- The final plan status is
  `machine_verified_exact_text_element_narration` — **not**
  `author_specified_unapproved_element_narration`. Later video staging and
  pixel QA recompute the original source/slide/script mapping. No human
  academic review is invented or required for the next technical stage.

## Protected outputs and contract

After complete TTS generation and QA, the stage installs **new files only**,
beside the original textbook subchapter:

    element_narration_plan.json
    element_wav/sNNN_e01.wav
    element_wav/_producer/script.txt
    element_wav/_producer/tts_input_manifest.json
    element_wav/_producer/.tts_attempt_evidence/   (only if fallback)
    element_tts_manifest.json

The original source.pdf, slides.pdf, script.txt, slideN.wav, historical
slides.mp4 and any already accepted video parts are never overwritten.
Existing/partial element outputs block instead of being silently reused or
replaced. Provider-failure diagnostics remain in isolated local AppData
staging; only newly created outputs from a failed install may be rolled back.

## Normal runner/three-PC integration

For one subchapter with source.pdf, slides.pdf and a valid script.txt:

    python -m selenium_pipeline --source-root SOURCE_ROOT --subchapter 8.4 --from-stage video --through-stage video

When an exact, ambiguity-free text-only mapping exists and no previous
element outputs exist, the runner automatically generates the individual
WAVs using the production TTS policy, installs the source-bound plan and
manifest, and hands off to the PR #137 highlighted video renderer. No routine
human consent is requested. The assigned HP/Dell-115/Yoga6 worker uses the
same route; Zenbook remains excluded.

**Honest current limitation:** Most actual lectures contain diagrams,
equations, rendered multisource blocks and narration that paraphrases
textbook/slide elements. The conservative exact-text matcher appropriately
blocks those. A next incremental task is *reliably producing and validating*
multielement mathematical and full-panel figure anchors, not weakening the
invariants. This is a real end-to-end pilot path for a narrow supported
content class, NOT a declaration that Thomas/Serway production is universally
unblocked.

All development tests mock TTS outputs and use local synthetic PDF/FFmpeg;
there are no actual Gemini/Cloud paid calls, no YouTube uploads, no Moodle
publication and no modifications to the original three-PC production
repositories in this development round.
