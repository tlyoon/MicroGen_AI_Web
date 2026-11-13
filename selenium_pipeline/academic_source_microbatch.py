"""Source-hash and prior-claim-locked short Gemini academic review plans.

A long original academic job that returns partial JSON must never be resent.
This source-preserving planner cuts only STILL UNCLAIMED original utterances
into at most two-unit review jobs before any future model Send. The shared
global original-unit index is authoritative across conversations and roots.
The old source job, original PDFs, prior model replies and claims are frozen.

This module makes no browser/model/TTS/media requests and never approves G2.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .ai_academic_web_review import review_instructions
from .figure_source_identity import require
from .source_review_autonomous_campaign import _assert_job, sha

MAX_UNITS_PER_JOB = 2
MAX_PLAN_JOBS = 24
MANIFEST_REVISION = 2


def _read(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(),
            "Microbatch input/source claim must exist and not be a link")
    value=json.loads(path.read_text(encoding="utf8"))
    require(type(value) is dict, "Untrusted source microbatch record")
    return value


def unclaimed_microbatch_plan(*, original_plan: Path,
                              checkpoint_parent: Path,
                              max_units: int=MAX_UNITS_PER_JOB) -> dict:
    """Verify original source jobs and all shared claims, without writing."""
    original_plan=Path(original_plan).absolute()
    checkpoint_parent=Path(checkpoint_parent).absolute()
    original=_read(original_plan)
    require(type(max_units) is int and 1<=max_units<=2
            and checkpoint_parent.is_dir() and not checkpoint_parent.is_symlink()
            and original.get("schema_version")==1
            and original.get("status")==
                "UNSENT_PHYSICALLY_CHANGED_G2_SOURCE_AND_VISUAL_EVIDENCE"
            and original.get("G2_approved") is False
            and original.get("student_publication_authorized") is False
            and type(original.get("jobs")) is list
            and 1<=len(original["jobs"])<=24,
            "Untrusted original unsent academic source review plan")
    source_sha=original.get("source_sha256")
    require(type(source_sha) is str and len(source_sha)==64
            and all(c in "0123456789abcdef" for c in source_sha),
            "Original source identity required for short academic review")
    claimed_ids=set()
    claim_root=checkpoint_parent/".microgen_academic_source_once"/source_sha
    require(not claim_root.is_symlink(), "Unsafe shared original-unit claims")
    if claim_root.exists():
        require(claim_root.is_dir(),"Invalid global original-source claim index")
        for filename in sorted(claim_root.glob("*.json")):
            claim=_read(filename)
            require(claim.get("schema_version")==1
                    and claim.get("type")==
                        "THIRD_PASS_CHANGED_SOURCE_REVIEW"
                    and claim.get("source_sha256")==source_sha
                    and type(claim.get("utterance_ids")) is list
                    and len(claim["utterance_ids"])>=1
                    and len(set(claim["utterance_ids"]))==
                        len(claim["utterance_ids"])
                    and type(claim.get("request_sha256")) is str
                    and filename.stem==claim["request_sha256"],
                    "Untrusted original-unit claim cannot be ignored")
            claimed_ids.update(claim["utterance_ids"])
    verified_original_uids=set()
    emitted=[]
    excluded=[]
    for entry in original["jobs"]:
        job,folder,prompt,uids=_assert_job(entry,source_sha)
        require(all(uid not in verified_original_uids for uid in uids),
                "Original source review unit repeated before microbatching")
        verified_original_uids.update(uids)
        usable=[uid for uid in uids if uid not in claimed_ids]
        excluded.extend(uid for uid in uids if uid in claimed_ids)
        for begin in range(0,len(usable),max_units):
            group=usable[begin:begin+max_units]
            keep=set(group)
            slides=[]
            for slide in job["slides"]:
                subset=[u for u in slide["utterances"] if u["id"] in keep]
                if subset:
                    slides.append({**slide,"utterances":subset})
            source_packet=job["verified_source_quote_candidates_v1"]
            selected_quotes=[
                record for record in source_packet["utterances"]
                if record["utterance_id"] in keep
            ]
            require(len(selected_quotes)==len(group) and
                    sum(len(s["utterances"]) for s in slides)==len(group),
                    "Missing original source quotation or short unit")
            filtered={**job,
                      "slides":slides,
                      "utterance_count":len(group),
                      "selected_original_slides":[s["slide"] for s in slides],
                      "verified_source_quote_candidates_v1":{
                          **source_packet,"utterances":selected_quotes},
                      "academic_approval":False,
                      "student_publication_authorized":False}
            # The exact original utterance IDs and source/slide/script hashes
            # remain unchanged. Only the subset of verified source candidates
            # appears in the model prompt. Never make up citations/targets.
            exact=review_instructions(filtered,mode="INDEPENDENT_CHALLENGE")
            emitted.append({**entry,
                            "source_job":filtered,
                            "source_job_request_sha256":
                                sha(exact.encode("utf8")),
                            "eligible_original_unresolved_units":group,
                            "change_reasons":{
                                uid:entry["change_reasons"][uid] for uid in group},
                            "actual_model_request_submitted":False,
                            "student_publication_authorized":False,
                            "source_microbatch_max_units":max_units,
                            "source_original_large_job_request_sha256":
                                entry["source_job_request_sha256"]})
    require(len(emitted)<=MAX_PLAN_JOBS,
            "More than 24 still-unclaimed jobs: split by distinct source range "
            "without dropping or resending source utterances")
    remaining=[uid for job in emitted for uid in
               job["eligible_original_unresolved_units"]]
    require(len(remaining)==len(set(remaining))
            and not (set(remaining)&claimed_ids)
            and len(remaining)+len(excluded)==len(verified_original_uids),
            "Microbatch omitted, duplicated or rescheduled consumed source units")
    return {"schema_version":1,
            "status":"UNSENT_PHYSICALLY_CHANGED_G2_SOURCE_AND_VISUAL_EVIDENCE",
            "source_sha256":source_sha,
            "original_utterances":original.get("original_utterances"),
            "original_plan_sha256":
                hashlib.sha256(original_plan.read_bytes()).hexdigest(),
            "source_microbatch_revision":MANIFEST_REVISION,
            "source_microbatch_max_units":max_units,
            "previous_consumed_units_excluded":len(excluded),
            "remaining_original_unclaimed_units":len(remaining),
            "academic_approval":False,
            "new_Gemini_or_TTS_requests":0,
            "independent_scientific_validation":False,
            "G2_approved":False,
            "student_publication_authorized":False,
            "jobs":emitted}


def ensure_microbatch_dispatch(*, original_plan:Path,
                               requested_root:Path) -> tuple[Path,Path,dict]:
    """Write-once normalized plan and sibling dispatch root, never old root.

    Both derived roots share original source-global claim index because they
    have the same checkpoint parent. Existing original jobs are untouched.
    """
    original_plan=Path(original_plan).absolute()
    requested_root=Path(requested_root).absolute()
    require(requested_root.is_dir() and not requested_root.is_symlink(),
            "Existing independent G2 checkpoint root required")
    base=requested_root.parent
    plan=unclaimed_microbatch_plan(original_plan=original_plan,
                                   checkpoint_parent=base)
    require(plan["jobs"],"No unclaimed original review jobs remain")
    derived_dir=base/".microgen_academic_microbatch_plans"
    require(not derived_dir.is_symlink(),"Unsafe immutable microbatch plan dir")
    derived_dir.mkdir(exist_ok=True)
    # review_instructions serializes the original source job in insertion
    # order; sorting nested keys changes the exact prompt bytes/SHA.
    # Preserve insertion order end-to-end and revalidate after disk reload.
    payload=json.dumps(plan,ensure_ascii=False,indent=2)+"\n"
    # New source-global claims change the remaining microbatch inventory.
    # Keep each previous short plan immutable; never overwrite it on resume.
    inventory_sha=hashlib.sha256(payload.encode("utf8")).hexdigest()[:20]
    plan_path=derived_dir/(plan["original_plan_sha256"][:20]+"_"+
                          inventory_sha+"_microbatch_v2.json")
    if plan_path.exists():
        require(not plan_path.is_symlink() and
                plan_path.read_text(encoding="utf8")==payload,
                "Existing short-plan must not be silently overwritten")
    else:
        try:
            with plan_path.open("x",encoding="utf8") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
        except FileExistsError:
            require(plan_path.read_text(encoding="utf8")==payload,
                    "Concurrent source microbatch plan drift")
    # Physical source and prompt SHA must survive exact file serialization.
    # The normal dispatcher will check again; fail before creating any
    # review attempt root when a planner serializer changes even whitespace.
    saved=_read(plan_path)
    require(saved["source_microbatch_revision"]==MANIFEST_REVISION
            and saved["source_sha256"]==plan["source_sha256"]
            and len(saved["jobs"])==len(plan["jobs"]),
            "Stale or foreign stored short-review plan")
    for entry in saved["jobs"]:
        _assert_job(entry,saved["source_sha256"])
    dispatch_root=base/(requested_root.name+"_microbatch_"+inventory_sha[:12])
    require(not dispatch_root.is_symlink(),
            "Unsafe sibling original-source short review root")
    dispatch_root.mkdir(exist_ok=True)
    return plan_path,dispatch_root,plan
