# Automatic Video 00 and single-PC course publisher (18 October 2026)

Development status: draft, not deployed. Stacked on the YouTube publisher PR #135.
This document supplements the owner's latest automatic-stage and YouTube-publication contracts.

## Video 00 — source-grounded course introduction

The course-video00 module creates a two-second course-title slate followed by a
montage of original source-grounded narrated lecture excerpts, targeting
45–55 seconds for the final encoded video. The trailer is NOT a new LLM-written
or TTS-narrated course script, and does not invent course content or mix voices.

- Source: only technically accepted multipart lecture MP4s from the verified
  YouTube course inventory; legacy slides.mp4 and review-only previews are refused.
- Selected material: whole 4–12-second spoken cue intervals from at least three
  distinct lecture subchapters, round-robin to cover multiple course sections.
- Audio: original encoded lecture soundtrack, never a second TTS engine.
  Consistent TTS model/voice identity must pass source script and effective
  TTS manifest validation for all source lessons. Different Gemini/Cloud
  engines are NEVER spliced into a single trailer.
- Technical guard: verify source PDF SHA-256, source MP4 SHA-256, original
  narration alignment hashes and unchanged TTS identity before/during render.
  FFmpeg creates a new 1280x720 H.264/AAC MP4, checks actual muxed duration,
  and writes an independent receipt/hash for the trailer and title image.
- Output, only when new:
  SOURCE_ROOT/.microgen_youtube/trailer/video_00.mp4
  SOURCE_ROOT/.microgen_youtube/trailer/title_card.jpg
  SOURCE_ROOT/.microgen_youtube/trailer/video_00_receipt.json
- No existing lecture, promo file, WAV, source or receipt is overwritten.
- The YouTube uploader now requires the verified Video 00 receipt and the
  unchanged original media before allowing Video 00 into the playlist.

Preview the video plan offline, no files written or accounts contacted:

    python -m selenium_pipeline.course_video00 plan --source-root SOURCE_ROOT --course-title "COURSE TITLE"

Create Video 00 when all original lecture media pass technical QA:

    python -m selenium_pipeline.course_video00 render --source-root SOURCE_ROOT --course-title "COURSE TITLE"

## Single designated PC and whole-course completion

The course_youtube_coordinator module reads the existing distributed
coordination manifest and each assigned worker's final per-run status, then
INDEPENDENTLY checks the full source-root videos again.

- Only HP, Dell-115, Yoga6 are valid worker IDs; never Zenbook.
- All worker IDs, run IDs, chapter assignments, complete topic worklists,
  status phases and exact video acceptance states must match. Chapters must
  not overlap and no source.pdf subchapter may be omitted from the run.
- Any incomplete or pilot-only campaign blocks real YouTube publication.
- A single pinned publisher PC identified by its actual Windows COMPUTERNAME
  creates Video 00, confirms the pinned YouTube channel, and uses the
  existing SHA-256 resumable uploader. No every-worker upload and no
  Google Cloud lease or fictional Google Drive atomic mutex.
- The publisher requires real source-bound highlighted part MP4 technical QA
  including STRICT duration <600 seconds per part. Human academic approval
  is optional under the latest owner amendment. Moodle is never used.

Read-only audit:

    python -m selenium_pipeline.course_youtube_coordinator audit --source-root SOURCE_ROOT --run-id RUN_ID --course-title "COURSE TITLE"

Run once after completion, on the designated publisher only:

    python -m selenium_pipeline.course_youtube_coordinator publish --source-root SOURCE_ROOT --run-id RUN_ID --course-title "COURSE TITLE" --publisher-host ACTUAL_COMPUTERNAME --expected-channel-id VERIFIED_CHANNEL_ID --visibility public

Start a bounded local completion watcher on the designated publisher:

    python -m selenium_pipeline.course_youtube_coordinator watch --source-root SOURCE_ROOT --run-id RUN_ID --course-title "COURSE TITLE" --publisher-host ACTUAL_COMPUTERNAME --expected-channel-id VERIFIED_CHANNEL_ID --visibility public --poll-seconds 60 --max-wait-seconds 86400

The watcher is a normal local process; it is not a ChatGPT background task.
Publication only follows the full course verification and OAuth account check.

## Contract limits and next work

These features have been tested with synthetic FFmpeg-rendered videos,
mocked publisher calls, and fake local completion manifests. A green
synthetic test is not proof that existing Thomas Calculus or Serway
lectures already have compliant real production receipts.

The existing generation worker still defers attempts that lack an accepted
audio-timed, element-highlighted multipart renderer. The next major
development stage is integrating and auditing a REAL end-to-end highlighted
generation campaign and verifying the pinned YouTube channel/token READ ONLY.
Before large public publication, perform a controlled nonpublic YouTube
canary with playback, captions, order and resume tests.

Original source folders, dirty working trees, all credentials, old lecture
MP4s and draft PR dependencies remain untouched. No actual YouTube upload,
Moodle publication or real account login was made in this implementation.
