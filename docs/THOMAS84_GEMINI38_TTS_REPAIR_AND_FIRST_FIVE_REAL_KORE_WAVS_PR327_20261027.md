# PR327 — Gemini 3.8 TTS SDK repair, genuine five-utterance Kore audio and real PCM-timed Slide-4 MP4 (27 October 2026)

## Root-cause diagnosis

The first genuine original-source Slide4 utterance TTS trial failed with `AttributeError` **before any network request** because Dell-115's old `google-genai==1.4.0` lacked `types.HttpRetryOptions`. The legacy code was also using `generate_content` rather than the documented Gemini 3.8 TTS Interactions API, and the initial Interactions draft passed a raw string where the API requires `[{"type":"user_input","content":[{"type":"text","text":...}]}]`. These defects are fixed in `gemini38_tts_interactions`, `gemini_keys` and `tts`.

The vendor's published TTS documentation: https://ai.google.dev/gemini-api/docs/speech-generation ; minimum Python SDK `google-genai>=2.25.0`, unary audio returns base64-encoded `audio/wav` RIFF container, not bare PCM, default 24 kHz mono PCM16. The adapter routes only approved Flash-Lite/Flash 3.8 models, with original **Kore** voice and an exact source-locked utterance string (no stage-direction contamination) through `client.interactions.create` with structured user input. It canonically verifies the returned WAV and refuses missing/unparseable audio. All model/API calls are made only after an SDK version/endpoint preflight.

**Windows-only, Dell-115 local deployment:** installed `google-genai==2.33.0` in isolated `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261027_GEMINI38_SDK_ISOLATED_VENV` without modifying Dell's existing system Python. Configured `MICROGEN_TTS_WORKER_PYTHON` in its private `%LOCALAPPDATA%\Microvid\.env`; general TTS watchdog now discovers that interpreter from normal production environment and checks its SDK BEFORE spending credits. No password/API keys committed, exported or printed. Existing G: dirty working tree remains untouched. No Ubuntu/Linux checks, no HP/Yoga6/Zenbook, no Whisper. Google Cloud Chirp fallback not called.

## Genuine provider output — FIVE new Kore-requested candidate WAVs

One FIRST utterance request was sent exactly once with actual compatible Gemini 3.8 Flash-Lite Interactions API. It returned genuine canonical PCM16 WAV and sanitized provider success evidence. The remaining 4 were generated with one-use per-utterance claims, exactly one configured provider key, local SDK retries=1, no automatic resubmission or Cloud fallback. Exclusive true source-SHA locked external folder:

`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261027_PR327_REAL_CORRECTED_FIVE_KORE_CANDIDATES_QUARANTINED`

| Original Slide-4 registered utterance | Corrected WAV duration (s) | SHA256 |
| --- | ---: | --- |
| 001 | 22.76 | `2a259d3da38f724f55252e8cabcf3c41cc4fbb034136e0389e89215f9ce76091` |
| 002 | 30.28 | `fdaa394d604b49bf771df6bc87e6b98f38c0db184925049ee2bbd4cf719db1cd` |
| 003 | 33.92 | `de4729d9e253e77479c6e1e6c84ad40cacb831e9ebe4cc0c8f9e9350bc3a6e14` |
| 004 | 32.56 | `b52bd27235a470d7293ffd408b5d31f0cc556f43b090a9d3c7b1273b94293b67` |
| 005 | 23.60 | `98518862b1f61cb5d02e6500e4d0ab74e582c6e69e6876b0a117bfff9e69f6be` |

These are **genuine new audio** with total 143.12s, each individually decoded mono/16-bit/24 kHz and non-identical to any historical protected 8.4–8.6 WAV. All five text SHA-256 identities correspond to PR319's independently source-PDF-registered corrected transcript. Each provider worker reported success (no provider request ID exposed; don't fabricate one). Requested voice **Kore** and provider model **Flash-Lite 3.8** recorded as the actual request settings, NOT independently certified audible speaker identity. Academic two-pass source verdict was NOT returned by Gemini web and remains a separate blocked condition; the previously consumed older academic request was not resent.

## Genuine corrected speech-to-highlight *chunk* review MP4

The already tested PR326 60-fps five-chunk source-PDF-element rendering pipeline was executed on ALL FIVE newly generated actual WAVs, never historical audio. The genuine PDF text/Figure8.2 mapped highlights are switched at real measured PCM chunk boundaries and decoded-pixel verified. **Actual H.264/AAC MP4 runtime 143.12s**, matches summed PCM durations, below 600s. Private review-only external output:

`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261027_PR327_REAL_KORE_PCM_FIVE_SOURCE_HIGHLIGHT_REVIEW_MP4`

All five visual source-pixel samples verified. The resulting MP4 has an unmistakable red `REVIEW ONLY – WAV WORDS AND KORE VOICE UNVERIFIED` banner and is **NOT** student-ready. PCM frames alone cannot prove words/voice identity; model-specific audible assessment and independent source mathematical review are still required. Original source.pdf, slides.pdf, script.txt, slide4.wav, slides.mp4 and protected G repo untouched. No publication to Moodle or YouTube.

## Speech-content quality checks without Whisper or paid recognition API

Windows local SAPI (en-US) can decode WAV but misrecognizes substantial math vocabulary, therefore not reliable for acceptance. The separate free Apache-2.0 Vosk 0.3.45 small-English ASR model (official `https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip`) was installed in an independent isolated AppData Windows environment; model ZIP 41,205,931 bytes, SHA256 `30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498`. A true unprompted offline first-WAV Vosk transcription recovered almost the exact source-locked corrected utterance including `negative`, `absolute value`, `signed leg`, `reference angle`, `zero`, and `degenerate`. No Whisper installed; no additional recognition API cost. Follow-on PR can quantitatively recheck all five with WER, independent transcript evidence and adverse-case tests. Do not elevate a free dictation model to indisputable word accuracy.

## Testing and strict next release gate

- Isolated modern SDK (2.33.0) offline tests **11 PASS** for actual official nested Interactions format, base64 PCM WAV, exact Kore voice model, no-cost SDK preflight, one-shot quarantine, and malformed WAV rejection.
- Genuine Dell one-shot provider outcomes: **five verified PCM candidates**, no Cloud fallback, original source SHA protected.
- Genuine real corrected-source review MP4: **143.12s, five decoded actual original-source-element pixels verified**.
- Formal source mathematics: independent Wolfram 13/13 exact trig/domain/root/endpoint checks plus SymPy; does not claim missing independent two-pass source model/human academic review verdict.
- **Never merge/publish an unapproved MP4**. Final gate requires source-grounded independent mathematical consensus, spoken-content and stable Kore-voice QA, true chunk-to-element synchronization QA, and the six new accepted, correctly split (<600s each) videos from §§8.4–8.6. No private source/media exported to GitHub.
