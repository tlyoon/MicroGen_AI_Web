# MicroGen_AI_Web — TTS Pronunciation QA Contract (Owner Revision, 27 October 2026)

**Status:** Authoritative for NEW TTS QA evaluations from this revision onward. The previous 99% verbatim word-fidelity and arbitrary 20% ASR word-error gates are deprecated for new evaluations. Preserve historical v1 reports unchanged.

## 1. Primary acceptance standard: intelligible and substantially similar

**A TTS WAV passes pronunciation/content screening if its spoken content sounds reasonably close to the intended narration and communicates substantially the same educational meaning.** Natural differences in accent, inflection, speech rhythm, connected speech, pauses, singular/plural grammar and harmless incidental wording are acceptable. A near-verbatim match is **NOT** required. Exact ASR transcription, a 99% word-level match or an arbitrary maximum word-error rate must **NOT** be prerequisites for allowing the WAV to advance.

ASR transcription is imperfect, particularly for mathematics. A spelling such as **“high pot news”** for *hypotenuse*, **“coast sign”** for *cosine*, **“see get”** for *secant*, **“eggs”** for the variable *x*, **“you”** for *u*, or **“pie”** for *pi* is generally acceptable *when the audio is intelligible and these represent similar spoken sounds*. Do not automatically regenerate the audio because of an ASR spelling variation or a minor word omission.

The default quality decision is **PASS_SIMILAR_SOUND** or **PASS_WITH_MINOR_VARIATIONS**, using source-registered PCM, measured audio, unbiased ASR evidence and context-aware sound-alike comparisons. Raw transcript WER remains available for diagnostics but does not govern acceptance. Speaker-embedding cosine similarity is useful supporting evidence, not a precise voice-identity or accent threshold; modest speaker-score variation must not independently block reasonably consistent recordings. Retain the primary approved Kore voice request and provenance; do not fabricate independent identity confirmation.

## 2. Fail only for clear, consequential errors

**The following unacceptable pronunciation/content errors remain strict failures** when actually detected, not merely guessed from the spelling of the prompt:

- **A mathematical letter `c` or `c.` pronounced “circa”** instead of its intended letter name “see.” This is specifically prohibited. Correctly pronouncing `C` as “see” is acceptable. Retain other definite letter/variable substitutions, such as `Y` incorrectly spoken as an unrelated word instead of its letter name.
- Clearly reversed meaning in **positive/negative, nonnegative/negative, plus/minus, greater/less, at least/at most, sign, numeric value, exponent, inequality, domain or formula**. Mathematical meanings are not interchangeable merely because surrounding prose sounds similar.
- Clearly substituting one mathematical object for another (e.g., **sine for cosine**, or **adjacent leg for hypotenuse**) when the audio meaning is materially different, not when ASR only uses a homophonically spelled phrase.
- Material speech omitted or unintelligible, prominent clipping/truncation, unrecoverable silence or unrelated content, genuine wrong unit/number/variable reading, or a demonstrably unsuitable/different speaker.

Do not regard generic, unconfirmed ASR uncertainty as proof of such an error. When the sound is materially similar but the recognizer misspells it, **pass with a brief advisory note** rather than stopping the pipeline. When the audio is truly unclear, use a targeted QA check; **do not automatically resubmit paid TTS solely because the ASR word-error rate is high**.

## 3. Separate engineering gates remain intact

A TTS pronunciation PASS establishes only **audio intelligibility/content similarity**. It does NOT independently approve the original textbook mathematics, signed radical identities, transcript-byte provenance, true Kore speaker identity, utterance boundary/hash registration, source-figure synchronization, strict encoded-video duration (<600 seconds per video), or student publication. Continue all source hashes, genuine PCM checks, no-original-overwrite, one-shot request checkpoints, Windows-only Dell-115 testing, and separate academic/media release checks.

This relaxation **does not require manual academic review** and **does not authorize external Moodle publication**, which remains prohibited by the project contract. Gemini TTS Flash-Lite 3.8 remains the first-choice synthesis model, with existing approved Cloud fallback policy unchanged. No Whisper is required or permitted. User's auto-development and AI-only QA preference continues.

## 4. Implementation and backward compatibility

- Implemented by `selenium_pipeline/tts_flexible_pronunciation_contract.py`, applying harmless phonetic normalizations while retaining `LETTER_C_INCORRECTLY_EXPANDED_TO_CIRCA` and serious math-number/sign/function/side-role failures.
- Applied to unbiased offline ASR for authentic Thomas §§8.4 utterances, the normal `tts_fidelity` audio listener and its rescore/reports, the production stage's `runner.valid("tts_qa")`, TTS repair/promotion, structural reconciliation and element-series audio checks.
- **New v2 reports**: `tts_qa_policy_version=TTS_PHONETIC_SIMILARITY_V2_20261027`, sound-alike pass flag and separate `tts_quality_percent`; new default comparison threshold **50% phonetic token similarity**, explicitly a permissive *screening floor* coupled with non-negotiable consequential-error checks, not a medical/scientific metric or a publication criterion. `PASS_SIMILAR_SOUND` generally scores ≥67%; `PASS_WITH_MINOR_VARIATIONS` scores from 50% to <67%. Below that or with empty recognition, refer for a targeted check rather than regenerating automatically. Because ASR is noisy, this threshold is **not** a percentage of words that must match exactly.
- **Historical v1 reports**: Retain their original `fidelity_percent`, 99% threshold and interpretation; never retroactively rewrite or claim that older scores were sound-alike metrics.
- Verify negative and positive tests, particularly **C → circa hard rejection**, changed mathematics/number hard rejection, unrecognizable speech review, and sound-alike benign examples.
- The genuine revised §8.4 Slide4 five-WAV Vosk transcripts had raw WER 2.0%, 28.0%, 24.1%, 25.7% and 26.3%. Their observed *phonetic* similarities were **100.0%, 96.0%, 98.734%, 93.617% and 98.246%**, with no reported consequential error, so **five out of five** pass the new TTS pronunciation screen without regenerating WAVs. This does not declare the five-slide source mathematics, audible Kore identity or full student-ready lecture completed.

**Owner rationale:** TTS QA should prevent *obviously wrong audio*, not punish good, comprehensible speech because a machine transcription spells technical words phonetically. Strict conceptual correctness and authentic original-media acceptance remain independent contracts.
