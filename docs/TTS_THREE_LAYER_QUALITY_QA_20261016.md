# Three-layer TTS quality screening (16 October 2026)

**Review-only implementation.** This draft is stacked on PR #100 and does
not alter Thomas Calculus 8.4 narration, slides, legacy MP4, or any student
material. No previously incomplete ASR evidence is fabricated or promoted.

## Checks implemented

1. **Technical audio measurements:** independent PCM16 mono WAV read, RMS
   loudness in dBFS, peak level, clipped sample fraction, proportion of
   low-energy 30 ms windows, leading/trailing and longest low-energy period.
   Clearly silent, mostly silent, heavily clipped or very quiet audio is
   rejected. A 30 ms energy test is *not* voice activity detection. Numeric
   thresholds are conservative screening defaults, not subjective quality
   guarantees.
2. **Spoken content:** use existing independent, *different Gemini model*
   transcript receipts, verifying exact authored plan, WAV and transcript
   hashes and model identity. Compute true minimum-word-edit distance/word
   count (rather than approximate difflib alignment), and flag WER >20%.
   Separately compare a conservative vocabulary of mathematical words:
   negation, signs, operators, pi, theta, trig function names and numbers.
   Synonyms and mathematical notation can produce review flags; never
   automatically normalize a questionable mathematical discrepancy into a
   pass.
3. **Perceptual screening cues:** detect unusually low/high *script-derived*
   speaking rate, very long energy silence and high overall loudness, for
   follow-up listening. These are screening heuristics, **not** measurements
   of true phonetic word timings, prosody, intelligibility or naturalness.

One immutable, detailed JSON receipt covers **every** narration clip with
WAV and script hashes, independent transcript text where available, numeric
metrics, explicit flags, and human-approval fields set to `false`.

The standalone screen is purely offline, stdlib Python; it makes **no**
transcription, cloud, browser or TTS request.

## Use from an isolated development checkout

Run quality screening on the exact frozen authored plan and original audio
folder, with the existing ASR receipts from that *same plan*:

```powershell
python -m selenium_pipeline.tts_quality_gate `
  --plan PATH_TO_AUTHORED_PLAN.json `
  --audio PATH_TO_48_FROZEN_WAV_DIRECTORY `
  --asr-dir PATH_TO_ASR_RECEIPTS `
  --output NEW_NONEXISTENT_TTS_QA_REVIEW_REPORT.json
```

An ASR directory is optional when seeking **audio-only preliminary
diagnostics**, but in that case every clip is flagged
`pending_independent_asr`. It cannot be marked machine complete.

To enforce both the independent transcription and acoustic/perceptual screen
within the already existing full-lecture audit, supply all its existing
source/staging/MP4/rebinding arguments *plus*:

```powershell
  --asr-dir PATH_TO_ASR_RECEIPTS `
  --require-asr `
  --quality-report PATH_TO_NEW_TTS_QA_REVIEW_REPORT.json `
  --require-quality
```

`--require-quality` rejects missing, incomplete and flagged screening
evidence, and additionally checks coverage, plan hash and every recorded
WAV/script SHA. It does **not** lift the permanent review-only
`production_eligible=false` status. Independent academic and listening
approval remain separate, manual gates.

## Current Thomas 8.4 acceptance boundary

As of the recorded evidence in PR #100, 14 of the 48 clips have real
independent transcripts; 13 are machine-consistent and one mathematical
speech segment remains flagged. The other 34 cannot pass the speech gate.
No new provider availability or real-audio screening result is claimed here
until this new screening CLI has been run against the frozen actual WAVs.

There is no Whisper dependency. Existing independent ASR uses the Gemini
audio-capable recognition model through the Google SDK; it is a
*model-level* comparison within the same provider, not vendor-independent
or human speech review. Investigate the user project's non-API/Selenium
policy separately before incorporating this into the standard runner.

## Tests and review obligations

Offline regression tests cover normal machine-consistent speech, missing
transcripts, math mismatch despite a low WER, clipped and silent WAVs, real
word edit distance, symbolic pi fractions, tampered transcript/audio
provenance, immutable report output and strict integrated gate behavior.

Before merging, run these tests on Dell-115, HP and Yoga 6; evaluate
thresholds on a representative real TTS clip collection, investigate flagged
clips through listening, and obtain lecturer review. Automated perceptual
screening alone must never be misrepresented as an approved lecture.
