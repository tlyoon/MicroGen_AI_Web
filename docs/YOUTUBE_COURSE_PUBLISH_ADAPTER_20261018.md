# MicroGen_AI_Web — Automatic YouTube Course Publishing Adapter

**18 October 2026. Draft integration, no live uploads performed.**

## Legacy provenance

Adapted from the MIT-licensed tlyoon/microcredential-video-generator publisher
(src/microvid/youtube_publish.py), including local OAuth, resumable video
uploads, ordered playlists, optional SRT captions, a square course image, and
persistent per-course publish state.

Unlike the Microvid uploader, this adapter consumes MicroGen_AI_Web's
numerical chapter/subchapter/source.pdf folders and the existing
production_video_contract.verify_series technical acceptance. It does not
require Microvid YAML manifests and never treats draft review videos, legacy
single-file slides.mp4 or overlong videos as publishable.

## Binding publication contract

The owner explicitly authorizes automatic publishing to their **YouTube
channel**, not Moodle, after all technical source/figure/narration/video QA
passes. Human academic and listening review is optional for internal
progression and for this separate authorized YouTube publication workflow.
The code never forges human approval or bypasses technical validation.

A **complete course** is the default precondition: every discovered
source.pdf subchapter must have an accepted, source-SHA-256-bound multipart
video receipt, with verified WAV/cue/MP4 integrity, actual audio and video
duration STRICTLY below 600 seconds per part, and synchronized highlights.
The publisher re-runs the technical acceptance check immediately before
remote uploads. If one subchapter is unfinished, automatic public course
publication is deferred. An optional offline partial preview lists omissions
but **cannot** be used for real partial-course publishing.

The uploader places lessons into one numerically ordered course playlist:
1. Optional independently verified course trailer Video 00.
2. Lecture subchapter 1.1, part 01; then part 02, etc.
3. Remaining completed subchapters in numerical source order (no invented
   chapters or subtopics).

An existing trailer MP4 may be supplied at publish time. It must reside
under the source root, have audio and video and be STRICTLY shorter than
59 seconds. **The automatic trailer compositor does not yet exist**; porting
it is the next development milestone, not something this PR claims to have
done. No synthetic trailer or unverified soundtrack is invented.

## Local OAuth setup — keep tokens off Drive

Each participating PC was found to have these NONEMPTY file names in
%LOCALAPPDATA%\Microvid:

- youtube_client_secret.json (Desktop OAuth app)
- youtube_token.json (saved user token)

Token presence is **not proof of currently valid upload permission or the
correct authorized YouTube account**. No token was opened or copied into
the repository. The read-only plan command never invokes OAuth.

Install on the designated publishing computer in a LOCAL Python environment:

    python -m pip install -r requirements-youtube.txt

Use an OAuth account with the YouTube Data API enabled. Do not substitute
the Google Cloud service-account JSON used for TTS.

## Read-only offline inventory (NO network, NO file writes)

    python -m selenium_pipeline.youtube_course_publish plan ^
      --source-root "G:\My Drive\Serway\Serway_8_14" ^
      --course-title "Physics: Electricity"

A strict plan reports missing or defective subchapters as a technical
failure. To inspect a partial inventory without uploading anything, add
the flag:

    --include-completed-only

This diagnostic mode cannot trigger publication.

## Publishing AFTER full technical completion

Specify exactly one fixed machine (HP, Dell-115 or Yoga6) as publisher,
using its ACTUAL Windows COMPUTERNAME. Example:

    python -m selenium_pipeline.youtube_course_publish publish ^
      --source-root "G:\My Drive\Serway\Serway_8_14" ^
      --course-title "Physics: Electricity" ^
      --publisher-host "ACTUAL_WINDOWS_COMPUTERNAME" ^
      --expected-handle "@tlyoon" ^
      --visibility public

The channel handle above is the legacy package's documented default.
Its correspondence to the saved OAuth identity is **not yet verified**.
A pinned --expected-channel-id is also supported, and is stronger than a
mutable handle. An incorrect publisher host, missing channel ID/handle
binding, a different authorized account or a playlist owned by a different
channel stops remote writes. Only the designated PC may publish; all
other workers must not attempt uploads. The local OS lock does NOT claim
that Google Drive provides a global atomic distributed mutex.

Optionally include an existing Video 00:

    --trailer "G:\My Drive\Serway\Serway_8_14\.microgen_youtube\trailer\video_00.mp4"

The legacy uploader's public-by-default behavior is retained. The adapter
checks reported privacy of each actual YouTube video and the playlist:
if an unaudited API project forces private visibility, the command
reports failure instead of claiming the public course is published.

## State, resume, cover and subtitles

Course state and a generated 1200x1200 square cover live at:

    SOURCE_ROOT\.microgen_youtube\publish_state.json
    SOURCE_ROOT\.microgen_youtube\course_cover.jpg

The state includes remote video/playlist IDs, per-part SHA-256 hashes, and
the dedicated publishing host. Existing accepted uploads are reused,
playlist membership is checked and ordering reconciled; matching part
subtitles (part_01.srt next to part_01.mp4) are uploaded if present.

Changed media (even if byte counts match) or changed captions FAIL CLOSED.
This adaptation does not silently replace, delete or unlist any previous
YouTube video. Any upload that may have reached YouTube but returned no ID
keeps an in-flight marker, so retries stop for manual remote reconciliation. Ambiguous playlist creation is likewise marked before the remote write and blocks blind duplicate playlist creation
rather than knowingly posting a duplicate.

## Technical limitations and next development steps

1. Implement fully automatic generic Video 00 scripting, TTS and editing
   from source-grounded completed lecture assets, 45–55 seconds target,
   never 59 seconds or longer, with Video 00 first in playlist.
2. Add a single-PC, course-wide post-generation trigger that invokes
   publishing only after all distributed work passes strict QA. The
   current CLI implements actual publication and resume, but the
   three-PC worker does not yet automatically call it.
3. Build source-bound SRT export and improved topic-name/title metadata
   without falsely claiming independent human academic review.
4. Add a carefully tested changed-video replacement flow that preserves
   previous IDs/history and verifies the new complete playlist first.
5. Verify the stored OAuth token actually belongs to the intended channel
   with a READ-ONLY API request; then perform a controlled private/unlisted
   test upload before any large public run.
6. Complete stacked draft PRs in dependency order. The current PR is an
   isolated development branch; production sources and Google Drive
   working directories are not overwritten.

**No real account authentication, YouTube upload, playlist modification
or Moodle publication was carried out while creating this adapter.**
