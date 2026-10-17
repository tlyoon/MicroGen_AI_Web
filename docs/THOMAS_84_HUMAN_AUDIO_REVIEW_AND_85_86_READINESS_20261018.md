# Source-bound Thomas narration acceptance worklist — 18 October 2026

**Purpose:** Prepare an auditable listening and academic review from the ORIGINAL 48 Thomas Calculus 8.4 TTS clips. This is explicitly *review-only*. Machine transcription is not certification, and no new ASR, TTS or billable service is invoked.

## Verified evidence

- Thomas 8.4 preserved source-bound bundle: `MicroGen_AI_Web_Thomas84_FullElement_GeminiKore_ReviewOnly_20261016` with original authored plan, SHA-bound Gemini Flash-Lite/Kore synthesis receipt and all 48 individual original WAV files.
- Existing Gemini-based screening: `MicroGen_AI_Web_Thomas84_Real48_TTS_Quality_20261016/ThreeLayer_Real48_Refined_QA.json` (13 machine-consistent, 1 transcript mismatch, 34 pending Gemini transcription).
- Existing independently produced historic offline recognition receipts: `MicroGen_AI_Web_Thomas84_IndependentOfflineSpeech_QA_20261016/recognition_receipts/*.wav.asr.json` (43 machine-consistent, 5 review-needed). **No recognition model was run during this update; these are existing historical records only.**
- Every one of the 48 clips from **both** historical screens matched the exact original WAV SHA-256 AND corresponding author-expected narration text SHA-256 in the preserved synthesis receipt. The prior slides PDF in some historical QA summary receipts has a different hash from the current source version. Such a summary is *not* substituted for the exact per-WAV evidence or used to approve current video semantics.

## New packet module

`selenium_pipeline.source_bound_narration_review_packet` first calls the source-bound preserved-audio preflight from PR #126, checks that neither historic quality screen claims human or production approval, binds every WAV hash and verbatim authored text to both retrospective screens, then copies the exact original WAVs into a NEW isolated folder (never overwrites existing media). It creates:

- `audio/sXX_eYY.wav`: 48 exact original PCM recordings
- `index.html`: local browser audio players and verbatim expected narration beside historical screen transcripts
- `lecturer_listening_worklist.csv`: spreadsheet-friendly review decisions, default all `NO`
- `review_packet_manifest.json`: source/slide/plan hashes, every original WAV digest and machine-screen discrepancy priority

**Review order:** P1 six flagged clips `s05_e03.wav`, `s07_e01.wav`, `s10_e01.wav`, `s12_e01.wav`, `s12_e02.wav`, `s13_e02.wav`; P2 29 clips lacking prior Gemini recognition; P3 13 machine-consistent clips. All 48 still require independent human audio listening. The `s05_e03` Gemini screen specifically reports missing/changed math-spoken tokens (equals/times/negative/positive); compare the actual WAV with the displayed equation and script before deciding whether a new full-batch isolated TTS rendering is necessary.

## Safe commands

From a clean isolated clone on HP, Dell-115 or Yoga 6, specify the original paths and a **new** destination outside the original sources. Example:

```powershell
$root = 'G:\My Drive\MicroGen_Experimental_Review_20261016'
$origin = Join-Path $root 'MicroGen_AI_Web_Thomas84_FullElement_GeminiKore_ReviewOnly_20261016'
$source = 'G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4'
$out = Join-Path $env:TEMP 'thomas84_human_audio_review_new' # must NOT exist
python -m selenium_pipeline.source_bound_narration_review_packet `
  --source (Join-Path $source 'source.pdf') `
  --slides (Join-Path $source 'slides.pdf') `
  --authored (Join-Path $origin 'authored_original_plan.json') `
  --frozen (Join-Path $origin 'frozen_inputs') `
  --synthesis-receipt (Join-Path $origin 'tts_synthesis_receipt.json') `
  --refined-screen (Join-Path $root 'MicroGen_AI_Web_Thomas84_Real48_TTS_Quality_20261016\ThreeLayer_Real48_Refined_QA.json') `
  --offline-receipts (Join-Path $root 'MicroGen_AI_Web_Thomas84_IndependentOfflineSpeech_QA_20261016\recognition_receipts') `
  --destination $out
```

This produces no `lecture_completion.json`, never changes a published file, and never invokes Whisper/ASR or external Google API. The HTML is intended for local browser playback with its sibling `audio` folder (not for direct Drive HTML execution). The reviewer's `YES/NO` columns in CSV remain `NO` until real human checking and separate academic signoff. CSV formula-injection guard is applied to untrusted machine transcript strings.

## Thomas 8.5 and 8.6 readiness

**8.5:** The already-preserved `Thomas85_AutoCandidates.json` matches the current `source.pdf`, `slides.pdf` and `script.txt` SHA-256. It contains 20 slides, 138 candidate visual targets, 78 existing narration utterances, **62 ambiguous mappings**, and `can_stage_or_synthesize_audio=false`.

**8.6:** The deterministic existing `element_plan_autodraft.propose` pipeline produced a new isolated draft from its unchanged current source, slides and script. It contains 17 slides, 114 candidate visual targets, 69 existing narration utterances, **50 ambiguous mappings**, and `can_stage_or_synthesize_audio=false`. HP, Dell-115 and Yoga6 generated byte-identical JSON SHA-256 `4728541d2c9022894443ebf783a05ed89eb1c4a16a5f3aed42892bb4472a52bd`. The new mandatory review worklist must be inspected before any true source-to-element timed narration can be generated. Reported zero `figure_panel_slide_count` means *no suspect panel was detected by the heuristic*, **not** lecturer confirmation that figures have no multipanel defect.

Neither 8.5 nor 8.6 is ready for honest element-highlighted replacement MP4s because the author-to-visual mappings and independent content approval are missing. Original single MP4s for 8.5 and 8.6 still exceed 600 s, so they must not be released as accepted videos.

## Remaining release gates

Authentic spoken-word fidelity, correct mathematical pronunciation, review of all equations and complete multipanel figures, full-lecture author signoff, and final student-publication permission are all separate obligations. Successful hash checks, scripted machine transcription, an audio player or technical video pixels do not fulfill them. Do not merge stacked draft PRs or sync dirty production trees until integration and acceptance are separately approved.