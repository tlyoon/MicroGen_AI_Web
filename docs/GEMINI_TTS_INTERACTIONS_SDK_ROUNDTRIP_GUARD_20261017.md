# Gemini 3.8 Flash-Lite/Kore SDK round-trip contract guard

**17 October 2026 — review-only, offline. No live API request or production publication.**

## Why PR #112 needed one more control

PR #112's source-independent synthetic Interactions trial verified fake-client WAV handling and separate live-cost authorization flags, but successful fake-client tests did not verify what the **actual** installed `google-genai` SDK serializes to HTTP or parses from an HTTP response. In addition, the trial only validated decoded WAV bytes, without checking the provider-returned model identity or completion state. A forged or mismatched provider response could then have produced an overconfident receipt.

## Confirmed SDK evidence on authorized PCs

On **Dell-115 and Yoga6**, with installed `google-genai==2.25.0`, tests use a deliberately invalid placeholder API key and intercept the HTTP client's `send` function **before any socket/network operation**. The actual SDK generates exactly one `POST /v1beta/interactions` request with model `gemini-3.8-flash-lite-tts`, `generation_config.speech_config[0].voice=Kore`, `speech_metadata` for the fixed synthetic text and `response_format={"type":"audio"}`.

An intercepted `HTTP 200` fixture carrying `model=gemini-3.8-flash-lite-tts`, `status=completed`, and base64 encoded `audio/wav` is parsed by the genuine SDK. The trial WAV checker recovers the exact original bytes and verifies complete non-silent 24 kHz, mono, 16-bit PCM audio. A separate intercepted `HTTP 403` fixture yields **one attempted HTTP send only**, with SDK retries configured as one attempt. **These are offline fixture responses, NOT real Gemini speech.**

The TTS trial is additionally hardened to reject any response without exactly `model=gemini-3.8-flash-lite-tts`, `status=completed` and `output_audio.mime_type=audio/wav`, even if a syntactically decodable WAV appears. Accepted synthetic trials record `provider_response_model_verified=true` and `provider_completion_status_verified=true` while leaving speech/voice quality, academic approval and publication false. Failures record a sanitized immutable failure receipt and disable automatic retries.

## New repeatable checks

- `tests/test_tts_interactions_sdk_wire.py`: real-SDK offline HTTP serialization and fake-response parse, rejection with no retries. Does not connect to Google or read credentials.
- `tests/test_tts_interactions_trial.py`: extra model-identity, status and MIME mismatch tests plus failure receipt and no-overwrite assertions.
- Both Dell-115 and Yoga6 passed the **12** trial and **2** real-SDK intercepted-wire tests, with no paid API or source modifications.

## Contract and deployment state

All changes are stacked in a **new draft PR** after #112 and kept out of the stale shared Drive working trees, which contain uncommitted user changes. No Whisper or prohibited ASR engine, automatic Google Cloud Chirp TTS, silent model switch, hidden billed API usage, original-file overwrite, student publication or bypass of synchronized highlights/duration acceptance is permitted. Exact target voice **Kore** is still unverified acoustically until independently listening to real provider audio.

**Still blocked:** Google's real server acceptance of one explicitly authorized billable Flash-Lite/Kore synthesis, authentic generated audio and separate voice/word-fidelity checks. The normal browser UI remains unverified for this exact TTS model. Prior synthetic QA/FFmpeg tests do not establish course release eligibility. The `--confirm-synthetic-trial --confirm-gemini-api-cost --confirm-live` flags must be supplied together for any real API trial; do not interpret generic development approval as cost approval. HP acceptance testing awaits online access. The original <600-second per-part and element-level narration-highlight synchronization requirements remain mandatory.
