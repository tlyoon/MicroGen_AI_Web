# PR506 — Original-source reviewed audio to actual FFmpeg MP4 operator handoff

This PR moves the **general lecture-generation pipeline** forward from
source-stage scripts and slides to the existing actual reviewed-element
audio/video renderer. It is not another fix for a particular Serway PDF or
Thomas Figure 8.3, and it does not resubmit any Gemini request.

## How to use the native Windows operator

From the exact isolated checkout on Dell-115, provide a new independent
original-source trial whose figures, Beamer slides, narration and deterministic
script QA are already accepted and SHA-bound. Provide the independently
reviewed element draft and selection, the exact pre-TTS request, and **already
recorded** PCM WAV files plus per-WAV verification receipts. The source,
slides and script are verified from the SAME staged original source tree.

~~~powershell
$repo = Join-Path $env:LOCALAPPDATA 'MicroGen_PR506_20261104'
$py = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web\pr493_clean_pypi_20261104\Scripts\python.exe'
Set-Location $repo
$common = @{
  Mode = 'LectureMediaReview'
  SourceRoot = 'EXACT_READ_ONLY_PUBLISHER_ROOT'
  Section = 'EXACT_NEW_SECTION'
  TrialDir = 'EXACT_NEW_EXTERNAL_IMMUTABLE_SOURCE_TRIAL'
  ReviewDraft = 'EXACT_SOURCE_MATCHED_ELEMENT_DRAFT.json'
  ReviewSelection = 'EXACT_REVIEWED_SELECTION.json'
  TtsRequest = 'EXACT_APPROVED_TTS_REQUEST.json'
  AudioDir = 'EXACT_EXISTING_FROZEN_RECORDED_WAV_DIRECTORY'
  ReviewOutDir = 'EXACT_NOT_YET_CREATED_EXTERNAL_MP4_REVIEW_DIRECTORY'
  Python = $py
}

# Strict preflight only; no model, no TTS, no MP4 render:
& .\MicroGen-Windows.ps1 @common

# One explicit local FFmpeg encoding request ONLY after review/audio evidence:
& .\MicroGen-Windows.ps1 @common -ConfirmMediaReviewRender
~~~

The first command is read-only and outputs
`REVIEWED_MEDIA_INPUTS_READY_EXPLICIT_FFMPEG_ONLY`, or a clearly
blocked state if the exact original source stages/audio receipts are missing.
The separate render command calls the already-implemented
`windows_reviewed_element_media_bridge.render_review()` after matching
the original-source SHA and frozen slides/script hashes.

That bridge re-derives source/slide/script candidate semantics and validates
the reviewer selection, exact spoken utterance coverage, TTS model/voice
identity and recorded WAV receipts. It uses local FFmpeg to emit H264/AAC
highlighted multipart MP4 reviews and independently decodes/rechecks pixels.
The new caller does NOT generate narration, TTS audio or a new PDF; it does
not automatically publish to Moodle/YouTube or students.

## Recovery and immutable technical acceptance

- The first render requires a **brand-new** external output directory. It
  never deletes or overwrites any existing user-owned media directory.
- The completed renderer's own `review_only_receipt.json` must match its
  actual report and the exact frozen source PDF, slides and script bytes.
- Only then the new wrapper commits an immutable canonical
  `sourcebound_media_handoff_receipt.json` including input draft,
  reviewer selection, pre-TTS request, every WAV and each WAV proof SHA,
  all exact decoded MP4 SHA values and a hash of the renderer's receipt.
- Subsequent `LectureMediaReview` invocations **reinspect and reuse**
  exact accepted MP4 bytes, without rerunning FFmpeg. Changed output,
  reviewed audio evidence, script or original source fails closed.
- A partially generated review output with no complete handoff receipt
  returns `HALTED_PARTIAL_MEDIA_OUTPUT_NO_REENCODE`. It is preserved
  for explicit operator review; it is NOT silently replayed or overwritten.
- The status after new successful encoding is
  `SOURCEBOUND_REVIEWED_MEDIA_NEW_MP4_TECHNICAL_PASS_ONLY`.
  Output remains **review-only**. Independent expert academic review,
  perceptual voice signoff, release authorization and student publication
  are still distinct barriers.

## Difference from prior stages

PR505's read-only handoff now correctly returns the *staged*
`source_tree/<chapter>/<section>/source.pdf` alongside `slides.pdf`
and `script.txt` in the same directory. The read-only publisher original
path is preserved separately as `publisher_source`, with both original and
staged PDF SHA verification. The reviewed media bridge's exact-source
triad is never forged by pointing at the protected publisher PDF.

The PR506 tests cover read-only preflight, exact staged source routing,
one successful mock reviewed encode, immutable prior reviewed media reuse,
corrupted video, changed WAV proof, partial output directory quarantine,
missing upstream source-stage receipts and publisher PDF mutation.
The existing separate `test_windows_reviewed_element_media_bridge`
already tests a genuine **FFmpeg synthetic MP4** encode and decoded
pixel review with fake in-memory TTS, not actual paid Gemini output.
PowerShell mode tests ensure FFmpeg is never invoked without explicit
consent and the original PDF must not be bypassed.

## Release boundary

The code can now drive a **complete review-video artifact** from an
independently accepted source, slides, script and previously recorded,
approved WAV evidence, using the same official Windows operator.
It is not evidence that a second real textbook source is complete.
That requires a distinct original generated lesson with real reviewed audio,
full QA, and separate authorization. Historical 770+ stacked commits have
not been merged into main. No HP/Yoga/Ubuntu or local model is involved.
