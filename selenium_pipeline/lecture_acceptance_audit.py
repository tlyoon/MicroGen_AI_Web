"""Read-only real lecture technical acceptance inventory.

Separate measured MP4 duration from actual encoded highlight/media proof and
source-figure scientific completeness. A legacy slides.mp4 is NEVER proof
of an accepted highlighted multipart lesson.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path

from .figure_textbook_pilot import inspect_textbook_figure_pilot
from .figure_vector_provenance import _checked_pdf
from .figure_source_identity import require, _sha
from .production_video_contract import (
    VideoContractError, _mp4_duration, verify_series,
)


def _regular_path(raw: Path, *, directory: bool=False)->Path:
    path=Path(raw).absolute()
    for part in (path,*path.parents):
        require(not part.is_symlink()
                and not getattr(part,"is_junction",lambda:False)(),
                "Original lecture path contains a link/junction")
    require(path.is_dir() if directory else path.is_file(),
            "Expected original regular lecture path missing")
    return path.resolve(strict=True)


def _scan_mp4(folder:Path)->list[Path]:
    # Fixed paths only: no recursive directory walk into historical storage.
    videos=[]
    old=folder/"slides.mp4"
    if old.exists():
        videos.append(_regular_path(old))
    for part in sorted(folder.glob("part_[0-9][0-9]")):
        if part.is_symlink() or not part.is_dir():
            raise ValueError("Unsafe/ambiguous multipart directory")
        media=part/(part.name+".mp4")
        if media.exists():
            videos.append(_regular_path(media))
    require(len(videos)<=40,"Excessive video candidate count")
    return videos


def inspect_real_lecture_acceptance(
    *,source:Path,slides:Path,lecture_folder:Path,
    source_page:int,slide_page:int,figure_id:str,probe=None,
)->dict:
    """Return auditable technical evidence with definite blocked statuses.

    probe is for synthetic unit tests only; when present never certify
    actual encoded duration, synchronized highlights or production.
    """
    source=_checked_pdf(source)
    slides=_checked_pdf(slides)
    folder=_regular_path(lecture_folder,directory=True)
    require(source.is_relative_to(folder) and slides.is_relative_to(folder),
            "Audit must apply to one actual original lecture directory")
    require(source!=slides,"Source and slides cannot be the same PDF")
    files=_scan_mp4(folder)
    original={str(p):_sha(p) for p in (source,slides,*files)}
    source_report=inspect_textbook_figure_pilot(
        source=source,slides=slides,source_page=source_page,
        slide_page=slide_page,figure_id=figure_id)
    require(source_report["tts_or_video_authorized"] is False,
            "Source pilot incorrectly claims production authorization")
    results=[]
    for media in files:
        duration_error=None
        try:
            measured=(probe or _mp4_duration)(media)
            require(type(measured) in (int,float)
                    and math.isfinite(measured) and measured>0,
                    "Invalid actual MP4 duration")
        except (VideoContractError,ValueError,OSError,RuntimeError,subprocess.TimeoutExpired) as exc:
            measured=None
            duration_error=str(exc)
        legacy=(media.name=="slides.mp4")
        results.append({
            "relative_path":str(media.relative_to(folder)).replace("\\","/"),
            "mp4_sha256":original[str(media)],
            "duration_s":round(measured,3) if measured is not None else None,
            "duration_below_strict_600_s":(
                measured<600 if measured is not None else False),
            "duration_measured_from_actual_media":(probe is None and
                                                   measured is not None),
            "legacy_single_file":legacy,
            "technical_highlight_proven":False,
            "media_error":duration_error,
        })
    # The standard complete-series verifier checks WAV duration, exact
    # recorded MP4 duration and audio-timed decoded pixel receipts.
    accepted=None
    media_error=None
    receipt=folder/"lecture_completion.json"
    if receipt.exists():
        try:
            accepted=verify_series(folder)
        except (VideoContractError,ValueError,OSError) as exc:
            media_error=str(exc)
    else:
        media_error="Missing verified multipart lecture_completion.json"
    if accepted is not None:
        require(accepted.get("status")=="accepted_synchronized_series",
                "Unexpected multipart media proof")
        if probe is None:
            ids={p["part_id"] for p in accepted["parts"]}
            require(all(p["duration_s"]<600 for p in accepted["parts"]),
                    "Full multipart receipt includes an overlong part")
            for item in results:
                if item["relative_path"] != "slides.mp4":
                    pid=item["relative_path"].split("/")[0]
                    if pid in ids:
                        item["technical_highlight_proven"]=True
    require(all(_sha(p)==original[str(p)] for p in (source,slides,*files)),
            "Original textbook/slides/MP4 mutated during read-only QA")
    duration_fail=any(item["duration_s"] is not None
                      and not item["duration_below_strict_600_s"]
                      for item in results)
    return {
        "schema_version":1,
        "status":"TECHNICAL_ACCEPTANCE_BLOCKED",
        "figure_id":figure_id,
        "source_report":source_report,
        "source_figure_evidence_complete":False,
        "actual_video_duration_violation_found":duration_fail and probe is None,
        "duration_violation_observed":duration_fail,
        "video_candidates":results,
        "multipart_media_verified":bool(
            accepted is not None and probe is None
            and accepted.get("status")=="accepted_synchronized_series"),
        "multipart_media_failure_reason":media_error,
        "original_assets_unchanged":True,
        "human_academic_listening_review_claimed":False,
        "figure_synchronized_narration_accepted":False,
        "student_publication_permitted":False,
        "next_action":"Ground complete original figure panel identity, then "
                      "run real encoded duration and pixel-highlight QA",
        "synthetic_duration_probe_used":probe is not None,
    }


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder",type=Path,required=True)
    parser.add_argument("--source-page",type=int,required=True)
    parser.add_argument("--slide-page",type=int,required=True)
    parser.add_argument("--figure-id",required=True)
    args=parser.parse_args()
    report=inspect_real_lecture_acceptance(
        source=args.folder/"source.pdf",
        slides=args.folder/"slides.pdf",lecture_folder=args.folder,
        source_page=args.source_page,slide_page=args.slide_page,
        figure_id=args.figure_id)
    print(json.dumps(report,indent=2,ensure_ascii=False))
    # A blocked report must not turn into an accidentally successful batch.
    # 2 = technical requirements NOT proven; output remains machine readable.
    if report["status"]!="TECHNICAL_ACCEPTANCE_VERIFIED":
        raise SystemExit(2)


if __name__=="__main__":
    main()
