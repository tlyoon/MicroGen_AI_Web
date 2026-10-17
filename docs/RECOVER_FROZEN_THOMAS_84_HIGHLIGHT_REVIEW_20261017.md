# Rebuild preserved Thomas 8.4 source-bound highlights — review only

17 October 2026. Development draft stacked after PR #125. Do not merge, deploy, overwrite existing content or publish to Moodle from technical verification.

## Recovered original inputs

Preserved review root: `G:\My Drive\MicroGen_Experimental_Review_20261016\MicroGen_AI_Web_Thomas84_FullElement_GeminiKore_ReviewOnly_20261016`.
Original lecture root: `G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4`.

The preserved review includes `authored_original_plan.json`, `tts_synthesis_receipt.json` and `frozen_inputs/` holding two instrumented PDFs, two storyboards, the per-part TTS manifests, element stage and input receipts, plus **48** original individual Gemini Flash-Lite/Kore PCM WAV segments. The plan covers 17 slides and is fully source bound.

Source PDF SHA-256: `b695018baa55f69ae3c9c875e7b1cb8ed284123d5a4b43f31314e659b1f22068`.
Slide PDF SHA-256: `f6219ee18be4e347132d59be0d55e19765f325efed0b9d3d6544959a6dda68d1`.
Authored plan SHA-256: `74bd58a7166f0b17615388a7ce0ae2fbc860b6a74bc53c69354c82851786caef`.

Before any output, `recover_frozen_highlight_review.preflight` verifies complete source/slide/plan/voice bindings and **all 48** original declared speech-text hashes and WAV content SHA-256 against the preserved original synthesis receipt. The original text binding alone does not establish acoustic speech fidelity.

## Safe repeatable command

Run only from a clean isolated development checkout, with a **new** local TEMP destination; never inside the original Drive folders:

```powershell
$source = 'G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4'
$review = 'G:\My Drive\MicroGen_Experimental_Review_20261016\MicroGen_AI_Web_Thomas84_FullElement_GeminiKore_ReviewOnly_20261016'
$destination = Join-Path $env:TEMP 'thomas84_fresh_review_unapproved' # Must not exist
python -m selenium_pipeline.recover_frozen_highlight_review `
  --source (Join-Path $source 'source.pdf') `
  --slides (Join-Path $source 'slides.pdf') `
  --authored (Join-Path $review 'authored_original_plan.json') `
  --frozen (Join-Path $review 'frozen_inputs') `
  --synthesis-receipt (Join-Path $review 'tts_synthesis_receipt.json') `
  --destination $destination
```

The command copies preserved inputs and WAVs to a **fresh, isolated local** review bundle; renders **new** encoded videos with offline FFmpeg and source-bound element timing; and independently re-decodes all highlighted regions using PR #125's pixel auditor. The destination contains `staged/`, `rendered/`, `frozen_original_element_audio/` and `recovered_review_technical_result.json`. All human/academic/production/student approval flags remain false. It is NOT a fresh re-audit of the previously archived MP4s.

## Actual three-PC verification

HP, Dell-115 and Yoga6 each independently rebuilt the real 8.4 lecture from preserved 48 WAVs without any paid TTS/API calls. Each passed an independent encoded frame active-element recheck:

| Rebuilt part | Slides | Encoded MP4 seconds | Verified element highlights |
|---|---:|---:|---:|
| Part 01 | 1–8 | 291.40 (<600) | 23/23 |
| Part 02 | 9–17 | 322.96 (<600) | 25/25 |
| Total | 17 | Two compliant parts | **48/48** |

Original source, slides, authored plan and provider synthesis receipt hashes were unchanged on each machine. The freshly encoded videos are separate review candidates with different hashes from the historical October 16 video exports. The original single-file 8.4 video remains overlong (633.93 s); original 8.5 (762.96 s) and 8.6 (630.96 s) are also overlong.

## Remaining release blockers

Fresh pixel verification establishes synchronized region highlighting in the newly rebuilt MP4s, not that the narrator actually says the displayed mathematics, that a highlighted figure is academically correct, or that the entire multipanel figure is complete. An earlier historic transcription effort assessed only 14/48 spoken elements and flagged one; independent listening and scientific approval are still needed. The software creates no `lecture_completion.json`, does not overwrite original lecture media and does not publish to students.

Regression tests cover complete-source preflight, source/WAV corruption rejection, refusal to overwrite, full fresh FFmpeg reconstruction and repeated read-only pixel re-audit. Keep all work limited to HP, Dell-115 and Yoga6 and do not use Zenbook, Whisper or GCS. The pre-existing Gemini Flash-Lite → Flash → conditionally approved Cloud TTS fallback policy remains unchanged.