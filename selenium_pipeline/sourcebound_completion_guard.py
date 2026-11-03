"""Recognize complete new multipart production without legacy slides.mp4.

Successful source-bound element-highlighted output uses a verified
lecture_completion.json and part_XX media, not an old monolithic slides.mp4.
This read-only contract prevents a finished full-run from restarting Gemini,
TTS or FFmpeg. Incomplete or tampered video receipts STOP before regeneration.
"""
from __future__ import annotations
import json
import re
from pathlib import Path


class SourceboundCompletionBlocked(RuntimeError):
    """Preserve the previous incomplete or ambiguous production candidate."""


def inspect_sourcebound_completion(source: Path) -> dict:
    source=Path(source).absolute()
    if source.name != "source.pdf" or not source.is_file() or source.is_symlink():
        raise SourceboundCompletionBlocked("Original source.pdf missing or unsafe")
    root=source.parent
    marker=root/"lecture_completion.json"
    part_dirs=[p for p in root.iterdir()
               if re.fullmatch(r"part_[0-9]{2}",p.name)]
    if not marker.exists() and not marker.is_symlink():
        if part_dirs:
            raise SourceboundCompletionBlocked(
                "Partial sourcebound multipart parts have no completion "
                "receipt; preserve them for targeted recovery, never pay "
                "for an automatic remake")
        return {"status":"NO_SOURCEBOUND_COMPLETION",
                "previous_media_preserved":True,
                "student_publication_authorized":False}
    if not marker.is_file() or marker.is_symlink():
        raise SourceboundCompletionBlocked(
            "Sourcebound completion receipt is not a genuine file")
    try:
        manifest=json.loads(marker.read_text(encoding="utf8"))
    except (OSError,ValueError) as exc:
        raise SourceboundCompletionBlocked(
            "Cannot decode prior sourcebound completion receipt") from exc
    if (manifest.get("status")!="accepted_synchronized_series"
            or manifest.get("origin")!="independent_fresh_decoded_pixel_reverification"
            or manifest.get("acceptance_scope")!="technical_only"
            or manifest.get("human_academic_review_verified") is not False
            or manifest.get("student_published") is not False):
        raise SourceboundCompletionBlocked(
            "Existing video manifest is not a validated technical-only "
            "sourcebound production release; refuse auto regeneration")
    wanted=manifest.get("parts")
    if (not isinstance(wanted,list) or not wanted
            or not all(isinstance(v,dict) for v in wanted)):
        raise SourceboundCompletionBlocked(
            "Sourcebound completion has no genuine contiguous parts")
    expected={x.get("part_id") for x in wanted}
    if (len(expected)!=len(wanted) or
            expected!={f"part_{i:02d}" for i in range(1,len(wanted)+1)}
            or {p.name for p in part_dirs}!=expected
            or any(not p.is_dir() or p.is_symlink() for p in part_dirs)):
        raise SourceboundCompletionBlocked(
            "Original sourcebound multipart files differ from the recorded "
            "complete series; do not repeat or overwrite media")
    # Existing production contract checks original source/author/plan SHA,
    # each PCM and MP4 hash, synchronized cues, duration <600 s, and actual
    # encoded MP4 stream via FFmpeg. No new model or TTS API is invoked.
    from .production_video_contract import verify_series
    try:
        result=verify_series(root)
    except (OSError,RuntimeError,ValueError) as exc:
        raise SourceboundCompletionBlocked(
            "Existing multipart receipt or encoded media failed physical "
            "verification; hold for targeted recovery") from exc
    if (result.get("status")!="accepted_synchronized_series"
            or result.get("student_publication_permitted") is not False
            or len(result.get("parts",[]))!=len(wanted)):
        raise SourceboundCompletionBlocked(
            "Physical multipart verification is not a complete technical pass")
    return {"status":"ALREADY_COMPLETED_SOURCEBOUND_MULTIPART",
            "part_count":len(wanted),
            "previous_media_preserved":True,
            "student_publication_authorized":False}
