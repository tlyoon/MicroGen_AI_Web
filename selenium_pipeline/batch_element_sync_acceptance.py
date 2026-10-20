"""Multi-subchapter source-bound lecture technical QA and safe recovery queue.

Does not create/bill TTS or replace original student materials. Reports which
subchapters need math-to-narration decisions versus actual encoded MP4 repairs.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from .figure_source_identity import require,_sha
from .original_wav_multipart_plan import inspect_original_slide_wav_plan
from .element_tts_safe_handoff import preflight as tts_preflight
from .original_audio_element_reconciliation import verify_full_staged_element_coverage

def audit(*,root:Path,names:tuple[str,...],staged:dict[str,Path]|None=None,
          check_all_staged_pixels:bool=True)->dict:
    root=Path(root).absolute()
    require(root.is_dir() and not root.is_symlink() and 1<=len(names)<=40
            and len(set(names))==len(names)
            and all(isinstance(x,str) and
                    len(x)<30 and x.replace(".","").isdigit()
                    and not x.startswith(".") and ".." not in x for x in names),
            "Invalid original subchapter root or target list")
    staged=staged or {}
    require(set(staged).issubset(set(names)),
            "External stage not associated with source subchapter")
    items=[]
    for name in names:
        folder=root/name
        record={"subchapter":name,"source_folder":str(folder),
                "status":"SOURCE_SUBCHAPTER_REVIEW_REQUIRED",
                "encoded_production_mp4_verified":False,
                "source_bound_spoken_element_synchronization_verified":False,
                "human_academic_listening_qa_verified":False,
                "student_publication_authorized":False,
                "existing_teaching_assets_modified":False,
                "next_actions":[]}
        source,slides,script=(folder/x for x in ("source.pdf","slides.pdf","script.txt"))
        if not folder.is_dir() or folder.is_symlink() or any(
                not p.is_file() or p.is_symlink() for p in (source,slides,script)):
            record["status"]="SOURCE_OR_SCRIPT_MISSING"
            record["next_actions"].append("RESTORE_ORIGINAL_SOURCE_AND_SCRIPT_EVIDENCE")
            items.append(record);continue
        originals={str(p):_sha(p) for p in (source,slides,script)}
        try:
            plan=inspect_original_slide_wav_plan(folder)
            record["original_wav_count"]=plan["original_wav_count"]
            record["original_wav_duration_s"]=plan["total_original_wav_duration_s"]
            record["proposed_parts"]=[{
                "slide_start":p["slide_start"],"slide_end":p["slide_end"],
                "original_wav_s":p["original_wav_duration_sum_s"]}
                for p in plan["proposed_parts"]]
            record["audio_only_split_plan_available"]=True
        except Exception as exc:
            record["audio_only_split_plan_available"]=False
            record["audio_preflight_error_type"]=type(exc).__name__
            record["next_actions"].append("RECOVER_INCOMPLETE_ORIGINAL_SLIDE_WAV_INVENTORY")
        try:
            tts=tts_preflight(source=source,slides=slides,script=script)
            record["original_element_tts_status"]=tts["status"]
            record["element_tts_mapping_prerequisite_passed"]=tts["element_mapping_prerequisite_passed"]
            if not tts["element_mapping_prerequisite_passed"]:
                record["next_actions"].append("REVIEW_ORIGINAL_MATH_AND_UTTERANCE_ELEMENT_MAPPING")
            else:
                record["next_actions"].append("RUN_APPROVED_CONSISTENT_VOICE_ELEMENT_TTS_STAGE")
        except Exception as exc:
            record["element_tts_mapping_prerequisite_passed"]=False
            record["tts_preflight_error_type"]=type(exc).__name__
            record["next_actions"].append("RESTORE_SOURCE_BOUND_ELEMENT_TTS_EVIDENCE")
        if name in staged:
            try:
                path=Path(staged[name]).absolute()
                require(path.is_dir() and not path.is_symlink()
                        and not path.is_relative_to(folder),
                        "Isolated staged review required")
                review=verify_full_staged_element_coverage(
                    original=folder,staged=path,
                    check_all_pixels=check_all_staged_pixels)
                record["staged_review_found"]=True
                record["staged_review_events_verified"]=(
                    review["all_events_encoded_pixel_recheck_count"])
                record["staged_review_all_events"]=review["total_provisional_highlight_events"]
                record["staged_review_status"]=review["status"]
                record["status"]="STAGED_REVIEW_MP4_TECHNICALLY_CHECKED_NOT_PUBLISHABLE"
                record["next_actions"].append("REPLACE_UNVERIFIED_AUDIO_PAUSE_HIGHLIGHTS_WITH_SOURCE_BOUND_ELEMENT_WAV_TIMING")
            except Exception as exc:
                record["staged_review_found"]=False
                record["staged_review_error_type"]=type(exc).__name__
                record["next_actions"].append("REPAIR_OR_REAUDIT_STAGED_MP4_UNVERIFIED")
        else:
            record["staged_review_found"]=False
            record["next_actions"].append("STAGE_REAL_SPLIT_MULTIPART_VIDEO_AFTER_VERIFIED_SOURCE_MAPPING")
        require(all(_sha(Path(path))==digest for path,digest in originals.items()),
                "Original source/slide/script altered during batch audit")
        items.append(record)
    return {"schema_version":1,
            "status":"MULTISUBCHAPTER_SOURCE_BOUND_TECHNICAL_AUDIT_REVIEW_REQUIRED",
            "subchapter_count":len(items),
            "staged_preview_subchapter_count":sum(bool(x.get("staged_review_found", False)) for x in items),
            "production_accepted_subchapter_count":0,
            "items":items,"all_original_assets_preserved":True,
            "full_spoken_highlight_sync_verified":False,
            "academic_listening_qa_verified":False,
            "student_publication_authorized":False}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--subchapters",nargs="+",required=True)
    p.add_argument("--staged-8-4",type=Path)
    p.add_argument("--skip-exhaustive-staged-pixels",action="store_true")
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    names=tuple(a.subchapters)
    record=audit(root=a.root,names=names,
        staged={"8.4":a.staged_8_4} if a.staged_8_4 else None,
        check_all_staged_pixels=not a.skip_exhaustive_staged_pixels)
    target=a.out.absolute()
    require(not target.exists() and target.parent.is_dir()
            and not target.is_relative_to(a.root.absolute()),
            "Audit output must be new and outside original lesson tree")
    with target.open("x",encoding="utf8") as fh:
        json.dump(record,fh,indent=2,sort_keys=True)
    print(json.dumps({"status":record["status"],
        "count":record["subchapter_count"],
        "staged_preview_count":record["staged_preview_subchapter_count"],
        "production_accepted_count":record["production_accepted_subchapter_count"]},
        indent=2,sort_keys=True))
    return 2
if __name__=="__main__":
    raise SystemExit(main())
