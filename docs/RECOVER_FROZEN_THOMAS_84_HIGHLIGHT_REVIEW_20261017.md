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
## Independent fresh recheck of the ORIGINAL preserved October 16 MP4s

After the new source-bound reference bundle was rebuilt, `recheck_archived_highlight_mp4.audit_archived()` was added to decode the **original archived MP4s themselves** (not just the new render) against the reconstructed narrated WAV, source-bound geometry and original storyboard. It demands the original archive series receipt match all archived MP4 SHA-256 digests, plan/source SHA-256, combined WAV SHA-256 and storyboard SHA-256 before decoding. It then validates the actual original encoded frame pixels against the independent active-element reference PNGs and uses actual decoded frame PTS versus each narration cue.

The exact original October 16 MP4 SHA-256 digests are:
- `Thomas_8_4_Part_1_Slides_1-8_REVIEW_ONLY.mp4`: `9adb55ae37075d48b682e0f27bde5726e0ae86ce1141e50bcb00c195848cc5c4`
- `Thomas_8_4_Part_2_Slides_9-17_REVIEW_ONLY.mp4`: `cf7885252b4bef7599ccaa18a369a7832cdb87bd27ca685f29d8862e9d95f8a9`

**HP, Dell-115 and Yoga 6 independently decoded both exact hash-verified preserved MP4s and found active target highlights at all 23 + 25 real events, with original durations of 291.40 and 322.96 seconds.** HP measured the maximum sampled decoded frame start offset as 0.00 seconds for both original MP4 parts. This is now fresh independent technical verification **of the archived MP4s**, not just a historical summary and not a claim that the encoded bytes equal the separately rebuilt videos.

### Adversarial pixel regression and corrective hardening

One synthetic attack test discovered that the old decoder's `err_base - err_expected >= 1` rule by itself could accept a **blacked-out** video. Example corrupted active-vs-reference mean absolute errors: **219 vs 238** RGB units, creating a misleading positive difference. The original preserved Thomas 8.4 videos had much lower true active-reference errors (part 1 **1.888–7.580**, part 2 **1.784–5.141**). The pixel verifier has been strengthened to require **all three** conditions: active highlight improves over base by at least 1 RGB-MAE unit, absolute active-frame MAE at most **30**, and active error at most **80%** of baseline error. Deliberately blackened frames should now fail even with a forged matching archived SHA-256 receipt.

Tests use local synthetic H.264/AAC encoding. Technical acceptance never implies actual acoustical spoken-word matching, mathematical correctness, complete figure panel adequacy or human release approval. No original PDF/WAV/MP4 was modified; neither the original nor rebuilt MP4s are automatically student-published.