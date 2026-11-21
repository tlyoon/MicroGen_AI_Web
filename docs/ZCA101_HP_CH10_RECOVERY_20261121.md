# ZCA101 HP Chapter 10 — autonomous recovery

## Scope
Host HP only. Source root G:\My Drive\Serway\Serway_8_14, chapter 10. Isolated MicroGen_AI_Web HP checkout. The five existing verified lecture packages must remain unchanged. New output can be accepted only after full source-grounding, figure, narration, audio and video checks.

## Verified repairs
- Figure cropping: SHA-bound source rectangle recovery, mandatory panel/edge/source-image checks, temporary local PNG rasterization followed by Google Drive readback. Chapter 10.9's Figures 10.22 through 10.27 pass complete source-bound crop verification. Figure 10.22 is uniquely registered for full original caption inclusion because its printed caption shares the source graphic rectangle; partial clipping remains forbidden.
- Slides: verified pre-Send Selenium picker failure permits one Gemini API fallback. Once Send is possible, one local claim binds request to source, prompt, backend and model; unknown responses block replay. A valid captured reply is reused across checkpoints. Gemini API has zero internal transient retries per slide request.
- Beamer: independently verified visible image appearance now tolerates legitimate thin-edge downsampling while original content-mismatch thresholds and half-covered image rejection remain.
- Saved slide recovery: failed slides can be republished without Gemini if both source hash and full current figure/LaTeX/compiled-PDF gates pass.
- Chapter supervisor: two-pass exhaustion marks recovery_pending, not completed. A persistent locked executor checks actual completion receipts, schedules finite escalating retry/backoff, wakes early on verified code changes and mirrors sanitized status to G:\My Drive\Serway\Serway_8_14\.microgen_coordination\hp_chapter_10_supervisor.json.

## HP operation
Working checkout: C:\Users\tlyoo\microgen_ai_web_hp_ch10
Dedicated Python: C:\Users\tlyoo\miniforge3\envs\microgen_ai\python.exe
Execution module: selenium_pipeline.chapter_recovery_supervisor
Arguments: --source-root "G:\My Drive\Serway\Serway_8_14" --chapter 10 --worker HP --run-prefix zca101_hp_ch10 --retry-hours 6
Private checkpoint: %LOCALAPPDATA%\Microvid\chapter_supervisors\hp_chapter_10\supervisor.json
Completion means all nine source-bound per-subtopic completion receipts are verified; stage attempts alone do not count.
User-login Startup entry provides restart after logging into HP; it is not a Windows service before login.

## Testing contract
Run offline and fault-injection tests for transport, source crop source-SHA, stale or tampered raw response, per-PC worker status, retry/backoff, PDF source image visibility and real Chapter 10.9 figure geometry. Confirm no Send retry after ambiguous outcome, no silent incomplete-to-complete transition, no source PDF overwrite and no unverified MP4 release. A production pilot for 10.1 demonstrated pre-Send picker failure classification, one API response, Beamer compile and three source figures accepted; saved slides published without an additional Gemini Send.
