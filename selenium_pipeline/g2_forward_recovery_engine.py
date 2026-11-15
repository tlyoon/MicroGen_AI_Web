"""Executable G2 classify -> recover -> verify -> persist -> advance engine.

This is the normal ONE-LAUNCH forward workflow. It calls the real original
source-bound G2 supervisor, which itself rechecks the academic queue, Gemini
one-Send claims, source/citation/Thinking, paid TTS guard and media evidence.
A completed recovery immediately starts the next independently eligible stage
within a *finite* 32-operation campaign, without a Windows scheduled task.

Never infer academic acceptance from script QA, model replies, provider health,
machine UNRESOLVED placeholders, WAV file existence or MP4 appearance.
A health-unqualified Gemini Send, ambiguous Send, missing independent citation,
or unauthorized paid operation is a terminal blocker for THIS invocation.
No automatic retry of an uncertain original request.  A crashed iteration
is source-reinspected and source-claim selection is delegated to the existing
immutable review queue; never replay the original Send.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Callable

from .evidence_reuse_contract import file_sha256
from .original_multisource_recovery_campaign import require


MAX_CYCLES_PER_INVOCATION=32
MAX_PERSISTED_CYCLES=256

_RESOLUTIONS={
    "FRESH_FIRST_ATTEMPT":"ORIGINAL_SOURCE_BOUND_ONE_SHOT_ACADEMIC_GEMINI",
    "RECONCILE_PRIOR_RESPONSE_NO_SEND":
        "SHA_LOCKED_SOURCE_CITATION_DOWNGRADE_AND_LOCAL_REPLY_RECONCILIATION",
    "PREPARED_UNSENT_NO_DUPLICATE":
        "VERIFY_OLD_EXCLUSIVE_CLAIM_AND_CERTIFIED_NO_SEND",
}
_DEFERRED={
    "G2_PROVIDER_HEALTH_DEFERRED_NO_NEW_SOURCE_SEND":
        "AWAIT_VERIFIED_NEWER_SOURCE_FREE_MODEL_RESPONSE",
    "G2_SOURCE_REVIEW_PASSED_COMPLEX_ELEMENT_AUDIO_ROUTE_REQUIRED":
        "SOURCE_GEOMETRY_EVIDENCE_NOT_UNIQUELY_RESOLVED",
    "G2_AUTONOMOUS_SUPERVISOR_SOURCE_GATE_BLOCKED":
        "ORIGINAL_SOURCE_SHA_OR_PROVENANCE_OR_APPROVAL_BLOCKED",
    "G2_MEDIA_GENERATED_AWAITING_INDEPENDENT_ACOUSTIC_QA":
        "INDEPENDENT_ACOUSTIC_AND_VIDEO_ACCEPTANCE_REQUIRED",
}
_TERMINAL_ATTEMPTS={
    "BOUNDED_REVIEW_STOPPED_NOT_READY",
    "BOUNDED_REVIEW_STOPPED_AFTER_UNACCEPTED_UNIT",
}
_DONE_ACCEPTED="GEMINI_SOURCE_REVIEW_ONE_SLIDE_COMPLETED"


def _sha(path:Path)->str:
    return file_sha256(path)


def _json_file(path:Path) -> dict:
    require(path.is_file() and not path.is_symlink()
            and 0<path.stat().st_size<=2_000_000,
            "Missing/linked/oversized original forward decision")
    obj=json.loads(path.read_text(encoding="utf8"))
    require(type(obj) is dict and obj.get("schema_version")==1,
            "Invalid original forward decision")
    return obj


def _new_json(path:Path,value:dict)->None:
    require(not path.exists() and not path.is_symlink(),
            "Original immutable forward receipt would be overwritten")
    raw=(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)
         +"\n").encode("utf8")
    require(len(raw)<=2_000_000,"Forward receipt contains unbounded output")
    with path.open("xb") as out:
        out.write(raw)
        out.flush()
        os.fsync(out.fileno())


def _source_lock(folder:Path,queue_root:Path)->dict:
    from .windows_g2_autonomous_qa_supervisor import _is_verified_folder
    _,hashes=_is_verified_folder(folder,queue_root)
    return hashes


def _home(*,folder:Path,queue_root:Path,work_root:Path)->Path:
    folder,queue_root,work_root=(Path(p).absolute()
                                 for p in (folder,queue_root,work_root))
    require(work_root.is_dir() and not work_root.is_symlink()
            and not work_root.is_relative_to(folder)
            and not queue_root.is_relative_to(work_root/"g2_forward_recovery_v1"),
            "G2 forward journal must not mutate original teaching files")
    sha=_source_lock(folder,queue_root)["source.pdf"]
    key=hashlib.sha256((str(queue_root)+"|"+str(folder)).encode("utf8")
                       ).hexdigest()[:16]
    location=work_root/"g2_forward_recovery_v1"/(sha[:16]+"_"+key)
    require(not location.is_symlink() and not location.parent.is_symlink(),
            "Unsafe recovery journal symlink")
    location.mkdir(parents=True,exist_ok=True)
    return location


def _recover_history(home:Path,hashes:dict,source:Path,queue:Path,
                     work_root:Path,health_family:str,auto_media:bool,
                     inspect:Callable)->tuple[int,str|None]:
    """Verify the exact chain; repair a torn stage by READ-ONLY inspection."""
    intents=sorted(home.glob("[0-9][0-9][0-9][0-9].intent.json"))
    results=sorted(home.glob("[0-9][0-9][0-9][0-9].result.json"))
    require(len(intents)<=MAX_PERSISTED_CYCLES
            and len(results)<=MAX_PERSISTED_CYCLES,
            "Forward checkpoint exceeded finite persistence cap")
    expected_no=1
    previous=None
    for intent_path in intents:
        matched=re.fullmatch(r"([0-9]{4})\.intent\.json",intent_path.name)
        require(matched is not None and int(matched[1])==expected_no,
                "Out-of-order non-atomic forward stage history")
        intent=_json_file(intent_path)
        require(intent.get("original_source_sha256")==hashes["source.pdf"]
                and intent.get("original_slides_sha256")==hashes["slides.pdf"]
                and intent.get("original_script_sha256")==hashes["script.txt"]
                and intent.get("original_source_folder")==str(source)
                and intent.get("original_review_queue")==str(queue)
                and intent.get("prior_result_sha256")==previous
                and intent.get("stage_classification") in (
                    "SOURCE_CITED_ACADEMIC_REVIEW",
                    "TWO_PASS_SOURCE_QA_TO_PRODUCTION_MEDIA"),
                "Forward decision/source/previous-stage SHA changed")
        result_path=home/f"{expected_no:04d}.result.json"
        if not result_path.is_file():
            require(expected_no==len(intents)
                    and not result_path.exists() and not result_path.is_symlink(),
                    "Only final crashed stage may be restored")
            # This can be run again across process deaths. It performs no
            # Gemini Send, no new TTS, no video, and does NOT certify completion.
            observed=inspect(folder=source,queue_root=queue,work_root=work_root,
                             health_family=health_family,auto_media=auto_media,
                             execute=False,max_units=0)
            require(type(observed) is dict and observed.get(
                "original_source_sha256")==hashes["source.pdf"],
                "Cracked source checkpoint cannot be read-only recovered")
            _new_json(result_path,{
                "schema_version":1,
                "status":"CRASHED_STAGE_SOURCE_REINSPECTED_NO_PROVIDER_REPLAY",
                "intent_sha256":_sha(intent_path),
                "actual_report":observed,
                "model_submission_outcome_unknown":True,
                "source_request_retried":False,
                "academic_and_media_success_claimed":False,
            })
        result=_json_file(result_path)
        require(result.get("intent_sha256")==_sha(intent_path)
                and type(result.get("actual_report")) is dict
                and result["actual_report"].get(
                    "original_source_sha256")==hashes["source.pdf"],
                "Last cycle result not source-and-intent bound")
        previous=_sha(result_path)
        expected_no+=1
    require(len(results)<=len(intents),
            "Orphan result without preceding original intent")
    return expected_no,previous


def _decision(report:dict, prior:dict)->tuple[str,str,bool]:
    """Stable classifier, no unsafe optimism from a model receipt label."""
    status=report.get("status")
    selection=report.get("next_safe_academic_action") or {}
    attempt=report.get("bounded_review_attempt") or {}
    if status in _DEFERRED:
        return ("HALT",_DEFERRED[status],False)
    if status=="G2_ACADEMIC_TWO_PASS_SOURCE_QA_READY_FOR_REAL_AUDIO":
        return ("HALT","SOURCE_ACADEMIC_PASS_BUT_MEDIA_NOT_AUTHORIZED_OR_DISABLED",
                False)
    if status=="G2_ACADEMIC_QA_INCOMPLETE_REVIEW_OR_SOURCE_REPAIR":
        new_selection=selection.get("action")
        review=attempt.get("stop_evidence",{}).get("review",{})
        completed=attempt.get("completed") or []
        if (type(completed) is list and completed
                and all(type(x) is dict and x.get("receipt_sha256")
                        for x in completed)):
            if selection.get("status")=="ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY":
                return ("CONTINUE","PREVIOUS_SOURCE_VERIFIED_STAGE_ACCEPTED",True)
            return ("HALT","NO_MORE_SOURCE_BOUND_REVIEW_OPERATIONS",False)
        if (attempt.get("status") in _TERMINAL_ATTEMPTS
                and selection.get("status")=="ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY"
                and new_selection=="RECONCILE_PRIOR_RESPONSE_NO_SEND"):
            return ("CONTINUE","RECONCILE_IMMUTABLE_MODEL_REPLY_WITHOUT_RESEND",True)
        if (attempt.get("status")=="BOUNDED_REVIEW_STOPPED_AFTER_UNACCEPTED_UNIT"
                and selection.get("status")=="ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY"
                and selection.get("next_slide") != prior.get("next_slide")):
            # The original Send is unknown. Exactly one next cycle may do
            # independent provider-health preflight and halt if not proven.
            return ("CONTINUE","NEXT_ELIGIBLE_SLIDE_REQUIRES_PROVIDER_HEALTH",True)
        if not attempt and selection.get("status")=="ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY":
            return ("HALT","NO_NEW_ACCEPTED_STAGE_THIS_CYCLE",False)
        return ("HALT","ACADEMIC_UNIT_BLOCKED_OR_UNRESOLVED_NO_RETRY",False)
    return ("HALT","UNRECOGNIZED_STAGE_REQUIRES_EXPLICIT_SOURCE_EVIDENCE",False)


def run(*,folder:Path,queue_root:Path,work_root:Path,
        execute:bool=False,max_cycles:int=MAX_CYCLES_PER_INVOCATION,
        health_family:str="pro",auto_media:bool=True,
        supervisor:Callable|None=None)->dict:
    """Continue every genuinely eligible stage now; stop at a proven blocker.

    No separate scheduled task or background dependency is installed.
    """
    require(type(execute) is bool and type(auto_media) is bool
            and type(max_cycles) is int and 1<=max_cycles<=MAX_CYCLES_PER_INVOCATION
            and health_family in ("flash","pro"),
            "Finite stage budget and verified Gemini family required")
    folder,queue_root,work_root=(Path(p).absolute()
                                 for p in (folder,queue_root,work_root))
    from .windows_g2_autonomous_qa_supervisor import step
    invoke=supervisor or step
    from .three_pc_worker import LocalInstanceLock
    digest=hashlib.sha256(str(queue_root).encode("utf8")).hexdigest()[:20]
    with LocalInstanceLock("g2_forward_"+digest,
                           work_root/".microgen_g2_forward_locks"):
        hashes=_source_lock(folder,queue_root)
        home=_home(folder=folder,queue_root=queue_root,work_root=work_root)
        # Existing explicit native read-only supervisor; never overwrite
        # a historical request claim to resume a crashed controller process.
        def inspect(**kw):
            return invoke(**kw)
        next_no,previous=_recover_history(
            home,hashes,folder,queue_root,work_root,health_family,
            auto_media,inspect)
        if not execute:
            report=invoke(folder=folder,queue_root=queue_root,
                          work_root=work_root,execute=False,max_units=0,
                          health_family=health_family,auto_media=auto_media)
            return {
                "status":"READONLY_G2_FORWARD_RECOVERY_PLAN",
                "journal":str(home),
                "recovered_cycles":next_no-1,
                "current_report":report,
                "new_provider_requests":False,
                "new_paid_tts_dispatched":False,
            }
        completed=[]
        for _ in range(max_cycles):
            require(next_no<=MAX_PERSISTED_CYCLES,
                    "Forward journal exhausted, prevent infinite stage loop")
            # A one-cycle supervisor stages original media only AFTER exact
            # source and independent science proof. One model Send maximum.
            from .ai_academic_review_queue import select_next_safe_review
            selection=select_next_safe_review(queue_root=queue_root,folder=folder)
            media_only=selection.get("status") != "ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY"
            kind=("TWO_PASS_SOURCE_QA_TO_PRODUCTION_MEDIA" if media_only else
                  "SOURCE_CITED_ACADEMIC_REVIEW")
            intent_path=home/f"{next_no:04d}.intent.json"
            _new_json(intent_path,{
                "schema_version":1,"original_source_folder":str(folder),
                "original_review_queue":str(queue_root),
                "original_source_sha256":hashes["source.pdf"],
                "original_slides_sha256":hashes["slides.pdf"],
                "original_script_sha256":hashes["script.txt"],
                "prior_result_sha256":previous,
                "stage_classification":kind,
                "selected_original_slide":selection.get("next_slide"),
                "selected_original_mode":selection.get("next_mode"),
                "recovery_mechanism":_RESOLUTIONS.get(
                    selection.get("action"),
                    "REVALIDATE_TWO_PASS_SOURCE_CONSENSUS_OR_STOP"),
                "never_resend_ambiguous_claim":True,
                "paid_operations_subject_to_existing_tts_cost_guard":True,
                "student_publication_authorized":False,
            })
            try:
                report=invoke(
                    folder=folder,queue_root=queue_root,work_root=work_root,
                    execute=True,max_units=0 if media_only else 1,
                    health_family=health_family,auto_media=auto_media)
            except Exception as exc:
                # A process or provider failure may occur AFTER a Send;
                # record uncertainty, never grant retry or scientific QA.
                report={
                    "schema_version":1,
                    "status":"G2_AUTONOMOUS_SUPERVISOR_SOURCE_GATE_BLOCKED",
                    "original_source_sha256":hashes["source.pdf"],
                    "reason_type":type(exc).__name__,
                    "reason":str(exc)[:400],
                    "student_publication_authorized":False,
                    "provider_submission_may_have_occurred":True,
                }
            require(type(report) is dict and report.get(
                "original_source_sha256")==hashes["source.pdf"],
                "Supervisor yielded no original-source-bound result")
            require(_source_lock(folder,queue_root)==hashes,
                    "Protected lecture files altered during forward stage")
            action,diagnosis,can_advance=_decision(report,selection)
            receipt_path=home/f"{next_no:04d}.result.json"
            _new_json(receipt_path,{
                "schema_version":1,"status":"G2_STAGE_CLASSIFIED_AND_PERSISTED",
                "intent_sha256":_sha(intent_path),
                "actual_report":report,
                "next_action":action,
                "blocker_class_or_recovery":diagnosis,
                "automatically_continue_to_next_eligible":can_advance,
                "new_source_scientific_consensus_fabricated":False,
                "paid_operation_authorization_bypassed":False,
            })
            previous=_sha(receipt_path)
            completed.append({
                "ordinal":next_no,"action":action,
                "observed_stage":report.get("status"),
                "classification":diagnosis,
                "receipt_sha256":previous,
                "original_two_pass_agreed":
                    report.get("two_pass_ai_source_agreed_segments"),
                "original_pending_or_disputed":
                    report.get("pending_or_disputed_segments"),
            })
            next_no+=1
            if not can_advance:
                return {
                    "status":"G2_FORWARD_STOPPED_AT_VERIFIED_ELIGIBILITY_BOUNDARY",
                    "journal":str(home),
                    "stage_cycles_this_invocation":completed,
                    "last_stage":report,
                    "next_scheduled_task_created":False,
                    "G2_claimed_complete":False,
                }
        return {
            "status":"G2_FINITE_FORWARD_BUDGET_REACHED_CHECKPOINT_PRESERVED",
            "journal":str(home),
            "stage_cycles_this_invocation":completed,
            "next_scheduled_task_created":False,
            "G2_claimed_complete":False,
        }


def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder",type=Path,required=True)
    parser.add_argument("--queue-root",type=Path,required=True)
    parser.add_argument("--work-root",type=Path,required=True)
    parser.add_argument("--health-family",choices=("flash","pro"),default="pro")
    parser.add_argument("--max-cycles",type=int,default=MAX_CYCLES_PER_INVOCATION)
    parser.add_argument("--execute",action="store_true")
    parser.add_argument("--no-auto-media",action="store_true")
    args=parser.parse_args(argv)
    try:
        result=run(folder=args.folder,queue_root=args.queue_root,
                   work_root=args.work_root,execute=args.execute,
                   max_cycles=args.max_cycles,health_family=args.health_family,
                   auto_media=not args.no_auto_media)
    except Exception as exc:
        result={
            "status":"G2_FORWARD_BLOCKED_SOURCE_OR_JOURNAL_UNVERIFIED",
            "reason_type":type(exc).__name__,
            "reason":str(exc)[:350],
            "new_source_scientific_consensus_fabricated":False,
            "new_paid_tts_without_authorization":False,
        }
    print(json.dumps(result,indent=2,ensure_ascii=False))
    return 2 if result["status"]=="G2_FORWARD_BLOCKED_SOURCE_OR_JOURNAL_UNVERIFIED" else 0


if __name__=="__main__":
    raise SystemExit(main())
