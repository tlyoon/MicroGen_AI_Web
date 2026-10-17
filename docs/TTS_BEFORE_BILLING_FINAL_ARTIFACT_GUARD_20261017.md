# MicroGen_AI_Web: reject protected audio before any TTS billing

**17 October 2026. Review-only change, stacked on PR #115. No real audio produced or API charge initiated in this development round.**

## Risk observed

Even after PR #115's strict Gemini model/voice, cache SHA receipts, and different-final-WAV overwrite protection, the normal TTS engine could generate (and potentially pay for) a complete set of new narration WAVs **before** discovering an already published `slideN.wav` or `tts_input_manifest.json` must not be overwritten. The worker subprocess also allowed `write_bytes()` on an arbitrarily pre-existing output path if manually invoked with an explicit provider cost flag.

These behaviors conflict with the agreed requirement to preserve all prior lecture outputs and avoid unreviewed billable work.

## Implementation

- **Final-artifact preflight:** `selenium_pipeline.tts_candidate_integrity.reject_existing_final_audio(folder)` scans the target folder for any final numeric `slideN.wav` (case-insensitive) or `tts_input_manifest.json`. Presence of even one file, malformed/legacy metadata or symlink causes a fail-closed error **before** checking credentials, initializing a provider, creating a new candidate job or making any paid TTS request. No file is adopted, renamed, overwritten or deleted. Independent verified reconciliation must happen in an isolated new output workspace, not a silent rerun.
- **Validated candidate resume is still available:** when no final artifacts exist, exact source/model/voice/audio-bound candidate receipts from PR #115 can be checked and safely resumed or fully published. Unverified legacy candidate WAVs remain preserved and blocked.
- **Direct TTS worker output:** refuses existing/symlink output path **before** reading the narration and issuing a request, and writes new WAVs with exclusive `open("xb")` semantics. A direct caller cannot spend credits and silently overwrite an existing file through this worker. The normal watchdog's output path is already a unique local temporary directory.
- Prior **explicit provider-cost opt-ins** from PR #114 remain necessary, and **automatic model/provider substitution remains disabled** by PR #115.

## Verification and limitations

Offline regression fixtures prove:
- Existing final WAV with different or identical bytes blocks any new Gemini call.
- Manifest-only and uppercase WAV filename collisions block any regeneration.
- Already verified partial candidates are unchanged when a final file blocks a run.
- Zero provider calls on protected worker outputs; new worker output is created exclusively in a fresh isolated folder.
- Normal first-run synthesis and verified candidate resume are not accidentally blocked.
- The historical TTS collision fixture was updated to assert **no request**, rather than expecting a simulated provider outage before the old collision check.

This change does **not** authorize re-publication, automatically reconcile historical files or replace real academic review. It does not claim a provider-generated 3.8 Flash-Lite/Kore WAV; all tests are offline. Independent speech content, exact figure-panel and equation mapping, encoded-pixel highlights, and **every MP4 part strictly shorter than 600 seconds** remain required before production acceptance.

**Additional future audit:** The separate selective TTS QA repair subsystem can replace staged audio after attempting quality repair. Before any production deployment, review its archival and source-bound provenance handling separately. Do not use this PR's passing tests to claim that older production material is safe to regenerate.

Do not merge stacked drafts, change shared Drive-synced dirty checkouts, access Zenbook, or publish any student-facing outputs as part of this review.
