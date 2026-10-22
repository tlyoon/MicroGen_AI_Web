"""Resumable original-source AI review queue; no phantom approvals or blind retries.

One source-bound slide and reviewer pass per bounded attempt. Failed model
output is never promoted, and an observed failed response requires an explicit
new attempt; already completed work is immutable and never re-submitted.
"""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from .figure_source_identity import require,_sha
from .ai_academic_web_review import build_review_job,run_web_review
from .series_gemini import decode_storyboard_response

def _receipt_name(slide:int,mode:str)->str:
    require(type(slide) is int and 1<=slide<=200
            and mode in ("INITIAL_REVIEW","INDEPENDENT_CHALLENGE"),
            "Invalid bounded reviewer unit")
    return f"slide_{slide:03d}_{mode.lower()}.json"

def prepare_resumable_review(*,folder:Path,output_root:Path,
                             slide_numbers:list[int])->dict:
    folder=Path(folder).absolute()
    output_root=Path(output_root).absolute()
    require(type(slide_numbers) is list and bool(slide_numbers)
            and len(slide_numbers)<=200 and
            all(type(n) is int for n in slide_numbers)
            and slide_numbers==sorted(set(slide_numbers))
            and output_root.parent.is_dir() and not output_root.exists()
            and not output_root.is_relative_to(folder),
            "New isolated queue cannot modify original teaching data")
    work=[]
    for n in slide_numbers:
        j=build_review_job(folder=folder,slide_numbers=[n])
        work.append({"slide":n,"utterance_count":j["utterance_count"],
                     "original_source_sha256":j["source_sha256"],
                     "original_slides_sha256":j["slides_sha256"],
                     "original_script_sha256":j["script_sha256"]})
    output_root.mkdir()
    plan={"status":"IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE",
          "original_source_folder":str(folder),
          "slide_jobs":work,"expected_utterances":sum(x["utterance_count"] for x in work),
          "provider_requests_performed":0,"approved_math_utterances":0,
          "student_publication_authorized":False}
    with (output_root/"queue.json").open("x",encoding="utf8") as f:
        json.dump(plan,f,indent=2);f.write("\n")
    return plan

def _check_queue(*,queue_root:Path,folder:Path,slide:int,mode:str)->dict:
    queue_root=Path(queue_root).absolute();folder=Path(folder).absolute()
    plan=json.loads((queue_root/"queue.json").read_text(encoding="utf8"))
    require(plan.get("status")=="IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE"
            and plan.get("original_source_folder")==str(folder)
            and plan.get("student_publication_authorized") is False
            and type(plan.get("slide_jobs")) is list
            and sum(x["utterance_count"] for x in plan["slide_jobs"])==plan["expected_utterances"],
            "Original immutable review queue corrupt")
    row=next((x for x in plan["slide_jobs"] if x["slide"]==slide),None)
    require(row is not None,"Original requested slide absent from queued review")
    for name,key in (("source.pdf","original_source_sha256"),("slides.pdf","original_slides_sha256"),
                     ("script.txt","original_script_sha256")):
        require(_sha(folder/name)==row[key],"Original source assets drifted")
    if mode=="INDEPENDENT_CHALLENGE":
        first=queue_root/_receipt_name(slide,"INITIAL_REVIEW")
        require(first.is_file() and not first.is_symlink(),
                "Independent challenge requires a successfully validated first-pass review")
        check=json.loads(first.read_text(encoding="utf8"))
        require(check.get("mode")=="INITIAL_REVIEW"
                and check.get("status")=="SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS"
                and check.get("review_count")==row["utterance_count"],
                "Initial source review failed or was incomplete")
    return row

def execute_one_review(*,queue_root:Path,folder:Path,
                       slide:int,mode:str,
                       attempt:int=1,transport=None)->dict:
    queue_root=Path(queue_root).absolute();folder=Path(folder).absolute()
    require(type(attempt) is int and 1<=attempt<=3,"No unbounded AI retry loop")
    row=_check_queue(queue_root=queue_root,folder=folder,slide=slide,mode=mode)
    success=queue_root/_receipt_name(slide,mode)
    require(not success.exists(),"Do not resubmit an already verified source review")
    evidence_file=queue_root/f"slide_{slide:03d}_{mode.lower()}_attempt_{attempt:02d}.json"
    require(not evidence_file.exists(),"Observed attempt receipt must never be overwritten")
    # Fail immediately after previous failures unless caller explicitly elects next attempt.
    for i in range(1,attempt):
        previous=queue_root/f"slide_{slide:03d}_{mode.lower()}_attempt_{i:02d}.json"
        require(previous.is_file(),"Cannot skip missing observed failure")
        prior=json.loads(previous.read_text(encoding="utf8"))
        require(prior.get("status")=="FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED"
                and prior.get("attempt")==i,
                "No duplicate successful or unaccounted earlier attempts")
    job=build_review_job(folder=folder,slide_numbers=[slide])
    require(job["utterance_count"]==row["utterance_count"],"Narration coverage changed")
    try:
        response=run_web_review(folder=folder,job=job,mode=mode,transport=transport)
    except (RuntimeError,ValueError,OSError) as exc:
        # Preserve only a concise bounded type/error description, never private tab text.
        fail={"status":"FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED",
              "slide":slide,"mode":mode,"attempt":attempt,
              "error_type":type(exc).__name__,"reason":str(exc)[:450],
              "requires_explicit_next_attempt":True,
              "academically_approved":False,"student_publication_authorized":False}
        with evidence_file.open("x",encoding="utf8") as f:
            json.dump(fail,f,indent=2);f.write("\n")
        return fail
    with success.open("x",encoding="utf8") as f:
        json.dump(response,f,indent=2);f.write("\n")
    done={"status":"GEMINI_SOURCE_REVIEW_ONE_SLIDE_COMPLETED",
          "slide":slide,"mode":mode,"attempt":attempt,
          "verified_original_utterances":response["review_count"],
          "receipt_sha256":_sha(success),
          "academic_independent_challenge_complete":False,
          "student_publication_authorized":False}
    with evidence_file.open("x",encoding="utf8") as f:
        json.dump(done,f,indent=2);f.write("\n")
    return done

def summarize_queue(*,queue_root:Path,folder:Path)->dict:
    plan=json.loads((Path(queue_root)/"queue.json").read_text(encoding="utf8"))
    complete=[];awaited=[];errors=[]
    for x in plan["slide_jobs"]:
        n=x["slide"]
        for mode in ("INITIAL_REVIEW","INDEPENDENT_CHALLENGE"):
            result=Path(queue_root)/_receipt_name(n,mode)
            if result.is_file():
                _check_queue(queue_root=queue_root,folder=folder,slide=n,mode=mode)
                complete.append({"slide":n,"mode":mode,"count":x["utterance_count"]})
            else:
                awaited.append({"slide":n,"mode":mode})
        errors.extend(str(f.name) for f in Path(queue_root).glob(f"slide_{n:03d}_*_attempt_*.json")
                      if json.loads(f.read_text(encoding="utf8")).get("status")
                      =="FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED")
    return {"status":"BOUNDED_AI_REVIEW_QUEUE_CURRENT",
            "expected_utterances":plan["expected_utterances"],
            "completed_passes":complete,"awaited_passes":awaited,
            "quarantined_failed_attempt_receipts":errors,
            "student_publication_authorized":False}
