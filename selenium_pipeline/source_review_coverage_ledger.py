"""Read-only source-reverified one-pass review coverage across bounded jobs.

All accepted rows are rechecked against the ORIGINAL PDF, slide targets,
spoken SHA and quote whitelist. No model request, no release approval, no
invention of missing reviews. Partial attempted replies are never counted as
a complete model review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from .evidence_reuse_contract import file_sha256
from .ai_academic_web_review import validate_model_review

class SourceCoverageBlocked(ValueError):
    pass

def need(condition, message):
    if not condition:
        raise SourceCoverageBlocked(message)

_FIELDS=("utterance_id","spoken_sha256","target_id","source_page",
         "verbatim_source_quote","verdict","math_explanation")

def _single(job:dict,slide:dict,unit:dict)->dict:
    matching=[item for item in job[
        "verified_source_quote_candidates_v1"]["utterances"]
        if item.get("utterance_id")==unit["id"]]
    need(len(matching)==1,"Original quote whitelist identity missing")
    return {**job,
            "utterance_count":1,
            "slides":[{**slide,"utterances":[unit]}],
            "verified_source_quote_candidates_v1":{
                **job["verified_source_quote_candidates_v1"],
                "utterances":matching}}

def _validated_row(*,folder:Path,job:dict,slide:dict,unit:dict,
                   row:dict)->dict:
    result=validate_model_review(
        folder=folder,job=_single(job,slide,unit),
        response={"status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
                  "rows":[{field:row.get(field) for field in _FIELDS}]},
        mode="INITIAL_REVIEW")
    need(result.get("review_count")==1 and
         result.get("student_publication_authorized") is False,
         "Source-scoped review could not be independently verified")
    return result["rows"][0]

def aggregate(*,manifest_path:Path,results:list[Path],out:Path)->dict:
    manifest_path=Path(manifest_path).absolute()
    out=Path(out).absolute()
    need(manifest_path.is_file() and not manifest_path.is_symlink()
         and manifest_path.name=="source_citation_batch_manifest.json"
         and out.parent.is_dir() and not out.exists()
         and len(results)<=24,
         "Source review aggregation requires a new bounded receipt")
    manifest=json.loads(manifest_path.read_text(encoding="utf8"))
    folder=Path(manifest["source_folder"]).absolute()
    root=manifest_path.parent
    need(folder.is_dir() and not folder.is_symlink()
         and not out.is_relative_to(folder)
         and manifest.get("total_slides",0)>0
         and len(manifest.get("jobs",[]))<=24
         and all(file_sha256(folder/name)==manifest[field]
                 for name,field in (
                     ("source.pdf","source_sha256"),
                     ("slides.pdf","slides_sha256"),
                     ("script.txt","script_sha256"))),
         "Original source or bounded academic job manifest changed")
    jobs={}
    all_units={}
    for entry in manifest["jobs"]:
        path=root/entry["job_filename"]
        need(path.is_file() and not path.is_symlink()
             and file_sha256(path)==entry["job_sha256"],
             "Original academic batch changed")
        j=json.loads(path.read_text(encoding="utf8"))
        need(j.get("source_sha256")==manifest["source_sha256"]
             and j.get("slides_sha256")==manifest["slides_sha256"]
             and j.get("script_sha256")==manifest["script_sha256"]
             and j.get("selected_original_slides")==entry["slides"]
             and len(j["slides"])==len(entry["slides"]),
             "Academic source/slide batch identity mismatch")
        units=[(s,u) for s in j["slides"] for u in s["utterances"]]
        need(len(units)==entry["utterance_count"],
             "Source unit count differs from batch manifest")
        for slide,unit in units:
            name=unit["id"]
            need(name not in all_units,"Duplicate original utterance in batches")
            all_units[name]=(entry["job_filename"],j,slide,unit)
        jobs[entry["job_filename"]]=(entry,j,units)
    assignment={}
    for path in results:
        path=Path(path).absolute()
        need(path.is_file() and not path.is_symlink()
             and not path.is_relative_to(folder)
             and path.stat().st_size<1_000_000,
             "Untrusted academic result path")
        doc=json.loads(path.read_text(encoding="utf8"))
        partial=doc.get("status")=="PARTIAL_SOURCE_WITNESSED_AI_REVIEW_NOT_COMPLETE"
        full=doc.get("status")=="SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS"
        need(partial or full,"No source-verified AI review status")
        rows=(doc.get("accepted_rows") if partial else doc.get("rows"))
        need(type(rows) is list and bool(rows),
             "Review has no accepted original utterances")
        names=[item.get("utterance_id") for item in rows]
        need(len(set(names))==len(names)
             and all(name in all_units for name in names),
             "Review response contains duplicate, foreign or invalid utterances")
        candidates={all_units[name][0] for name in names}
        need(len(candidates)==1,"Review result spans multiple original jobs")
        match=next(iter(candidates))
        entry,job,units=jobs[match]
        need(match not in assignment,"Academic job already counted from a different reply")
        if partial:
            need(doc.get("source_batch_job_sha256")==entry["job_sha256"]
                 and doc.get("source_sha256")==manifest["source_sha256"]
                 and doc.get("slides_sha256")==manifest["slides_sha256"]
                 and doc.get("script_sha256")==manifest["script_sha256"]
                 and doc.get("new_model_or_tts_requests")==0
                 and doc.get("original_submission_preserved_no_resend") is True
                 and doc.get("full_source_and_math_review_accepted") is False,
                 "Partial model-source reply identity changed")
            checkpoint=Path(doc.get("original_dispatch_checkpoint",""))
            raw=checkpoint/"model_response_untrusted.txt"
            need(raw.is_file() and not raw.is_symlink()
                 and file_sha256(raw)==doc.get("source_model_response_sha256"),
                 "Partial rows have no original owned Gemini response")
            original=json.loads(raw.read_bytes().decode("utf8"))
            actual_rows={r["utterance_id"]:r for r in original["rows"]}
            for row in rows:
                raw_item=actual_rows.get(row["utterance_id"])
                need(type(raw_item) is dict
                     and all(raw_item.get(k)==row.get(k)
                             for k in _FIELDS),
                     "Partially recovered row differs from original Gemini response")
            bad=doc.get("untrusted_rows")
            need(type(bad) is list
                 and {x["utterance_id"] for x in bad}==
                     {u["id"] for _s,u in units}-set(names),
                 "Untrusted utterance gap not explicitly preserved")
        else:
            need(len(rows)==len(units)
                 and doc.get("review_count")==len(rows)
                 and doc.get("student_publication_authorized") is False
                 and doc.get("academic_mathematics_independently_verified") is False,
                 "Whole batch model review not complete or wrongly approved")
            need(set(names)=={u["id"] for _s,u in units},
                 "Whole batch has missing/repeated utterance IDs")
        validated=[]
        unit_map={u["id"]:(s,u) for s,u in units}
        for row in rows:
            s,u=unit_map[row["utterance_id"]]
            validated.append(_validated_row(folder=folder,job=job,
                                           slide=s,unit=u,row=row))
        assignment[match]={
            "result_filename":str(path),
            "result_sha256":file_sha256(path),
            "is_partial":partial,
            "original_utterances":len(units),
            "source_validated":validated,
            "untrusted_utterance_count":len(units)-len(validated),
        }
    total=sum(len(units) for _entry,_job,units in jobs.values())
    good=sum(len(v["source_validated"]) for v in assignment.values())
    invalid=sum(v["untrusted_utterance_count"] for v in assignment.values())
    pending=total-good-invalid
    all_valid=[row for v in assignment.values() for row in v["source_validated"]]
    supported=sum(row["verdict"]=="SUPPORTED" for row in all_valid)
    unresolved=sum(row["verdict"]=="UNRESOLVED" for row in all_valid)
    incorrect=sum(row["verdict"]=="INCORRECT" for row in all_valid)
    need(total==good+invalid+pending
         and good==supported+unresolved+incorrect,
         "Summarized source review coverage does not reconcile")
    result={
        "schema_version":1,
        "status":("ALL_ORIGINAL_ONE_PASS_ROWS_RECHECKED_NOT_ACADEMIC_APPROVAL"
                  if good==total else "PARTIAL_ONE_PASS_SOURCE_REVIEW_WITH_GAPS"),
        "source_sha256":manifest["source_sha256"],
        "slides_sha256":manifest["slides_sha256"],
        "script_sha256":manifest["script_sha256"],
        "slide_count":manifest["total_slides"],
        "original_utterance_count":total,
        "individually_source_validated":good,
        "untrusted_utterances":invalid,
        "not_yet_reviewed_utterances":pending,
        "source_supported":supported,
        "source_unresolved":unresolved,
        "source_incorrect":incorrect,
        "review_batch_count":len(jobs),
        "review_batches_with_saved_responses":len(assignment),
        "academic_science_independently_verified":False,
        "release_approved":False,
        "new_model_tts_requests":0,
        "jobs":[{
            "job":name,
            "slides":entry["slides"],
            "original_utterances":len(units),
            "validated":len(assignment.get(name,{}).get("source_validated",[])),
            "untrusted":assignment.get(name,{}).get("untrusted_utterance_count",0),
            "missing_review":name not in assignment,
            "original_result_sha256":assignment.get(name,{}).get("result_sha256")}
            for name,(entry,_j,units) in jobs.items()],
    }
    with out.open("x",encoding="utf8") as stream:
        json.dump(result,stream,indent=2,ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--results",type=Path,nargs="*",default=[])
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(argv)
    try:
        result=aggregate(manifest_path=a.manifest,results=a.results,out=a.out)
    except (ValueError,OSError,RuntimeError,KeyError,TypeError) as exc:
        result={"status":"SOURCE_REVIEW_COVERAGE_AGGREGATION_REJECTED",
                "reason":str(exc)[:500],"new_model_tts_requests":0}
    print(json.dumps(result,indent=2))
    return 0 if not result["status"].endswith("_REJECTED") else 2

if __name__=="__main__":
    raise SystemExit(main())
