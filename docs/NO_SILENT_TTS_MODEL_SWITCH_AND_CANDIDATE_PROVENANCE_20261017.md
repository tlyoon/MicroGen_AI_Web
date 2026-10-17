# MicroGen_AI_Web — No silent TTS model switch, no unverified cache reuse

**17 October 2026 — review-only patch stacked after PR #114. No paid API, no student publication and no existing course asset modification.**

## Corrected contract violation

Earlier TTS logic automatically substituted `gemini-3.8-flash-tts` when the configured `gemini-3.8-flash-lite-tts` job exhausted its retry queue. A measured voice-similarity score (even 99%) cannot make these different models the same configured engine, guarantee narration consistency, or authorize a new billable provider request. A second code path could silently regenerate an *entire batch* under the other model. Google Cloud Chirp was previously removed as a Gemini fallback in PR #110, but automatic Gemini model switches remained possible until this patch.

**New rule:** `_fallback_specs` returns no alternate provider/model candidates for any TTS job. Legacy `MICROGEN_TTS_ENABLE_PROVIDER_FALLBACK=1` and `MICROGEN_TTS_ENABLE_BATCH_FALLBACK=1` cannot override this. When the configured model fails after the established bounded retry queue, the job reports an unresolved error, preserves already successful source-bound candidates, does not publish partial audio and leaves model choice unchanged. Switching to a different TTS model needs a *separate reviewed, explicitly cost-authorized job* with consistent voice and source checks, not an automatic repair. Standard model remains **Gemini 3.8 Flash-Lite TTS / Kore**.

## Hidden cache-provenance defect corrected

Previously the main `selenium_pipeline.tts` workflow accepted any existing `.tts_candidate/slideN.wav` that had a RIFF header and size above 44 bytes. It could therefore re-label previously synthesized Flash or Chirp audio as Flash-Lite/Kore, or reuse speech for an *older script*, even without any declared alternate-model fallback.

New `selenium_pipeline.tts_candidate_integrity` binds a candidate job to:
- Exact provider/model/voice
- SHA-256 of the complete narration script and each slide's original text
- Exact candidate WAV SHA-256 and the frozen job-identity hash

Each newly synthesized candidate receives a one-shot `slideN.wav.verified.json` receipt, with an immutable candidate job identity created before requests. A candidate can resume only when every existing WAV and receipt agrees with the current exact source/model/voice identity. Legacy unverified WAVs, partial files, mismatched models/voices/script, tampered WAV bytes, orphaned receipts or unexpected slide numbers **fail closed, without deletion or silent adoption**. The historical unverified candidate may require separate manual reconciliation; the patch does not overwrite it to make a new run seem successful.

The final publication path refuses to overwrite any existing **different** `slideN.wav` or different TTS input manifest. After a complete successful batch, receipt sidecars and the candidate job identity are retained under `.tts_candidate_receipts/<unique_run_id>` for audit; the published manifest retains the selected primary provider, model and voice. The path is not a new academic or course-release approval.

## Verification

- Unit and integration tests for exact verified cache reuse, different provider model, changed voice/script, missing/altered proof, old legacy unverified candidates, partial/orphaned files, published-output immutability and audit retention
- Mocked TTS outage with previous valid slide 2/3 audio: no per-slide fallback, no whole-batch alternate-model regeneration even when old fallback toggles explicitly equal 1
- Other publication contract remains unchanged: each MP4 **strictly shorter than 600 seconds**, appropriate equation/figure/paragraph element highlighted in sync with the *actual* audio, figure-panel integrity, source QA and academic approval separate
- **Zero** new real Gemini API/Google Cloud charges, no use of Whisper/ASR substitution, no direct edits to production working trees on Dell-115, Yoga 6 or HP, no Zenbook, no Moodle/student publication

## Explicit limitations

The enhanced candidate cache receipts prove that local bytes have not changed and their declared input identities match; they do **not** prove the provider actually spoke the intended words or selected the voice acoustically. A real provider WAV, independent listening/content validation, complete mathematical figure QA and real encoded-video timing acceptance are still required before release.

These changes are draft review work only. Do not merge stacked PRs to main, or mutate original lecture outputs, until their unresolved acceptance gates have been satisfied.
