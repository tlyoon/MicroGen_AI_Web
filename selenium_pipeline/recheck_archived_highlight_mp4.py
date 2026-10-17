"""Read-only fresh pixel recheck of RECEIPT-HASHED older archived review MP4s.

Uses a separately rebuilt, source-bound review bundle as an independent
reference: this tool never substitutes newly rendered MP4s for archived
files. All academic, listening, publication and production flags stay false.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .encoded_highlight_pixels import (
    verify_encoded_highlight_pixels, _frame_pts,
)
from .highlight_video_preview import ffmpeg_path, probe_mp4
from .read_only_video_review_audit import audit_existing
from .recover_frozen_highlight_review import (
    PreservedReviewRecoveryError, file_sha, json_file, preflight, need,
)


def audit_archived(*, source: Path, slides: Path, authored: Path,
                   frozen: Path, synthesis_receipt: Path,
                   rebuilt_review: Path, archived_receipt: Path,
                   archived_mp4s: list[Path]) -> dict:
    """Fresh decode the exact OLD archived MP4s against preserved source WAVs."""
    paths = [source,slides,authored,frozen,synthesis_receipt,
             rebuilt_review,archived_receipt,*archived_mp4s]
    need(not any(Path(x).is_symlink() for x in paths),
         "Symlinked source, reference or archived video is unsafe")
    source,slides,authored,frozen,synthesis_receipt,rebuilt_review,archived_receipt=[
        Path(x).resolve(strict=True) for x in paths[:7]]
    old_videos = [Path(x).resolve(strict=True) for x in archived_mp4s]
    state=preflight(source=source,slides=slides,authored=authored,
                    frozen=frozen,synthesis_receipt=synthesis_receipt)
    need(len(old_videos)==state["part_count"]
         and len({str(x) for x in old_videos})==len(old_videos),
         "Archived MP4 count or uniqueness differs from preserved authored parts")
    manifest=json_file(archived_receipt)
    claims=manifest.get("parts")
    need(manifest.get("schema_version")==1
         and manifest.get("status")=="review_only_not_approved"
         and manifest.get("source_sha256")==state["source_sha256"]
         and manifest.get("plan_sha256")==state["plan_sha256"]
         and manifest.get("accepted_lecture_completion_created") is False
         and manifest.get("student_published") is False
         and isinstance(claims,list) and len(claims)==len(old_videos),
         "Archived video series receipt is unbound or falsely approved")
    # Refresh checks against the independently rebuilt full source,
    # geometry, transcript and WAV bundle. This does not create any reports.
    verified = audit_existing(
        source=source,slides=slides,authored=authored,
        audio=rebuilt_review/"frozen_original_element_audio",
        review_root=rebuilt_review)
    need(verified["covered_elements"]==state["audio_elements"]
         and len(verified["parts"])==len(old_videos),
         "Newly recovered reference bundle does not cover archived narration")
    ffmpeg=ffmpeg_path()
    results=[]
    for index,(old,claim) in enumerate(zip(old_videos,claims),1):
        part_id=f"part_{index:02d}"
        need(isinstance(claim,dict)
             and claim.get("part_id")==part_id
             and claim.get("status")=="review_only_not_approved"
             and claim.get("original_source_sha256")==state["source_sha256"]
             and claim.get("plan_sha256")==state["plan_sha256"]
             and claim.get("mp4_sha256")==file_sha(old),
             f"{part_id}: archived MP4 differs from preserved historical receipt")
        render=rebuilt_review/"rendered"/part_id
        regenerated=json_file(render/"review_receipt.json")
        need(file_sha(render/"narration.wav")==claim.get("wav_sha256")
             and regenerated.get("storyboard_sha256")==
                 claim.get("storyboard_sha256")
             and regenerated.get("original_source_sha256")==
                 state["source_sha256"],
             f"{part_id}: reconstructed audio/storyboard not identical to archived source")
        geometry=json_file(render/"element_geometry.json")
        timeline=json_file(render/"narration_timeline.json")
        observed=probe_mp4(old,exe=ffmpeg)
        need(0<observed["duration_s"]<600
             and abs(observed["duration_s"] -
                     timeline.get("duration_ms",0)/1000) <=0.40
             and abs(observed["duration_s"] -
                     claim.get("encoded_mp4_seconds",-900)) <=0.11,
             f"{part_id}: original encoded MP4 duration/alignment not accepted")
        verified_pixels=verify_encoded_highlight_pixels(
            mp4=old,frames_dir=render/"scratch_frames",
            geometry=geometry,timeline=timeline)
        events=timeline["events"]
        need(verified_pixels.get("count_events")==len(events)
             and all(len(x["target_checks"])==1
                     for x in verified_pixels["checks"]),
             f"{part_id}: not every narrated original element has decoded active pixels")
        # Re-measure actual decoded original frame timestamps, not JSON's
        # historically claimed frame-drift receipt.
        pts=[t for _,t in _frame_pts(old,exe=ffmpeg)]
        need(len(pts)>=len(events), "Archived MP4 has too few actual encoded frames")
        drifts=[min(abs(t-event["start_ms"]/1000) for t in pts)
                for event in events]
        need(bool(drifts) and max(drifts)<=0.15,
             f"{part_id}: actual original encoded highlight frames drift from narration")
        results.append({
            "part_id":part_id,
            "archived_mp4_sha256":file_sha(old),
            "decoded_encoded_duration_s":observed["duration_s"],
            "narrated_events":len(events),
            "independent_original_mp4_pixel_checks":verified_pixels["count_events"],
            "max_original_frame_start_drift_s":round(max(drifts),4),
            "source_approved":False,
        })
    return {
        "status":"ORIGINAL_ARCHIVED_MP4_FRESH_PIXEL_RECHECK_TECHNICAL_ONLY",
        "original_archived_mp4s_independently_redecoded":True,
        "source_sha256":state["source_sha256"],
        "slides_sha256":state["slides_sha256"],
        "authored_plan_sha256":state["plan_sha256"],
        "covered_slides":verified["covered_slides"],
        "covered_narrated_elements":sum(row["narrated_events"] for row in results),
        "archived_parts":results,
        "audible_spoken_text_verified":False,
        "scientific_semantic_mapping_approved":False,
        "human_listening_approved":False,
        "production_approved":False,
        "student_published":False,
    }


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("source","slides","authored","frozen","synthesis-receipt",
                 "rebuilt-review","archived-receipt"):
        parser.add_argument("--"+name,required=True,type=Path)
    parser.add_argument("--archived-mp4",required=True,type=Path,
                        action="append",dest="archived_mp4s",
                        help="Provide in authored part order, once per part")
    args=parser.parse_args(argv)
    result=audit_archived(
        source=args.source,slides=args.slides,authored=args.authored,
        frozen=args.frozen,synthesis_receipt=args.synthesis_receipt,
        rebuilt_review=args.rebuilt_review,archived_receipt=args.archived_receipt,
        archived_mp4s=args.archived_mp4s)
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
