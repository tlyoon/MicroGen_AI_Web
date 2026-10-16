# Phase 4 local, offline ASR — controlled validation

**16 October 2026. REVIEW-ONLY. Draft stacked on PR #103.**

## Goal and provenance

Provide a genuinely separate-vendor and **no-Google-API** speech
verification option for MicroGen_AI_Web. The first candidate is an on-device
Whisper speech-recognition network executed with the `faster-whisper`
CTranslate2 CPU/int8 runtime. **Whisper is not a TTS engine**; Gemini Flash
Lite Kore remains the TTS synthesizer. Whisper is used solely to independently
transcribe the resulting narration audio for comparison with the intended
script. Automated recognition does not prove mathematical correctness or
natural speech.

The tool must not download models, submit private lecture WAVs to a cloud
provider, mix previously stored Gemini ASR receipts with local receipts, or
silently grant production approval. Source PDFs, slides, original narration
WAVs and generated MP4s remain untouched.

## Real device provisioning assessment

On Dell-115, HP and Yoga 6, the default Python installations **had no
faster-whisper/Whisper/torch/Vosk ASR package**. Dell-115 had a Hugging Face
`faster-whisper-small.en` cache *reference* but **no model snapshot or
weights**.

An isolated environment was created outside all MicroGen repositories at
`%LOCALAPPDATA%\MicroGen_LocalASR_Env_20261016`. On Dell-115,
`faster-whisper==1.2.1` with `ctranslate2` installed successfully.
`WhisperModel` was inspected and supports `local_files_only=True`.
Model weights were **not available** in the provided local cache.
A one-time model-provisioning execution was blocked by the remote
execution safety checks, and **the block was respected**. Therefore, a
genuine inference run on Thomas 8.4 cannot honestly be claimed.

## Reusable implementation

The generic `selenium_pipeline.phase4_local_asr` uses an
**explicit existing absolute local directory** containing these model files:

- `config.json`
- `tokenizer.json`
- `model.bin`

Acceptable declared model tiers: `base.en`, `small.en`, both
CPU/int8. Each file's SHA-256 is bound to the job; no model identifier
can silently change during a resumable job. Invocation uses
`WhisperModel(..., device="cpu", compute_type="int8",
local_files_only=True)`, with fixed English transcription settings and
no source-script prompt.

Completed per-clip model transcripts carry distinct, source-bound local
model identity, audio WAV SHA-256, intended narration SHA-256, transcript
SHA-256 and true minimum word edit distance. A resumed job skips verified
receipts, rejects changed models/audio/scripts and never replaces immutable
prior evidence. Local inference failures halt and preserve completed clips.

The shared `tts_quality_gate` and `element_series_audit` accept only
explicitly whitelisted offline model ids **with full local model file
hash metadata and provenance**. They do not accept vague `whisper`
strings, mixed provider receipts or edited transcripts. Mathematical
sign/order discrepancies remain flagged by the earlier Phase 4 checks;
the strict student publication and human academic review gates remain
disabled.

To run *after separately approved model provisioning*, from the project
checkout:

```powershell
$py = "$env:LOCALAPPDATA\MicroGen_LocalASR_Env_20261016\Scripts\python.exe"
& $py -m selenium_pipeline.phase4_local_asr `
  --plan PATH_TO_UNCHANGED_AUTHORED_PLAN.json `
  --audio PATH_TO_ORIGINAL_48_WAVS `
  --model-dir PATH_TO_PREINSTALLED_CTRANSLATE2_MODEL_DIRECTORY `
  --model-size base.en `
  --output NEW_EMPTY_LOCAL_ASR_EVIDENCE_DIRECTORY `
  --max-new 3
```

Choose model-size `small.en` instead of `base.en` only if that tier
was installed and matches its explicit model directory. Once an initial
3-clip quality and speed benchmark passes, resume the **same frozen job**
with larger `--max-new`. Never compare two different model tiers as one
ASR job. Never change TTS model/voice as a way to bypass a mismatch.

For real lecture release, run all 48 original WAVs through the selected
single offline ASR engine, audit mathematical discrepancies, complete the
three-layer acoustic/synchronization QA, and record independent human
listening and lecturer academic signoff.

## Current accepted facts / blockers

- **10 new offline/fault-injection unit tests** are passing on Dell-115
  using artificial *mock* CTranslate2 model files and injected transcript
  callbacks. These are tests of job persistence, isolation and integrity,
  **not proof of actual Whisper recognition accuracy**.
- Existing real Thomas Calculus 8.4 Gemini recognition: **14/48 clips
  checked, 13 machine-consistent and one flagged for inverse-sine math
  notation; 34 not yet independently transcribed.**
- Existing 48/48 WAV basic acoustic checks pass; no justified selective
  regeneration candidates.
- **True local-ASR empirical WER, mathematical-token recall and CPU time
  have not been measured**, because the actual model weights are absent.
- No Whisper transcript receipts from real audio exist yet.
- Original content remains untouched. Production release remains blocked.

**Next criterion:** obtain authorized offline model weights, benchmark 3
previously validated clips including the math ambiguity `s05_e03.wav`,
compare actual ASR WER, operator/sign preservation and execution speed
against the existing independent Gemini receipts, then decide whether to
commit to all 48 local transcriptions or seek separate authorization for
the already working Google Gemini audio API alternative.
