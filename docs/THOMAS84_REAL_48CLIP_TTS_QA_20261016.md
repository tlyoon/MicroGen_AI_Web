# Thomas Calculus 8.4: three-layer TTS QA on all 48 real Gemini WAVs

**16 October 2026 — review-only evidence; NOT a production approval.**

This is a source-bound run of the reusable offline three-layer TTS quality
screen, not merely unit tests. It uses the existing corrected-layout authored
plan, 48 original Gemini 3.8 Flash Lite TTS / Kore WAVs, and the 14 completed
Gemini 3.1 Flash Lite ASR receipts. The original source PDF, slides, WAVs,
and both corrected review MP4s were not modified.

## Measured actual WAV results

| Measurement | Result |
| --- | --- |
| Clips technically screened | 48/48 |
| Audio technical rejection | 0 |
| RMS loudness range (dBFS) | -19.53 to -15.85 |
| Peak level range (dBFS) | -1.92 to -0.54 |
| Clipped sample fraction | 0 for every clip |
| Script-derived pace | 88.5 to 149.0 words/minute |
| Longest low-energy interval | 0.36 to 0.87 seconds |
| Independent ASR transcripts available | 14/48 |
| Machine-consistent and no review flags | 13 |
| Mathematical/speech recognition mismatch flagged | 1 (s05_e03.wav) |
| Clips missing independent ASR | 34 |
| Human listening/academic signoff | NOT performed |
| Production acceptance | BLOCKED |

All 48 have technically acceptable basic energy and clipping measures.
This is not a guarantee of human-like speech, a correct mathematical voice,
or perceptual clarity. Energy-based silence detection is **not** voice activity
detection; words/minute is computed from *intended script*, not an actual
word-level time alignment.

## False-positive fix and strict evidence recalculation

The initial review marked `s01_e01.wav` because the synthesized narration
script said “Section eight point four” and Gemini ASR wrote “Section 8.4”.
The conservative math-token checker originally flagged the digit spellings.
The corrected checker normalizes *single-digit glyphs* to number words while
retaining negative/positive signs and all operators. After this change, the
false alarm disappears. This cannot remove the separate genuine question at
`s05_e03.wav`, where inverse-sine/±π/2 notation remains uncertain.

The strict full-series gate was strengthened to reproduce every acoustic
metric and independent-transcript/math flag from original source inputs,
rejecting even correctly named but *altered* QA JSON rows. It does not rely on
a mutable `machine_passed` label. A new forged-report regression is included.

For the actual Thomas 8.4 corrected two-part videos:
- Independent technical re-evaluation **PASS**: unchanged 17 slides, all 48
  WAV SHA-256 values, 23+25 decoded highlight events, two MP4 lengths <600s.
- Independent TTS quality screen: **13 screen-consistent, 1 flagged, 34 pending**.
- Full-series audit with `--require-quality` **REJECTED** the remaining
  review requirements, creating no approval receipt.
- All output files are review-only; no independent academic or human
  listening approval was claimed.

## Reproduction

Run the existing offline `selenium_pipeline.tts_quality_gate` command with
the exact corrected authored plan and original WAV folder. Use the
rebound-plan-specific 14-clip ASR evidence directory so the hash binding
matches the corrected slide PDF. Save to a *new* JSON path only.

Use the existing `selenium_pipeline.element_series_audit` command with
`--quality-report` pointing to the actual report. It now fully recomputes
the quality screen, and can refuse pending/flagged cases using
`--require-quality`. To require the independent transcription gate as well,
add `--require-asr`; neither option grants academic permission automatically.

**Next real blocker**: obtain and assess the remaining 34 actual ASR clips,
resolve `s05_e03.wav` through listening/mathematical verification, and
complete academic approval. Keep PRs #91 onward draft and unmerged, and do
not replace original student-facing files.
