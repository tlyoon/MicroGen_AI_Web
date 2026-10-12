# Portable video, slide splitting and cleanup safeguards

This document describes the safeguards used by the maintained Selenium
pipeline on **any Windows PC** running MicroGen. They are not specific to
Yoga 6, Dell-115, a textbook or a drive letter.

## Why

Encoding a static slide while FFmpeg reads images or audio directly from
a Google Drive-mounted folder can stall for many minutes. Removing a
synchronised temporary folder can also raise Windows errors 5, 32 or 145
after the final lecture outputs have been successfully published.

## How it works

1. `selenium_pipeline.slide_pdf_split` verifies the slide deck and splits
   it in an OS-local temporary directory. Each single-page PDF is checked
   before an atomic rename into the subchapter workspace. The source deck
   is never modified, and unchanged split pages are reused.
2. `selenium_pipeline.video_ffmpeg` copies each uncached input PDF **and**
   WAV to the machine-local video cache, verifying SHA-256 before use.
   FFmpeg reads only locally staged images/audio. The existing input hashes
   are part of the cache identity; edits invalidate just the affected slide.
3. FFmpeg reports frame and media-time progress. No-progress and hard
   deadlines stop a hung child process. Per-slide encoded segments are
   validated and cached, so restarting the video stage reuses validated
   segments instead of redoing earlier work.
4. The completed MP4 must contain audio and video and meet the expected
   duration. A hash-verified staged copy is promoted to the final destination.
   Previously published files are not replaced by a failed or partial render.
5. Final-workspace cleanup checks that all final assets and referenced
   graphics are present. A known Google Drive busy/access error on a
   **generated temporary** file is logged as deferred and does not invalidate
   a verified lecture. An unrelated or unowned directory must never be removed.
   A deferred cleanup can be retried after Google Drive synchronization.

## Cross-PC defaults and settings

- `MICROGEN_VIDEO_CACHE_ROOT`: optional **local** per-PC cache root
  (default: `%LOCALAPPDATA%\\MicroGen\\video_cache` on Windows).
  Do not configure this on Google Drive, OneDrive or a network mount.
- `MICROGEN_VIDEO_FPS`: defaults to 2 fps for static slide video.
- `MICROGEN_FFMPEG_STALL_SECONDS`: defaults to 90 seconds without advancing
  media time or frame number; can be increased on a slow PC.
- `MICROGEN_FFMPEG_TIMEOUT_SECONDS`: defaults to 1,200 seconds per FFmpeg
  command, independent of the no-progress watchdog.
- `MICROGEN_SLIDE_SPLIT_TIMEOUT_SECONDS`: defaults to 900 seconds.
- `MICROGEN_VIDEO_STAGE_TIMEOUT_SECONDS`: defaults to 3,600 seconds.

Avoid running two encoders for the same subchapter simultaneously. Keep
`source.pdf` and all generated deliverables under the specified source
tree; each PC stages temporary work in its own local directories.

## Validation

Run `python -m unittest discover -s tests -p 'test_portable_media.py' -v`,
`python -m unittest discover -s tests -p 'test_stage2_video_recovery.py' -v`,
and `python -m unittest discover -s tests -p 'test_completed_cleanup.py' -v`.
The actual-video recovery test runs when PyMuPDF and FFmpeg are installed.
Always perform a two-slide real FFmpeg smoke test before deploying into a
running multi-PC queue.

**Rollout rule:** do not overwrite the Python modules of an active job.
Update the PC's code only after its current job exits, then start a new
job from the validated checkpoint.
