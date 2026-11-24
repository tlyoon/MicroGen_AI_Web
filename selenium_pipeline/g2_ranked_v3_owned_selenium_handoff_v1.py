"""Bounded, source-locked G2 V3 model-review handoff: no old Send replay.

The nine original physically verified ranked-target V3 review INPUTS are NOT
AI agreements. Validate their exact publisher/spoken/visible-target identities,
original V1 and V2 provenance, canonical prompt SHA and an EXISTING immutable
finite G2 review campaign. Any new Selenium Send requires:
  * explicit execution authorization;
  * a genuinely fresh owned post-incident Neon/High source-free health receipt;
  * an unused pre-Send reservation in the same historical named campaign;
  * a brand-new SHA-distinct V3 request directory (not an old V1 or uncertain
    whole-slide request).
Even a successful first/challenge model Send does NOT auto-promote scientific
agreement; independent raw-response two-pass revalidation is still required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .academic_review_checkpoint import (
    _load, fingerprint, validate_saved)
from .ai_academic_web_review import (
    review_instructions, run_web_review, validate_source_demoted_review)
from .autonomous_recovery_continuation_v1 import (
    _campaign, _append, _possible_sends, _reservation, _owned_neon_high)
from .figure_source_identity import _sha,require
from .g2_distinct_focused_source_review_v1 import plan, _health_ok
from .g2_focused_source_target_preflight_v1 import stage as source_preflight
from .g2_ranked_source_review_candidate_v3 import (
    stage as ranked_stage, ROOT as CANDIDATE_ROOT, STATUS as CANDIDATE_STATUS)
from .recovery_registry import lookup_mechanism
from .series_gemini import decode_storyboard_response
from .three_pc_worker import LocalInstanceLock

KIND="g2_ranked_v3_owned_science_handoff"
SIGNATURE="G2_RANKED_V3_REVIEW_INPUT_NEEDS_DISTINCT_NEON_MODEL_CLAIM"
MECHANISM="BIND_ORIGINAL_RANKED_INPUT_TO_OWNED_FINITE_SELENIUM_SCIENCE_REVIEW"
ROOT="G2_RANKED_V3_OWNED_SELENIUM_REVIEW_V1"
MODE={"INITIAL_REVIEW":"INITIAL","INDEPENDENT_CHALLENGE":"CHALLENGE"}


def _verify(*,folder:Path,queue_root:Path,candidate_file:Path)->tuple[dict,dict]:
    folder,queue_root,candidate_file=(
        Path(folder).absolute(),Path(queue_root).absolute(),
        Path(candidate_file).absolute())
    require(candidate_file.parent==queue_root.parent/CANDIDATE_ROOT
            and candidate_file.is_file() and not candidate_file.is_symlink(),
            "Only original immutable ranked V3 source-science inputs allowed")
    row=json.loads(candidate_file.read_text("utf8"))
    require(row["status"]==CANDIDATE_STATUS
            and row["scope_sha256"]==candidate_file.stem
            and row["schema_version"]==3
            and row["new_review_send_authorized"] is False
            and row["independent_academic_QA_complete"] is False
            and row["student_publication_authorized"] is False,
            "Original V3 is not a directly approved model-Send instruction")
    item=plan(folder=folder,queue_root=queue_root,
              slide=row["original_slide"],
              utterance_id=row["original_utterance_id"])
    preflight=source_preflight(
        folder=folder,queue_root=queue_root,item=item)
    observed=ranked_stage(
        folder=folder,queue_root=queue_root,item=item,
        source_preflight=preflight)
    require(Path(observed["receipt"])==candidate_file
            and observed["scope_sha256"]==row["scope_sha256"]
            and observed["new_review_send_authorized"] is False,
            "Original V3 physical textbook source proof changed")
    job=row["source_science_review_job"]
    require(job["source_sha256"]==_sha(folder/"source.pdf")
            and job["slides_sha256"]==_sha(folder/"slides.pdf")
            and job["script_sha256"]==_sha(folder/"script.txt")
            and len(job["slides"])==1
            and len(job["slides"][0]["utterances"])==1
            and len(job["slides"][0]["visual_targets"])==1
            and job["slides"][0]["utterances"][0]["id"]==
                row["original_utterance_id"]
            and job["slides"][0]["visual_targets"][0]["id"]==
                row["corrected_ranked_physical_target_id"]
            and job["academic_approval"] is False
            and job["student_publication_authorized"] is False,
            "Original publisher/narration/physical target V3 job drift")
    for mode,key in (("INITIAL_REVIEW","new_initial_prompt_sha256"),
                     ("INDEPENDENT_CHALLENGE",
                      "new_challenge_prompt_sha256")):
        require(hashlib.sha256(
            review_instructions(job,mode=mode).encode("utf8")
            ).hexdigest()==row[key],
            "Original V3 canonical saved prompt SHA changed")
    return row,job


def _saved_initial(*,review_root:Path,folder:Path,job:dict)->bool:
    request=review_root/"initial_request"
    if not request.exists():
        return False
    require(request.is_dir() and not request.is_symlink(),
            "Invalid original V3 first-pass checkpoint")
    state=_load(request)
    expected=fingerprint(
        request_text=review_instructions(job,mode="INITIAL_REVIEW"),
        source_hashes={n:job[n.replace(".pdf","")+"_sha256"]
            if n!="script.txt" else job["script_sha256"]
            for n in ("source.pdf","slides.pdf","script.txt")},
        review_mode="INITIAL_REVIEW")
    require(state["request_fingerprint"]==expected
            and state["status"]=="SOURCE_VALIDATED_ONE_PASS_UNAPPROVED"
            and (request/"model_response_untrusted.txt").is_file(),
            "Old V3 initial model Send is uncertain or invalid; no replay")
    validated=validate_saved(
        checkpoint=request,expected_fingerprint=expected,
        validator=lambda raw:validate_source_demoted_review(
            folder=folder,job=job,
            response=decode_storyboard_response(raw),
            mode="INITIAL_REVIEW"),
        required_model_family="neon")
    require(validated["mode"]=="INITIAL_REVIEW",
            "Actual original V3 first review not source-validated")
    return True


def _inspect_under_owner_lock(*,folder:Path,queue_root:Path,candidate_file:Path,
            campaign_id:str,mode:str="INITIAL_REVIEW",
            execute:bool=False,authorized:bool=False,
            health_result:Path|None=None,reviewer=None)->dict:
    require(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
            "Source-specific V3 owned reviewer handoff not registered")
    require(mode in MODE and type(execute) is bool
            and type(authorized) is bool,
            "V3 model review must explicitly select a valid mode")
    folder,queue_root=Path(folder).absolute(),Path(queue_root).absolute()
    row,job=_verify(
        folder=folder,queue_root=queue_root,candidate_file=candidate_file)
    import re
    require(type(campaign_id) is str and
            re.fullmatch("[A-Za-z0-9][A-Za-z0-9_-]{2,63}",campaign_id),
            "Existing authorized finite G2 science campaign ID required")
    home=queue_root/"autonomous_recovery_continuation_v1"/campaign_id
    header=home/"campaign.json"
    require(header.is_file() and not header.is_symlink(),
            "Never create a new campaign to evade exhausted old Send budget")
    previous=json.loads(header.read_text("utf8"))
    cap=previous.get("max_possible_model_sends")
    require(type(cap) is int and 0<=cap<=6,
            "Original G2 science possible-Send cap is untrusted")
    home,original,events=_campaign(
        root=queue_root/"autonomous_recovery_continuation_v1",
        campaign_id=campaign_id,source_sha=job["source_sha256"],
        queue_sha=_sha(queue_root/"queue.json"),max_sends=cap)
    used=_possible_sends(events)
    scope=row["scope_sha256"]
    review_root=queue_root.parent/ROOT/scope
    require(not review_root.is_symlink()
            and not review_root.is_relative_to(folder)
            and not review_root.is_relative_to(queue_root),
            "New V3 review scope cannot modify old source or old model claims")
    status="G2_V3_INDEPENDENT_REVIEW_AWAITING_EXISTING_SEND_BUDGET_NO_SEND"
    phase=MODE[mode]
    def report(status,*,reserved=0):
        return {"status":status,"scope_sha256":scope,
            "original_utterance_id":row["original_utterance_id"],
            "original_corrected_physical_target_id":
                row["corrected_ranked_physical_target_id"],
            "mode":mode,"original_immutable_campaign":campaign_id,
            "original_campaign_possible_sends_reserved":used,
            "original_campaign_cap":cap,
            "new_browser_sends_reserved":reserved,
            "paid_gemini_API_calls":0,
            "original_historical_requests_replayed":False,
            "independent_two_pass_science_accepted":False,
            "student_publication_authorized":False}
    if used>=cap or _reservation(events,scope,phase):
        return report(status)
    if mode=="INDEPENDENT_CHALLENGE" and not _saved_initial(
            review_root=review_root,folder=folder,job=job):
        return report("G2_V3_INITIAL_SOURCE_REVIEW_MISSING_NO_CHALLENGE_SEND")
    if not execute or not authorized:
        return report("G2_V3_NEW_DISTINCT_MODEL_INPUT_READY_NO_SEND")
    old_claim=(queue_root/
        f"slide_{row['original_slide']:03d}_initial_review_attempt_01_request"/
        "dispatch_attempted.claim")
    if health_result is None:
        return report("G2_V3_FRESH_OWNED_NEON_HEALTH_REQUIRED_NO_SEND")
    _health_ok(
        health_result=Path(health_result),queue_root=queue_root,
        source_sha=job["source_sha256"],old_claim=old_claim,family="neon")
    request=review_root/(
        "initial_request" if mode=="INITIAL_REVIEW" else "challenge_request")
    # Any prior possibly sent request cannot simply be sent again, even when
    # a new day, source-free health or a different campaign would be available.
    if request.exists():
        return report("G2_V3_PRIOR_MODEL_REQUEST_MUST_RECONCILE_NO_REPLAY")
    events=_append(
        home,original,events,"RESERVE",scope=scope,phase=phase,
        detail=row["original_utterance_id"])
    used=_possible_sends(events)
    try:
        review_root.mkdir(parents=True,exist_ok=True)
        with _owned_neon_high():
            (reviewer or run_web_review)(
                folder=folder,job=job,mode=mode,
                checkpoint_dir=request,chrome_port=9222,wait_cap_s=240,
                required_model_family="neon")
        state=_load(request)
        require(state["status"]=="SOURCE_VALIDATED_ONE_PASS_UNAPPROVED",
                "Model response not source-validated and persisted")
        events=_append(home,original,events,"RESULT",
            scope=scope,phase=phase,
            detail="V3_ONE_PASS_SOURCE_VALIDATED_UNAPPROVED")
        return report("G2_V3_MODEL_ONE_PASS_SOURCE_VALIDATED_UNAPPROVED",
                      reserved=1)
    except Exception as exc:
        # A failure after RESERVE can mean the request was submitted. HOLD
        # consumes that possible Send and prevents future automatic replay.
        _append(home,original,events,"HOLD",
                scope=scope,phase=phase,detail=type(exc).__name__[:120])
        return report("G2_V3_MODEL_ATTEMPT_UNCERTAIN_HOLD_NO_REPLAY",
                      reserved=1)


def inspect(*,folder:Path,queue_root:Path,candidate_file:Path,
            campaign_id:str,mode:str="INITIAL_REVIEW",
            execute:bool=False,authorized:bool=False,
            health_result:Path|None=None,reviewer=None)->dict:
    """Share the SAME exclusive G2 original-supervisor Send ownership lock.

    Otherwise two processes can both observe spare budget before reserving,
    or two independently prepared V3 sources can interleave possible Sends.
    Held tasks remain unchanged when the owner is already running.
    """
    queue_root=Path(queue_root).absolute()
    lock_name="g2_qa_"+hashlib.sha256(
        str(queue_root).encode("utf8")).hexdigest()[:20]
    with LocalInstanceLock(
            lock_name,queue_root/".microgen_g2_supervisor_locks"):
        return _inspect_under_owner_lock(
            folder=folder,queue_root=queue_root,candidate_file=candidate_file,
            campaign_id=campaign_id,mode=mode,execute=execute,
            authorized=authorized,health_result=health_result,
            reviewer=reviewer)


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--folder",required=True,type=Path)
    p.add_argument("--queue-root",required=True,type=Path)
    p.add_argument("--candidate-file",required=True,type=Path)
    p.add_argument("--campaign-id",required=True)
    p.add_argument("--review-mode",choices=list(MODE),default="INITIAL_REVIEW")
    p.add_argument("--execute",action="store_true")
    p.add_argument("--authorize-owned-selenium-science",action="store_true")
    p.add_argument("--health-result",type=Path)
    args=p.parse_args(argv)
    result=inspect(
        folder=args.folder,queue_root=args.queue_root,
        candidate_file=args.candidate_file,campaign_id=args.campaign_id,
        mode=args.review_mode,execute=args.execute,
        authorized=args.authorize_owned_selenium_science,
        health_result=args.health_result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
