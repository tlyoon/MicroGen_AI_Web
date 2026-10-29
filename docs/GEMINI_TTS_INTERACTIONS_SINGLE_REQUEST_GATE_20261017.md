# Contract-safe Gemini 3.8 Flash-Lite / Kore Interactions TTS trial

**17 October 2026 — review only; no billable request executed in this development round.**

## Why the change was needed

Google's current official [TTS documentation](https://ai.google.dev/gemini-api/docs/speech-generation) specifies `google-genai >= 2.25.0` and `client.interactions.create` for Gemini 3.8 speech, with an `input` text transcript, a `speech_metadata` annotation, `generation_config.speech_config=[{"voice":"Kore"}]`, and `response_format={"type":"audio"}`. Unary responses are documented as complete RIFF WAV files (24 kHz mono 16-bit PCM).

The historical MicroGen `selenium_pipeline.tts._gemini_say` uses an older `models.generate_content` pattern. Passing simulated model tests is *not proof* that the old pattern works with 3.8 TTS. This trial is a separate, strictly isolated adapter; it **does not silently replace** the production renderer, TTS backend, or paid-API authorizations from PR #108.

The user's established contract still controls: Gemini 3.8 Flash-Lite TTS with Kore, no Whisper, no automatic Google Cloud Chirp fallback, no hidden metered API call, slide/element highlighting synchronized with the actual speech, MP4 parts **strictly shorter than 600 seconds**, no source-output replacement, no academic approval and no student publication by technical tests alone.

## Implementation

`selenium_pipeline.tts_interactions_trial` has two modes:

- **Default/offline:** checks installed SDK version, prepares the canonical fixed synthetic sentence and model/voice request identity, and writes an immutable isolated `preflight.json`. **Does not load credentials, instantiate the SDK client or access the network.** `api_request_started=false` and `real_audio_generated=false`.
- **Explicit live synthetic trial:** enabled **only** if all three CLI flags are present: `--confirm-synthetic-trial --confirm-gemini-api-cost --confirm-live`. Never inferred from normal `Proceed` instructions. Uses the single approved model/voice and exactly one API key with SDK retries set to one attempt, no key failover, no model substitution, no Cloud TTS or Whisper. A new isolated directory must be provided. Writes an exclusive `request_intent.json` before the request and accepts only fully decodable PCM RIFF WAV; receipt includes audio SHA-256, duration, sample format, input/request SHA-256 and **all academic/production approvals false**. On any missing/invalid/ambiguous response, writes a sanitized failure receipt and does not retry. This CLI does not take or upload any course text.

Even a genuine trial WAV proves only transport capability, not that the speech sounds like Kore or reads mathematical notation correctly. Separate Gemini independent ASR and human listening review remain necessary for the course pipeline.

## Observations on authorized PCs

- Dell-115 and Yoga6 both report `google-genai 2.25.0`.
- The current SDK method exists; its Python signature accepts `**body`, not individual named `model`/`input` keywords in the signature. This is consistent with the documented keyword call but is **not** proof of server acceptance until a real authorized test.
- A default preflight on each machine wrote `API_INTERACTIONS_PREFLIGHT_ONLY`, matching request hash `7b26bd09a386bb1f1e49c391fba65a553187487b9b0f3f6393b6f7d12c17402c`, no WAV, no credential read and no API request.
- Offline tests with injected fake clients cover the exact request format, valid WAV, incorrect WAV/mime/base64/silence, absence of a key-read on preflight, forbidden partial confirmation flags, stale SDK, no overwrites, source-root exclusion and failure receipts. **Mocked WAVs are not real synthesized audio.**
- Prior Google AI Studio browser probes showed no selectable Flash-Lite/Kore editor in the logged-in session. This independent API trial does not claim to repair that UI or turn it into a free browser path.

## Safe CLI (no billing)

From an isolated up-to-date project checkout, using a **new** directory not within the teaching source tree:

```powershell
python -m selenium_pipeline.tts_interactions_trial --output-dir "$env:TEMP\microgen_interactions_check_NEW"
```

No secret data is written to the receipt.

## Live trial — deliberately NOT executed

The following is a documented command template, **not an instruction to execute without explicit cost authorization**:

```powershell
python -m selenium_pipeline.tts_interactions_trial `
  --output-dir "$env:TEMP\microgen_interactions_live_NEW" `
  --confirm-synthetic-trial `
  --confirm-gemini-api-cost `
  --confirm-live
```

The requested TTS is a synthetic, non-course sentence only; billing tier cannot be inferred from locally stored credentials. Consult the current official [pricing](https://ai.google.dev/gemini-api/docs/pricing) before authorizing any expense.

## Still blocked

1. Actual server acceptance of the Interactions request and one genuine WAV.
2. Independent speech/voice verification of any real generated audio.
3. Integration of demonstrated transport with **approved** element segmentation without changing the existing production contracts.
4. Full three-PC verification (HP currently offline), reconciliation of uncommitted shared Git working trees, production acceptance and eventual release authorization.

PRs #106 onward remain review-only stacked drafts. Do not merge or publish this branch as a production release on the strength of synthetic tests.
