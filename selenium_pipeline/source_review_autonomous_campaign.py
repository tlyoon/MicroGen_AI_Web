"""Bounded source-evidence-changed Gemini academic review, crash-safe and no-repeat.

Reconnect three existing pipeline contracts:
1. source-grounded changed-evidence-only planner;
2. durable academic_review_checkpoint per owned Gemini browser Send;
3. exact PDF+slide+script source validator and next queued review job.

No pre-existing claim is ever repeated, including if the prompt changed again.
A technically successful answer with UNRESOLVED/INCORRECT source claims is NOT
a scientific, math, narration-element or G2 acceptance. No TTS/video/uploads.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Callable

from .academic_review_checkpoint import (
    fingerprint, prepare, validate_saved, recover_claimed_observation,
)
from .ai_academic_web_review import (
    review_instructions, run_web_review, validate_model_review,
)
from .figure_source_identity import _sha, require


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(),
            "Missing or linked immutable academic campaign file")
    obj=json.loads(path.read_text(encoding="utf8"))
    require(type(obj) is dict,"Invalid academic campaign receipt")
    return obj


def _new(path: Path, value: dict) -> None:
    with path.open("x",encoding="utf8") as f:
        json.dump(value,f,indent=2,sort_keys=True,ensure_ascii=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def _global_claim_root(root: Path, source_sha256: str) -> Path:
    """Shared Windows checkpoint-parent index, survives new session folders.

    A fresh campaign folder is not permission to resend the SAME original
    utterance. Always check this stable per-source claim index first.
    """
    require(type(source_sha256) is str and len(source_sha256)==64
            and all(c in "0123456789abcdef" for c in source_sha256),
            "Expected exact original source SHA for no-repeat ledger")
    base=Path(root).absolute().parent/".microgen_academic_source_once"
    require(not base.is_symlink(),"Unsafe shared academic claim root")
    base.mkdir(exist_ok=True)
    folder=base/source_sha256
    require(not folder.is_symlink(),"Unsafe source-specific claim index")
    folder.mkdir(exist_ok=True)
    return folder


def _assert_job(entry: dict, source_hash: str) -> tuple[dict,Path,str,list[str]]:
    job=entry["source_job"]
    require(type(job) is dict
            and job.get("status")=="SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED"
            and job.get("source_sha256")==source_hash
            and job.get("source_research_is_new_evidence_only") is True
            and job.get("academic_approval") is False
            and job.get("student_publication_authorized") is False,
            "Only genuine changed source candidates, not prior reviews")
    folder=Path(job["original_folder"]).absolute()
    hashes={name:job[key] for name,key in (
        ("source.pdf","source_sha256"),
        ("slides.pdf","slides_sha256"),
        ("script.txt","script_sha256"))}
    require(all(_sha(folder/name)==digest for name,digest in hashes.items()),
            "Source/author assets drifted since changed review plan")
    uids=[x["id"] for s in job["slides"] for x in s["utterances"]]
    require(uids==entry["eligible_original_unresolved_units"]
            and 1<=len(uids)==job["utterance_count"]<=40
            and len(set(uids))==len(uids),
            "Changed evidence job omitted, reordered or repeated original units")
    prompt=review_instructions(job,mode="INDEPENDENT_CHALLENGE")
    require(sha(prompt.encode("utf8"))==entry["source_job_request_sha256"],
            "Original intended source/visual evidence changed since preflight")
    return job,folder,prompt,uids


def _saved_valid_result(checkpoint: Path, job: dict, folder: Path,
                        prompt: str) -> dict:
    """Resume exact owned source response with ZERO new Gemini calls."""
    hashes={name:job[field] for name,field in (
        ("source.pdf","source_sha256"),("slides.pdf","slides_sha256"),
        ("script.txt","script_sha256"))}
    expected=fingerprint(request_text=prompt,source_hashes=hashes,
                         review_mode="INDEPENDENT_CHALLENGE")
    state=_load(checkpoint/"request_state.json")
    require(state.get("request_fingerprint")==expected,
            "Previously claimed model response is from a different prompt")
    if (state["status"] in ("SUBMITTED_OR_UNCERTAIN","NO_RESPONSE_UNRESOLVED")
            and (checkpoint/"model_response_identity.json").is_file()):
        recover_claimed_observation(checkpoint=checkpoint,
                                    expected_fingerprint=expected)
    require(state["status"] in (
        "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED",
        "MODEL_REPLY_OBSERVED_UNVALIDATED",
        "SUBMITTED_OR_UNCERTAIN","NO_RESPONSE_UNRESOLVED"),
        "Cannot recover an unverified, corrupt or forbidden review checkpoint")
    require((checkpoint/"model_response_identity.json").is_file(),
            "No SHA-bound model reply; do not resend an uncertain submission")
    from .series_gemini import decode_storyboard_response
    return validate_saved(
        checkpoint=checkpoint,expected_fingerprint=expected,
        validator=lambda raw:validate_model_review(
            folder=folder,job=job,
            response=decode_storyboard_response(raw),
            mode="INDEPENDENT_CHALLENGE"))


def import_previous_claimed_review(*,old_plan: Path,position: int,
                                   result_path: Path,checkpoint: Path,
                                   campaign_root: Path) -> dict:
    """Import a *real* earlier source-model Send into the no-repeat ledger.

    This is needed if a campaign is resumed after a repository migration or
    earlier third-pass experiment. Only real SHA-locked owned response bytes
    and validated utterance IDs may reserve a historical claim.
    """
    old=_load(Path(old_plan).absolute())
    require(old.get("status")==
            "UNSENT_PHYSICALLY_CHANGED_G2_SOURCE_AND_VISUAL_EVIDENCE"
            and type(position) is int and 1<=position<=len(old["jobs"]),
            "Original checked Gemini review plan required")
    entry=old["jobs"][position-1]
    job,folder,prompt,uids=_assert_job(entry,old["source_sha256"])
    validated=_saved_valid_result(Path(checkpoint).absolute(),job,folder,prompt)
    provided=_load(Path(result_path).absolute())
    require(provided==validated,
            "External prior review result does not match owned model response")
    root=Path(campaign_root).absolute()
    require(root.is_dir() and not root.is_symlink()
            and not root.is_relative_to(folder),
            "External academic campaign root required")
    (root/"claimed").mkdir(exist_ok=True)
    filename="prior_"+sha((old["source_sha256"]+
        sha(prompt.encode("utf8"))).encode())[:32]+".json"
    destination=root/"claimed"/filename
    payload={"schema_version":1,
             "type":"THIRD_PASS_CHANGED_SOURCE_REVIEW",
             "source_sha256":old["source_sha256"],
             "utterance_ids":uids,
             "request_sha256":sha(prompt.encode("utf8")),
             "historical_owned_response_sha256":
                 _sha(Path(checkpoint).absolute()/"model_response_untrusted.txt"),
             "historical_technical_model_result_only":True,
             "academic_approved":False,
             "student_publication_authorized":False}
    global_marker=_global_claim_root(
        root,old["source_sha256"])/(sha(prompt.encode("utf8"))+".json")
    for marker in (global_marker,destination):
        if marker.exists():
            existing=_load(marker)
            # Older automatic Send claims already lock source+units+prompt.
            # Importing its finally observed model reply merely adds a
            # *separate* immutable provenance receipt, never replaces that
            # earlier claim or resets its one-send permission.
            require(all(existing.get(key)==payload.get(key) for key in (
                        "schema_version","type","source_sha256",
                        "utterance_ids","request_sha256",
                        "academic_approved","student_publication_authorized"))
                    and (not existing.get(
                        "historical_owned_response_sha256")
                        or existing["historical_owned_response_sha256"]==
                           payload["historical_owned_response_sha256"]),
                    "Different historical attempt occupied a source no-repeat claim")
        else:
            _new(marker,payload)
    return {"status":"PRIOR_THIRD_PASS_REVIEW_CLAIM_REUSED_NO_NEW_MODEL_CALL",
            "utterance_count":len(uids),"claim_file":str(destination),
            "student_publication_authorized":False}


def run(*,plan_path: Path,root: Path,max_jobs: int=2,
        transport: Callable | None=None,
        chrome_port: int=9222,
        only_positions: set[int] | None=None) -> dict:
    """Attempt up to max_jobs previously UNATTEMPTED changed-evidence jobs.

    Each selected utterance is claimed before submission; if a worker crashes
    after claim/Send, the same job's saved reply may be re-validated but no
    replacement prompt is sent for those utterances. No automatic G2 approval.
    """
    plan_path=Path(plan_path).absolute()
    plan=_load(plan_path)
    require(plan.get("schema_version")==1
            and plan.get("status")==
                "UNSENT_PHYSICALLY_CHANGED_G2_SOURCE_AND_VISUAL_EVIDENCE"
            and plan.get("G2_approved") is False
            and plan.get("student_publication_authorized") is False
            and type(plan.get("jobs")) is list
            and 1<=len(plan["jobs"])<=24
            and type(max_jobs) is int and 0<=max_jobs<=6
            and (only_positions is None or (
                type(only_positions) is set
                and all(type(x) is int and 1<=x<=len(plan["jobs"])
                        for x in only_positions))),
            "Untrusted changed-evidence academic review plan")
    root=Path(root).absolute()
    require(root.is_dir() and not root.is_symlink()
            and not root.is_relative_to(plan_path.parent),
            "Campaign must use an independent existing external checkpoint root")
    all_uids=set()
    jobs=[]
    for position,entry in enumerate(plan["jobs"],1):
        job,folder,prompt,uids=_assert_job(entry,plan["source_sha256"])
        require(not root.is_relative_to(folder)
                and not folder.is_relative_to(root)
                and all(uid not in all_uids for uid in uids),
                "Duplicate, overlapping or in-source campaign")
        all_uids.update(uids)
        jobs.append((position,entry,job,folder,prompt,uids))
    previous_claimed={}
    global_claims=_global_claim_root(root,plan["source_sha256"])
    local_claims=root/"claimed"
    require(not local_claims.is_symlink(),"Unsafe local review claim directory")
    if not local_claims.exists():
        local_claims.mkdir()
    for directory in (global_claims,local_claims):
        for marker in directory.glob("*.json"):
            previous=_load(marker)
            require(previous.get("schema_version")==1
                    and previous.get("source_sha256")==plan["source_sha256"]
                    and previous.get("type")=="THIRD_PASS_CHANGED_SOURCE_REVIEW"
                    and type(previous.get("utterance_ids")) is list
                    and type(previous.get("request_sha256")) is str,
                    "Untrusted or foreign academic request claim")
            for uid in previous["utterance_ids"]:
                earlier=previous_claimed.get(uid)
                require(earlier is None
                        or earlier["request_sha256"]==previous["request_sha256"]
                        and earlier["utterance_ids"]==previous["utterance_ids"],
                        "Original unit already attempted under DIFFERENT source "
                        "claim; never submit a duplicate source review")
                previous_claimed[uid]=previous
    completed=[];skipped=[];attempted=0
    for position,entry,job,folder,prompt,uids in jobs:
        if only_positions is not None and position not in only_positions:
            skipped.append({"job":position,"status":"NOT_SELECTED_IN_BOUNDED_PASS"})
            continue
        filename=f"job_{position:02d}"
        checkpoint=root/(filename+"_checkpoint")
        result_path=root/(filename+"_result.json")
        claim_path=root/"claimed"/(filename+".json")
        if result_path.exists():
            existing=_load(result_path)
            require(existing.get("status")==
                    "SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS"
                    and len(existing.get("rows",[]))==len(uids)
                    and [x["utterance_id"] for x in existing["rows"]]==uids,
                    "Campaign existing result not from planned original units")
            outcome=_saved_valid_result(checkpoint,job,folder,prompt)
            require(existing==outcome,"Saved model reply differs from campaign result")
            completed.append({"job":position,"status":"REUSED_VERIFIED_RESULT",
                              "reviewed":len(uids)})
            continue
        claimed=[uid for uid in uids if uid in previous_claimed]
        if claimed:
            # When any component was already sent, do not repackage the same
            # original claims in another changed prompt. Preserve unresolved
            # work and instead proceed with OTHER uniquely eligible units.
            if len(claimed)<len(uids):
                raise RuntimeError(
                    "Partial overlap with prior academic review claim; "
                    "replan genuinely unattempted source units first")
            if not claim_path.exists():
                # If a crash happened between shared-global and local
                # journal creation, a SAME request which is provably
                # PREPARED_NOT_SENT can resume without any duplicate Send.
                state_file=checkpoint/"request_state.json"
                pre=_load(state_file) if state_file.is_file() else None
                if (pre and pre.get("status")=="PREPARED_NOT_SENT"
                        and not (checkpoint/"dispatch_attempted.claim").exists()
                        and previous_claimed[uids[0]]["request_sha256"]==
                            sha(prompt.encode("utf8"))
                        and previous_claimed[uids[0]]["utterance_ids"]==uids):
                    _new(claim_path,previous_claimed[uids[0]])
                else:
                    skipped.append({"job":position,
                                    "status":"ORIGINAL_UNITS_ALREADY_ATTEMPTED"})
                    continue
            saved_state=_load(checkpoint/"request_state.json") if (
                checkpoint/"request_state.json").is_file() else None
            if saved_state and saved_state["status"]== "PREPARED_NOT_SENT" and (
                    not (checkpoint/"dispatch_attempted.claim").exists()):
                pass  # definitely no Send; resume exact prepared request
            elif saved_state and saved_state["status"]== "REJECTED_RESPONSE_UNTRUSTED":
                # A captured response with a bad source citation or malformed
                # payload may be saved on disk, but MUST NOT be promoted,
                # revalidated in a retry loop, or submitted again.
                skipped.append({"job":position,
                                "status":"REJECTED_ORIGINAL_MODEL_REPLY_NO_RETRY"})
                continue
            elif saved_state and (checkpoint/"model_response_identity.json").exists():
                outcome=_saved_valid_result(checkpoint,job,folder,prompt)
                _new(result_path,outcome)
                completed.append({"job":position,"status":"RECOVERED_SAVED_REPLY",
                                  "reviewed":len(uids)})
                continue
            else:
                skipped.append({"job":position,
                                "status":"PREVIOUS_SEND_UNCERTAIN_NO_RETRY"})
                continue
        if attempted>=max_jobs:
            skipped.append({"job":position,"status":"CAMPAIGN_FINITE_BUDGET"})
            continue
        if not claim_path.exists():
            # PREPARE strictly checks source, template, prior request identity,
            # before claiming the original utterances and entering browser Send.
            hashes={name:job[key] for name,key in (
                ("source.pdf","source_sha256"),
                ("slides.pdf","slides_sha256"),("script.txt","script_sha256"))}
            prepare(checkpoint=checkpoint,original_folder=folder,
                    request_text=prompt,source_hashes=hashes,
                    review_mode="INDEPENDENT_CHALLENGE")
            claim={
                "schema_version":1,"type":"THIRD_PASS_CHANGED_SOURCE_REVIEW",
                "source_sha256":job["source_sha256"],
                "utterance_ids":uids,"request_sha256":sha(prompt.encode("utf8")),
                "academic_approved":False,
                "student_publication_authorized":False}
            shared=global_claims/(sha(prompt.encode("utf8"))+".json")
            # Shared claim FIRST: no other new conversation's checkpoint
            # directory can dodge the bound even if this process crashes
            # before its per-job local claim is installed.
            if shared.exists():
                require(_load(shared)==claim,
                        "Global original-unit claim already exists or was changed")
            else:
                _new(shared,claim)
            _new(claim_path,claim)
            for uid in uids:
                previous_claimed[uid]=claim
        attempted+=1
        try:
            outcome=run_web_review(folder=folder,job=job,
                        mode="INDEPENDENT_CHALLENGE",
                        transport=transport,chrome_port=chrome_port,
                        checkpoint_dir=checkpoint)
        except Exception as exc:
            skipped.append({"job":position,
                "status":"TRANSPORT_OR_VALIDATION_BLOCKED_NO_RETRY",
                "error_type":type(exc).__name__})
            break   # never continue paid batch after an unexplained failure
        _new(result_path,outcome)
        completed.append({"job":position,"status":"NEW_VALID_SOURCE_REVIEW",
                          "reviewed":len(uids),
                          "supported":sum(r["verdict"]=="SUPPORTED"
                                          for r in outcome["rows"]),
                          "unresolved":sum(r["verdict"]=="UNRESOLVED"
                                           for r in outcome["rows"])})
    return {"schema_version":1,
            "status":"BOUNDED_CHANGED_SOURCE_REVIEW_NOT_G2_APPROVED",
            "original_source_sha256":plan["source_sha256"],
            "selected":len(jobs),"new_requests_attempted":attempted,
            "jobs_completed":completed,"jobs_not_rerun":skipped,
            "any_unresolved_academic_science":True,
            "independent_math_safety_verified":False,
            "per_element_wav_sync_verified":False,
            "G2_approved":False,"G3_authorized":False,
            "student_publication_authorized":False}


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan",type=Path,required=True)
    p.add_argument("--checkpoint-root",type=Path,required=True)
    p.add_argument("--max-new-jobs",type=int,default=2)
    p.add_argument("--chrome-port",type=int,default=9222)
    p.add_argument("--only-job",type=int,action="append",
                   help="Bounded job position (repeatable); defaults to full queue")
    a=p.parse_args(argv)
    result=run(plan_path=a.plan,root=a.checkpoint_root,
               max_jobs=a.max_new_jobs,chrome_port=a.chrome_port,
               only_positions=set(a.only_job) if a.only_job else None)
    print(json.dumps(result,indent=2,sort_keys=True))
    return int(result["G2_approved"] is False and
               not result["jobs_completed"] and result["new_requests_attempted"]>0)


if __name__=="__main__":
    raise SystemExit(main())
