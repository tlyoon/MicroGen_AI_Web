# PR318 — Genuine three-section six-video replacement handoff, no fake acceptance

26 October 2026. Windows-only Dell-115; stacked on PR317 (`79ff65fab7a07d4a7780c2d7a6cdd101a94030f3`) whose durable academic-review request claims block accidental Gemini resubmission.

## The measured ORIGINAL six-part scope

The new `selenium_pipeline.original_replacement_video_handoff` independently reads the protected original Thomas' Calculus 8.4, 8.5, 8.6 PDFs, all slide-level WAV sample frames, and FFmpeg-probed original encoded MP4 streams on Dell-115. Each whole-slide WAV map includes SHA-256 identity and duration. It builds an **external, exclusive, no-overwrite** JSON handoff in AppData:

`%LOCALAPPDATA%\MicroGen_AI_Web_Checkpoints\20261026_pr318_Thomas_8_4_to_8_6_SIX_VIDEO_HANDOFF.json`

**Observed, not estimated:**

| Section | Original WAV total | Original encoded MP4 | Proposed audio-only, whole-slide video parts |
|---|---:|---:|---|
| 8.4 | 632.7107 s | **633.93 s** (10:33.93) | 1–8:321.8927 s; 9–17:310.8180 s |
| 8.5 | 761.1567 s | **762.96 s** (12:42.96) | 1–11:398.6187 s; 12–20:362.5380 s |
| 8.6 | 629.2007 s | **630.96 s** (10:30.96) | 1–9:330.7080 s; 10–17:298.4927 s |

**All three original MP4s fail strict <600-second acceptance.** The six proposed replacement boundaries come from current original audio and **must be recalculated using actual corrected WAVs** before any production render. No final MP4 part is implied by this manifest.

## Safe genuine-audio promotion conditions

The follow-up `check_replacement_audio_readiness` rejects missing candidate WAVs, replacing old narration with a byte-identical original WAV, symlink/path traversal into protected original folders, arbitrary fake `*.wav` bytes, mixed/missing voice and invalid text/academic review metadata. It requires a valid nonempty 16–48 kHz 16-bit mono PCM WAV **outside originals** and corresponding SHA-bound corrected text and two-pass review receipt fields, but explicitly states that actual speech fidelity, timing, and synchronized encoded video are **still unverified**. An untrusted receipt field alone is never enough for student publication.

The existing strict `speech_segment_timing.build_segment_timeline`, `encoded_highlight_pixels.verify_encoded_highlight_pixels` and `production_video_contract.verify_series` remain required for final technical acceptance. They must be given newly generated and independently verified real input data, never a simulator-only success.

## Actual Dell-115 verification

- 4 focused offline tests PASS on the **real original** 8.4/8.5/8.6 media, including SHA checks, exactly six contiguous whole-slide splits, rejection of historical PCM substitution and of bogus WAV bytes, no false audio-content approval.
- Actual external original video handoff JSON successfully created once, `any_new_mp4_created=false`, `student_publication_authorized=false`.
- Protected original source/script/audio/video, historical 633.93/762.96/630.96s MP4 files, main, three preexisting modified G checkout files unmodified.
- 0 additional provider/Gemini/API requests. No Whisper, HP/Yoga/Zenbook, Ubuntu checks or Moodle publication.

**Release still blocked:** genuine independently source-mapped two-pass math QA, fresh Kore revised speech for §8.4 and any other corrected scripts, timed Figure 8.2 (and all other element) highlights, encoded pixel/audio proof and all replacement MP4 durations strictly below 600s. No manual academic signoff is demanded by this code; AI-source review must be autonomous but source-grounded and fail closed.

Next step: integrate safe request/resume+source-locked corrected independent review once provider actually responds, then generate five revised Slide4 authentic Kore WAVs, rebuild each multipart plan from the new WAVs and accept each rendered encoded video only against the strict production-video gate.
