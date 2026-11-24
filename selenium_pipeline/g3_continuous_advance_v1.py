"""Advance eligible G3 source-science stages *within one bounded run*.

After the original science reviewers flag an irrelevant citation, this
controller automatically stages the new source context and sends a distinct
first/challenge review when exact Neon/High browser health is present.
Then selects another eligible task until its persisted global Send budget
is reached. It does not schedule runs, re-enable disabled Windows tasks,
replay any uncertain Send or auto-release academic/audio/video material.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from .autonomous_recovery_continuation_v1 import (
    _campaign, _append, _possible_sends, _reservation)
from .g3_context_followup_task_v1 import (
    stage as stage_context, TASK_ROOT, REVIEW_ROOT, READY)
from .g3_distinct_semantic_science_v1 import (
    run_one, _after_incident, _pinned_task)
from .g3_semantic_neon_health_v1 import latest as latest_health, probe_once
from .g3_semantic_source_repair_v1 import _read, _sha, need
from .g3_multisection_autoforward_v71 import (
    run_campaign as source_campaign, _verified_specs)
from .recovery_registry import lookup_mechanism

KIND="g3_source_context_autoforward"
SIGNATURE="TWO_G3_SCIENCE_REVIEWERS_UNRESOLVED_BUT_NEW_PUBLISHER_CONTEXT_FOUND"
MECHANISM="BIND_CONTEXT_AND_OLD_DISPUTE_CREATE_DISTINCT_REVIEW_THEN_AUTO_ADVANCE"
ORIGINAL="G3_DISTINCT_SOURCE_SEMANTIC_QA_READY_NO_SEND"
UNSAFE_REPLAY_STATES={
    "SUBMITTED_OR_UNCERTAIN","NO_RESPONSE_UNRESOLVED",
    "REJECTED_RESPONSE_UNTRUSTED","LEGACY_SENT_NO_RESPONSE",
}


def _prior_uncertain_send(*,review_root:Path,scope:str)->bool:
    """Skip an already possibly-sent source claim across *all* campaigns.

    Per-source academic checkpoints outlive daily global Send budgets.
    A fresh date must never turn an uncertain old request into a new
    eligible task, wasting budget or replaying that request.
    """
    from .academic_review_checkpoint import _load
    need(lookup_mechanism(
        "g3_cross_campaign_held_send",
        "G3_UNCERTAIN_ONE_SEND_REAPPEARS_AS_ELIGIBLE_NEXT_CAMPAIGN"
    )=="SKIP_HELD_OR_UNVERIFIED_SCOPE_ACROSS_CAMPAIGNS_NO_SEND",
         "Source-claim cross-campaign exclusion missing from repair registry")
    home=Path(review_root).absolute()/scope
    if not home.exists():
        return False
    need(home.is_dir() and not home.is_symlink(),
         "Unsafe prior G3 science checkpoint")
    for name in ("initial_request","challenge_request"):
        claim=home/name
        if not claim.exists():
            continue
        need(claim.is_dir() and not claim.is_symlink(),
             "Invalid previous owned academic request directory")
        state=claim/"request_state.json"
        if not state.is_file() or state.is_symlink():
            # Incomplete or corrupted checkpoint: do not trust a
            # newly generated campaign to replay the possibly-sent claim.
            return True
        row=_load(claim)
        status=row["status"]
        if (status=="PREPARED_NOT_SENT"
                and (claim/"dispatch_attempted.claim").exists()):
            return True
        if status in UNSAFE_REPLAY_STATES:
            if status in {"SUBMITTED_OR_UNCERTAIN",
                          "NO_RESPONSE_UNRESOLVED"}:
                observed=claim/"model_response_identity.json"
                if observed.is_file() and not observed.is_symlink():
                    # Old response may be independently recoverable by
                    # run_one's exact-fingerprint, source-bound _saved().
                    continue
            return True
    return False


def _eligible(*,specs:list,state_root:Path,
              section:str|None,utterance_id:str|None)->list[dict]:
    items=[]
    state_root=Path(state_root).absolute()
    for spec in specs:
        if section is not None and spec["section"]!=section:
            continue
        old_root=state_root/"g3_distinct_semantic_science_tasks_v1"/spec["section"]
        if not old_root.exists():
            continue
        need(old_root.is_dir() and not old_root.is_symlink(),
             "Unsafe original G3 utterance inventory")
        originals=sorted(old_root.glob("*.json"))
        need(len(originals)<=128,"Unbounded G3 utterance tasks")
        for file in originals:
            task=_read(file)
            if task.get("status")!=ORIGINAL:
                continue
            _pinned_task(
                spec=spec,
                worklist_root=state_root/"offline_source_quote_worklists_v2",
                task_file=file)
            if (utterance_id is not None and task.get(
                    "original_utterance_id")!=utterance_id):
                continue
            scope=task["scope_sha256"]
            previous=(state_root/"g3_distinct_semantic_science_reviews_v1"/
                      scope/"two_pass_science_evidence.json")
            if previous.exists():
                need(previous.is_file() and not previous.is_symlink(),
                     "Previously accepted model science evidence was altered")
                # Even when the original science task is complete, continue
                # to the following originally independent context task.
                from .g3_semantic_context_recovery_v2 import recover
                review_home=state_root/"g3_distinct_semantic_science_reviews_v1"/scope
                # Repair a missing V3 receipt immediately from the two
                # saved owned Neon replies; never require another command.
                rec=recover(folder=Path(spec["source_folder"]),
                            task=task,review_root=review_home)
                if rec.get("new_distinct_recovery_action")==(
                    "NEW_DISTINCT_EXAMPLE_CONTEXT_REVIEW_TASK_REQUIRED"):
                    followup,ft=stage_context(
                        spec=spec,state_root=state_root,original_task=file)
                    done=state_root/REVIEW_ROOT/ft["scope_sha256"]/"two_pass_science_evidence.json"
                    if (not done.exists()
                            and not _prior_uncertain_send(
                                review_root=state_root/REVIEW_ROOT,
                                scope=ft["scope_sha256"])):
                        items.append({"section":spec["section"],
                            "utterance_id":ft["original_utterance_id"],
                            "original_slide":task["original_rejected_slide"],
                            "kind":"NEW_CONTEXT",
                            "scope":ft["scope_sha256"],
                            "spec":spec,"file":followup})
                continue
            if not _prior_uncertain_send(
                    review_root=state_root/"g3_distinct_semantic_science_reviews_v1",
                    scope=scope):
                items.append({"section":spec["section"],
                              "utterance_id":task["original_utterance_id"],
                              "original_slide":task["original_rejected_slide"],
                              "kind":"ORIGINAL_DISTINCT",
                              "scope":scope,"spec":spec,"file":file})
    # Include entirely new publisher-context evidence discovered BEFORE
    # any review Send. Navigation-only utterances must NOT enter the
    # science-Send queue; their visual QA remains a separate obligation.
    from .g3_prepass_source_gap_repair_v1 import (
        ROOT as GAP_ROOT, SCI_ROOT as GAP_SCI_ROOT, STATUS_SCI)
    for spec in specs:
        if section is not None and spec["section"]!=section:
            continue
        folder=state_root/GAP_ROOT/spec["section"]
        if not folder.exists():
            continue
        need(folder.is_dir() and not folder.is_symlink(),
             "Unsafe recovered source-gap task inventory")
        files=sorted(folder.glob("*.json"))
        need(len(files)<=128,"Unbounded new G3 publisher tasks")
        for file in files:
            row=_read(file)
            if row.get("status")!=STATUS_SCI:
                continue
            if (utterance_id is not None and
                    row["original_utterance_id"]!=utterance_id):
                continue
            scope=row["scope_sha256"]
            report=state_root/GAP_SCI_ROOT/scope/"two_pass_science_evidence.json"
            if report.exists():
                need(report.is_file() and not report.is_symlink(),
                     "Invalid saved G3 source-gap science result")
                continue
            if _prior_uncertain_send(
                    review_root=state_root/GAP_SCI_ROOT,scope=scope):
                continue
            items.append({"section":spec["section"],
                          "utterance_id":row["original_utterance_id"],
                          "original_slide":row["original_slide"],
                          "kind":"NEW_PUBLISHER_PREPASS",
                          "scope":scope,"spec":spec,"file":file})
    # Publisher-gap source context is an eligible NEW task; prioritize
    # it along with new context over repeated old source attempts.
    return sorted(items,key=lambda x:(
        {"NEW_PUBLISHER_PREPASS":0,"NEW_CONTEXT":1}.get(x["kind"],2),
        x["section"],x["original_slide"],x["utterance_id"]))


def advance(*,manifest:Path,state_root:Path,
            campaign_id:str,max_science_sends:int=2,
            max_tasks:int=2,max_health_probes:int=1,
            section:str|None=None,utterance_id:str|None=None,
            execute:bool=True,
            health_probe=None,review_transport=None)->dict:
    need(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
         "G3 source-first automatic advancement not in recovery registry")
    need(type(execute) is bool
         and type(max_science_sends) is int
         and 0<=max_science_sends<=8
         and max_science_sends%2==0
         and type(max_tasks) is int and 1<=max_tasks<=4
         and type(max_health_probes) is int and 0<=max_health_probes<=2,
         "Finite source review/health budget required")
    root=Path(state_root).absolute()
    manifest=Path(manifest).absolute()
    need(root.is_dir() and not root.is_symlink()
         and manifest.is_file() and not manifest.is_symlink(),
         "Missing original G3 source-manifest checkpoint")
    _,specs=_verified_specs(manifest)
    source_set=hashlib.sha256("|".join(
        sorted(spec["identity"]["source_inputs_sha256"]["source.pdf"]
               for spec in specs)).encode()).hexdigest()
    pinned_manifest=_sha(manifest)
    home=root/"g3_continuous_advance_v1"
    need(not home.is_symlink(),"Redirected G3 automatic progress journal")
    home.mkdir(exist_ok=True)
    log,header,events=_campaign(
        root=home,campaign_id=campaign_id,
        source_sha=source_set,queue_sha=pinned_manifest,
        max_sends=max_science_sends)
    observations=[]
    probe_count=0
    attempts=0
    for _ in range(max_tasks):
        choices=_eligible(specs=specs,state_root=root,
                          section=section,utterance_id=utterance_id)
        # Recover a previously reserved task before considering fresh work.
        # A quarantined/uncertain Send is a boundary for THAT task, not
        # a reason to strand other source-independent eligible tasks.
        # Before considering fresh work, resume only a crashed reservation
        # that has neither a completed RESULT nor a recorded HOLD.
        finished_or_held={
            e["scope"] for e in events if e["type"] in ("RESULT","HOLD")}
        pending=[v for v in choices
                 if _reservation(events,v["scope"],"INITIAL")
                 and v["scope"] not in finished_or_held]
        item=(pending or [v for v in choices
            if not _reservation(events,v["scope"],"INITIAL")])
        if not item:
            break
        item=item[0]
        same=_reservation(events,item["scope"],"INITIAL")
        if not same and _possible_sends(events)+2>max_science_sends:
            break
        spec=item["spec"]
        src_sha=spec["identity"]["source_inputs_sha256"]["source.pdf"]
        from .g3_browser_post_send_health_gate_v1 import (
            latest_unresolved_incident,receipt_is_fresher)
        last_incident=max(
            _after_incident(spec=spec),
            latest_unresolved_incident(
                state_root=root,section=spec["section"],
                source_sha256=src_sha))
        receipt=latest_health(
            root=root,source_sha=src_sha,
            after_unix=last_incident)
        if not receipt_is_fresher(
                receipt=receipt,incident_unix=last_incident):
            receipt=None
        if execute and receipt is None and probe_count<max_health_probes:
            probe_count+=1
            from .g3_bounded_owned_browser_window_v1 import (
                bounded_science_response)
            with bounded_science_response(absolute_max_seconds=180):
                receipt=probe_once(
                    root=root,source_sha=src_sha,browser_request=health_probe)
            if not receipt_is_fresher(
                    receipt=receipt,incident_unix=last_incident):
                receipt=None
        if execute and receipt is None:
            observations.append({"scope":item["scope"],
                "section":item["section"],"kind":item["kind"],
                "status":"FRESH_OWNED_NEON_HEALTH_REQUIRED_NO_SOURCE_SEND",
                "source_sends_reserved":0})
            break
        if not same and execute:
            events=_append(log,header,events,"RESERVE",
                scope=item["scope"],phase="INITIAL",
                detail="G3_SOURCE_CONTEXT_AUTOFORWARD")
            events=_append(log,header,events,"RESERVE",
                scope=item["scope"],phase="CHALLENGE",
                detail="G3_TWO_PASS_SCIENCE_FINITE_BUDGET")
        result=run_one(
            spec=spec,task_file=item["file"],
            worklist_root=root/"offline_source_quote_worklists_v2",
            state_root=root,campaign_id=campaign_id,
            max_possible_sends=2 if execute else 0,
            execute=execute,transport=review_transport)
        attempts+=1
        observations.append({"scope":item["scope"],
            "section":item["section"],"kind":item["kind"],
            "status":result["status"],
            "source_sends_reserved":result["possible_sends_reserved"],
            "model_science_agreement":(
                result["two_pass_science_evidence"] or {}).get(
                    "science_AI_source_agreed"),
            "new_source_context_staged":(
                result["semantic_context_recovery"] or {}).get(
                    "new_distinct_recovery_action")==
                    "NEW_DISTINCT_EXAMPLE_CONTEXT_REVIEW_TASK_REQUIRED"})
        if execute:
            events=_append(log,header,events,
                           "RESULT" if result["two_pass_science_evidence"]
                           is not None else "HOLD",
                           scope=item["scope"],phase="RECONCILE",
                           detail=result["status"][:120])
        if not execute:
            break
        # Even when the previous task was quarantined, the next iteration
        # selects a DIFFERENT eligible scope. Never replay its uncertain Send.
        # The next iteration recomputes candidates from the saved state,
        # so a newly eligible context task is forwarded WITHOUT asking user.
    candidates=_eligible(specs=specs,state_root=root,
                        section=section,utterance_id=utterance_id)
    return {
        "schema_version":1,
        "status":(
            "FINITE_G3_SOURCE_CAMPAIGN_BUDGET_EXHAUSTED"
            if _possible_sends(events)>=max_science_sends else
            "G3_SOURCE_AUTOFORWARD_MORE_ELIGIBLE"
            if candidates else "G3_SOURCE_AUTOFORWARD_NO_ELIGIBLE_TASKS"),
        "campaign_id":campaign_id,
        "max_science_browser_sends":max_science_sends,
        "science_browser_sends_reserved":_possible_sends(events),
        "max_health_probes":max_health_probes,
        "health_probes_attempted_this_run":probe_count,
        "stages_advanced_this_run":attempts,
        "stage_results":observations,
        "remaining_eligible_tasks":len(candidates),
        "automatic_forward_after_verified_science_stage":True,
        "original_historical_model_claims_replayed":False,
        "source_scientific_approval_automatically_granted":False,
        "G3_original_semantic_mappings_promoted":0,
        "independent_acoustic_video_QA_complete":False,
        "student_publication_authorized":False,
        "paid_gemini_API_requests":0,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--state-dir",type=Path,required=True)
    p.add_argument("--campaign-id",required=True)
    p.add_argument("--max-science-sends",type=int,default=2)
    p.add_argument("--max-tasks",type=int,default=2)
    p.add_argument("--max-health-probes",type=int,default=1)
    p.add_argument("--section")
    p.add_argument("--utterance-id")
    p.add_argument("--dry-run",action="store_true")
    args=p.parse_args(argv)
    # Historical rejection review, original PDF physical worklists and
    # new per-utterance tasks are reverified at the beginning of EVERY run.
    result=source_campaign(
        manifest=args.manifest,state_dir=args.state_dir,
        max_new_sends=0,auto_offline_repair=True,
        auto_semantic_source_repair=True)
    need(result["new_browser_dispatch_attempts_this_run"]==0
         and result["student_publication_authorized"] is False,
         "Source-first G3 stage must never issue old original review Sends")
    answer=advance(manifest=args.manifest,state_root=args.state_dir,
        campaign_id=args.campaign_id,
        max_science_sends=args.max_science_sends,
        max_tasks=args.max_tasks,
        max_health_probes=args.max_health_probes,
        section=args.section,utterance_id=args.utterance_id,
        execute=not args.dry_run)
    print(json.dumps(answer,indent=2,sort_keys=True,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
