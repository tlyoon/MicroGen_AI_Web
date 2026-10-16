# MicroGen_AI_Web — optional offline narration word-consistency check

**16 October 2026. Status: independent-machine review, not production approval.**

## Why this stage was built

Gemini 3.1/3.5/3.7 Flash audio transcription repeatedly failed with
HTTP 503 after the first three Thomas 8.4 Gemini TTS recordings. Windows'
legacy offline dictation produced unsuitable low-confidence mathematical
terms. Neither tool can be substituted for actual evidence.

The new optional `selenium_pipeline.offline_speech_audit` uses
**faster-whisper 1.2.1 / CTranslate2 CPU int8 with a local
Systran/faster-whisper-small.en model**. All model inference runs on the
user-controlled PC; nothing is sent to the cloud once model files have
been downloaded. A private, isolated Python virtual environment is used
rather than adding large mandatory dependencies to MicroGen_AI_Web.

The model sees **only recorded WAV bytes**, never the expected text.
Each result is compared with the TTS requested narration afterwards.
Every immutable per-WAV receipt includes recorded SHA256, script SHA256,
recognized text and its SHA256, actual local model file SHA256, and
word-error rate. The full job is also locked to the exact 48-element
corrected-lecture authored-plan SHA256 and the source TTS receipt SHA256.

**Independent vendor does not mean guaranteed correct ASR.**
Mathematical words, equation punctuation and dictated symbols often differ
even when the spoken audio is correct. WER <=0.20 is only a preliminary
machine-consistency signal. Any missing recording or above-threshold clip
is flagged for lecturer listening, never silently accepted.

### Reproduction with isolated local dependencies

In Windows PowerShell, from the MicroGen_AI_Web repository directory:

```powershell
python -m venv "$env:LOCALAPPDATA\MicroGenASR_venv"
& "$env:LOCALAPPDATA\MicroGenASR_venv\Scripts\python.exe" -m pip install faster-whisper==1.2.1

# Model download is a one-time online step; use the *same frozen model
# directory* for the entire audit. Never automatically replace its weights.
& "$env:LOCALAPPDATA\MicroGenASR_venv\Scripts\python.exe" -c '
from huggingface_hub import snapshot_download
snapshot_download("Systran/faster-whisper-small.en",
  local_dir=r"C:\NEW_PRIVATE_ASR_MODEL_FOLDER",
  allow_patterns=["config.json","model.bin","tokenizer.json",
                  "vocabulary.txt"])'

# The MicroGen code is imported from the repository, while the optional
# ASR dependency is imported from the isolated environment:
& "$env:LOCALAPPDATA\MicroGenASR_venv\Scripts\python.exe" -m selenium_pipeline.offline_speech_audit `
  --plan NEW_CORRECTED_VOICE_BOUND_PLAN.json `
  --audio ORIGINAL_FROZEN_KORE_WAV_DIRECTORY `
  --model-dir C:\NEW_PRIVATE_ASR_MODEL_FOLDER `
  --output C:\NEW_UNWRITABLE_BEFORE_RUN_ASR_REVIEW_FOLDER

# Running the identical command again resumes matching SHA-attested clips.
# Different model files, WAVs, or intended spoken words reject reuse.
```

The model folder and ASR receipts MUST NOT be committed to GitHub.
Only the optional source code, test fixtures, and instructions belong in
the software repository.

### Reproducible private lecturer review

`selenium_pipeline.speech_listening_packet` writes an independent,
offline-compatible `index.html`, CSV checklist, original playback WAV
copies, and machine transcript receipts. **Every text field is escaped**;
the packet shows flagged segments first and does not claim academic approval.

```powershell
python -m selenium_pipeline.speech_listening_packet `
  --plan NEW_CORRECTED_VOICE_BOUND_PLAN.json `
  --recordings ORIGINAL_FROZEN_KORE_WAV_DIRECTORY `
  --asr NEW_ASR_REVIEW_FOLDER `
  --destination NEW_PRIVATE_LISTENING_PACKET_FOLDER
```

The full video acceptance audit supports
`--asr-dir NEW_ASR_REVIEW_FOLDER --require-asr`. It now validates
a distinct offline model, original synthesis job hash, per-WAV and
per-transcript digests, model file SHA, all 48 clip IDs, and fails closed
on any absent/flagged report. It does **not** convert a machine-consistent
record into an audible-word certification or academic sign-off.

### Original corrections and release policy

The corrected Thomas Calculus 8.4 MP4s remain in the private previous
review handoff folder. No TTS WAV was regenerated in this round,
and neither of the two reviewed MP4s is rewritten. Their strict
durations/encoded-pixel/slide coverage acceptance remain valid.

**Release stays blocked** until a suitably qualified person listens to
the flagged voice samples, checks actual spoken equations against the
textbook, and verifies the meaning/academic quality and figure legibility.
No automatic speech-to-text tool can certify mathematical correctness.
Do not merge draft PRs #91–#98 or publish the lectures solely because an
automatic recognition audit has finished.
