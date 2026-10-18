"""YouTube course publishing adapter for MicroGen_AI_Web.

Adapted from tlyoon/microcredential-video-generator/src/microvid/youtube_publish.py
(MIT-licensed project); retain attribution. Existing MicroGen source folders and
strict technical video receipts, NOT Microvid YAML, are the source of truth.

No model calls, no YouTube access from plan(). Real uploads require explicit
publisher host and verified authorized channel, but no per-stage academic signoff.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .production_video_contract import _mp4_duration, verify_series

SUBCHAPTER = re.compile(r"^([0-9]+)\.([0-9]+)$")
PART = re.compile(r"^part_([0-9]{2})$")
VIDEO_ID = re.compile(r"^[a-zA-Z0-9_-]{6,64}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
APP_DIR = "Microvid"
OAUTH_SCOPES = ("https://www.googleapis.com/auth/youtube.upload",
                "https://www.googleapis.com/auth/youtube.force-ssl")
STATE_DIR = ".microgen_youtube"


class YouTubeCourseError(ValueError):
    """Unsafe or incomplete course publishing input."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise YouTubeCourseError(message)


def sha256(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"Missing regular file: {path}")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _inside(root: Path, candidate: Path) -> bool:
    return candidate.resolve().is_relative_to(root.resolve())


@dataclass(frozen=True)
class UploadItem:
    key: str
    title: str
    mp4: Path
    sha256: str
    duration_s: float
    source_sha256: str
    subchapter: str
    part_id: str
    caption: Path | None = None
    caption_sha256: str | None = None

    def metadata(self) -> dict:
        return {
            "key": self.key, "title": self.title,
            "sha256": self.sha256, "duration_s": self.duration_s,
            "source_sha256": self.source_sha256,
            "subchapter": self.subchapter, "part_id": self.part_id,
            "caption_sha256": self.caption_sha256,
        }


def plan_course(source_root: Path, *, course_title: str,
                trailer: Path | None = None,
                require_complete: bool = True) -> dict:
    """Read-only discovery with real MP4, WAV, pixel-cue and source hash QA.

    Never silently publish old single-MP4 or 'review_only' candidate clips.
    One ordered playlist for one explicit source root, not a guessed union
    of courses on Google Drive.
    """
    root = Path(source_root).expanduser().resolve()
    require(root.is_dir() and bool(course_title.strip()),
            "Source root and nonempty course title are required")
    folders = []
    for chapter in root.iterdir():
        if not chapter.is_dir() or not chapter.name.isdecimal():
            continue
        for folder in chapter.iterdir():
            match = SUBCHAPTER.fullmatch(folder.name)
            if (folder.is_dir() and match
                    and int(match[1]) == int(chapter.name)
                    and (folder / "source.pdf").is_file()):
                folders.append((int(match[1]), int(match[2]), folder))
    folders.sort(key=lambda x: (x[0], x[1]))
    require(folders, "No chapter/subchapter source.pdf folders found")
    items = []
    excluded = []
    for _, _, folder in folders:
        try:
            verified = verify_series(folder)
        except (OSError, ValueError) as exc:
            excluded.append({"subchapter": folder.name, "reason": str(exc)[:400]})
            continue
        src_sha = sha256(folder / "source.pdf")
        require(verified.get("verification_scope") == "technical_media_only",
                "Unexpected technical acceptance scope")
        for part in verified["parts"]:
            pid = part["part_id"]
            require(PART.fullmatch(pid) is not None, "Unrecognized part number")
            video = folder / pid / (pid + ".mp4")
            require(_inside(folder, video), "Video escapes its source subchapter")
            items.append(UploadItem(
                key=folder.name + "/" + pid,
                title=f"{folder.name} | Lecture part {int(pid[5:])}",
                mp4=video,
                sha256=sha256(video),
                duration_s=part["duration_s"],
                source_sha256=src_sha,
                subchapter=folder.name,
                part_id=pid,
                caption=(folder / pid / (pid + ".srt")
                         if (folder / pid / (pid + ".srt")).is_file() else None),
                caption_sha256=(sha256(folder / pid / (pid + ".srt"))
                                if (folder / pid / (pid + ".srt")).is_file() else None)))
    if require_complete:
        require(not excluded, f"Course incomplete: {len(excluded)} subchapters fail QA; "
                f"first: {excluded[0] if excluded else ''}")
    require(items, "No technically accepted highlighted multipart video parts")
    if trailer is not None:
        promo = Path(trailer).expanduser().resolve()
        require(promo.is_file() and promo.suffix.lower() == ".mp4"
                and _inside(root, promo), "Trailer must be an MP4 under the course source root")
        duration = _mp4_duration(promo)
        require(0 < duration < 59.0, "Promotional Video 00 must be <59 seconds")
        # An arbitrary user-supplied video is not a technically accepted
        # source-grounded promotional lecture. Verify independent media/source
        # hashes and the actual muxed duration before YouTube publication.
        from .course_video00 import verify_video00
        verify_video00(promo, source_root=root)
        items.insert(0, UploadItem(
            key="video_00", title=f"{course_title} | Course introduction",
            mp4=promo, sha256=sha256(promo),
            duration_s=duration, source_sha256="", subchapter="", part_id="video_00"))
    return {
        "schema_version": 1,
        "course_title": course_title.strip(),
        "source_root": str(root),
        "items": items,
        "excluded": excluded,
        "trailer_included": trailer is not None,
        "complete_course": not excluded,
        "human_approval_required": False,
        "technical_qa_required": True,
    }


def summary(plan: dict) -> dict:
    """No secrets, no local absolute media paths in published metadata."""
    return {key: val for key, val in plan.items()
            if key not in ("items", "source_root")} | {
        "videos": [item.metadata() for item in plan["items"]],
        "upload_count": len(plan["items"]),
    }


def local_auth_dir() -> Path:
    custom = os.environ.get("MICROVID_CONFIG_DIR")
    if custom:
        return Path(custom).expanduser()
    return Path(os.environ.get("LOCALAPPDATA") or
                str(Path.home() / "AppData" / "Local")) / APP_DIR


def authenticate_youtube():
    """Reuse local OAuth token; never send or log token contents."""
    root = local_auth_dir()
    client = root / "youtube_client_secret.json"
    token = root / "youtube_token.json"
    require(client.is_file(), "YouTube OAuth client file missing from Microvid directory")
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise YouTubeCourseError("Install google-api-python-client, google-auth-oauthlib "
                                 "and google-auth-httplib2 in the publisher environment") from exc
    credentials = None
    if token.is_file():
        try:
            credentials = Credentials.from_authorized_user_file(str(token), list(OAUTH_SCOPES))
        except (ValueError, OSError):
            credentials = None
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(client), list(OAUTH_SCOPES))
        credentials = flow.run_local_server(port=0, open_browser=True)
    root.mkdir(parents=True, exist_ok=True)
    # Token storage remains local, never in Google Drive or the Git repository.
    token.write_text(credentials.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


def verify_channel(youtube, *, expected_channel_id: str | None,
                   expected_handle: str | None) -> dict:
    require(bool(expected_channel_id or expected_handle),
            "A pinned --expected-channel-id or --expected-handle is mandatory")
    result = youtube.channels().list(part="id,snippet", mine=True).execute(num_retries=5)
    channels = result.get("items", [])
    require(len(channels) == 1, "Cannot uniquely identify authorized channel")
    ch = channels[0]
    ident = str(ch.get("id", ""))
    handle = str(ch.get("snippet", {}).get("customUrl", ""))
    require(bool(ident), "Authorized channel has no ID")
    if expected_channel_id:
        require(ident == expected_channel_id, "OAuth channel ID differs from pinned channel")
    if expected_handle:
        # A missing handle is not evidence of a match.
        require(handle.casefold() == expected_handle.casefold(),
                "OAuth channel handle differs from pinned handle or is absent")
    return {"id": ident, "handle": handle}


def generate_course_cover(course_title: str, path: Path) -> Path:
    """Adapt the Microvid square course image for any subject."""
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new("RGB", (1200, 1200), (16, 34, 57))
    draw = ImageDraw.Draw(image)
    for y in range(1200):
        tone = int(30 * y / 1199)
        draw.line((0, y, 1200, y), fill=(16, 34 + tone, 57 + tone))
    try:
        bold = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "segoeuib.ttf"
        font = ImageFont.truetype(str(bold), 72) if bold.is_file() else ImageFont.load_default()
        small = ImageFont.truetype(str(bold), 34) if bold.is_file() else ImageFont.load_default()
    except (OSError, ValueError):
        font = ImageFont.load_default()
        small = font
    draw.text((75, 90), "MICROGEN COURSE", font=small, fill=(80, 221, 196))
    words=course_title.split()
    lines=[]
    current=""
    for word in words:
        trial=(current+" "+word).strip()
        if current and draw.textbbox((0, 0), trial, font=font)[2] > 1040:
            lines.append(current)
            current=word
        else:
            current=trial
    if current:
        lines.append(current)
    require(1 <= len(lines) <= 8,
            "Course title too long for a legible generated YouTube cover")
    for n, line in enumerate(lines):
        draw.text((75, 270 + n * 108), line, font=font, fill="white")
    draw.text((75, 1090), "Source-grounded microlectures", font=small,
              fill=(172, 223, 229))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="JPEG", quality=88, optimize=True)
    require(path.stat().st_size < 2_000_000, "YouTube course image exceeds 2MB")
    return path


def _upload_caption(youtube, video_id: str, caption_path: Path) -> str:
    from googleapiclient.http import MediaFileUpload
    result = youtube.captions().insert(
        part="snippet",
        body={"snippet": {
            "videoId": video_id, "language": "en",
            "name": "Lecture subtitles", "isDraft": False,
        }},
        media_body=MediaFileUpload(str(caption_path), mimetype="application/octet-stream"),
    ).execute(num_retries=5)
    cap_id=str(result.get("id", ""))
    require(bool(cap_id), "YouTube returned no caption ID")
    return cap_id


def _upload_cover(youtube, playlist_id: str, cover: Path) -> str:
    from googleapiclient.http import MediaFileUpload
    result=youtube.playlistImages().insert(
        part="snippet",
        body={"snippet": {"playlistId": playlist_id, "type": "hero"}},
        media_body=MediaFileUpload(str(cover), mimetype="image/jpeg"),
    ).execute(num_retries=5)
    img_id=str(result.get("id", ""))
    require(bool(img_id), "YouTube returned no playlist image ID")
    return img_id


@contextmanager
def _local_publisher_lock():
    """Local singleton *plus* pinned machine, not a Drive-only mutex."""
    directory = local_auth_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "microgen_youtube_publisher.lock"
    with path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            handle.write(b"X")
            handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise YouTubeCourseError("Publisher already running on this PC") from exc
        else:
            import fcntl
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise YouTubeCourseError("Publisher already running on this PC") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def _state(path: Path) -> dict:
    if not path.is_file():
        return {"schema_version": 1, "playlist": {}, "uploads": {}}
    obj = json.loads(path.read_text(encoding="utf-8"))
    require(type(obj) is dict and obj.get("schema_version") == 1
            and type(obj.get("playlist")) is dict
            and type(obj.get("uploads")) is dict, "Invalid publish state")
    return obj


def _save_state(path: Path, state: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".youtube_state_", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as dst:
            json.dump(state, dst, sort_keys=True, indent=2)
            dst.write("\n")
            dst.flush()
            os.fsync(dst.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _upload_mp4(youtube, item: UploadItem, *, visibility: str,
                description: str) -> str:
    from googleapiclient.http import MediaFileUpload
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": item.title,
                "description": description,
                "categoryId": "27",
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en",
            },
            "status": {
                "privacyStatus": visibility,
                "selfDeclaredMadeForKids": False,
            },
        },
        notifySubscribers=False,
        media_body=MediaFileUpload(
            str(item.mp4), mimetype="video/mp4",
            resumable=True, chunksize=8 * 1024 * 1024),
    )
    result = None
    while result is None:
        _, result = request.next_chunk(num_retries=5)
    youtube_id = str(result.get("id", ""))
    require(VIDEO_ID.fullmatch(youtube_id) is not None,
            "YouTube did not return a valid video ID")
    return youtube_id


def _add_item(youtube, playlist_id: str, youtube_id: str, position: int) -> str:
    response = youtube.playlistItems().insert(
        part="snippet",
        body={"snippet": {
            "playlistId": playlist_id, "position": position,
            "resourceId": {"kind": "youtube#video", "videoId": youtube_id},
        }}).execute(num_retries=5)
    result = str(response.get("id", ""))
    require(bool(result), "YouTube did not return a playlist item ID")
    return result


def _list_items(youtube, playlist_id: str) -> list[dict]:
    data, page = [], None
    while True:
        response = youtube.playlistItems().list(
            part="snippet", playlistId=playlist_id,
            maxResults=50, pageToken=page).execute(num_retries=5)
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            data.append({
                "id": item.get("id", ""),
                "video_id": snippet.get("resourceId", {}).get("videoId", ""),
            })
        page = response.get("nextPageToken")
        if not page:
            return data


def _reorder(youtube, playlist_id: str, wanted: list[str]) -> None:
    """Idempotent Microvid-style reorder, then check real YouTube positions."""
    entries = _list_items(youtube, playlist_id)
    for n, vid in enumerate(wanted):
        index = next((j for j, row in enumerate(entries)
                      if row["video_id"] == vid), None)
        require(index is not None, f"Uploaded video absent from playlist: {vid}")
        if index == n:
            continue
        item = entries[index]
        youtube.playlistItems().update(
            part="snippet", body={
                "id": item["id"], "snippet": {
                    "playlistId": playlist_id, "position": n,
                    "resourceId": {"kind": "youtube#video", "videoId": vid},
                }
            }).execute(num_retries=5)
        entries.insert(n, entries.pop(index))
    require([row["video_id"] for row in _list_items(youtube, playlist_id)
             ][:len(wanted)] == wanted,
            "YouTube playlist order still differs after reconciliation")


def _verify_playlist_owner(youtube, playlist_id: str, *,
                           expected_channel_id: str, visibility: str) -> None:
    result=youtube.playlists().list(
        part="snippet,status", id=playlist_id).execute(num_retries=5)
    matches=result.get("items",[])
    require(len(matches)==1 and
            matches[0].get("snippet",{}).get("channelId")==expected_channel_id,
            "Destination playlist is missing or not owned by the pinned channel")
    require(matches[0].get("status",{}).get("privacyStatus")==visibility,
            "Destination playlist visibility differs from intended publication")


def _verify_uploaded_video(youtube, video_id: str, *,
                           expected_channel_id: str, visibility: str) -> None:
    response = youtube.videos().list(
        part="id,snippet,status", id=video_id).execute(num_retries=5)
    videos = response.get("items", [])
    require(len(videos) == 1
            and videos[0].get("snippet", {}).get("channelId") == expected_channel_id,
            "Uploaded video unavailable or not owned by the expected channel")
    require(videos[0].get("status", {}).get("privacyStatus") == visibility,
            "YouTube did not confirm intended video visibility; check API-project "
            "privacy restrictions before claiming publication")


def publish_course(plan: dict, *, youtube, expected_channel_id: str | None = None,
                   expected_handle: str | None = None,
                   publisher_host: str, visibility: str = "public") -> dict:
    """One designated PC publishes accepted source-bound parts automatically.

    The course must already be technically accepted. Human review is optional.
    No destructive replacement or unauthorized reuse of a different channel.
    """
    require(visibility in ("public", "unlisted", "private"), "Bad visibility")
    hostname = socket.gethostname()
    require(bool(publisher_host) and publisher_host.casefold() == hostname.casefold(),
            "Wrong publisher PC: only the configured publisher host may upload")
    root = Path(plan["source_root"])
    require(root.is_dir(), "Course source root disappeared")
    state_path = root / STATE_DIR / "publish_state.json"
    with _local_publisher_lock():
        # Recheck at the last possible point before remote writes; reject
        # changed source/media and newly incomplete receipts.
        current = plan_course(
            root, course_title=plan["course_title"],
            trailer=(next((x.mp4 for x in plan["items"]
                           if x.key == "video_00"), None)),
            require_complete=True)
        require([(x.key, x.sha256, x.caption_sha256) for x in current["items"]]
                == [(x.key, x.sha256, x.caption_sha256) for x in plan["items"]],
                "Course plan or MP4 bytes changed after preflight")
        channel = verify_channel(
            youtube, expected_channel_id=expected_channel_id,
            expected_handle=expected_handle)
        state = _state(state_path)
        require(state.get("publisher_host", hostname).casefold() == hostname.casefold(),
                "Existing course is owned by a different publisher host")
        require(state.get("channel_id", channel["id"]) == channel["id"],
                "Existing publishing state belongs to another channel")
        require(state.get("course_title", plan["course_title"]) == plan["course_title"],
                "Publishing state has a different course identity")
        require(state.get("visibility", visibility) == visibility,
                "Visibility change requires a separate explicit migration")
        state.update(publisher_host=hostname, channel_id=channel["id"],
                     course_title=plan["course_title"], visibility=visibility)
        playlist = state["playlist"]
        if not playlist.get("id"):
            # A failed response does not prove playlist creation failed.
            # Record the dangerous window BEFORE attempting a remote insert.
            require(not playlist.get("creating"),
                    "Ambiguous interrupted playlist creation; reconcile "
                    "remote YouTube playlists before retrying")
            playlist["creating"] = True
            _save_state(state_path, state)
            result = youtube.playlists().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": plan["course_title"],
                        "description": "Source-grounded microlectures, ordered by subchapter.",
                    },
                    "status": {"privacyStatus": visibility},
                }).execute(num_retries=5)
            ident = str(result.get("id", ""))
            require(bool(ident), "YouTube returned no playlist ID")
            playlist["id"] = ident
            playlist.pop("creating",None)
            playlist["url"] = "https://www.youtube.com/playlist?list=" + ident
            _save_state(state_path, state)
        playlist_id = str(playlist["id"])
        _verify_playlist_owner(
            youtube, playlist_id, expected_channel_id=channel["id"],
            visibility=visibility)
        for n, item in enumerate(plan["items"]):
            record = state["uploads"].setdefault(item.key, {})
            if record.get("sha256"):
                require(record["sha256"] == item.sha256,
                        f"Previously published bytes changed: {item.key}; "
                        "automatic replacement is disabled")
                require(record.get("source_sha256") == item.source_sha256,
                        "Video origin source changed since upload")
            if not record.get("video_id"):
                # Write an in-flight mark before remote posting. An upload
                # interrupted before its video ID is saved MUST NOT blindly
                # retry and create possible duplicate videos.
                require(not record.get("in_flight"),
                        "Ambiguous interrupted YouTube upload; reconcile "
                        "remote channel before retrying")
                require(sha256(item.mp4) == item.sha256,
                        "MP4 changed before upload")
                record["in_flight"] = True
                _save_state(state_path, state)
                try:
                    ident = _upload_mp4(
                        youtube, item, visibility=visibility,
                        description=(f"{plan['course_title']} | {item.title}\n"
                                     "AI-assisted, source-grounded lecture."))
                except Exception:
                    # Preserve in_flight. Failure could have reached YouTube.
                    raise
                record.update(video_id=ident, sha256=item.sha256,
                              source_sha256=item.source_sha256, in_flight=False)
                _save_state(state_path, state)
            _verify_uploaded_video(
                youtube, record["video_id"], expected_channel_id=channel["id"],
                visibility=visibility)
            if item.caption is not None:
                require(sha256(item.caption) == item.caption_sha256,
                        "Original caption changed after QA planning")
                require(record.get("caption_sha256", item.caption_sha256)
                        == item.caption_sha256,
                        "Previously uploaded subtitles changed")
                if not record.get("caption_id"):
                    record["caption_id"] = _upload_caption(
                        youtube, record["video_id"], item.caption)
                    record["caption_sha256"] = item.caption_sha256
                    _save_state(state_path, state)
            if not record.get("playlist_item_id"):
                # If the API succeeded but the local state was lost, recover
                # an existing playlist entry rather than duplicating it.
                found = next((row["id"] for row in _list_items(youtube, playlist_id)
                              if row["video_id"] == record["video_id"]), None)
                record["playlist_item_id"] = found or _add_item(
                    youtube, playlist_id, record["video_id"], n)
                _save_state(state_path, state)
        wanted = [state["uploads"][x.key]["video_id"] for x in plan["items"]]
        _reorder(youtube, playlist_id, wanted)
        if not playlist.get("image_id"):
            cover_path=root/STATE_DIR/"course_cover.jpg"
            cover=generate_course_cover(plan["course_title"], cover_path)
            playlist["image_id"]=_upload_cover(youtube, playlist_id, cover)
            _save_state(state_path, state)
        state["complete"] = True
        _save_state(state_path, state)
        return {
            "status": "YOUTUBE_COURSE_PUBLISHED",
            "playlist_url": playlist["url"],
            "channel_id": channel["id"],
            "videos": len(wanted),
            "student_published": visibility == "public",
            "automatic_technical_release": True,
            "human_review_required": False,
        }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="MicroGen source-bound YouTube course publisher")
    p.add_argument("command", choices=("plan", "publish"))
    p.add_argument("--source-root", type=Path, required=True)
    p.add_argument("--course-title", required=True)
    p.add_argument("--trailer", type=Path,
                   help="Optional existing QA-checked Video 00 MP4 under source root")
    p.add_argument("--include-completed-only", action="store_true",
                   help="Plan only QA-compliant subchapters; publishing refuses incomplete courses")
    p.add_argument("--expected-handle")
    p.add_argument("--expected-channel-id")
    p.add_argument("--publisher-host",
                   help="Pin exactly one of HP, Dell-115 or Yoga6 by OS hostname")
    p.add_argument("--visibility", choices=("public", "unlisted", "private"), default="public")
    args = p.parse_args(argv)
    try:
        plan = plan_course(args.source_root, course_title=args.course_title,
                           trailer=args.trailer,
                           require_complete=(not args.include_completed_only))
        if args.command == "plan":
            print(json.dumps(summary(plan), indent=2))
            return 0
        require(not args.include_completed_only,
                "Do not publish a partial course using the complete-course command")
        require(args.publisher_host is not None
                and bool(args.expected_handle or args.expected_channel_id),
                "Publishing requires pinned publisher host and channel identity")
        require(args.publisher_host.casefold() == socket.gethostname().casefold(),
                "This is not the pinned publisher machine; refusing OAuth login")
        youtube = authenticate_youtube()
        report = publish_course(
            plan, youtube=youtube,
            expected_channel_id=args.expected_channel_id,
            expected_handle=args.expected_handle,
            publisher_host=args.publisher_host,
            visibility=args.visibility)
        print(json.dumps(report, indent=2))
        return 0
    except (YouTubeCourseError, OSError, ValueError) as exc:
        print(f"YOUTUBE_COURSE_REJECTED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
