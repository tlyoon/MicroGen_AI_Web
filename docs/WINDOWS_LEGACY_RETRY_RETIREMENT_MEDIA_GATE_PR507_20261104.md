# PR507 — Stop legacy automatic retries; verify sourcebound MP4 release evidence

The Windows production source-to-video code has been connected in
PR505/506, but the old multi-retry orchestration command remained callable.
PR507 explicitly removes that unsafe **live entrypoint**, while preserving
historical SHA-bound checkpoints and read-only evidence inspection.

This is a general codebase milestone, not another attempt to repair
Serway §24.4 slides or Thomas calculus Figure 8.3.

## 1. A single supported production dispatch path

Use `MicroGen-Windows.ps1` on Dell-115 in these distinct modes:

1. `LectureStatus` for read-only original figure/slide/script/QA
   status and the single next eligible stage.
2. `LectureAdvance` for **one** explicitly authorized source stage.
   No automatic chain or retry; stage/model claims are persisted first.
   The independent API route requires `-ConfirmContentApiCost`.
3. `LectureMediaReview` for read-only review of previously approved,
   recorded per-element WAV audio. Local FFmpeg encoding requires
   separately explicit `-ConfirmMediaReviewRender`.
4. The read-only `windows_release_readiness_board` now takes the
   existing external reviewed MP4 path for independent revalidation.

Do not use the old module's `--execute-live` or
`--resume-after-code-repair`: both return
`LEGACY_MULTIRETRY_PIPELINE_RETIRED` with an error exit, **before**
PDF staging, provider submission, TTS or video work. Its historical
`stage_tree`, SHA helper and recovered checkpoint data remain available
for historical compatibility. Its old non-live planning mode may still
create an isolated local snapshot/checkpoint; it cannot make provider
requests and is **not** the supported new production operator. No old source request is
implicitly retried on another Gemini key after 503/504.

## 2. Read-only independent release evidence

PR506's verified technical review video receipt is external to both
the publisher PDF and the staged source folder. PR507 adds exact
`review_input_paths` roles for draft, reviewer selection, frozen TTS
request and existing per-WAV audio folder, alongside the prior SHA
dictionary binding each WAV and verification proof, original PDF,
slideshow, script and each decoded H264/AAC MP4 part.

The independent inspector:

- Loads only an existing immutable trial and existing media directory.
- Reconfirms the authentic original publisher source, staged byte-identical
  PDF, exact prior figure/slide/narration/script-QA receipts and technical
  checks. Missing or changed source bytes stop the verification.
- Reconstructs role paths from the immutable media receipt and hashes the
  same reviewed draft, selection, pre-TTS request, every WAV and proof.
- Verifies the FFmpeg review receipt and actual sourcebound encoded MP4
  SHA values. It never re-encodes or generates model/TTS content.
- Reports `EXACT_SOURCEBOUND_MP4_TECHNICAL_EVIDENCE_VERIFIED_ONLY` with
  `technical_sourcebound_mp4_verified = true` only when **all** exact
  byte checks pass. An incomplete, tampered or foreign receipt is blocked.

To inspect it within the existing Windows release-readiness report:

~~~powershell
$repo = Join-Path $env:LOCALAPPDATA 'MicroGen_PR507_20261104'
$py = Join-Path $env:LOCALAPPDATA 'MicroGen_AI_Web\pr493_clean_pypi_20261104\Scripts\python.exe'
Set-Location $repo
& $py -m selenium_pipeline.windows_release_readiness_board `
  --repo $repo `
  --jobs-dir 'EXACT_EXISTING_IMMUTABLE_JOB_DIRECTORY' `
  --fresh-trial-dir 'EXACT_EXISTING_SOURCE_LOCKED_TRIAL' `
  --reviewed-media-dir 'EXACT_EXISTING_EXTERNAL_MP4_REVIEW' `
  --worker-python $py
~~~

Without `--reviewed-media-dir`, the technical MP4 gate stays false.
With a damaged or unauthorized media reference, the gate explicitly
reports `SOURCEBOUND_REVIEWED_MP4_EVIDENCE_REJECTED`, rather than
trusting a claimed successful video or repeating FFmpeg.

## 3. Release remains blocked until independently accepted

This new gate is named
`reviewed_sourcebound_mp4_technical_integrity_verified`.
Its passing status **does not mean** any of the following is true:

- Original mathematical/diagram quality independently approved.
- Perceptual accuracy and the requested TTS voice identity certified.
- A distinct second genuine original-source complete lecture accepted.
- The accumulated historical draft PR stack reviewed and safely merged.
- Exact final-head Windows CI, final installation and release signoff done.
- Student distribution, Moodle or YouTube publication authorized.

`second_distinct_new_original_full_lecture_accepted` is deliberately
still false even when the technical MP4 check is green. The release
board can never grant publication from an MP4 signature alone.

## 4. Regression evidence and operational boundary

The new tests use a synthetic section 77.9, mock-only prerecorded PCM
and locally created reviewed-media evidence. They verify actual
source-stage and media receipt SHA chains, exact MP4 bytes, original
script mutation, WAV proof mutation, missing canonical receipt,
rejected malformed role paths and the release board's separate blocked
academic/publication states. Legacy live and repair-epoch entrypoints
are tested to refuse execution without even creating source snapshots.
PR506's existing Windows FFmpeg pixel-decoding tests remain included
in the release regression suite, with **no paid Gemini content/TTS**.

Any real second distinct textbook lesson must still follow the new
one-source per-stage mode, and generate reviewed narration/audio only
under explicit authorization. The historic Thomas §8.4 acceptance
cannot be represented as a new complete source by this receipt gate.

Dell-115 Windows only. Do not modify G: publisher/original files,
the shared dirty main checkout, or immutable previous attempts. No
HP/Yoga/Ubuntu/local models and no automatic student publication.
