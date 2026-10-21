"""Restart-safe batch ORIGINAL-WAV whole-slide MP4 technical preview staging.

Each independently valid subchapter produces strictly short review-only parts.
Never overwrites existing stage or lecture files and never confuses whole-slide
playback with source/utterance-to-element synchronization.
"""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from .figure_source_identity import require
from .original_wav_multipart_plan import inspect_original_slide_wav_plan
from .original_slide_multipart_rehearsal import rehearse_contiguous_original_slides

def stage_original_preview_batch(*,root:Path,subchapters:tuple[str,...],
                                 destination:Path,max_parts_per_subchapter:int=40,
                                 start_part:int=1)->dict:
    root,destination=Path(root).absolute(),Path(destination).absolute()
    require(root.is_dir() and not root.is_symlink()
            and destination.parent.is_dir() and not destination.exists()
            and not destination.is_relative_to(root)
            and type(subchapters) is tuple and 1<=len(subchapters)<=30
            and len(set(subchapters))==len(subchapters)
            and all(type(n) is str and re.fullmatch(r"[1-9]\d*\.[1-9]\d*",n)
                    for n in subchapters)
            and type(max_parts_per_subchapter) is int
            and 1<=max_parts_per_subchapter<=40
            and type(start_part) is int and 1<=start_part<=40,
            "Choose bounded independent original lecture targets and new external staging")
    destination.mkdir()
    records=[]
    for name in subchapters:
        folder=root/name
        rec={"subchapter":name,"status":"UNPROCESSED","parts":[],
             "student_publication_authorized":False,
             "element_spoken_word_sync_verified":False}
        try:
            plan=inspect_original_slide_wav_plan(folder)
            rec["original_sha256"]={
                "source.pdf":plan["source_sha256"],"slides.pdf":plan["slides_sha256"]}
            rec["original_audio_part_count"]=plan["proposed_part_count"]
            rec["starting_part_number"]=start_part
            for part in plan["proposed_parts"][
                    start_part-1:start_part-1+max_parts_per_subchapter]:
                stage=destination/name/part["part_id"]
                stage.parent.mkdir(exist_ok=True)
                try:
                    result=rehearse_contiguous_original_slides(
                        folder=folder,slide_start=part["slide_start"],
                        slide_end=part["slide_end"],destination=stage)
                    rec["parts"].append({
                        "part_id":part["part_id"],"status":result["status"],
                        "slide_range":result["slide_range"],
                        "encoded_seconds":result["actual_encoded_mp4_duration_s"],
                        "sha256":result["mp4_sha256"]})
                except (OSError,ValueError,RuntimeError) as exc:
                    rec["parts"].append({
                        "part_id":part["part_id"],
                        "status":"INDEPENDENT_PREVIEW_PART_FAILED_REVIEW_REQUIRED",
                        "error_type":type(exc).__name__})
                    break
            complete=(start_part==1
                      and len(rec["parts"])==plan["proposed_part_count"]
                      and all(x["status"]=="GENUINE_WHOLE_SLIDE_MULTIPART_REVIEW_ONLY"
                              for x in rec["parts"]))
            rec["status"]=("COMPLETE_WHOLE_SLIDE_TECHNICAL_PREVIEWS_NOT_ELEMENT_SYNC"
                          if complete else "PARTIAL_OR_BLOCKED_TECHNICAL_PREVIEW")
        except (OSError,ValueError,RuntimeError) as exc:
            rec["status"]="SOURCE_SUBCHAPTER_BLOCKED_INDEPENDENTLY"
            rec["error_type"]=type(exc).__name__
        records.append(rec)
        # Durable per-subchapter checkpoint even when a later one fails.
        with (destination/f"{name.replace('.','_')}_receipt.json").open(
                "x",encoding="utf8") as out:
            json.dump(rec,out,indent=2)
            out.write("\n")
    result={
        "status":"GENUINE_ORIGINAL_WAV_MULTIPART_TECHNICAL_PREVIEWS_ONLY",
        "subchapters":records,
        "completed_review_only_subchapters":sum(
            r["status"]=="COMPLETE_WHOLE_SLIDE_TECHNICAL_PREVIEWS_NOT_ELEMENT_SYNC"
            for r in records),
        "all_element_audio_sync_verified":False,
        "human_academic_and_listening_qa_completed":False,
        "production_media_approved":False,
        "student_publication_authorized":False}
    with (destination/"batch_summary.json").open("x",encoding="utf8") as out:
        json.dump(result,out,indent=2)
        out.write("\n")
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--subchapters",nargs="+",required=True)
    p.add_argument("--destination",type=Path,required=True)
    p.add_argument("--max-parts-per-subchapter",type=int,default=40)
    p.add_argument("--start-part",type=int,default=1)
    a=p.parse_args(argv)
    r=stage_original_preview_batch(root=a.root,
       subchapters=tuple(a.subchapters),destination=a.destination,
       max_parts_per_subchapter=a.max_parts_per_subchapter,
       start_part=a.start_part)
    print(json.dumps({"status":r["status"],
        "completed_review_only_subchapters":r["completed_review_only_subchapters"],
        "publication_authorized":r["student_publication_authorized"]},
        indent=2))
    return 0 if all(x["status"] in (
        "COMPLETE_WHOLE_SLIDE_TECHNICAL_PREVIEWS_NOT_ELEMENT_SYNC",
        "PARTIAL_OR_BLOCKED_TECHNICAL_PREVIEW") for x in r["subchapters"]) else 2

if __name__=="__main__":
    raise SystemExit(main())
