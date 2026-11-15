"""Forward-only, restart-safe NEW-source engineering campaign on Dell Windows.

One blocked textbook section is never a reason to revisit its uncertain
Gemini Send or stall engineering across other distinct original sources.

This module performs only the existing actual seven-stage *dry-run* for
distinct SHA-pinned publisher PDFs, then read-only next-stage inspection.
It NEVER sends a model request, executes paid TTS, encodes media, or marks
scientific/release acceptance. The model-capable single-stage runner remains
the existing separate guarded API; no bypass or reset of old once claims.

The campaign freezes a finite source list once. It persistently records each
dry-run result before moving on to the next source. On restart, physically
rehashes sources, reuses immutable per-source receipts, and never replays a
recorded trial, including failures. A damaged section is isolated so that
unrelated sources still make forward progress. The original publisher tree
is read only; all staging and receipts stay inside the external registry.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
from functools import wraps
from typing import Callable

from .evidence_reuse_contract import file_sha256
from .original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked, _new_atomic, _verified_json, require,
)
from .windows_original_source_candidate_inventory import find_candidates

_STATUS = "WINDOWS_SOURCE_INDEPENDENT_DRYRUN_CAMPAIGN_V1"
_TERMINAL = frozenset((
    "FRESH_SOURCE_SEVEN_STAGE_DRY_RUN_READY",
    "FRESH_SOURCE_DRY_RUN_FAILED",
    "FRESH_SOURCE_DRY_RUN_TIMEOUT",
))
_SLUG = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
_SECTION = re.compile(r"[0-9]+\.[0-9]+\Z")
_SHA = re.compile(r"[a-f0-9]{64}\Z")


def _trial_name(section: str, sha: str) -> str:
    return "source_" + section.replace(".", "_") + "_" + sha[:16]


def _validate_roots(*, publisher_root: Path, registry_root: Path,
                    campaign_name: str, max_sources: int) -> tuple[Path,Path,Path]:
    require(os.name == "nt", "Source advancement is native Windows only")
    source = Path(publisher_root).absolute()
    registry = Path(registry_root).absolute()
    require(source.is_dir() and registry.is_dir()
            and not source.is_symlink() and not registry.is_symlink()
            and not source.is_relative_to(registry)
            and not registry.is_relative_to(source),
            "Publisher root and existing external trial registry must be separate")
    require(type(campaign_name) is str and _SLUG.fullmatch(campaign_name)
            is not None and type(max_sources) is int
            and 1 <= max_sources <= 12,
            "Bounded, safely named forward-source campaign required")
    # The normal Windows immutable claim writers use local filesystem rename.
    # No original evidence, checkpoints or source files may be written on G:.
    local = Path(os.environ.get("LOCALAPPDATA", "")).absolute()
    require(local.is_dir() and registry.is_relative_to(local),
            "External source staging registry must reside under LOCALAPPDATA")
    campaign = registry / campaign_name
    require(not campaign.exists() or (campaign.is_dir()
            and not campaign.is_symlink()),
            "Unsafe or symlinked existing source advancement campaign")
    return source, registry, campaign


def _contract(*, source: Path, registry: Path, selected: list[dict],
              max_sources: int) -> dict:
    return {
        "schema_version":1,
        "status":_STATUS,
        "publisher_root":str(source),
        "external_registry":str(registry),
        "selected_distinct_sources":[{
            "section":row["section"],
            "relative_source_path":row["relative_source_path"],
            "source_sha256":row["source_sha256"],
            "source_bytes":row["source_bytes"],
        } for row in selected],
        "max_selected_new_sources":max_sources,
        "single_source_stage_send_authorized":False,
        "model_tts_or_video_execution":False,
        "old_source_retry_authorized":False,
        "student_publication_authorized":False,
    }


def _validate_contract(contract:dict,*,source:Path,registry:Path,
                       max_sources:int) -> list[dict]:
    require(type(contract) is dict and contract.get("schema_version")==1
            and contract.get("status")==_STATUS
            and contract.get("publisher_root")==str(source)
            and contract.get("external_registry")==str(registry)
            and contract.get("max_selected_new_sources")==max_sources
            and contract.get("single_source_stage_send_authorized") is False
            and contract.get("model_tts_or_video_execution") is False
            and contract.get("old_source_retry_authorized") is False
            and contract.get("student_publication_authorized") is False,
            "Forward-source campaign contract changed or incompatible")
    rows=contract.get("selected_distinct_sources")
    require(type(rows) is list and len(rows)<=max_sources,
            "Unsafe source campaign inventory size")
    names=set()
    hashes=set()
    for row in rows:
        require(type(row) is dict
                and set(row)=={
                    "section","relative_source_path","source_sha256","source_bytes"}
                and type(row["section"]) is str
                and _SECTION.fullmatch(row["section"]) is not None
                and type(row["source_sha256"]) is str
                and _SHA.fullmatch(row["source_sha256"]) is not None
                and type(row["source_bytes"]) is int and row["source_bytes"]>100
                and row["relative_source_path"]==(
                    row["section"].split(".")[0]+"/"+row["section"]+"/source.pdf"),
                "Invalid immutable forward-source candidate")
        require(row["section"] not in names
                and row["source_sha256"] not in hashes,
                "Duplicate source or conflicting section in immutable campaign")
        names.add(row["section"])
        hashes.add(row["source_sha256"])
    return rows


def _exclusive_campaign(fn):
    """Windows kernel file lease; automatically released after process crash.

    A second invocation cannot race the same source campaign, even when
    started from another ChatGPT session or different local terminal.
    Do NOT delete the lock file: the kernel lease, not file existence,
    records active ownership and survives safe process restart.
    """
    @wraps(fn)
    def guarded(*, publisher_root:Path, registry_root:Path,
                campaign_name:str="forward_source_pipeline_v1",
                max_sources:int=3, **kwargs):
        _,registry,_=_validate_roots(
            publisher_root=publisher_root,registry_root=registry_root,
            campaign_name=campaign_name,max_sources=max_sources)
        lock=registry/(".microgen_forward_"+campaign_name+".lock")
        require(not lock.is_symlink()
                and (not lock.exists() or
                     lock.is_file() and lock.stat().st_size<=1),
                "Unsafe interprocess campaign lock file")
        import msvcrt
        with lock.open("a+b") as stream:
            if stream.tell()==0 and lock.stat().st_size==0:
                stream.write(b"1")
                stream.flush()
                os.fsync(stream.fileno())
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            except OSError as exc:
                raise CampaignRecoveryBlocked(
                    "Another forward campaign invocation is active; "
                    "no concurrent source reprocessing") from exc
            try:
                return fn(publisher_root=publisher_root,
                          registry_root=registry_root,
                          campaign_name=campaign_name,
                          max_sources=max_sources,**kwargs)
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
    return guarded


def _require_no_provider_send_intents(trial:Path)->None:
    """A dry-run with a staged Send-intent is no longer a safe dry-run."""
    if not trial.exists():
        return
    for name in ("figures_attempt_started.json",
                 "stage_slides_started.json",
                 "stage_narration_started.json",
                 "stage_script_qa_started.json"):
        p=trial/name
        require(not p.exists() and not p.is_symlink(),
                "Forward dry-run must never acquire a provider Send claim")


@_exclusive_campaign
def run_forward_campaign(
    *, publisher_root:Path, registry_root:Path,
    campaign_name:str="forward_source_pipeline_v1", max_sources:int=3,
    dryrun_runner:Callable|None=None, stage_inspector:Callable|None=None,
    after_record:Callable|None=None,
) -> dict:
    """Perform up to 12 distinct original seven-stage dry-runs, never Send.

    A callback is solely an offline injected fault-injection test seam.
    """
    source,registry,campaign=_validate_roots(
        publisher_root=publisher_root,registry_root=registry_root,
        campaign_name=campaign_name,max_sources=max_sources)
    contract_file=campaign/"forward_source_campaign_contract.json"
    if campaign.exists():
        require(contract_file.is_file() and not contract_file.is_symlink(),
                "Uncontracted source campaign directory; never overwrite")
        contract=_verified_json(contract_file)
    else:
        # Candidate search is deliberately scoped, not a global assurance
        # that no other provider session ever submitted source bytes. No
        # model call is permitted from this campaign even if found new.
        discovered=find_candidates(
            publisher_root=source,trial_registry_root=registry)
        selected=discovered["potential_new_candidates"][:max_sources]
        contract=_contract(source=source,registry=registry,selected=selected,
                           max_sources=max_sources)
        campaign.mkdir()
        _new_atomic(contract_file,contract)
    rows=_validate_contract(contract,source=source,registry=registry,
                            max_sources=max_sources)
    from .windows_fresh_source_trial import run_trial
    from .windows_lecture_progression_coordinator import inspect_progress
    runner=dryrun_runner or run_trial
    inspector=stage_inspector or inspect_progress
    reports=[]
    new=previous=rejected=0
    for row in rows:
        section=row["section"]
        sha=row["source_sha256"]
        trial=campaign/_trial_name(section,sha)
        receipt=campaign/(_trial_name(section,sha)+".dryrun.json")
        try:
            pdf=source/row["relative_source_path"]
            require(pdf.is_file() and not pdf.is_symlink()
                    and not pdf.parent.is_symlink()
                    and not pdf.parent.parent.is_symlink()
                    and pdf.stat().st_size==row["source_bytes"]
                    and file_sha256(pdf)==sha,
                    "Original source SHA/size/path changed after campaign selection")
            _require_no_provider_send_intents(trial)
            if receipt.exists() or receipt.is_symlink():
                saved=_verified_json(receipt)
                require(saved.get("schema_version")==1
                        and saved.get("section")==section
                        and saved.get("source_sha256")==sha
                        and saved.get("status") in _TERMINAL
                        and saved.get("model_or_tts_calls") is False
                        and saved.get("student_publication_authorized") is False
                        and saved.get("external_trial_dir")==str(trial),
                        "Previously completed dry-run receipt is invalid")
                state=saved["status"]
                previous+=1
                progress="PRIOR_DRY_RUN_REUSED_WITHOUT_RERUN"
            else:
                require(not trial.exists() or
                        (trial.is_dir() and not trial.is_symlink()),
                        "Unsafe external source dry-run staging folder")
                if not trial.exists():
                    trial.mkdir()
                result=runner(
                    source_root=source,section=section,trial_dir=trial,
                    attempt_figures=False)
                # Production run_trial itself rechecks original and staged
                # file SHA before returning. Do it again here even for any
                # injected/stubbed runner or unexpected local process.
                require(file_sha256(pdf)==sha
                        and pdf.stat().st_size==row["source_bytes"],
                        "Publisher source changed during forward dry-run")
                _require_no_provider_send_intents(trial)
                require(type(result) is dict
                        and result.get("status") in _TERMINAL
                        and result.get("original_source_sha256")==sha
                        and result.get("staged_original_sha256")==sha
                        and result.get("new_model_or_tts_calls") is False
                        and result.get("student_publication_authorized") is False
                        and result.get("new_video_rendered") is False,
                        "Original source dry-run has no trusted no-Send result")
                state=result["status"]
                saved={
                    "schema_version":1,"section":section,
                    "source_sha256":sha,"status":state,
                    "external_trial_dir":str(trial),
                    "model_or_tts_calls":False,
                    "student_publication_authorized":False,
                }
                _new_atomic(receipt,saved)
                new+=1
                progress="NEW_BOUNDED_SOURCE_DRY_RUN_RECORDED"
                if after_record is not None:
                    after_record(section)
            # Provider readiness is ephemeral. Read it again instead of
            # freezing a possible later change as immutable source evidence.
            stage_status="SOURCE_DRY_RUN_INCOMPLETE_NO_LIVE_STAGE"
            if state=="FRESH_SOURCE_SEVEN_STAGE_DRY_RUN_READY":
                try:
                    stage=inspector(source_root=source,section=section,
                                    trial_dir=trial)
                    require(type(stage) is dict
                            and stage.get("new_model_or_tts_calls") is False
                            and stage.get("student_publication_authorized") is False,
                            "Untrusted read-only next-stage inspection")
                    stage_status=stage.get("status")
                    require(type(stage_status) is str and len(stage_status)<128,
                            "Untrusted stage status")
                except (CampaignRecoveryBlocked,ValueError,OSError,TypeError):
                    stage_status="READ_ONLY_SOURCE_STAGE_INSPECTION_BLOCKED"
            reports.append({
                "section":section,"source_sha256":sha,
                "job_state":progress,"dry_run_status":state,
                "current_next_stage_status":stage_status,
                "new_model_or_tts_calls":False,
                "student_publication_authorized":False,
            })
        except (CampaignRecoveryBlocked,OSError,ValueError,TypeError):
            rejected+=1
            reports.append({
                "section":section,"source_sha256":sha,
                "job_state":"SOURCE_SECURITY_OR_INTEGRITY_REJECTED_NO_SEND",
                "dry_run_status":"NOT_APPROVED",
                "new_model_or_tts_calls":False,
                "student_publication_authorized":False,
            })
            # Do not abandon unrelated source inputs because this section
            # is corrupted. Never overwrite an untrusted immutable receipt.
            continue
    return {
        "schema_version":1,
        "status":(
            "NO_NEW_SOURCES_IN_SCOPED_INVENTORY" if not reports else
            "FORWARD_SOURCE_DRYRUN_PARTIAL_WITH_SECURITY_REJECTION"
            if rejected else "FORWARD_SOURCE_DRYRUN_CAMPAIGN_RECORDED"
        ),
        "campaign_contract":str(contract_file),
        "selected_distinct_original_sources":len(rows),
        "new_independent_source_dry_runs":new,
        "reused_source_dry_runs":previous,
        "rejected_source_sections":rejected,
        "new_provider_sends":0,"new_tts_calls":0,
        "media_encoded":False,"original_source_claim_replays":0,
        "verified_pdf_to_mp4_complete":False,
        "student_publication_authorized":False,
        "section_results":reports,
    }


def main(argv=None)->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--publisher-root",type=Path,required=True)
    ap.add_argument("--trial-registry-root",type=Path,required=True)
    ap.add_argument("--campaign-name",default="forward_source_pipeline_v1")
    ap.add_argument("--max-new-sources",type=int,default=3)
    args=ap.parse_args(argv)
    try:
        record=run_forward_campaign(
            publisher_root=args.publisher_root,registry_root=args.trial_registry_root,
            campaign_name=args.campaign_name,max_sources=args.max_new_sources)
    except (CampaignRecoveryBlocked,OSError,ValueError,TypeError) as exc:
        record={"status":"FORWARD_SOURCE_CAMPAIGN_REJECTED",
                "error_type":type(exc).__name__,
                "new_provider_sends":0,"new_tts_calls":0,
                "student_publication_authorized":False}
    print(json.dumps(record,indent=2))
    return 2 if record["status"] in (
        "FORWARD_SOURCE_CAMPAIGN_REJECTED",
        "FORWARD_SOURCE_DRYRUN_PARTIAL_WITH_SECURITY_REJECTION") else 0


if __name__=="__main__":
    raise SystemExit(main())
