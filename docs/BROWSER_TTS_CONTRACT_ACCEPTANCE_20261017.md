# MicroGen_AI_Web contract-locked TTS continuation — 17 October 2026

**Review-only development, not production approval.** This document accompanies the stacked draft branch above PR #109 and does not authorize its merge or any student release.

## Binding contract

1. Work exclusively on `tlyoon/MicroGen_AI_Web` for this package. Do not alter `MicroGen_AI` or reuse its working tree.
2. Preserve every existing textbook PDF, slide, narration, WAV and MP4. The repository checkout and the separate PDF source root remain distinct; outputs eventually belong beside each `source.pdf` only after approved production stages.
3. Every published MP4 part must be **strictly under 600 seconds**; each spoken slide element, equation or composite figure must receive its correct synchronized highlight. Technical pixel/audio acceptance alone never establishes academic approval.
4. Primary voice/model remains **Kore / gemini-3.8-flash-lite-tts**. Never relabel `gemini-3.8-flash-tts` as Flash-Lite or assert a merely visible model card was selected.
5. **No Whisper, faster-whisper or CTranslate2 Whisper dependencies.** Independent Gemini ASR, as supported and source-bound, is the established speech verification direction.
6. Billable **Gemini Flash-Lite TTS is permitted by the latest owner instruction**, but an actual API invocation must still use the explicit authorization flags and receipts defined in PR #108. Never silently leave browser mode for the API. **Expensive Google Cloud Chirp TTS is not an acceptable automatic fallback.**
7. HP, Dell-115 and Yoga6 are the only authorized distributed workers; no Zenbook. Drive-native coordination, immutable job receipts, source hashes, bounded retries, no duplicated work and no automatic reassignment stay mandatory.
8. No PR merge, original-file replacement or student publication based merely on browser screenshots, model cards, synthetic tests or unreviewed narration.

## Real Dell-115 read-only check (17 October 2026)

Using the unchanged PR #109 Selenium preflight in a **fresh temporary cloned checkout**, attached to the signed-in Chrome debugging port 9222:

- Google AI Studio speech UI accessible.
- Visible model ID: `gemini-3.8-flash-tts` only.
- **Not confirmed:** exact `gemini-3.8-flash-lite-tts` selection, Kore voice, editable speech composer, downloadable PCM WAV or browser billing terms.
- `No API key selected` visible in that UI; this is distinct from local APPDATA credentials.
- The receipt correctly says `BROWSER_TTS_GENERATION_UNVERIFIED` and `usable_for_automatic_element_tts=false`.
- No speech generation, API call, key selection, source upload, Cloud TTS, or lecture publication was performed.

## Corrective code in this branch

- Programmatic preflight validates model and voice **before** any Chrome connection.
- Origin verification requires the exact HTTPS AI Studio host and speech path, rejecting deceptive hostname and path prefixes.
- UI model/voice *visibility* is distinguished from selected model/voice *verification*; neither is inferred from a card or editable field.
- Receipt symlinks are rejected before canonical path resolution; protected-source and no-overwrite guards remain.
- Automatic Gemini TTS fallback now stays within Gemini; the costly Google Cloud Chirp fallback is removed from its automatic candidate list. Explicit manual provider features are untouched, but not authorized for this campaign.
- New regression tests exercise these contract boundaries; original no-Whisper and production video gates remain in scope.

## Release / next stage

Browser audio generation is **blocked** pending real evidence of a supported, explicitly selected exact model/voice, viable editor, billing terms and genuine WAV retrieval. Do not implement a Selenium Run-clicker or claim production capability before these conditions are satisfied.

If Gemini browser generation is unavailable, the existing *explicitly authorized* Gemini Flash-Lite API TTS path in PR #108 is a separate, clearly labelled option; it must not be invoked as an invisible fallback. Mathematical source-to-highlight selection and incomplete independent speech review remain blocked from academic signoff, even if audio synthesis succeeds.

The Dell-115 and Yoga6 Drive-synced local Git checkouts were found behind remote main and with uncommitted modifications in `runner.py`, `tts.py` and the template Selenium file. **Do not pull, reset, merge, stash, edit or overwrite these local working trees without separate preservation and reconciliation.** Changes here were prepared in an isolated checkout/remote review branch. HP was offline when checked.
