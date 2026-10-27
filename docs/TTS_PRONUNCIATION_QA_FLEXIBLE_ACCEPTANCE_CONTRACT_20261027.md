# MicroGen_AI_Web — Revised TTS pronunciation QA acceptance contract
**Effective 27 October 2026; owner-directed amendment. Applies to all subsequent TTS WAV generation and QA, including Thomas Calculus.**

## A. Principle: audibly equivalent is sufficient

A TTS-generated narration WAV **PASSES pronunciation QA** when a reasonable listener would hear substantially the intended source-registered teaching narration, in an intelligible and fluent manner, **even if an automatic speech-recognition engine does not reproduce the exact spelling or every word**. Exact ASR token agreement, minimal WER, identical punctuation, inflections, harmless pauses, accent differences, innocuous rewording, and ordinary technically plausible pronunciations are **NOT acceptance requirements**. Sound-alike recognitions of the intended mathematical terms (e.g., *hypotenuse* → “high pot news,” *cosine* → “coast sign,” *secant* → “see get” or “ac can't,” variable *x* → “eggs,” and spoken *pi* → “pie”) are **acceptable ASR spelling errors**, provided the underlying explanation is clear and contextually equivalent.

The WAV's authentic PCM structure, actual original-source/utterance identity, content completeness, and requested consistent voice still matter. The goal is clear teaching, not ASR competition.

## B. Non-negotiable errors requiring corrective action

Continue to flag genuine audible errors that make the lecture wrong, misleading or distracting, especially:
- **Gross letter/symbol expansion:** a standalone mathematical variable **c** pronounced as **“circa”**. This example is permanently retained as a regression test. Other seriously misleading substitutions require targeted correction rather than blanket TTS regeneration.
- **Mathematical sign or meaning reversed or omitted:** *negative* vs *nonnegative*, positive vs negative, absolute value omitted where essential, incorrect domain restrictions or boundary/zero-leg conditions.
- **Changed mathematical functions or formulae:** e.g. *sine* substituted for *cosine*, *secant* substituted for *tangent*, changed indices, powers or units; critical omitted words that change the derivation.
- **Audio actually unusable:** silence, missing narration, truncation, severe distortion or unrecognizable technical content, or a genuine incorrect/different speaker that violates the established same-voice contract.

When the automatic recognizer merely spells a phrase phonetically, do not automatically classify that as a TTS pronunciation defect. Distinguish **ASR ambiguity** from **confirmed audible defect**.

## C. Pragmatic automated pass rules and intervention policy

1. Confirm nonempty, decodable, source-SHA-bound WAV and preserved speaker profile. Check actual spoken-word coverage by independent offline recognition where practical; use a **conservative, documented set of sound-alike equivalents** to compensate for ASR phonetic spellings.
2. The default automated pronunciation screen tolerates up to **35% normalized WER after documented phonetic normalization**; this is an operational screening heuristic, not a precise measure of audio quality. A high raw ASR WER, by itself, **must not** mandate regeneration. Explicit meaning-changing math polarity/function mismatches or known gross variable expansions override any favorable similarity score.
3. If intelligibility and meaning are preserved, mark **`TTS_PRONUNCIATION_QA_PASS`** and move to the subsequent timing/video stages without repeated synthesis. **Do not require verbatim source text** to pass.
4. For a genuine serious issue or unresolved critical sign/function ambiguity, mark **`TARGETED_REVIEW_REQUIRED`**, retaining the original WAV and evidence. Retry/regenerate **only the defective affected utterance** after a grounded audio defect is identified. Never repeat the entire subchapter or multiple paid calls merely because the ASR rendered technical terms differently.
5. Pronunciation QA **does not substitute** independent academic/source fidelity review, voice identity and provenance evidence, nor actual utterance-to-highlight and encoded-video acceptance. These gates remain separately tracked, and an ASR screen pass by itself is **not** permission to publish student lecture media.

## D. Regression examples

| Expected narration | ASR rendering / detected speech | Pronunciation QA |
|---|---|---|
| “The hypotenuse is the square root” | “The high pot news is the square root” | **PASS** as sound-alike |
| “Cosine u is nonnegative” | “Coast sign you is non negative” | **PASS** as sound-alike |
| “For x equals a secant u” | “For eggs equals ac can't you” | **PASS** as sound-alike |
| Variable “c” | Actually read “circa” | **FAIL** (gross symbol expansion) |
| “Cosine is nonnegative” | “Cosine is negative” | **FAIL/targeted review** |
| “Cosine” | A truly spoken “sine” instead | **FAIL/targeted review** |
| Muffled, missing or completely unrecognizable speech | Unrelated/empty recognized text | **REVIEW** |
| Correct and clear speech, but ASR reports spelling errors | Meaning unchanged | **PASS** |

This supersedes the previous routine use of **≤20% raw WER plus rigid recall** as hard TTS acceptance requirements. Retain raw WER as diagnostics. **No manual owner academic review** is newly introduced: automated/offline independent evidence and explicitly scoped targeted technical review should be preferred; never fabricate an unavailable reviewer verdict.

**Implementation:** `selenium_pipeline/flexible_tts_pronunciation_qa.py`, invoked by `selenium_pipeline/offline_vosk_corrected_math_speech_qa.py`, tests `tests/test_flexible_tts_pronunciation_qa.py`. Applies across subjects by meaning, with per-source approved sound-alike terms added through regression tests rather than broad indiscriminate fuzzy replacement.
