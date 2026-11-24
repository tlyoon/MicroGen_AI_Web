"""Restart-safe finite G3 multi-section Selenium source-review campaign.

The normal v7.1 development daemon remains OFFLINE ONLY. This separate,
explicitly invoked single-owner controller connects the already verified
source-pinned G3 review jobs and advances through eligible slides. Its provider
path is the EXISTING authenticated Selenium-only original reviewer, not an API.
No model output can authorize scientific acceptance, TTS, video or publication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from . import g3_rich_mapping_auto_continuation_v71 as reviewer
from .recovery_registry import lookup_mechanism
from .historical_quarantine_evidence_v1 import inspect_historical_quarantine

STATUS="G3_SOURCE_PINNED_MULTISECTION_BROWSER_CAMPAIGN_V71"
KIND="g3_multisection_autoforward"
SIGNATURE="G3_ONE_SECTION_REVIEW_ENDS_WITH_OTHER_ELIGIBLE_SOURCE_WORK"
REPAIR="FINITE_GLOBAL_SOURCE_PINNED_BROWSER_DISPATCH_REUSE_AND_RESUME"
MAX_SECTIONS=8
MAX_REQUESTS_PER_RUN=32


def require(ok, message):
    if not ok:
        raise ValueError(message)


def _hash(value):
    return hashlib.sha256(json.dumps(
        value,sort_keys=True,separators=(",",":"),ensure_ascii=False,
        allow_nan=False).encode("utf8")).hexdigest()


def _json(path):
    require(path.is_file() and not path.is_symlink()
            and 2<=path.stat().st_size<=1000000,
            "Missing, linked or oversized G3 campaign JSON")
    item=json.loads(path.read_text("utf8"))
    require(type(item) is dict,"Expected G3 JSON object")
    return item


def _write_once(path,value):
    require(not path.exists() and not path.is_symlink()
            and path.parent.is_dir() and not path.parent.is_symlink(),
            "Historical campaign checkpoint already exists")
    with path.open("x",encoding="utf8") as out:
        json.dump(value,out,ensure_ascii=False,sort_keys=True,indent=2)
        out.write("\n")
        out.flush()
        os.fsync(out.fileno())


def _persist_historical_quarantine(root:Path,identity:dict,
                                   prior_sha:str,captures:list)->str|None:
    """Persist evidence under existing campaign owner; no review promotion.

    Hash-addressed atomic admission supports restart after a staged crash.
    An unrelated or modified previous receipt must not be overwritten.
    """
    if not captures:
        return None
    report={
        "schema_version":1,
        "status":"HISTORICAL_G3_QUARANTINE_NO_REPLAY_EVIDENCE_V1",
        "campaign_identity_sha256":_hash(identity),
        "last_immutable_dispatch_receipt_sha256":prior_sha,
        "captures":captures,
        "new_model_requests":0,
        "retry_authorized":False,
        "independent_scientific_QA_complete":False,
        "student_publication_authorized":False,
    }
    target=root/("historical_quarantine_"+_hash(report)[:24]+".json")
    staged=target.with_name(target.name+".stage")
    require(not target.is_symlink() and not staged.is_symlink(),
            "Historical recovery receipt may not be symlinked")
    if target.exists():
        require(_json(target)==report,"Historical recovery receipt changed")
        return str(target)
    if staged.exists():
        require(_json(staged)==report,"Interrupted historical receipt differs")
    else:
        with staged.open("x",encoding="utf8") as handle:
            json.dump(report,handle,ensure_ascii=False,sort_keys=True,indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    os.replace(staged,target)
    return str(target)


def _verified_specs(manifest:Path):
    require(lookup_mechanism(KIND,SIGNATURE)==REPAIR,
            "Source-bound G3 campaign auto-forward is not registered")
    manifest=Path(manifest).absolute()
    data=_json(manifest)
    require(set(data)=={"schema_version","status","sections",
                        "browser_port","paid_gemini_api_requests_authorized",
                        "student_publication_authorized"}
            and data["schema_version"]==1
            and data["status"]==STATUS
            and data["paid_gemini_api_requests_authorized"]==0
            and data["student_publication_authorized"] is False
            and type(data["browser_port"]) is int
            and data["browser_port"] in range(9222,9324)
            and type(data["sections"]) is list
            and 1<=len(data["sections"])<=MAX_SECTIONS,
            "Unrecognized or unbounded source-only campaign contract")
    names=set()
    specs=[]
    for section in data["sections"]:
        require(type(section) is dict and
                set(section)=={"section","source_folder","checkpoint","review_root"},
                "Unexpected source manifest section keys")
        name=section["section"]
        require(type(name) is str and 1<=len(name)<=32
                and name.replace("_","").replace("-","").isalnum()
                and name not in names,
                "Duplicate or unsafe original section")
        names.add(name)
        paths={}
        for key in ("source_folder","checkpoint","review_root"):
            value=section[key]
            require(type(value) is str and len(value)>3
                    and Path(value).is_absolute(),
                    "Source path must be explicitly absolute")
            paths[key]=Path(value).absolute()
        require(len(set(paths.values()))==3,
                "Original source and checkpoints must be separate")
        # This call verifies the actual PDF/slide/script/candidate hashes
        # and creates NO Gemini/API requests. No source mutation.
        proof=reviewer.prepare(**paths)
        specs.append({**paths,"section":name,"identity":proof})
    return data,specs


def _state_root(state_dir:Path,source_manifest:Path,contract:dict,specs:list):
    root=Path(state_dir).absolute()
    require(root.parent.is_dir() and not root.parent.is_symlink()
            and not root.is_symlink()
            and all(not root.is_relative_to(x[key])
                    and not x[key].is_relative_to(root)
                    for x in specs for key in ("source_folder","checkpoint","review_root")),
            "Campaign receipts may not be written into protected source folders")
    if not root.exists():
        root.mkdir()
    require(root.is_dir() and not root.is_symlink(),
            "Unsafe G3 campaign state storage")
    identity={
        "schema_version":1,"status":STATUS,
        "original_manifest_path":str(Path(source_manifest).absolute()),
        "source_manifest_sha256":reviewer._sha(Path(source_manifest)),
        "contract_sha256":_hash(contract),
        "source_identity":[{
            "section":s["section"],
            "source_inputs_sha256":s["identity"]["source_inputs_sha256"],
            "mapping_checkpoint_sha256":s["identity"]["mapping_checkpoint_sha256"],
            "original_slides":s["identity"]["original_slides"],
        } for s in specs],
        "selenium_only":True,"paid_api_requests_authorized":0,
        "student_publication_authorized":False,
        "offline_development_daemon_modified":False,
    }
    path=root/"campaign_identity.json"
    if path.exists() or path.is_symlink():
        require(_json(path)==identity,
                "Original source, files or campaign plan changed; no continuation")
    else:
        _write_once(path,identity)
    return root,identity


def _events(root,identity):
    expected=0
    previous=None
    result=[]
    for file in sorted(root.glob("event_*.json")):
        require(file.name==f"event_{expected:04d}.json",
                "Missing, duplicate or out-of-order campaign checkpoint")
        row=_json(file)
        require(row.get("schema_version")==1
                and row.get("status")=="IMMUTABLE_ORIGINAL_G3_BROWSER_DISPATCH_STEP"
                and row.get("campaign_identity_sha256")==_hash(identity)
                and row.get("previous_receipt_sha256")==previous
                and row.get("section") in {
                    s["section"] for s in identity["source_identity"]}
                and row.get("browser_dispatch_attempts")==1
                and row.get("provider_transport")=="selenium_browser_only"
                and row.get("paid_api_requests")==0
                and row.get("student_publication_authorized") is False,
                "Malformed or altered original G3 dispatch audit chain")
        previous=reviewer._sha(file)
        result.append(row)
        expected+=1
    require(expected<=256,"Unbounded historical G3 campaign evidence")
    return result,previous


def _survey(specs):
    observed=[]
    for spec in specs:
        report=reviewer.run(
            source_folder=spec["source_folder"],
            checkpoint=spec["checkpoint"],
            review_root=spec["review_root"],
            max_new_sends=0)
        require(report["new_browser_dispatch_attempts_this_run"]==0
                and report["paid_gemini_api_requests"]==0
                and report["student_publication_authorized"] is False
                and report["developer_api_fallback_permitted"] is False,
                "Existing source-only reviewer contract changed")
        observed.append({"section":spec["section"],"report":report})
    return observed


def _counts(observed):
    return {
        "source_audited_original_slides":sum(x["report"]["original_reviewed_slides_reused"]
                                             for x in observed),
        "verified_source_text_anchors":sum(
            x["report"]["original_textbook_and_rendered_text_anchors_proven"]
            for x in observed),
        "semantic_gaps_in_audited_slides":sum(
            x["report"]["source_review_gaps_within_reviewed_slides"]
            for x in observed),
        "untouched_original_slides":sum(
            x["report"]["remaining_unreviewed_slides"] for x in observed),
        "quarantined_or_uncertain_original_slides":sum(
            x["report"]["quarantined_or_uncertain_slides"] for x in observed),
        "source_rejected_original_slides":sum(
            x["report"].get("source_rejected_slides",0) for x in observed),
    }


def run_campaign(*,manifest:Path,state_dir:Path,
                 max_new_sends:int=0,wait_s:int=120,
                 auto_offline_repair:bool=False,
                 auto_semantic_source_repair:bool=False):
    require(type(auto_offline_repair) is bool
            and type(auto_semantic_source_repair) is bool
            and (not auto_semantic_source_repair or auto_offline_repair),
            "Semantic source repair needs prior immutable offline worklists")
    require(type(max_new_sends) is int
            and 0<=max_new_sends<=MAX_REQUESTS_PER_RUN
            and type(wait_s) is int and 20<=wait_s<=180,
            "Campaign cannot start an unlimited Gemini browser request loop")
    contract,specs=_verified_specs(manifest)
    root,identity=_state_root(state_dir,manifest,contract,specs)
    # A single OS byte lock for ALL sections. Each source reviewer also
    # enforces its own durable one-owner lock and one-Send original claim.
    with reviewer._exclusive(root):
        events,prior_sha=_events(root,identity)
        observations=_survey(specs)
        attempted=0
        stopped_reason="NO_NEW_SENDS_REQUESTED" if max_new_sends==0 else None
        failures=0
        chosen_count={s["section"]:0 for s in specs}
        for event in events:
            if event["section"] in chosen_count:
                chosen_count[event["section"]]+=1
        while attempted<max_new_sends:
            totals=_counts(observations)
            # This circuit breaker is GLOBAL, not just local to a single
            # original subsection; prior uncertain request outcomes in
            # another section remain counted after a process restart.
            if totals["quarantined_or_uncertain_original_slides"]>=2:
                stopped_reason="GLOBAL_TWO_UNCERTAIN_BROWSER_REQUESTS_NO_RETRY"
                break
            ready=[s for s in specs if next(x for x in observations
                    if x["section"]==s["section"])["report"][
                    "remaining_unreviewed_slides"]>0]
            if not ready:
                stopped_reason=("NO_UNREVIEWED_SLIDES_LEFT"
                    if totals["quarantined_or_uncertain_original_slides"]==0
                    and totals["source_rejected_original_slides"]==0
                    else "REMAINING_SOURCE_REJECTIONS_OR_UNCERTAIN_CLAIMS_NO_REPLAY")
                break
            # Fairness: least recently selected source first, with a
            # deterministic higher-backlog tie-break; no starvation.
            ready.sort(key=lambda s:(
                chosen_count[s["section"]],
                -next(x for x in observations if x["section"]==s["section"])[
                  "report"]["remaining_unreviewed_slides"],
                s["section"]))
            chosen=ready[0]
            new=reviewer.run(
                source_folder=chosen["source_folder"],
                checkpoint=chosen["checkpoint"],
                review_root=chosen["review_root"],
                max_new_sends=1,
                port=contract["browser_port"],wait_s=wait_s)
            require(new["new_browser_dispatch_attempts_this_run"]<=1
                    and new["paid_gemini_api_requests"]==0
                    and new["student_publication_authorized"] is False,
                    "Real Selenium source review escaped its bounded contract")
            if new["new_browser_dispatch_attempts_this_run"]!=1:
                stopped_reason="UNEXPECTED_PROVIDER_DISPATCH_COUNT_NO_REPEAT"
                break
            attempted+=1
            chosen_count[chosen["section"]]+=1
            record={
                "schema_version":1,
                "status":"IMMUTABLE_ORIGINAL_G3_BROWSER_DISPATCH_STEP",
                "campaign_identity_sha256":_hash(identity),
                "previous_receipt_sha256":prior_sha,
                "section":chosen["section"],
                "browser_dispatch_attempts":1,
                "provider_transport":"selenium_browser_only",
                "paid_api_requests":0,
                "student_publication_authorized":False,
                "source_audited_original_slides":new["original_reviewed_slides_reused"],
                "remaining_unreviewed_original_slides":new["remaining_unreviewed_slides"],
                "quarantined_or_uncertain_slides":new["quarantined_or_uncertain_slides"],
                "dispatch_failures":new["dispatch_failures"],
            }
            event_path=root/f"event_{len(events):04d}.json"
            _write_once(event_path,record)
            prior_sha=reviewer._sha(event_path)
            events.append(record)
            observations=_survey(specs)
            if any(x.get("failure_classification")!=
                   "SOURCE_QUOTE_REJECTED_NO_REPLAY"
                   for x in new["dispatch_failures"]):
                failures+=1
                if failures>=2:
                    stopped_reason="TWO_CONSECUTIVE_BROWSER_FAILURES_NO_REPEAT"
                    break
            else:
                # Publisher-quote rejection is a scientific-model-content
                # failure on ONE immutable slide, not provider unavailability.
                # Preserve it and advance independent eligible source work.
                failures=0
        if stopped_reason is None:
            stopped_reason=("BOUNDED_RUN_BUDGET_REACHED"
                if attempted==max_new_sends else "NO_MORE_ELIGIBLE_WORK")
        counters=_counts(observations)
        # Historical failures are evidence-only. An empty, hash-valid raw
        # quarantine establishes NO retrievable reply, never a failed Send.
        historical_uncertain_captures=[{
            "section":event["section"], "slide":failure.get("slide"),
            "capture":inspect_historical_quarantine(failure.get("error")),
        } for event in events
          for failure in event.get("dispatch_failures",[])
          if failure.get("failure_classification")=="UNTRUSTED_OR_UNCERTAIN_SEND"]
        historical_receipt=_persist_historical_quarantine(
            root,identity,prior_sha,historical_uncertain_captures)
        offline_worklists=None
        if auto_offline_repair:
            # A provider circuit breaker does NOT prohibit source-local
            # correction evidence. Reverify rejected original response
            # bytes and extract actual PDF text without any new Gemini Send.
            from .g3_source_rejected_offline_repair_v1 import materialize
            offline_worklists=materialize(
                specs=specs,output_root=root/"offline_source_quote_worklists_v2")
            require(offline_worklists["new_browser_sends"]==0
                    and offline_worklists["new_paid_gemini_API_requests"]==0
                    and offline_worklists["new_original_source_review_acceptances"]==0
                    and offline_worklists["student_publication_authorized"] is False,
                    "G3 source-only offline work cannot bypass scientific QA")
        semantic_tasks=None
        if auto_semantic_source_repair:
            from .g3_semantic_source_repair_v1 import materialize as stage_semantic
            semantic_tasks=stage_semantic(
                specs=specs,
                worklist_root=root/"offline_source_quote_worklists_v2",
                output_root=root/"g3_distinct_semantic_science_tasks_v1")
            require(semantic_tasks["new_browser_sends"]==0
                    and semantic_tasks["paid_gemini_API_calls"]==0
                    and semantic_tasks["independent_scientific_QA_accepted"]==0
                    and semantic_tasks["student_publication_authorized"] is False,
                    "Only independent semantic review tasks, never approval")
        gap_recovery=None
        if auto_semantic_source_repair:
            from .g3_prepass_source_gap_repair_v1 import materialize as close_gaps
            gap_recovery=close_gaps(
                specs=specs,
                worklist_root=root/"offline_source_quote_worklists_v2",
                state_root=root)
            require(gap_recovery["new_browser_sends"]==0
                    and gap_recovery["paid_gemini_API_calls"]==0
                    and gap_recovery["academic_source_acceptances_added"]==0
                    and gap_recovery["student_publication_authorized"] is False,
                    "Missing-source repair is never an academic approval")
        visual_question_worklists=None
        if auto_semantic_source_repair:
            from .g3_original_visual_question_source_audit_v1 import (
                materialize as stage_visual_questions)
            visual_question_worklists=stage_visual_questions(
                specs=specs,state_root=root)
            require(visual_question_worklists["new_provider_sends"]==0
                    and visual_question_worklists["paid_gemini_API_calls"]==0
                    and visual_question_worklists["independent_scientific_QA_approved"]==0
                    and visual_question_worklists["independent_visual_QA_approved"]==0
                    and visual_question_worklists["student_publication_authorized"] is False,
                    "Original rendered visual source excerpts are never science approval")
        untouched_preflight=None
        if auto_semantic_source_repair:
            from .g3_unreviewed_source_preflight_v1 import (
                materialize as preflight_original_untouched)
            untouched_preflight=preflight_original_untouched(
                specs=specs,state_root=root)
            require(untouched_preflight["new_browser_sends"]==0
                    and untouched_preflight["paid_gemini_API_calls"]==0
                    and untouched_preflight["original_science_approvals"]==0
                    and untouched_preflight["student_publication_authorized"] is False,
                    "Untouched original source task cannot certify a slide")
        untouched_source_witnesses=None
        if auto_semantic_source_repair:
            from .g3_untouched_source_witness_v2 import (
                materialize as stage_original_publisher_witnesses)
            untouched_source_witnesses=stage_original_publisher_witnesses(
                specs=specs,state_root=root)
            require(untouched_source_witnesses["new_browser_sends"]==0
                    and untouched_source_witnesses["paid_gemini_API_calls"]==0
                    and untouched_source_witnesses["independent_scientific_QA_accepted"]==0
                    and untouched_source_witnesses["independent_visual_QA_accepted"]==0
                    and untouched_source_witnesses["student_publication_authorized"] is False,
                    "Physical publisher quotes cannot grant original G3 approval")
        return {
            "schema_version":1,
            "untouched_original_source_witnesses":untouched_source_witnesses,
            "historical_uncertain_captures":historical_uncertain_captures,
            "historical_quarantine_evidence_receipt":historical_receipt,
            "source_rejected_offline_recovery":offline_worklists,
            "semantic_source_recovery":semantic_tasks,
            "prepass_source_gap_recovery":gap_recovery,
            "rendered_visual_question_source_recovery":visual_question_worklists,
            "untouched_source_preflight":untouched_preflight,
            "status":("G3_SOURCE_MAPPING_INPUT_REVIEW_COVERAGE_COMPLETE_REVIEW_ONLY"
                      if counters["untouched_original_slides"]==0 and
                         counters["quarantined_or_uncertain_original_slides"]==0
                         and counters["source_rejected_original_slides"]==0
                      else "G3_SOURCE_MAPPING_CONTINUATION_CHECKPOINTED"),
            "stopped_reason":stopped_reason,
            **counters,
            "original_sections":[{"section":x["section"],
                "source_audited_slides":x["report"]["original_reviewed_slides_reused"],
                "untouched_slides":x["report"]["remaining_unreviewed_slides"],
                "quarantined_slides":x["report"]["quarantined_or_uncertain_slides"],
                "source_rejected_slides":x["report"].get("source_rejected_slides",0),
                "source_text_anchors":x["report"][
                    "original_textbook_and_rendered_text_anchors_proven"]}
                for x in observations],
            "new_browser_dispatch_attempts_this_run":attempted,
            "total_immutable_dispatch_receipts":len(events),
            "paid_gemini_api_requests":0,
            "offline_development_daemon_modified":False,
            "independent_scientific_QA_complete":False,
            "independent_acoustic_QA_complete":False,
            "highlighted_video_accepted":False,
            "student_publication_authorized":False,
        }


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--state-dir",type=Path,required=True)
    parser.add_argument("--max-new-sends",type=int,default=0)
    parser.add_argument("--wait-s",type=int,default=120)
    parser.add_argument("--auto-offline-source-repair",action="store_true")
    parser.add_argument("--auto-semantic-source-repair",action="store_true")
    parser.add_argument("--auto-forward-science",action="store_true")
    parser.add_argument("--science-max-sends",type=int,default=4)
    parser.add_argument("--science-max-tasks",type=int,default=2)
    parser.add_argument("--science-max-health-probes",type=int,default=2)
    parser.add_argument("--science-campaign-id",default=None)
    args=parser.parse_args(argv)
    if args.auto_forward_science:
        require(args.max_new_sends==0,
                "New G3 science must not dispatch the unsafe original whole-slide queue")
        if args.science_campaign_id is None:
            from datetime import datetime,timezone
            import hashlib
            # Identical source+UTC date gives a stable restart budget with
            # no manual campaign-id input. Next date can advance the NEXT
            # unreviewed task, but immutable per-task Send claims persist.
            digest=hashlib.sha256(Path(args.manifest).read_bytes()).hexdigest()[:12]
            day=datetime.now(timezone.utc).strftime("%Y%m%d")
            args.science_campaign_id=f"g3_source_auto_{digest}_{day}"
    value=run_campaign(manifest=args.manifest,state_dir=args.state_dir,
                       max_new_sends=args.max_new_sends,wait_s=args.wait_s,
                       auto_offline_repair=(
                           args.auto_offline_source_repair or args.auto_forward_science),
                       auto_semantic_source_repair=(
                           args.auto_semantic_source_repair or args.auto_forward_science))
    if args.auto_forward_science:
        from .g3_continuous_advance_v1 import advance
        progress=advance(
            manifest=args.manifest,state_root=args.state_dir,
            campaign_id=args.science_campaign_id,
            max_science_sends=args.science_max_sends,
            max_tasks=args.science_max_tasks,
            max_health_probes=args.science_max_health_probes,
            execute=True)
        value={"source_only_recovery":value,
               "continuing_science_automatically":progress,
               "original_historical_send_replayed":False,
               "student_publication_authorized":False}
    print(json.dumps(value,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
