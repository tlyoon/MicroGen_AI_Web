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
## Refreshed Thomas 8.5 draft comparison — do not confuse algorithm changes with academic approval

The historical 16 October auto-candidate remained **62/78 ambiguous**. Regenerating it from the same source PDF, slides PDF and verbatim script under the current checkout on 18 October yielded **58/78 ambiguous**, with all 20 slides and 78 original narration utterance texts byte-for-byte identical. Exactly four *automated ambiguity booleans* changed from true to false: `s003.utterance.004`, `s008.utterance.003`, `s009.utterance.004` and `s012.utterance.004`. These are heuristic ranking changes, **not** author-approved mappings. The refreshed candidate remains `REVIEW_REQUIRED_NOT_TTS_READY` and `can_stage_or_synthesize_audio=false`.

HP, Dell-115 and Yoga6 reproduced the logical UTF-8 serialized draft hash **`3df6f7ae0292b1017e86fda53ee775aa6491d9716ceed9c4bc1010ae8ce21414`**. The copy written to disk by Windows Python has CRLF newlines and a different raw file digest; raw newline conversion is **not** a semantic or content discrepancy. A new isolated review-only Drive folder `MicroGen_AI_Web_Thomas85_RefreshedAutoCandidates_ReviewOnly_20261018` contains the new JSON, new author mapping-review worklist and explicit comparison of the four flipped heuristics. The historical Oct 16 draft remains untouched.

## New Google Drive review-only deliverables (copied without changing originals)

- Thomas 8.4 48-clip full listening packet: `https://drive.google.com/drive/folders/1rc7SyZ86sitX0TWslSgkG2W1E2szDrdH` — 48 WAVs plus HTML, CSV and JSON (51 files; byte-identical after transfer).
- Thomas 8.5 refreshed mapping worklist: `https://drive.google.com/drive/folders/1aX-LSJwv7RHmyF_SVlaYU5tw2nPBUjv6` — refreshed JSON, worklist and four-heuristic comparison (3 files).
- Thomas 8.6 new mapping worklist: `https://drive.google.com/drive/folders/17xZZDVUetP4TWTvuBBEVoSm7TZeO2_jm` — source-bound review-only candidate JSON and worklist (2 files).

All three generated folders are **distinct, newly created review-only outputs**, separate from the production source directory, and every transferred file was checked byte-for-byte. None constitutes student-ready speech or video.