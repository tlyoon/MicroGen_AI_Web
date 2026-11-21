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


## Narration API recovery follow-up (21 November 2026)
The live regeneration of Chapter 10.1 returned 14 complete source-grounded narration blocks via API. The original full narration QA rejected the physically unambiguous phrase "position labeled A" as a mid-sentence article, then a later API attempt encountered Gemini 504 deadline errors. PR #575 refined only explicit labeling contexts: unlabeled ambiguous capital A remains blocking, and labeled A retains pronunciation review.

The executable narration recovery now checks previously rejected postprocessed API narration against the original source SHA, the chronology of the compiled slide PDF and every current narration QA rule before restoring script.txt. No new model request is made to reuse saved verified words. Narration API calls now use one SDK attempt per source-bound request, with independent request/response SHA claims and no automatic replay on an uncertain 504/timeout. The chapter supervisor fingerprints these narration mechanisms and wakes deferred jobs after verified code repairs. An HP-only worker stage policy may select API narration without changing the default modes on other PCs. The user-login HP launcher explicitly enables this path.

Real HP validation: the original saved 10.1 narration passed all current complete narration validators, with 14 slide titles and zero warnings. The full targeted source/supervisor/narration regression suite passed 66 tests prior to integration. This validates the saved narration as a candidate for stage publication, not the final audio or MP4 acceptance.
