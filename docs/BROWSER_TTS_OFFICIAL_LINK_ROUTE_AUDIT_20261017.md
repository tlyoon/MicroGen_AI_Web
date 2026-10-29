# Official Flash-Lite TTS model-link route audit (17 October 2026)

**Scope: read-only browser development evidence. No actual audio produced, no charge initiated by this check.**

## Why this matters

The owner-approved production configuration is Gemini 3.8 Flash-Lite TTS, Kore voice, separate source-linked WAV per spoken element, synchronized highlights and MP4 parts **strictly shorter than 600 seconds**. No Whisper, silent paid Gemini API fallback, expensive Google Cloud Chirp fallback, unreviewed academic signoff, student publication, or overwrite of original PDF/slide/WAV/MP4 is permitted.

The official Google model documentation published on 9 October 2026 confirms:
- `gemini-3.8-flash-lite-tts` is a supported API model: https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash-lite-tts
- Kore is an advertised studio voice: https://ai.google.dev/gemini-api/docs/speech-generation
- Gemini API has separately described free and paid TTS pricing tiers: https://ai.google.dev/gemini-api/docs/pricing

**These published facts do not prove that a signed-in Google AI Studio session is using that exact model, voice or pricing tier.** Any actual paid Gemini Flash-Lite API route must retain the explicit `--confirm-reviewed-tts-request`, `--confirm-gemini-api-cost`, and `--confirm-live` authorization gates from PR #108. An ordinary `Proceed` instruction must not become a hidden API opt-in.

## Live authenticated Dell-115 experiments

1. Original Google AI Studio `/generate-speech` read-only preflight: visible model card `gemini-3.8-flash-tts` only; no selected Flash-Lite, Kore voice, editor or verified download. Session showed `No API key selected`.
2. Official Flash-Lite documentation deep link: `https://aistudio.google.com/?model=gemini-3.8-flash-lite-tts`. The authenticated Chrome UI redirected to `https://aistudio.google.com/generate-speech` and **the model query parameter was dropped**. No verified model selector, voice choice or editable speech prompt was exposed. The link itself does **not** force or prove model selection.
3. New reproducible CLI check, no submitted audio: `python -m selenium_pipeline.browser_tts_preflight --model gemini-3.8-flash-lite-tts --voice Kore --check-official-model-link --output NEW_ISOLATED_RECEIPT.json`. Live receipt: `official_model_link_requested=true`, `official_link_query_retained=false`, `official_link_is_selection_proof=false`, `selected_model_verified=false`, `selected_voice_verified=false`, `usable_for_automatic_element_tts=false`. The only observed model remains `gemini-3.8-flash-tts`.
4. Read-only DOM survey of the landing page: `visible_text_entry_count=0`, `combobox_count=0`, iframe count one. No audio-generation button was clicked. Only sanitized control categories were output, never account credentials, private chat, cookies, or raw HTML.

## Reusable code path

The read-only CLI can use exactly two hardcoded browser destinations: default Google AI Studio speech UI, or the official Flash-Lite documentation deep link. Arbitrary URLs and model/voice mismatches are rejected **before** Chrome attaches or writes any receipt. The selected-model flags remain false even if a model query parameter persists or a visible model card matches; a link, button, card or mock return cannot claim actual generated WAVs. Full browser tab ownership and Chrome port lock are retained.

Regression coverage: five additional tests for official-link behavior, inability to spoof generation approval, invalid route/model rejection and URL parameter misinterpretation. Tests on Dell-115 and Yoga 6: **24 preflight cases, 23 passed / one Windows symlink privilege skip on each PC**, plus 5/5 no-Whisper cases on each.

## Follow-up gate

The browser TTS production worker **must not be activated yet**. Next investigate an actually supported authenticated TTS editor and explicit model/voice selection with known billing conditions; then perform a bounded non-course real WAV trial, independently verify its sample bytes, speech content and provenance, and add resumable source-bound element generation. If such a browser route does not exist, raise a precise transport-blocked result; only a separately authorized low-cost Gemini Flash-Lite API experiment may be considered, **never** automatic Google Cloud Chirp, model substitution, Whisper or unsanctioned billing.

PRs #106–#111 are review-only stacked drafts, not a production release. Original Dell-115/Yoga6 Drive-sync working trees have uncommitted changes and must remain untouched; all experiments used isolated temporary clones. HP was offline.
