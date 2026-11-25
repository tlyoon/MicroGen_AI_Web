"""Fresh, explicitly scoped G2 V3 review capacity; never renew an old budget.

A user's distinct approval permits at most ONE source- and UTC-day-bound
campaign of exactly two Selenium Neon/High model turns (initial/challenge),
for one previously unreviewed ranked V3 utterance. This is not a reset of any
earlier campaign. The old reservation journal remains hash-pinned and read-only.
Academic agreement remains separately adjudicated from authentic model bytes.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .figure_source_identity import _sha, require
from .autonomous_recovery_continuation_v1 import _campaign, _possible_sends
from .three_pc_worker import LocalInstanceLock
from .recovery_registry import lookup_mechanism

KIND="g2_explicit_scoped_science_capacity"
SIGNATURE="G2_NEW_DISTINCT_SCIENCE_SCOPE_USER_AUTHORIZED_AFTER_FINITE_CAP"
MECHANISM="PIN_FRESH_ONE_SCOPE_TWO_PASS_BUDGET_WITHOUT_OLD_SEND_REPLAY"
ROOT="G2_EXPLICIT_SCOPED_SCIENCE_GRANTS_V1"
PREFIX="g2_v3_explicit_"
STATUS="G2_SCOPED_DISTINCT_TWO_PASS_CAPACITY_AUTHORIZED_UNAPPROVED"
CONSENT="USER_PROCEED_WITH_FIRST_NEW_INDEPENDENT_G2_TWO_PASS_REVIEW_20261125"
PARENT="g2_autoforward_live_20261123a"


def _read(path:Path)->dict:
    require(path.is_file() and not path.is_symlink()
            and 0<path.stat().st_size<=20000,"Missing/unsafe explicit grant")
    value=json.loads(path.read_text(encoding="utf8"))
    require(type(value) is dict,"Malformed scoped consent grant")
    return value


def _parent(queue_root:Path, source_sha:str, queue_sha:str)->dict:
    root=queue_root/"autonomous_recovery_continuation_v1"
    home=root/PARENT
    require(home.is_dir() and (home/"campaign.json").is_file(),
            "Do not create or reset the previously exhausted campaign")
    raw=_read(home/"campaign.json")
    require(raw.get("max_possible_model_sends")==2
            and raw.get("source_sha256")==source_sha
            and raw.get("queue_sha256")==queue_sha,
            "Original finite campaign source/budget changed")
    _,_,events=_campaign(root=root,campaign_id=PARENT,
        source_sha=source_sha,queue_sha=queue_sha,max_sends=2)
    require(_possible_sends(events)==2
            and len(events)==4
            and [x["type"] for x in events]==[
                "RESERVE","RESULT","RESERVE","RESULT"]
            and all(events[i]["scope"]==events[i+1]["scope"]
                    and events[i]["phase"]==events[i+1]["phase"]
                    for i in (0,2))
            and events[0]["phase"]=="INITIAL"
            and events[2]["phase"]=="CHALLENGE",
            "Original old model Send claims unresolved; no new capacity")
    files=sorted(home.glob("event_*.json"))
    return {"original_campaign_id":PARENT,"original_reserved":2,
            "original_cap":2,"immutable_parent_sha256":{
                f.name:_sha(f) for f in [home/"campaign.json",*files]}}


def _location(queue_root:Path,source_sha:str,day:str)->Path:
    require(len(day)==8 and day.isdecimal(),"Invalid UTC date")
    root=queue_root.parent/ROOT/source_sha
    require(not (queue_root.parent/ROOT).is_symlink()
            and not root.is_symlink()
            and not (root/(day+".json")).is_symlink(),
            "Redirected explicit science authorization")
    return root/(day+".json")


def verify_grant(*,queue_root:Path, source_sha:str, scope_sha:str,
                 candidate_sha:str,campaign_id:str,cap:int)->dict:
    queue_root=Path(queue_root).absolute()
    day=campaign_id.split("_")[3] if campaign_id.startswith(PREFIX) else ""
    # Canonical name: g2_v3_explicit_YYYYMMDD_<12-hex scope prefix>.
    require(campaign_id==PREFIX+day+"_"+scope_sha[:12]
            and cap==2 and day==datetime.now(timezone.utc).strftime("%Y%m%d"),
            "Not a currently authorized distinct G2 science campaign")
    path=_location(queue_root,source_sha,day)
    grant=_read(path)
    require(grant.get("status")==STATUS and grant.get("consent_reference")==CONSENT
            and grant.get("eligible_scope_sha256")==scope_sha
            and grant.get("candidate_file_sha256")==candidate_sha
            and grant.get("source_sha256")==source_sha
            and grant.get("queue_sha256")==_sha(queue_root/"queue.json")
            and grant.get("campaign_id")==campaign_id
            and grant.get("max_possible_model_sends")==2
            and grant.get("model_family")=="neon"
            and grant.get("thinking_level")=="high"
            and grant.get("browser_selenium_only") is True
            and grant.get("automatic_paid_api_fallback_authorized") is False
            and grant.get("original_request_replay_authorized") is False
            and grant.get("student_publication_authorized") is False
            and grant.get("two_pass_science_accepted") is False,
            "Scoped G2 campaign exceeds explicitly authorized purpose")
    original=_parent(queue_root,source_sha,grant["queue_sha256"])
    require(grant["original_campaign_snapshot"]==original,
            "Original old campaign mutated after new-scoped approval")
    home=queue_root/"autonomous_recovery_continuation_v1"/campaign_id
    require((home/"campaign.json").is_file()
            and _read(home/"campaign.json").get("max_possible_model_sends")==2,
            "Only previously provisioned finite G2 campaign allowed")
    return grant


def provision(*,folder:Path,queue_root:Path,candidate_file:Path,
              health_result:Path,explicit_user_consent:bool=False)->dict:
    require(lookup_mechanism(KIND,SIGNATURE)==MECHANISM,
            "Scoped new science capacity recovery is not registered")
    require(explicit_user_consent is True,
            "No fresh, explicit authorization for a second scoped campaign")
    from .g2_ranked_v3_owned_selenium_handoff_v1 import _verify,ROOT as REVIEW_ROOT
    from .g2_distinct_focused_source_review_v1 import _health_ok
    folder,queue_root,candidate_file=(
        Path(folder).absolute(),Path(queue_root).absolute(),Path(candidate_file).absolute())
    row,job=_verify(folder=folder,queue_root=queue_root,candidate_file=candidate_file)
    source_sha=job["source_sha256"]
    queue_sha=_sha(queue_root/"queue.json")
    scope=row["scope_sha256"]
    day=datetime.now(timezone.utc).strftime("%Y%m%d")
    name=PREFIX+day+"_"+scope[:12]
    old_claim=queue_root/f"slide_{row['original_slide']:03d}_initial_review_attempt_01_request"/"dispatch_attempted.claim"
    _health_ok(health_result=Path(health_result),queue_root=queue_root,
               source_sha=source_sha,old_claim=old_claim,family="neon")
    with LocalInstanceLock("g2_qa_"+hashlib.sha256(str(queue_root).encode("utf8")).hexdigest()[:20],
                           queue_root/".microgen_g2_supervisor_locks"):
        parent=_parent(queue_root,source_sha,queue_sha)
        target=queue_root.parent/REVIEW_ROOT/scope
        grant_path=_location(queue_root,source_sha,day)
        existing=grant_path.exists()
        if not existing:
            require(not target.exists() and not target.is_symlink(),
                    "Previously claimed V3 model request must never be re-sent")
            require(not any(x.is_file() for x in grant_path.parent.glob("*.json")),
                    "Already authorized another G2 scope for this source/day")
        grant={"schema_version":1,"status":STATUS,"consent_reference":CONSENT,
            "eligible_scope_sha256":scope,"candidate_file_sha256":_sha(candidate_file),
            "source_sha256":source_sha,"queue_sha256":queue_sha,
            "campaign_id":name,"max_possible_model_sends":2,
            "model_family":"neon","thinking_level":"high",
            "browser_selenium_only":True,
            "automatic_paid_api_fallback_authorized":False,
            "original_request_replay_authorized":False,
            "student_publication_authorized":False,
            "two_pass_science_accepted":False,
            "original_campaign_snapshot":parent}
        if existing:
            require(_read(grant_path)==grant,"Previous grant changed; do not renew")
        else:
            grant_path.parent.mkdir(parents=True,exist_ok=True)
            with grant_path.open("x",encoding="utf8") as out:
                out.write(json.dumps(grant,sort_keys=True,indent=2)+"\n")
                out.flush();os.fsync(out.fileno())
        _campaign(root=queue_root/"autonomous_recovery_continuation_v1",
            campaign_id=name,source_sha=source_sha,
            queue_sha=queue_sha,max_sends=2)
        verify_grant(queue_root=queue_root,source_sha=source_sha,scope_sha=scope,
                     candidate_sha=_sha(candidate_file),campaign_id=name,cap=2)
        return {"status":STATUS,"scope_sha256":scope,
                "new_campaign_id":name,"new_cap":2,"old_cap_unchanged":True,
                "authorization_receipt":str(grant_path),
                "new_model_requests":0,"paid_api_calls":0,
                "two_pass_science_accepted":False,
                "student_publication_authorized":False}

