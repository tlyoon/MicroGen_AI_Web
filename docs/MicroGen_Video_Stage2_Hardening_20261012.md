# MicroGen Stage 2 — FFmpeg performance and recovery hardening (12 October 2026)

**Status:** implemented on an isolated branch; review and cross-PC production acceptance pending.

## Failure diagnosis

Real full-length Serway/Calculus jobs on HP, Dell-115 and Yoga6 spent tens of minutes in the video stage. HP's Calculus 10.3 runner reached the 3,600-second hard deadline while an FFmpeg process survived afterwards. The old encoder rendered 24 frames/second even though each source PDF page was static. Process heartbeat logs showed that FFmpeg was alive but did not prove media progress. On a failure, the entire temporary segment directory was discarded.

## Implemented changes

1. Encode static slides at **2 fps** rather than 24 fps by default: 12 times fewer redundant frames (not a measured 12x runtime improvement). Retain H.264/AAC, 1280x720, the existing quality setting and duration validation.
2. Report FFmpeg's actual output duration, frame number and speed through its progress pipe. Abort on media-progress stall even if the process still exists.
3. Enforce independent 1,200-second per-encode, 300-second no-progress and 3,600-second full video-stage deadlines.
4. On full-stage timeout, terminate **only** the video's child process tree; do not kill unrelated Chrome or other lecture processes. On Windows this uses scoped taskkill /PID /T /F.
5. Cache successful encoded slide segments on **local disk**, identified by source folder. Reuse requires verified SHA-256 PDF/WAV hashes, audio duration, video profile and valid media streams. Reject unverified pending segments.
6. Verify the complete candidate MP4 before source-adjacent publication. Preserve the previous MP4 in .history if one already exists. Cache cleanup is nonfatal after successful publication.
7. Bound input-stream probing to 60 seconds.

## Environment settings

| Setting | Default | Purpose |
|---|---|---|
| MICROGEN_VIDEO_FPS | 2 | Frames/second for static slides; 24 restores old mode |
| MICROGEN_FFMPEG_TIMEOUT_SECONDS | 1200 | Per FFmpeg child hard deadline |
| MICROGEN_FFMPEG_STALL_SECONDS | 300 | Deadline without actual media progress |
| MICROGEN_VIDEO_STAGE_TIMEOUT_SECONDS | 3600 | Entire video-stage hard deadline |
| MICROGEN_VIDEO_CACHE_ROOT | LOCALAPPDATA/MicroGen/video_cache on Windows | Local crash recovery cache |
| MICROVID_FFMPEG | auto | FFmpeg binary override |

## Verified isolated acceptance

- Zenbook test checkout did not modify running HP/Dell-115/Yoga6 production code or Google Drive lecture outputs.
- Python syntax checks passed for both modified production files.
- 15 targeted test cases passed locally, covering narration safeguards, existing media inputs, real video restart and scoped timeout cleanup.
- Real synthetic two-slide PDF/WAV smoke: deliberately aborted before slide 2; confirmed first segment survived; retried with slide 1 reused; validated complete 5.02-second H.264/AAC output; changed a WAV; validated 6.02-second regenerated output; confirmed the previous MP4 was preserved in .history.
- Automated cross-platform CI now includes the new real-media recovery regression.

## Safe deployment and limitations

Never modify a running job's code or terminate unidentified FFmpeg tasks. Once existing jobs are safely finished or deferred, deploy a single merged code SHA on each machine. Pilot a video-only source-adjacent restart on one incomplete lecture per PC; inspect media, QA, synchronization, receipts and orphan process state before resuming the queue.

Keep chapter assignments disjoint across PCs. A machine-local cache does not provide atomic cross-PC locking on Google Drive. This release does not certify all lecture content or guarantee uninterrupted access to Gemini.
