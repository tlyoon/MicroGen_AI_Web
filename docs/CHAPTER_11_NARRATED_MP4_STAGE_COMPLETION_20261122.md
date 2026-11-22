# Chapter 11 narrated-MP4 stage completion — 22 November 2026

User-authorized scope: slide → narration → TTS → MP4, explicitly skipping independent highlight verification. The full G3 visual-highlight criterion remains **unverified**, not implicitly waived in other projects.

## Verified Dell-115 outputs

| Section | Narration/audio QA | Canonical MP4s | Result |
| --- | --- | --- | --- |
| 11.1 | 15/15 passed | slides.mp4, slides_part02.mp4 | Completed; static slides |
| 11.2 | historical 21/21 report | slides.mp4, slides_part02.mp4, slides_part03.mp4 | Existing files re-decoded |
| 11.3 | 15/15 passed | slides.mp4, slides_part02.mp4 | Completed; static slides |
| 11.4 | historical 23/23 report | slides.mp4, slides_part02.mp4, slides_part03.mp4 | Existing files re-decoded |
| 11.5 | 10/10 passed | slides.mp4 | Completed; static slides |

All **11 canonical MP4 parts** exist under the corresponding 11.x subfolder in G:\My Drive\Serway\Serway_8_14\11 on Dell-115. Every part was verified below 600 seconds, with audio/video streams and successful full FFmpeg decode. The five newly published parts are byte-identical copies of SHA-verified previously rendered review-only MP4s, after live source/PDF/script/WAV/acoustic-QA/preview-manifest verification. No TTS or paid Gemini requests were made. No previous media was overwritten.

11.2 and 11.4 retain their existing source-based completion receipts, three-part manifests and original MP4 files. Their old WAVs were previously cleaned up, so independent acoustic re-listening was not performed during this stage-only run; this operation reverified their 21/21 and 23/23 *recorded* QA and the actual MP4 streams.

## Explicit status separation

For 11.1, 11.3 and 11.5, the new technical scope receipt is .microgen_narrated_video_chain.json, and the existing lecture_parts_manifest.json style is used to index canonical MP4s. The independent_visual_highlight_acceptance value explicitly indicates not performed.

The chapter-level status is stored in G:\My Drive\Serway\Serway_8_14\11\.microgen_ch11_narrated_mp4_chain_status.json.

Do not create a conventional .microgen_completion.json for the three new sections or assert full G3 acceptance: source-timed highlighting remains outside the requested scope. The existence of an encoded narrated MP4 is not proof of independent source-grounded equation/figure activation or student-release permission.

## Repeatable, zero-provider-cost command

On Dell-115, from the verified code checkout, with the existing Python environment:

    python -m selenium_pipeline.narrated_video_chain --chapter-folder "G:\My Drive\Serway\Serway_8_14\11" --scope narrated-video-only

The exact user-scoped execution method is registered under EXPLICIT_USER_SCOPED_NARRATED_MP4_WITHOUT_HIGHLIGHT_QA in the executable recovery registry. Missing registry entry or scope flag fails closed; the normal visual-highlight release gate stays unchanged. Each rerun validates source, script, QA and original MP4 identities, reuses identical outputs without rerendering, and refuses conflicts or unsynchronized media.

## Real validation

- Actual run exited 0 at 17:31 MYT on 22 November 2026.
- Five preview-to-canonical copy operations retained exact SHA-256 checksums.
- Real 11.1/11.3/11.5 source and acoustic QA checks, with full encoded-media decode for all 11 parts.
- Recovery unit tests verify idempotence, conflicting-final refusal, unsafe sources, missing QA, maximum duration and disabled registry.
