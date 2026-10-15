# Strict multipart + synchronized-highlight video contract: release gate (Phase 0)

Date: 15 October 2026. Scope: MicroGen_AI_Web only.

## Current implementation state

This change is **the first mandatory safety gate, not a completed multipart/highlight production engine**. The original seven-stage workflow used static slides and a single \`slides.mp4\` per subchapter. Its previous video validation checked file existence only. Lessons 8.4 (622.93 s), 8.5 (762.18 s), and 8.6 (630.96 s) are *legacy source-adjacent products*, not compliant final video parts.

User's clarified contract: **every resulting video must have actual duration strictly below 600.0 s**. Target 8–9 min. Videos longer than the target must be *replanned into coherent teaching parts before production*, not chopped at arbitrary timestamps. Final-audio-timed highlights must identify the displayed element being discussed; simply showing the correct static slide during narration is not enough.

## Protection now applied

1. \`video_ffmpeg.assemble\` rejects one-file narration of 599.5 seconds or more *before starting FFmpeg*, retaining a small AAC/container overhead reserve. It measures actual final MP4 duration independently and blocks publication if duration is \`>=600.0 s\`.
2. The offline synchronized-highlight preview rejects \`>=600.0 s\` audio or MP4; an older experimental 10:30 threshold is no longer acceptable.
3. The source-aware top-down planner uses a 590-second conservative planned bound and a 600-second absolute final ceiling. Its output remains a pre-generation estimate; it is not mistaken for measured media duration.
4. \`production_video_contract.verify_series\` requires a source-hash-bound \`lecture_completion.json\`, ordered \`part_NN\` entries and per-part receipts matching the actual MP4, final WAV, narration alignment and visual cue bytes. It checks:
   - Part sequence and independent measured MP4 duration **strictly below 600 seconds**.
   - Final WAV duration less than 600 seconds and consistency with media container duration.
   - Every highlight has a non-overlapping speech-time interval and explicit \`slide_id\` and \`target_id\`; exact alignment-to-visual-cue equality.
   - Visual and alignment records are bound to the same *final WAV*; encoded transition proof reports acceptable drift.
   - Hash checks and accepted-renderer status; synthetic previews, unhighlighted legacy clips, missing receipts or asserted status without evidence are rejected.
5. \`runner.valid("video")\` no longer accepts \`slides.mp4\` merely because it exists. The historical **static slide** video branch is **intentionally disabled before any expensive full-run or Gemini calls**. Consequently **no new 7-stage run should be claimed complete** until the new multi-part production assembler, source-approved lesson plan, verified speech alignment and final renderer are integrated. \`--dry-run\` remains available.

The fail-closed transition protects archived lesson outputs and the user from silent non-compliance. A successful CI run on this PR validates the rules but **does not mean that the full new contract has been fulfilled end to end**.

## Additional implementation still required

- Connect reviewed concept/source outline and \`plan_series\` before slide creation (domain-profile and pedagogy gate).
- Generate and publish coherent \`part_NN\` slides and per-part narration, reserve 8–9 min, replan oversize parts.
- Obtain verified **actual audio word/phrase timing** from final TTS; map each to stable slide element IDs and checked PDF geometry.
- Promote \`highlight_video_preview\` from its synthetic proof-of-concept to a production renderer with intermediate part receipts, meaningful visualization comparison, final audio/video drift check, source-bound QA and atomic publication.
- Prove the full pipeline on an *authorized* independent-source scientific pilot. Preserve all legacy original videos, scripts and figures. Do not equate a valid MP4 or self-reported approval with educator/source fidelity.

## Rollout constraints

Never hot-swap worker code under a running job. The pinned launchers on HP, Dell-115 and Yoga 6 should **not** be changed to this fail-closed development branch until it has passed CI and a validated new production interface is available. Old \`slides.mp4\` files and their historical receipts remain recoverable, but must be labeled \`legacy_noncompliant\` in any new-contract audit.


## All production entrypoints, rollback, and test scope

The standard selenium_pipeline.runner, the historical microgen_batch.py batch launcher
and the three-PC worker have distinct old-video paths. All are now fail-closed
against unhighlighted legacy output. Their static generator methods are retained
only for rollback/development compatibility; they cannot be used to claim
contract compliance. The worker reports a deferred result instead of
triggering another potentially long and noncompliant campaign.
Historical receipts remain readable for archival diagnostics.

This Phase 0 validator cannot create semantic cue geometries or forced-aligned
speech and does not independently prove that highlighted pixels are visible at
every encoded event. Its accepted status requires matching output hashes,
a renderer declaration and transition timing QA, but end-to-end production
acceptance must additionally compare decoded frame highlights with source-
verified target boxes. The blocking code remains intentionally undeployed
to current verified launchers until the new renderer and QA are ready.
