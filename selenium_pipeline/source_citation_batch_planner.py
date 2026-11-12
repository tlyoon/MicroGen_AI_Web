"""Autonomous bounded source-cited academic review batching without Gemini calls.

The strict source citation validator has a 13k prompt cap. Instead of
repeating an oversized Gemini request or truncating verified quotes,
partition genuine original slide jobs into 1-4 slide batches. If a SINGLE
slide still exceeds the cap, retain an explicit unresolved witness and stop.
Only physically source-witnessed quotes remain; planning is not AI QA.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from .ai_academic_web_review import build_review_job
from .figure_source_identity import FigureIdentityReviewRequired
from .runner import blocks
from .evidence_reuse_contract import file_sha256

class AcademicBatchPlanningError(ValueError):
    pass

def require(ok, msg):
    if not ok: raise AcademicBatchPlanningError(msg)

def plan(*, folder:Path, max_batch:int=4, job_builder=None)->dict:
    folder=Path(folder).absolute()
    require(folder.is_dir() and not folder.is_symlink()
            and type(max_batch) is int and 1<=max_batch<=4,
            "Only 1-4 original slides per bounded source-cited job")
    source,slides,script=(folder/n for n in ("source.pdf","slides.pdf","script.txt"))
    require(all(f.is_file() and not f.is_symlink()
                for f in (source,slides,script)),
            "Original sources incomplete or symlinked")
    from .runner import check_valid
    require(check_valid("narration",folder),
            "No source-locked slide/narration block coverage")
    numbers=[i for i,_ in blocks(script.read_text(encoding="utf8"))]
    require(numbers==list(range(1,len(numbers)+1)) and len(numbers)<=500,
            "Original narration slide numbering is missing or discontinuous")
    builder=build_review_job if job_builder is None else job_builder
    jobs=[]
    unresolved=[]
    idx=0
    while idx<len(numbers):
        success=None
        for take in range(min(max_batch,len(numbers)-idx),0,-1):
            subset=numbers[idx:idx+take]
            try:
                proposed=builder(folder=folder,slide_numbers=subset)
            except FigureIdentityReviewRequired as exc:
                if "Too many source citation candidates for bounded academic prompt" not in str(exc):
                    raise
                if take==1:
                    unresolved.append({
                        "slide":subset[0],
                        "reason":"SOURCE_CITATION_PROMPT_LIMIT_EVEN_FOR_ONE_SLIDE",
                        "requires_more_GROUNDED_candidate_reduction":True,
                        "provider_send_attempted":False,
                    })
                continue
            require(proposed.get("selected_original_slides")==subset
                    and proposed.get("source_sha256")==file_sha256(source)
                    and proposed.get("slides_sha256")==file_sha256(slides)
                    and proposed.get("script_sha256")==file_sha256(script)
                    and proposed.get("student_publication_authorized") is False
                    and proposed.get("verified_source_quote_candidates_v1",{}).get("status")
                        =="PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1",
                    "Untrusted academic review job or source-citation evidence")
            success=proposed
            break
        if success is None:
            require(unresolved and unresolved[-1]["slide"]==numbers[idx],
                    "No finite source-cited batch progress")
            idx+=1
        else:
            jobs.append(success)
            idx+=len(success["selected_original_slides"])
    require(sorted([n for job in jobs for n in job["selected_original_slides"]]
                   +[x["slide"] for x in unresolved])==numbers,
            "Source citation planner omitted or duplicated a source slide")
    return {
        "schema_version":1,
        "status":("ALL_SOURCE_CITED_REVIEW_JOBS_READY_NOT_DISPATCHED"
                  if not unresolved
                  else "PARTIAL_SOURCE_CITED_REVIEW_JOBS_UNRESOLVED_NO_SEND"),
        "source_sha256":file_sha256(source),
        "slides_sha256":file_sha256(slides),
        "script_sha256":file_sha256(script),
        "source_folder":str(folder),
        "total_slides":len(numbers),
        "jobs":jobs,"unresolved":unresolved,
        "max_review_batch_size":max_batch,
        "model_or_tts_calls":0,
        "all_scientific_claims_reviewed":False,
        "student_publication_authorized":False,
    }

def save_jobs(*, folder:Path, output_dir:Path, max_batch:int=4)->dict:
    out=Path(output_dir).absolute()
    folder=Path(folder).absolute()
    require(out.parent.is_dir() and not out.parent.is_symlink()
            and not out.exists() and not out.is_symlink()
            and not out.is_relative_to(folder)
            and not folder.is_relative_to(out),
            "Academic source citation output must be a distinct new directory")
    report=plan(folder=folder,max_batch=max_batch)
    out.mkdir()
    saved=[]
    for i,job in enumerate(report.pop("jobs"),1):
        slide_ids=job["selected_original_slides"]
        target=out/f"job_{i:02d}_slides_{slide_ids[0]:03d}_{slide_ids[-1]:03d}.json"
        with target.open("x",encoding="utf8") as stream:
            json.dump(job,stream,indent=2,ensure_ascii=False)
            stream.write("\n")
        saved.append({
            "job_filename":target.name,
            "job_sha256":file_sha256(target),
            "slides":slide_ids,
            "utterance_count":job["utterance_count"],
            "source_quote_evidence_complete":True,
            "AI_review_submitted":False,
        })
    report["jobs"]=saved
    manifest=out/"source_citation_batch_manifest.json"
    with manifest.open("x",encoding="utf8") as stream:
        json.dump(report,stream,indent=2,ensure_ascii=False)
        stream.write("\n")
    return report

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--max-batch",type=int,default=4)
    a=p.parse_args(argv)
    try:
        report=save_jobs(folder=a.folder,output_dir=a.output_dir,
                         max_batch=a.max_batch)
    except (OSError,ValueError) as exc:
        report={"status":"SOURCE_CITATION_BATCH_PLANNING_BLOCKED",
                "reason":str(exc),"model_or_tts_calls":0}
    print(json.dumps({k:v for k,v in report.items() if k!="jobs"},
                     indent=2))
    print("job_count",len(report.get("jobs",[])))
    return 2 if report["status"]=="SOURCE_CITATION_BATCH_PLANNING_BLOCKED" else 0

if __name__=="__main__":
    raise SystemExit(main())
