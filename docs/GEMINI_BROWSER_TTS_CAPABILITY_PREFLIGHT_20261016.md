# Gemini browser-only TTS capability gate — 16 October 2026

**MicroGen_AI_Web; REVIEW ONLY. No speech-generation job started.**

## The original contract

The project must produce genuine narration of every referenced slide
element with a synchronized visible highlight. Each MP4 part must remain
strictly shorter than 600 seconds. The preferred TTS is **Gemini 3.8
Flash-Lite TTS** with the **Kore** voice. The ordinary software mode
avoids Gemini API calls and therefore avoids unexpected metered API
costs. Whisper and all Whisper-dependent packages are expressly excluded.

The already tested Gemini 3.8 Flash-Lite element audio pipeline in PR
#108 uses the **Gemini API behind explicit paid-API authorization**.
Do not silently remove those opt-in flags or mislabel a different model.
A browser pathway must be independently demonstrated before enabling it.

## Confirmed evidence on the real Dell-115 browser

The authenticated ordinary Gemini page at
`https://gemini.google.com/app` showed a **Flash High chat model**
and upload tools, but no dedicated text-to-speech output interface.

Google's official TTS documentation directs users to Google AI Studio
to try speech generation. The real browser at
`https://aistudio.google.com/generate-speech` showed:

- An explicit **Gemini 3.8 Flash TTS**
  (`gemini-3.8-flash-tts`) model card, **not** confirmation that
  `gemini-3.8-flash-lite-tts` is selected or available.
- **No API key selected** in the session.
- An introductory gallery of dialog and voice examples.
- The inspected "Create new dialog" interaction did **not** expose an
  editable TTS request field or an audio download surface during two
  bounded tests. This may reflect UI state, authorization or product
  behavior; it does not prove speech generation is universally unavailable.
- No validated Kore selection, decoded WAV, price-free generation
  guarantee or speech synthesis receipt was obtained.

The browser inspection opened only an isolated temporary tab under the
shared Chrome port lock, captured allowlisted model/key/editor evidence,
and closed its own tab without submitting requests, clicking billing
choices or reading/uploading real lecturer files.

A Google AI Studio site showing a TTS model does NOT automatically
establish that its web playground is free, provides the specific
Flash-Lite engine, supports an unchanged Kore voice, or offers an
exportable byte-identical WAV through public UI controls. Do not
fabricate that result.

## Executable status preflight

From an authorized PC with the existing signed-in Chrome debugging
port 9222, run:

```powershell
python -m selenium_pipeline.browser_tts_preflight `
  --model gemini-3.8-flash-lite-tts `
  --voice Kore `
  --output "NEW_ISOLATED_browser_tts_preflight.json"
```

The probe performs NO text submission, audio generation, API request,
API-key selection or source-file modification. It strictly distinguishes
`gemini-3.8-flash-tts` from `gemini-3.8-flash-lite-tts`.
It collects no Google Account email, personal conversation text,
transcript, cookies, credentials or raw HTML. All reports say
`BROWSER_TTS_GENERATION_UNVERIFIED` until a separate real-audio
workflow proves the actual selected model, selected voice, safe billing
status and downloadable audio.

The report's `usable_for_automatic_element_tts` flag is always
**false in this inspection-only implementation**. Neither a model card,
editable field, nor a developer's fabricated mock success can change it.
The separate production/staging code therefore remains incapable of
treating hypothetical browser WAVs as real verified audio.

## Next legitimate development gate

1. Confirm a **visible**, supported Gemini browser speech UI offers
   either the exact **Flash-Lite TTS** model and Kore, or an explicitly
   accepted alternate model with separately labelled provenance.
2. Establish the UI generation/billing conditions **without silently
   selecting an API key or causing paid API usage**; seek explicit
   approval if a key or metered service is mandatory.
3. In a new, isolated test workspace, submit a **synthetic test
   sentence only** and verify a real downloadable WAV at the UI,
   including speaker identity evidence, WAV format, audible content,
   SHA-256 and any provider-surface limits.
4. Only then add a Selenium worker that holds the Chrome/PC lock,
   resumes immutable per-element receipts and never skips failed or
   ambiguous WAVs. Test HP and Yoga6 as well as Dell-115 before wider
   student-course use.
5. Recheck real source/equation/figure mappings and the remaining
   independent Gemini ASR of Thomas 8.4 (34 clips unverified). Even a
   technically valid downloaded WAV is **not academic approval**.

No Whisper, Google Cloud fallback, hidden Gemini API call, student
publication, merge or original teaching-file overwrite is permitted by
this capability probe.

## Multi-PC Python environment caveat

The default `python` on HP and Yoga6 can run the core offline validation
tests, but initially has **no installed Selenium package**, even when a
separate MicroGen environment or already-open Chrome browser may exist.
This is not evidence about Google's model availability. The read-only
preflight now emits a distinct `BROWSER_TTS_PREFLIGHT_UNAVAILABLE`
receipt with `selenium_python_dependency_unavailable`, leaving all
model/voice/key observations unknown and every production permission
false. A future run must use an already-configured approved Selenium
environment for that machine; this code installs nothing automatically.

## Existing per-PC Google credentials (clarification)

The project already stores each Windows user's **local configuration**
under `%LOCALAPPDATA%\Microvid\.env`, with other Google configuration
files alongside it, and reuses persistent Gemini Chrome profile data
under that machine's own `%LOCALAPPDATA%`. This pre-existing local
layout is correct and should not be migrated to the GitHub checkout,
copied across PCs, or replaced with new secrets.

A presence-only check on **Dell-115, HP, and Yoga6** verified that
`Microvid\.env`, Google Cloud credentials, Drive OAuth configuration
and a persistent Gemini browser profile exist on all three machines.
The check used file-existence operations only: **no secret file content,
token, credential value, account identity or raw Chrome profile was read
or displayed**.

Important distinction: Google AI Studio displaying **"No API key
selected"** reports the web playground's own selected-key state.
It does **not** establish that MicroGen's separate locally stored
Google credentials are missing, expired or invalid. Conversely,
the mere presence of files in `%LOCALAPPDATA%` does **not** establish
that a browser can generate free Flash-Lite TTS audio or authorize
metered API calls.

The preflight now emits separate local file-presence booleans together
with the observed browser-state booleans. It explicitly records that
no secret contents were read and never converts local configuration
presence into `usable_for_automatic_element_tts=true`. No Google
login, key selection, API mode change or new credential provision is
required for running this presence check. API TTS still requires
independent explicit paid-API permission, as defined in PR #108.
