# PR215–PR219: real recorded-audio encoded multipart previews (Dell-115)

21 October 2026. Stacked draft PRs on #214. This batch intentionally
does NOT reopen the solved Figure 8.3 layout bug (#169/#170, #193).

## Progress verified on real original Thomas Calculus materials

- PR215: independent decoded-frame checks *before and after* actual
  element WAV boundaries. Rejects shifted or forged transition receipts.
  Tested using real FFmpeg with synthetic separate PCM clips.
- PR216: isolated real slide-PDF and original recorded WAV video preview
  with SHA-256 immutable source/script/slides/WAV checks. Real Thomas 8.4
  slide 1: source PCM 3.8653s, encoded MP4 3.87s.
- PR217: contiguous original recorded slide/WAV multipart preview,
  immutable originals, bounded duration; real 8.4 slides 1-2: original
  43.4606s, encoded 43.5s. An initial FFmpeg -shortest duration drift
  for slide2 (40.9s encoded vs 39.5953s WAV) was detected; corrected
  with explicit measured PCM duration cap before acceptance.
- PR218: independent batch orchestration and durable subchapter receipt
  recovery for authentic WAV multipart VIDEO previews; no overwriting.
  Three full genuine first-part review MP4 files independently rendered.
- PR219: start-at-second-part run option and independent dual-stage
  source/audio/video acceptance gate. On Dell-115 all six genuine recorded
  WAV multipart review MP4s now exist in separate local staged folders:

| Topic | Encoded part 1 | Encoded part 2 |
| --- | ---: | ---: |
| 8.4 | 321.88 s | 310.78 s |
| 8.5 | 398.53 s | 362.57 s |
| 8.6 | 330.66 s | 298.46 s |

Each real encoded part is STRICTLY < 600 seconds. The independent
cross-stage auditor re-read original WAV/PDF checksums, per-part records,
actual MP4 hashes and ffprobe durations and confirmed six valid technical
WHOLE-SLIDE review parts. External review locations on Dell-115:

- `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\genuine_84_85_86_first_parts_preview_1909`
- `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\genuine_84_85_86_second_parts_preview_1916`
- `%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\genuine_84_85_86_all_six_parts_verified_20261021.json`

## What is NOT proven

These use genuine original slide-level recorded audio and actual PDFs.
**They are not narration-to-individual-slide-element synchronized videos.**
No element-level Flash-Lite/Kore TTS audio was generated or billed.
Source mathematical semantic mapping / speech-to-highlight alignment
and manual academic/listening QA remain distinct requirements before
any production/students acceptance. Do NOT auto-promote these six
previews into the original student video locations or overwrite any
original slides/WAVs/MP4s. No HP/Yoga6/Zenbook, no Whisper/ASR,
no GCS distributed lease, no protected-main merge, no publication.

## Next justifiable work

Complete source-confirmed nonliteral math-target mapping for the 218
original narration segments across 8.4-8.6, use the existing approved
Flash-Lite/Kore same-voice TTS workflow once exact segment-level source
selections and billing authorization are valid, and use PR214/215
genuine per-element MP4 encoding plus decoded frame-boundary audits.
Real whole-slide previews now demonstrate the genuine media preservation,
part splitting and measured duration features work end-to-end.
