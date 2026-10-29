# Thomas 8.4 six-clip narration and source-slide review — 18 October 2026

**Review-only acceptance preparation. No actual human listening, math/figure release approval, regenerated TTS, paid call or student publishing.**

## Evidence and source chain

Original lecture PDFs are `G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4\source.pdf` and `slides.pdf`. Original narrated per-element WAVs and authored plan are retained in `MicroGen_AI_Web_Thomas84_FullElement_GeminiKore_ReviewOnly_20261016`. Historical 48-clip Gemini and offline recognition reports were checked against every *original* source-bound WAV SHA-256 and verbatim reference speech text SHA-256; all 48 matched, before selecting six flagged items.

The original slide PDF contains 17 pages. Actual source-bound PDF pages **5, 7, 10, 12, 13** were inspected (text extraction only as an aid, not authoritative for roots or fractions). An independent reviewer can now view locally rendered page PNGs beside each original WAV, the author-expected words and both fallible historical machine transcripts. This avoids conflating a model's mathematical glyphs with the actual words spoken.

## Specific review checks (not adjudications)

| Original WAV | Slide | Original authored mathematics on slide (as checked from PDF content) | Historical discrepancy | What the human must verify |
|---|---:|---|---|---|
| `s05_e03.wav` | 5 | `x = a sin u`, inverse branch `−π/2 ≤ u ≤ π/2` | Gemini rendered spoken `equals`, `times`, `negative`, `positive` as `=`, `*`, `−`, `+`; offline ASR WER 0.0645 | Actual pronunciation and signs, both endpoints, and 'middle graph' visual referent |
| `s07_e01.wav` | 7 | `∫ dx/√(4+x²)`, `x=2 tan u`, `dx=2 sec²u du` | Offline transcript mainly uses `1`, `4`, `2`, `dx`, `du` vs words; raw WER 0.30 | Confirm integrand grouping, powers, `sec²` and substitution audibly |
| `s10_e01.wav` | 10 | `∫ x² dx/√(9−x²)`, `x=3 sin u`, `dx=3 cos u du` | ASR digits `3`, `9` vs words; WER 0.2069 | Listen to denominator/radical and distinguish numerator `x²` visually; the short original utterance names the denominator rather than restating full integrand |
| `s12_e01.wav` | 12 | `∫ dx/√(25x²−4)` for `x>2/5` | ASR `25x`, `1`, `two-fifths` formatting; WER 0.25 | Check positive domain restriction, radical boundary, all signs |
| `s12_e02.wav` | 12 | `√(25x²−4)=5√(x²−(2/5)²)` | ASR `4 25ths` vs 'four twenty-fifths'; WER 0.2667 | Confirm `5√(x²−4/25)` is articulated unambiguously and radical/fraction scope is intact |
| `s13_e02.wav` | 13 | `sec u=5x/2`, `tan u=√(25x²−4)/2` | ASR numeric glyphs and math layout; WER 0.2963 | Confirm division and square-root scope, plus correct reference-triangle geometry |

**Important:** These written source/narration expressions are *plausibly consistent*, and model outputs often differ only in typography, but neither source-text extraction nor machine recognition proves the original human-audible WAV correctly speaks the math. This is not a numerical-WER-based acceptance gate. A figure can be wrongly cropped or a radical's scope can be wrong even when text extraction looks consistent. Every clip remains explicitly unresolved.

## Repeatable reviewer-packet command

On HP, Dell-115 or Yoga6, in a **clean isolated** checkout (not the production code folder), specify a **new unused** local output path:

```powershell
$root = 'G:\My Drive\MicroGen_Experimental_Review_20261016'
$original = Join-Path $root 'MicroGen_AI_Web_Thomas84_FullElement_GeminiKore_ReviewOnly_20261016'
$src = 'G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4'
python -m selenium_pipeline.flagged_narration_slide_review `
  --source (Join-Path $src 'source.pdf') `
  --slides (Join-Path $src 'slides.pdf') `
  --authored (Join-Path $original 'authored_original_plan.json') `
  --frozen (Join-Path $original 'frozen_inputs') `
  --synthesis-receipt (Join-Path $original 'tts_synthesis_receipt.json') `
  --refined-screen (Join-Path $root 'MicroGen_AI_Web_Thomas84_Real48_TTS_Quality_20261016\ThreeLayer_Real48_Refined_QA.json') `
  --offline-receipts (Join-Path $root 'MicroGen_AI_Web_Thomas84_IndependentOfflineSpeech_QA_20261016\recognition_receipts') `
  --destination (Join-Path $env:TEMP 'thomas84_new_six_flagged_slide_review')
```

The program first refuses mismatched source/slide/plan hashes, incomplete or changed original WAV identities, missing/transcript-mismatched historical QA receipts, previous false human approval, missing slide images, or an existing/unsafe destination. It creates a temporary staging directory before renaming the complete packet; incomplete outputs are cleaned. The pack includes six original WAV files, five slide PNGs, `index.html` for side-by-side local browser review and `evidence.json` with all listening/science approvals still `false`.

### Actual Thomas 8.4 result

HP created the new isolated packet and SHA-verified the copied **13/13 files** in this distinct review-only Drive folder:

`G:\My Drive\MicroGen_Experimental_Review_20261016\MicroGen_AI_Web_Thomas84_SixFlaggedMathAudioSlide_ReviewOnly_20261018`.

Contents: **6 original source-hash-bound audio clips + 5 rendered slide page images + 1 HTML playback page + 1 JSON evidence manifest.** SHA-256 of `evidence.json`: `0d649ab0c0815c17270105792195a35aad67b8918e18fed95c20ed03a86c120b`. Audio regeneration and provider billing were not run.

## Release blockers remain

Academic/lecturer listening, pronunciation of every math symbol, complete figure panels and the remaining 42 audio clips must be independently accepted. The two existing Thomas 8.4 archived review MP4s passed technical strict <600 second and actual decoded 48/48 highlighted-pixel checks on three PCs, **but no student publication permission follows**. Thomas 8.5/8.6 author mapping ambiguities and compliant replacement videos are separate pending work. Keep draft PRs unmerged until integration and content approval.