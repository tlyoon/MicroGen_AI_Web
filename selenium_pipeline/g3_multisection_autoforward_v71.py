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
    }


def run_campaign(*,manifest:Path,state_dir:Path,
                 max_new_sends:int=0,wait_s:int=120):
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
                    else "REMAINING_CLAIMS_QUARANTINED_NO_SAFE_SEND")
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
            if new["dispatch_failures"]:
                failures+=1
                if failures>=2:
                    stopped_reason="TWO_CONSECUTIVE_BROWSER_FAILURES_NO_REPEAT"
                    break
            else:
                failures=0
        if stopped_reason is None:
            stopped_reason=("BOUNDED_RUN_BUDGET_REACHED"
                if attempted==max_new_sends else "NO_MORE_ELIGIBLE_WORK")
        counters=_counts(observations)
        return {
            "schema_version":1,
            "status":("G3_SOURCE_MAPPING_INPUT_REVIEW_COVERAGE_COMPLETE_REVIEW_ONLY"
                      if counters["untouched_original_slides"]==0 and
                         counters["quarantined_or_uncertain_original_slides"]==0
                      else "G3_SOURCE_MAPPING_CONTINUATION_CHECKPOINTED"),
            "stopped_reason":stopped_reason,
            **counters,
            "original_sections":[{"section":x["section"],
                "source_audited_slides":x["report"]["original_reviewed_slides_reused"],
                "untouched_slides":x["report"]["remaining_unreviewed_slides"],
                "quarantined_slides":x["report"]["quarantined_or_uncertain_slides"],
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
    args=parser.parse_args(argv)
    value=run_campaign(manifest=args.manifest,state_dir=args.state_dir,
                       max_new_sends=args.max_new_sends,wait_s=args.wait_s)
    print(json.dumps(value,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
