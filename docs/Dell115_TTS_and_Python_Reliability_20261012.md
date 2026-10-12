# Dell-115 MicroGen reliability repair — October 2026

## Root causes established

During the Serway 46-unit recovery campaign, Dell-115 completed 1/14 assigned lectures; HP 7/14 and Yoga6 8/18. Three different blockers were observed:

1. The Dell-115 default MicroGen Python environment was stored in a Google Drive for Desktop folder and **did not have PyMuPDF**. A separate document-processing environment contained PyMuPDF, but that separate environment lacked google-genai. As a result, missing-figure diagnostics failed with ModuleNotFoundError. This was not a graphics-extraction algorithm failure.
2. On several 8.x and 9.x jobs, Gemini TTS repeatedly timed out on **slide 1** (25–48 characters), while the remaining slide WAVs were already reusable. The inner Gemini SDK's default 120-second HTTP request exceeded the parent's 105-second per-slide watchdog, preventing bounded key failover. A whole-batch voice fallback then buffered stdout while running, so its parent observed no output for 900 seconds and aborted.
3. Other 8.x/9.x jobs failed due to missing source-grounded figure references or Gemini UI prompt submission failures. Those are tracked separately and must not be described as fixed merely by changing the Python environment.

## Verified Dell environment repair

An isolated local Windows virtual environment was constructed at:
`%LOCALAPPDATA%\MicroGenRecovery\venvs\microgen_dell_20261012`

The original `G:\My Drive\Projects\MicroGen_AI_Web\.venv`, the separate docling environment, the Google Drive lectures and existing audio were **not replaced**. Due to transient package index DNS issues, the needed runtime packages were migrated locally from the existing pinned MicroGen environment; a working PyMuPDF 1.27.2.3 package was copied from the separate document-processing environment. No credential files or browser profiles were copied. The new environment passed `python -m pip check` and the targeted offline regressions. This migration is machine-local; new PC installations should use the versioned `requirements-worker.txt` when package indexes are available, not copy another virtualenv.

A single live API test generated 8.1's previously failing 43-character title with Gemini 3.8 Flash-Lite TTS and voice Kore in **5.7 seconds**. The output was a valid 4.52-second WAV in the isolated recovery folder, not in the lecture source folder. Two configured API keys were detected without displaying them.

## Permanent safeguards

- The TTS child SDK request deadline now fits inside the parent's hard timeout **across all configured keys**, with one SDK request attempt and immediate transient key rotation. A second configured key can actually be tried before the parent watchdog expires.
- A whole-batch fallback now streams progress and a bounded heartbeat to the supervising worker. This avoids false 900-second idle aborts when the fallback is legitimately generating WAVs. The 3600-second hard timeout and voice-consistency checks remain unchanged.
- Figure recovery is available from the new local environment. Preview generation must not invent or silently publish scientific figures.
- Keep all source-adjacent published MP4s, existing WAVs and .history archives; resume individual jobs only from verified stages.

## Acceptance before campaign restart

1. `python -m pip check` succeeds in the new local environment.
2. Off-line TTS timing and fallback streaming tests pass.
3. Read-only missing-figure review for Serway 8.5 completes with no published-source modifications.
4. Live first-slide Gemini Flash TTS completes and the waveform is valid.
5. A controlled actual subchapter recovery proves subsequent TTS QA and video generation, preserving prior deliverables.
6. Change the Dell worker launcher to use the new **local** worker Python executable and verified code version; keep browser session, PDF source root, authentication and per-worker stage-python settings compatible. Do not hot-swap code under a running job.

## Limitations

This environment repair cannot fix inaccessible Gemini accounts or scientifically missing/incorrect figures. An authenticated Flash UI and compatible API model remain required, and figure crops still need source-grounded review. The campaign is not fully complete until all original 46 subchapters have verified completion receipts.
