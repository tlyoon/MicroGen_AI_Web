# PR184 — Gemini Flash-Lite element TTS source-review preflight

The new `element_tts_safe_handoff` checks original source.pdf, slides.pdf, script.txt and the immutable 71-utterance worklist before any paid call. It can accept a fully validated source-reviewed draft/selection through existing `element_plan_review_bridge.promoted(prepare_tts=True)`, or the very restricted existing `automatic_element_narration.inspect_text_only` when exact figure-free text-only evidence is sufficient. A fake, incomplete or altered review does not approve billing. This preflight **never sends TTS**; separate existing live TTS has explicit user/paid consent flags and frozen job identities.

Real Thomas Calculus 8.4 remains `ELEMENT_TTS_BLOCKED_SOURCE_MAPPING_UNVERIFIED`; no actual paid calls or element WAVs generated. All 71 original utterances remain source review-only because original mathematical expressions/figures are not equivalently mapped, and false approval must not be invented. The primary contract is Gemini Flash-Lite TTS/Kore with one consistent effective voice; Cloud fallback only after three genuine failures evidenced by existing retry journal. No voice mixing, original asset overwrite, Whisper, ASR or GCS lease.

Dell-115 only, parent PR183 SHA 52bf848643078619f9fdc5a380d660f33093e49e. No HP/Yoga6, main merge or publication.
