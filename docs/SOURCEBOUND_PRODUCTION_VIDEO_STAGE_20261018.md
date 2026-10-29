# MicroGen_AI_Web production source-bound highlighted video stage

18 October 2026. Draft development on PR #137, stacked on draft PR #136.

## What is implemented

The old static slideshow encoder cannot provide element-synchronized highlighting and strict multipart splitting. Previously the normal runner blocked every new video. The generic source-bound renderer produced independently checked review-only parts, but no standard technical production receipts.

The new selenium_pipeline/sourcebound_production_video.py bridges those paths without pretending that review-only assets already count as production.

It independently rechecks the original source PDF, every slide, the entire source-grounded authored element plan and every frozen original element WAV using the existing element_highlight_workflow.verify_rendered with fresh decoded MP4 pixel QA (beginning, middle and end of speech and unhighlighted pauses). It copies into a new isolated candidate, rechecks source/audio hashes and actual encoded pixels again, then constructs source-bound visual_cues.json, narration_alignment.json, part_receipt.json and lecture_completion.json. It verifies those standard receipts using production_video_contract.verify_series before any installation.

Installation is non-overwriting: new part_NN folders and a final completion receipt are added beside source.pdf only after matching the source and slide hashes. Existing source.pdf, slides.pdf, narration WAVs, slides.mp4 and any existing parts or accepted lecture are never replaced. If an install fails midway, only newly claimed assets are rolled back; each installed MP4 is independently decoded and checked again.

The regular runner video-only path and three-PC video stage use this process automatically, without human academic approval, when genuine source-bound element-level inputs exist. If those inputs are absent, the old static slideshow renderer remains disabled.

## Required source-adjacent inputs

- slides.pdf: the actual complete slide deck
- element_narration_plan.json: complete source-anchored element geometry, spoken text, part boundaries and WAV file mapping for every slide
- element_wav/: a distinct original PCM WAV per spoken element
- element_tts_manifest.json: SHA-256-bound original source, slides, plan, each WAV and spoken-text hash, with a homogeneous effective model and voice

The manifest status is verified_source_bound_element_audio, schema version 1. Authorized identities: Gemini Flash-Lite TTS/Kore first, Gemini Flash TTS/Kore after fallback, conditional Cloud Chirp3 HD/Corey after the required retries. Mixed voices or unproven Cloud fallback are forbidden. The manifest asserts technical provenance only, not independent server-model proof or human listening.

To process a fully prepared lecture on its assigned worker:

    python -m selenium_pipeline --source-root SOURCE_ROOT --subchapter 8.4 --from-stage video --through-stage video

The standalone adapter accepts a previously verified review bundle:

    python -m selenium_pipeline.sourcebound_production_video accept --source SOURCE_PDF --slides SLIDES_PDF --authored ELEMENT_PLAN --audio ELEMENT_WAV_DIR --review-root PREVIOUS_REVIEW_DIR --candidate FRESH_CANDIDATE_DIR

It also provides separate verify and install subcommands, with new destinations and no destructive replacement.

## Contract constraints and incomplete upstream work

Every part MUST be strictly less than 600 seconds. Encoded highlighting must follow the narration at the specific source slide element, with complete multipanel images. Human academic approval is OPTIONAL for stage progression and not fabricated. No Whisper, external GCS lease, Zenbook or Moodle publication is used. YouTube publication requires the independent authorized channel and whole-course technical QA.

**Important:** The regular slide TTS stage still generates slide-level, not per-element WAVs. The missing upstream automatic generation of accurately segmented element narration, anchored plans, individual WAVs and their technical manifest remains a blocker for a fully unattended source-to-video campaign. This draft hardens and connects the downstream real production renderer only when those genuine inputs exist. Do not treat synthetic acceptance tests as proof existing Thomas Calculus/Serway lectures already meet this contract.

No original production assets or YouTube credentials were changed while developing this isolated branch.
