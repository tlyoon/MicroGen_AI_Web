# MicroGen source-bound multipart highlighted review bridge

15 October 2026. Status: tested review-only prototype; NOT an approved production renderer.

## Purpose

This bridge turns prepared semantic video parts into separate playable MP4 review previews. Each part requires a source-bound storyboard, a PDF with stable element-ID hyperlinks, and final narration WAV chunks whose order and spoken-text hashes match the storyboard. Timing is measured from the WAV chunks, not inferred from the finished MP4 or invented from narration text.

## Prepared input folder

Place all inputs outside the textbook source directory:

stage/series_inputs.json
stage/part_01/storyboard.json
stage/part_01/instrumented.pdf
stage/part_01/tts_chunks.json
stage/part_01/wav/n1.wav, n2.wav ...
stage/part_02/... (same files for its own part)

The series_inputs.json contains schema_version=1, status=review_only_source_bound_inputs, the exact original source_pdf SHA-256, the canonical plan SHA-256 and the ordered part names (part_01, part_02, etc.). Every storyboard part_id and plan_sha256 must match. TTS chunk metadata uses the exact segment_id, filename, speech_sha256, voice_id, pause_after_ms keys.

## Command

From a MicroGen code checkout (use an existing correct Python environment):

    python -m selenium_pipeline.series_cli render-preview --source-pdf PATH_TO_SOURCE_PDF --prepared-parts PATH_TO_STAGE --output PATH_TO_NEW_REVIEW_FOLDER

Optional standalone equivalent:

    python -m selenium_pipeline.series_review_cli --source-pdf PATH_TO_SOURCE_PDF --prepared-parts PATH_TO_STAGE --output-root PATH_TO_NEW_REVIEW_FOLDER

Each part is composed as a timed H.264/AAC MP4 by the existing highlight_video_preview code, with source-linked PDF geometry, per-chunk WAV frame timing and encoded transition evidence. A plain slide is displayed during intentional speech pauses. The working directory must be empty and all outputs must be created at new paths.

## Safety guarantees and limitations

- No Gemini/TTS calls are made; source PDF and prepared WAV/slide input remain unchanged.
- Rejects stale source SHA, invalid/out-of-order parts, missing or reused chunk filenames, and target paths inside the source tree or existing targets.
- Reuses pixel-identical link-stripping, geometry and image-text-clearance guards; measures encoded MP4 and enforces strictly less than 600 seconds per part.
- Every output is explicitly review_only_not_approved; only review_receipt.json and series_review_receipt.json are created, never lecture_completion.json.
- Speech timing follows final WAV SEGMENT boundaries. A whole-slide narration WAV is not proof of precise internal spoken words. Segment speech-text fidelity still requires QA; no word-level forced alignment is claimed.
- Synthetic waveform test tones demonstrate rendering, not actual intelligible narration. Do not claim full teaching-content correctness.
- To publish an actual course lesson, conduct mathematical/source/figure review, verify highlighted encoded pixels against target regions and spoken words, and issue new production receipts only after independently checked acceptance.

## Verified offline evidence

Tests/test_series_review_preview.py creates two real synthetic highlighted MP4s from separate part_01 and part_02 Beamer-like instrumented PDF pages. It verifies source-hash binding, SHA-256, both strict durations, correct ordered part labels, preview-only status, no production acceptance receipt, and safe rejection of tampered sources, missing WAVs and unsafe paths. Existing highlight_video_preview tests independently decode sample frames and verify visual changes during speech and pauses.

Production launchers on HP, Yoga 6 and Dell-115 are not altered by this work. The historic Thomas 8.4, 8.5 and 8.6 MP4 files remain archived and noncompliant with the new contract.
## Encoded-pixel verification added

Timing proofs alone do not prove which source-linked highlight is visible in an MP4. The review bridge now decodes the real VFR frame timestamps and selects the last actual encoded frame at or before each measured speech-segment midpoint. It compares target-region pixels against the expected active-emphasis PNG and against the plain slide; if the active highlight does not measurably improve the match, the preview fails rather than producing a review receipt. Each part includes encoded_pixel_qa.json with per-target difference evidence. A negative regression encodes a plain static slide with the same audio and confirms the pixel verifier rejects that impostor. Mathematical meaning and exact spoken-word fidelity remain separate review gates.
