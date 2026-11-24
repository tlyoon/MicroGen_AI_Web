"""Bounded two-pass G3 source-semantic review of one NEW original utterance.

Requires a genuinely distinct task from the rejected whole-slide original
Gemini response, exact publisher quote witness and separately owned,
fresh Neon/High *source-free* browser health. Uses the shared academic
one-Send checkpoint for each of two independent passes. Neither pass,
nor their mutual agreement, alters the old G3 acceptance, acoustic,
highlight/video or student publication.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

from .g3_semantic_source_repair_v1 import (
    _verified_packet, _one_unit, _canon, _sha, _read, need)
from .g3_semantic_neon_health_v1 import latest as qualified_health
from .g2_distinct_focused_source_review_v1 import (
    _last_original_gemini_quarantine_mtime)
from .autonomous_recovery_continuation_v1 import (
    _campaign,_append,_possible_sends,_reservation)
from .ai_academic_web_review import (
    run_web_review, review_instructions, validate_source_demoted_review)
from .ai_academic_review_consensus import (
    _actual_model_rows,_independently_check_saved_pass,
    _canonical_academic_rationale)
from .academic_review_checkpoint import (
    _load,fingerprint,validate_saved,recover_claimed_observation)
from .series_gemini import decode_storyboard_response
from . import g3_rich_mapping_auto_continuation_v71 as reviewer
from .recovery_registry import lookup_mechanism

KIND="g3_distinct_semantic_science"
SIGNATURE="G3_DISTINCT_ORIGINAL_UTTERANCE_NEEDS_TWO_INDEPENDENT_SOURCE_REVIEWS"
MECHANISM="ONCE_ONLY_NEON_SCIENCE_PASSES_WITH_BOUND_SOURCE_CLAIMS_AND_NO_RELEASE"
REPORT="G3_DISTINCT_SEMANTIC_TWO_PASS_SCIENCE_AI_EVIDENCE_NO_ORIGINAL_PROMOTION"


def _pinned_task(*,spec:dict,worklist_root:Path,task_file:Path)->dict:
    task_file=Path(task_file).absolute()
    row=_read(task_file,limit=100_000)
    if row.get("status")=="G3_DISTINCT_EXAMPLE_CONTEXT_SCIENCE_REVIEW_READY_NO_SEND":
        from .g3_context_followup_task_v1 import pinned
        return pinned(spec=spec,state_root=Path(worklist_root).absolute().parent,
                      task_file=task_file)
    need(row.get("status")=="G3_DISTINCT_SOURCE_SEMANTIC_QA_READY_NO_SEND"
         and row.get("science_review_job") is not None
         and row.get("new_source_review_send_allowed_without_fresh_neon_health") is False
         and row.get("old_whole_slide_request_replayed") is False
         and row.get("independent_scientific_QA_complete") is False
         and row.get("student_publication_authorized") is False
         and row.get("section")==spec["section"]
         and task_file.name==row.get("scope_sha256","")+".json"
         and task_file.parent.name==spec["section"],
         "G3 science task must be a genuinely new original spoken unit")
    folder=Path(worklist_root).absolute()/spec["section"]
    need(folder.is_dir() and not folder.is_symlink(),
         "Missing original publisher worklist section")
    options=[p for p in folder.glob("slide_*.json")
             if p.is_file() and not p.is_symlink()
             and _sha(p)==row["source_worklist_sha256"]]
    need(len(options)==1,"Original source worklist hash not unique")
    packet,request=_verified_packet(spec=spec,worklist=options[0])
    old=[u for u in packet["publisher_quote_worklist"]
         if u["utterance_id"]==row["original_utterance_id"]]
    need(len(old)==1,"Original source-rejected narration no longer unique")
    expected=_one_unit(
        spec=spec,packet=packet,request=request,row=old[0],
        worklist_sha=_sha(options[0]))
    need(row==expected and task_file.read_bytes()==_canon(expected),
         "Distinct G3 source QA task differs from original publisher evidence")
    return row


def _saved(*,job:dict,folder:Path,path:Path,mode:str)->dict:
    """Revalidate exact previous model bytes, never issue another Send."""
    state=_load(path)
    hashes={name:job[name.split(".")[0]+"_sha256"] for name in
            ("source.pdf","slides.pdf","script.txt")}
    digest=fingerprint(request_text=review_instructions(job,mode=mode),
                       source_hashes=hashes,review_mode=mode)
    need(state.get("request_fingerprint")==digest,
         "Existing saved G3 science reviewer has a foreign source/prompt")
    if (state["status"] in (
         "SUBMITTED_OR_UNCERTAIN","NO_RESPONSE_UNRESOLVED")
         and (path/"model_response_identity.json").is_file()):
        recover_claimed_observation(
            checkpoint=path,expected_fingerprint=digest)
        state=_load(path)
    need(state.get("status") in (
        "MODEL_REPLY_OBSERVED_UNVALIDATED",
        "SOURCE_VALIDATED_ONE_PASS_UNAPPROVED"),
        "Uncertain G3 source reviewer claim cannot be replayed")
    return validate_saved(
        checkpoint=path,expected_fingerprint=digest,
        validator=lambda raw:validate_source_demoted_review(
            folder=folder,job=job,
            response=decode_storyboard_response(raw),mode=mode),
        required_model_family="neon")


def _after_incident(*,spec:dict)->float:
    """Recent possible original model Sends invalidate older health."""
    audited=Path(spec["review_root"])/"audited"
    need(audited.is_dir() and not audited.is_symlink(),
         "Original G3 pending Send claims unavailable")
    claims=list(audited.glob("slide_*.submission_held.json"))
    need(len(claims)<=120
         and all(p.is_file() and not p.is_symlink() for p in claims),
         "G3 historic browser claim inventory invalid")
    return max(_last_original_gemini_quarantine_mtime(),
               max((x.stat().st_mtime for x in claims),default=0.0))


def _agreement(*,folder:Path,job:dict,first:dict,second:dict,
               checkpoint_initial:Path,checkpoint_challenge:Path,
               source_scope:str)->dict:
    a=_independently_check_saved_pass(
        folder=folder,job=job,record=first,mode="INITIAL_REVIEW")
    b=_independently_check_saved_pass(
        folder=folder,job=job,record=second,mode="INDEPENDENT_CHALLENGE")
    need(_actual_model_rows(first,a)==_actual_model_rows(second,b)==1,
         "Two actual independently saved G3 model science reviews required")
    x,y=a[0],b[0]
    unit=job["slides"][0]["utterances"][0]
    need(x["utterance_id"]==y["utterance_id"]==unit["id"]
         and x["spoken_sha256"]==y["spoken_sha256"]==unit["spoken_sha256"],
         "G3 source math reviewers changed original narration identity")
    raw1=checkpoint_initial/"model_response_untrusted.txt"
    raw2=checkpoint_challenge/"model_response_untrusted.txt"
    need(raw1.is_file() and raw2.is_file()
         and not raw1.is_symlink() and not raw2.is_symlink(),
         "Independent original browser response text missing")
    sha1,sha2=_sha(raw1),_sha(raw2)
    need(sha1!=sha2,
         "Two identical raw answers are not independent science arguments")
    agree=bool(
        x["verdict"]==y["verdict"]=="SUPPORTED"
        and x["target_id"]==y["target_id"] is not None
        and x["source_page"]==y["source_page"]
        and x["exact_textbook_quote_verified"] is True
        and y["exact_textbook_quote_verified"] is True
        and _canonical_academic_rationale(x["math_explanation"])!=
            _canonical_academic_rationale(y["math_explanation"]))
    return {
        "schema_version":1,
        "status":(
            REPORT if agree else
            "G3_DISTINCT_SEMANTIC_SOURCE_AI_DISPUTED_NO_PROMOTION"),
        "scope_sha256":source_scope,
        "source_sha256":job["source_sha256"],
        "original_utterance_id":unit["id"],
        "original_spoken_sha256":unit["spoken_sha256"],
        "first_owned_source_review_sha256":sha1,
        "independent_challenge_owned_response_sha256":sha2,
        "two_distinct_review_modes":True,
        "two_actual_model_scientific_reviews":True,
        "physical_source_quote_in_both":bool(
            x["exact_textbook_quote_verified"] and
            y["exact_textbook_quote_verified"]),
        "science_AI_source_agreed":agree,
        "original_G3_semantic_mappings_promoted":0,
        "independent_scientific_QA_human_attestation":False,
        "independent_acoustic_QA_complete":False,
        "video_and_highlights_accepted":False,
        "student_publication_authorized":False,
        "new_provider_requests_during_reconciliation":0,
        "paid_gemini_API_calls":0,
    }


def run_one(*,spec:dict,task_file:Path,
            worklist_root:Path,state_root:Path,
            campaign_id:str,max_possible_sends:int=2,
            execute:bool=False,transport=None)->dict:
    need(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
         "G3 independent source science controller not in recovery registry")
    need(type(execute) is bool
         and type(max_possible_sends) is int
         and 0<=max_possible_sends<=2,
         "Source math two-pass campaign has finite possible Sends")
    state_root=Path(state_root).absolute()
    need(state_root.is_dir() and not state_root.is_symlink(),
         "No isolated real G3 campaign owner")
    with reviewer._exclusive(state_root):
        task=_pinned_task(spec=spec,worklist_root=worklist_root,
                          task_file=task_file)
        scope=task["scope_sha256"]
        context=task["status"]=="G3_DISTINCT_EXAMPLE_CONTEXT_SCIENCE_REVIEW_READY_NO_SEND"
        job=task["review_job"] if context else task["science_review_job"]
        source=Path(spec["source_folder"]).absolute()
        root=state_root/(
            "g3_distinct_example_context_reviews_v1" if context else
            "g3_distinct_semantic_science_reviews_v1")/scope
        need(not root.is_symlink() and not root.is_relative_to(source),
             "Redirected G3 scientific review owner")
        root.mkdir(parents=True,exist_ok=True)
        campaign,header,events=_campaign(
            root=root,campaign_id=campaign_id,
            source_sha=job["source_sha256"],
            queue_sha=task["source_worklist_sha256"],
            max_sends=max_possible_sends)
        phases=(("INITIAL","INITIAL_REVIEW","initial_request"),
                ("CHALLENGE","INDEPENDENT_CHALLENGE","challenge_request"))
        passes={}
        status="G3_DISTINCT_SCIENCE_TASK_HEALTH_GATE_NOT_MET"
        progress=[]
        for phase,mode,name in phases:
            checkpoint=root/name
            if checkpoint.exists():
                try:
                    passes[mode]=_saved(
                        job=job,folder=source,path=checkpoint,mode=mode)
                    progress.append({"phase":phase,"status":"SAVED_SOURCE_MODEL_REVALIDATED_NO_SEND"})
                    continue
                except Exception as exc:
                    status="G3_DISTINCT_SCIENCE_UNCERTAIN_NO_REPLAY"
                    progress.append({"phase":phase,
                                     "error_class":type(exc).__name__,
                                     "new_model_requests":0})
                    break
            if not execute:
                status="G3_DISTINCT_SCIENCE_AWAITING_AUTHORIZED_EXECUTION"
                break
            if (_possible_sends(events)>=max_possible_sends
                or _reservation(events,scope,phase)):
                status="G3_DISTINCT_SCIENCE_BUDGET_OR_CLAIM_EXHAUSTED_NO_REPLAY"
                break
            proof=qualified_health(root=state_root,
                source_sha=job["source_sha256"],
                after_unix=_after_incident(spec=spec))
            if proof is None:
                status="G3_DISTINCT_SCIENCE_FRESH_NEON_HEALTH_REQUIRED"
                break
            events=_append(campaign,header,events,"RESERVE",
                           scope=scope,phase=phase,detail=task["original_utterance_id"])
            try:
                from .g3_bounded_owned_browser_window_v1 import (
                    bounded_science_response)
                with bounded_science_response(absolute_max_seconds=180):
                    result=run_web_review(
                        folder=source,job=job,mode=mode,
                        checkpoint_dir=checkpoint,
                        required_model_family="neon",
                        wait_cap_s=120,transport=transport)
                need(result["status"]=="SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS"
                     and result["review_count"]==1
                     and result["academic_mathematics_independently_verified"] is False
                     and result["student_publication_authorized"] is False,
                     "One source-AI reply is never academic acceptance")
                passes[mode]=result
                events=_append(campaign,header,events,"RESULT",
                               scope=scope,phase=phase,detail=result["status"])
                progress.append({"phase":phase,"status":result["status"],
                                 "one_possible_browser_send_reserved":True})
                status="G3_DISTINCT_SCIENCE_ONE_PASS_UNAPPROVED"
            except Exception as exc:
                events=_append(campaign,header,events,"HOLD",
                               scope=scope,phase=phase,
                               detail=type(exc).__name__[:125])
                status="G3_DISTINCT_SCIENCE_FAILED_OR_UNCERTAIN_NO_REPLAY"
                progress.append({"phase":phase,
                                 "error_class":type(exc).__name__,
                                 "one_possible_browser_send_reserved":True})
                break
        report=None
        semantic_context=None
        if all(mode in passes for _,mode,_ in phases):
            report=_agreement(
                folder=source,job=job,
                first=passes["INITIAL_REVIEW"],
                second=passes["INDEPENDENT_CHALLENGE"],
                checkpoint_initial=root/"initial_request",
                checkpoint_challenge=root/"challenge_request",
                source_scope=scope)
            from .g3_semantic_source_repair_v1 import _write_once
            if context:
                report={
                    **report,
                    "status":("G3_DISTINCT_CONTEXT_SOURCE_AI_AGREEMENT_UNAPPROVED"
                              if report["science_AI_source_agreed"] else
                              "G3_DISTINCT_CONTEXT_SOURCE_AI_DISPUTED_NO_PROMOTION"),
                    "parent_original_review_scope_sha256":
                        task["parent_original_task_scope_sha256"],
                    "context_science_candidate_is_not_semantic_proof":True,
                    "original_G3_semantic_mappings_promoted":0,
                    "student_publication_authorized":False,
                }
            _write_once(root/"two_pass_science_evidence.json",report)
            if not context:
                # A physically present publisher quote may still be
                # unrelated. Two independently unresolved reviewers trigger
                # new offline context retrieval, never another old Send.
                from .g3_semantic_context_recovery_v2 import recover
                semantic_context=recover(
                    folder=source,task=task,review_root=root)
                need(semantic_context["new_gemini_browser_sends"]==0
                     and semantic_context["student_publication_authorized"] is False
                     and semantic_context["original_G3_semantic_mappings_promoted"]==0,
                     "Offline textbook context cannot bypass G3 scientific QA")
            status=report["status"]
        return {
            "schema_version":1,"status":status,
            "source_scope_sha256":scope,
            "original_utterance_id":task["original_utterance_id"],
            "campaign_id":campaign_id,
            "max_possible_sends":max_possible_sends,
            "possible_sends_reserved":_possible_sends(events),
            "stage_results":progress,
            "two_pass_science_evidence":report,
            "semantic_context_recovery":semantic_context,
            "original_historical_request_replayed":False,
            "old_G3_semantic_mappings_promoted":0,
            "independent_scientific_QA_human_attestation":False,
            "independent_acoustic_QA_complete":False,
            "video_and_highlights_accepted":False,
            "student_publication_authorized":False,
            "paid_gemini_API_calls":0,
        }


def main(argv:list[str]|None=None)->int:
    """Single foreground G3 source-first, finite auto-review handoff.

    Re-run the original offline G3 source stage before selecting exactly
    one remaining distinct scientific task. No background scheduling or
    implicit source-textbook Send. The selected task advances both distinct
    reviewer passes automatically within its at-most-two-Send budget.
    """
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",required=True,type=Path)
    parser.add_argument("--state-dir",required=True,type=Path)
    parser.add_argument("--campaign-id",required=True)
    parser.add_argument("--section",default=None)
    parser.add_argument("--utterance-id",default=None)
    parser.add_argument("--max-possible-sends",type=int,default=0)
    parser.add_argument("--execute",action="store_true")
    a=parser.parse_args(argv)
    from .g3_multisection_autoforward_v71 import (
        _verified_specs,run_campaign)
    offline=run_campaign(
        manifest=a.manifest,state_dir=a.state_dir,
        max_new_sends=0,auto_offline_repair=True,
        auto_semantic_source_repair=True)
    need(offline["new_browser_dispatch_attempts_this_run"]==0
         and offline["student_publication_authorized"] is False
         and offline["semantic_source_recovery"]["new_browser_sends"]==0,
         "Original G3 uncertain browser claims must not be replayed")
    _,specs=_verified_specs(a.manifest)
    root=Path(a.state_dir).absolute()
    candidates=[]
    for spec in specs:
        folder=root/"g3_distinct_semantic_science_tasks_v1"/spec["section"]
        if not folder.is_dir():
            continue
        for file in folder.glob("*.json"):
            t=_read(file)
            if t.get("status")!="G3_DISTINCT_SOURCE_SEMANTIC_QA_READY_NO_SEND":
                continue
            if a.section is not None and spec["section"]!=a.section:
                continue
            if a.utterance_id is not None and t["original_utterance_id"]!=a.utterance_id:
                continue
            result_root=(root/"g3_distinct_semantic_science_reviews_v1"/
                         t["scope_sha256"])
            if (result_root/"two_pass_science_evidence.json").exists():
                continue
            candidates.append((spec["section"],t["original_rejected_slide"],
                               t["original_utterance_id"],spec,file))
    candidates.sort(key=lambda r:(r[0],r[1],r[2]))
    if not candidates:
        report={
            "status":"NO_ELIGIBLE_NEW_G3_SOURCE_SEMANTIC_REVIEW",
            "original_G3_requests_replayed":False,
            "new_provider_requests":0,
            "student_publication_authorized":False,
        }
    else:
        _section,_slide,_uid,spec,path=candidates[0]
        report=run_one(
            spec=spec,task_file=path,
            worklist_root=root/"offline_source_quote_worklists_v2",
            state_root=root,
            campaign_id=a.campaign_id,
            max_possible_sends=a.max_possible_sends,
            execute=a.execute)
    print(json.dumps(report,sort_keys=True,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
