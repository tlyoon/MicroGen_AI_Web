# MicroGen_AI_Web Phase 3C — Timed highlight MP4 preview compositor

**Date:** 13 October 2026
**Status:** Tested, sandbox-only **synthetic preview** integration; not yet the live Gemini/TTS textbook production pipeline.

## Purpose

Convert the accepted Phase 3B chain into a **real playable H.264/AAC MP4** whose visual emphasis follows the actual speech-segment boundaries from the final combined PCM WAV. This is *rendering an upstream-authored highlighting plan*, not retroactively splitting an overlong MP4.

## Pipeline

Input: approved in principle `storyboard.json`, *clean static* `slides.pdf` with its pixel-equivalence receipt, exact geometry map, sample-frame-derived `alignment.json`, and concatenated WAV.

1. Reject if PDF, audio, storyboard, geometry or timing hashes/receipts disagree. The workspace must be empty and destination file absent. Reject over-limit audio ≥630 s before encoding.
2. Render a base slide image and individual transparent/outlining highlight images (the source equations, letters, graph labels and figures are not obscured).
3. Schedule a variable-frame-rate image sequence with **each highlighted image displayed for its actual WAV-segment duration**, and a **plain unhighlighted slide** during intentional narration pauses. Respect changes of slide IDs.
4. Encode with FFmpeg H.264 video and AAC audio, preserve original narration sample speed, and probe the **encoded** MP4's audio/video streams and duration. Fail if the resulting clip is ≥630 s or differs from the actual input audio by >250 ms.
5. Decode the **encoded MP4** using FFmpeg's `showinfo` filter and compare actual frame timestamps with expected segment/pause transitions. Default tolerance: ≤150 ms. Do not claim the export passed merely because the WAV manifest contained correct times.
6. Publish only the passed candidate to a **new** requested path, never overwriting an existing output.

Implementation: `selenium_pipeline/highlight_video_preview.py`. This code leaves the existing MicroGen_AI_Web legacy `runner.py` and all production generation stages unchanged.

## Synthetic acceptance case

The offline regression `tests/test_highlight_video_preview.py` creates a vector PDF slide with three stable semantic regions and synthetic 1.0 s, 1.2 s, 1.4 s PCM audio chunks, separated by 100 ms pauses. It builds Beamer-style geometry, strips private PDF links with pixel-identical output, derives the audio event timeline, then produces an **actual 3.8-second H.264/AAC MP4**.

Expected display sequence:

| Time range | Visual emphasis |
|---|---|
| 0.0–1.0 s | Region 1 highlighted |
| 1.0–1.1 s | Base slide, no highlight |
| 1.1–2.3 s | Region 2 highlighted |
| 2.3–2.4 s | Base slide, no highlight |
| 2.4–3.8 s | Region 3 highlighted |

The test validates container duration, the presence of video/audio streams, segment change times **from actual decoded output**, and differences between frames captured during speech and pauses. It also checks that a stale audio hash blocks encoding before any preview file is created.

## Explicit limits

This is a working **technical synchronization proof**, not a subject-authorized lecture: synthetic signal WAV chunks contain test tone, not spoken English. Text-to-WAV semantic fidelity is not verified; there is no word-level forced alignment. The full subchapter planner, real slide+voice generation, accurate scientific figure review, intro/outro inspection, and final student-facing acceptance still need to be connected in the live runner.

The MP4 duration rule in this preview is an additional fail-closed guard. Full production multipart output must still be **planned top-down** by the approved Phase 2 lesson planner and every real MP4 independently measured strictly below 630 seconds. Do not cut finished long video files in response to a duration failure.

The original textbook source root remains `G:\My Drive\Projects\Thomas_calculus_13ed`, separate from local isolated test clones and fixtures. No original `source.pdf`, previously generated slides, WAVs, MP4s, or the old Thomas subchapter folder were touched by this development. The production shared code clone is intentionally not reset or overwritten.
