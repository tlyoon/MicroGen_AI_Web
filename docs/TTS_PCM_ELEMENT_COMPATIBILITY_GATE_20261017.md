# Reviewed TTS audio: PCM and element-level compatibility (2026-10-17)

Review-only, non-billable change stacked after draft PR #118.

## Problems addressed

1. Matching a WAV SHA256 and RIFF header alone does not prove audio is decodable. A corrupted WAV can also have a perfectly correct hash. The reviewed TTS handoff now validates full RIFF/WAVE length, decoded sample frames, uncompressed 24000 Hz / 16-bit / mono PCM, and 0.2–120 second duration on all original, proposed, and earlier repair-attempt files.
2. A reviewed slideN.wav contains narration for the *whole slide*. It is not automatically equivalent to separate recorded narration for equations, figures, and paragraph highlights. The read-only compatibility gate rejects plans using multiple narrated elements on a slide rather than assuming or inventing timing boundaries.

## Offline preflight

python -m selenium_pipeline.tts_reviewed_element_compat --source-pdf SOURCE_PDF --slides-pdf SLIDES_PDF --authored-plan ELEMENT_PLAN_JSON --reviewed-audio ISOLATED_AUDIO_FOLDER

Requires a prior independent-audio handoff receipt, original source/slides hashes, exact Flash-Lite/Kore provenance, manifest/script/WAV SHA256 matches, valid decoded audio, matching text for the sole narrated element on every slide, and strict audio timing via the existing element-highlight preflight. Returns REVIEW_ONLY_AUDIO_ELEMENT_COMPATIBILITY, not academic review, a video approval or student-publication permission.

Multi-element slide narration requires *separate* source-bound per-element audio with independent listening review. Splitting or duplicating a slide WAV without verified speech boundaries is forbidden. Figure crops and mathematical content still need visual review.

No paid Gemini or Google Cloud calls; no Whisper/ASR; no default model switching; original audio, PDFs, MP4s and Drive-synced dirty code trees preserved. The standard release contract remains: all video parts strictly shorter than 600 seconds, real decoded-pixel element highlighting synced to the spoken WAV, accurate figures, human academic review, and explicit permission before Moodle publication.

All changes are draft and are not deployed to production.