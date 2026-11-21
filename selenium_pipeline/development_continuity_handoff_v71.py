"""Bounded dynamic *offline* handoff after a fixed v7.1 roadmap is blocked.

New work requires an exact, immutable next_*.json plan in the separately
configured local handoff directory. Each action uses the existing code-reviewed
read-only executor allowlist; no provider Sends, code writes, PRs, scheduled task
mutations or publication are available to this module.

Admission writes a durable filename->SHA claim BEFORE dispatch. A changed
source plan is quarantined, not replayed. The same filename/identical bytes
uses the original worker receipts after process restarts. Independent plans
continue when another is malformed or awaiting permission.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re

from .development_continuity_executor_v71 import (
    _atomic_json, _plan, _read_json, _sha, execute, require_recovery,
)

MAX_HANDOFF_PLANS = 12
PLAN_NAME = re.compile(r"^next_[a-zA-Z][a-zA-Z0-9_-]{0,55}\.json$")
LEDGER_NAME = "handoff_intake_v1.json"


def scan_and_dispatch(*, handoff_dir: Path, state_dir: Path,
                      repo_root: Path) -> dict:
    """Execute every eligible, source-pinned independent plan in this cycle."""
    require_recovery("IMMUTABLE_GLOBAL_OFFLINE_HANDOFF")
    from .recovery_registry import lookup_mechanism
    if (lookup_mechanism(
        "global_checkpoint_handoff",
        "V71_IMMUTABLE_INDEPENDENT_OFFLINE_HANDOFF")
        != "DISCOVER_SOURCE_PINNED_OFFLINE_PLANS_AFTER_LOCAL_BATCH"):
        raise ValueError("Missing executable global handoff recovery registration")
    # Windows can spell one directory using its 8.3 short-name alias while
    # Path.resolve() expands another. Compare CANONICAL paths, never an
    # absolute string against a resolved repository identity. Preserve
    # fail-closed symlink checks on the *supplied* paths before resolution.
    handoff_input=Path(handoff_dir).absolute()
    state_input=Path(state_dir).absolute()
    repo_input=Path(repo_root).absolute()
    if (not handoff_input.is_dir() or handoff_input.is_symlink()
        or not state_input.is_dir() or state_input.is_symlink()
        or not repo_input.is_dir() or repo_input.is_symlink()):
        raise ValueError("Offline handoff directory/state/repository ownership invalid")
    handoff_dir=handoff_input.resolve(strict=True)
    state_dir=state_input.resolve(strict=True)
    repo_root=repo_input.resolve(strict=True)
    if (handoff_dir.is_relative_to(repo_root)
        or state_dir.is_relative_to(repo_root)
        or repo_root.is_relative_to(handoff_dir)):
        raise ValueError("Offline handoff directory/state/repository ownership invalid")
    candidates=sorted(
        entry for entry in handoff_dir.iterdir()
        if entry.name.startswith("next_") and entry.name.endswith(".json"))
    if len(candidates)>MAX_HANDOFF_PLANS:
        raise ValueError("Unbounded offline handoff queue")
    ledger_path=state_dir/LEDGER_NAME
    if ledger_path.exists():
        ledger=_read_json(ledger_path)
        if (set(ledger)!={"schema_version","status","plans"}
            or ledger["schema_version"]!=1
            or ledger["status"]!="SOURCE_PINNED_GLOBAL_OFFLINE_HANDOFF"
            or type(ledger["plans"]) is not dict):
            raise ValueError("Corrupt handoff admission ledger")
    else:
        ledger={"schema_version":1,
                "status":"SOURCE_PINNED_GLOBAL_OFFLINE_HANDOFF",
                "plans":{}}
        _atomic_json(ledger_path,ledger)
    seen=0
    new_worker_starts=0
    outcomes=[]
    for plan_file in candidates:
        if not PLAN_NAME.fullmatch(plan_file.name):
            outcomes.append({"file":plan_file.name,
                             "status":"INVALID_HANDOFF_NAME_NO_EXECUTION"})
            continue
        name=plan_file.stem
        if (plan_file.is_symlink() or not plan_file.is_file()
            or not 0 < plan_file.stat().st_size <= 240000):
            outcomes.append({"file":plan_file.name,
                             "status":"INVALID_HANDOFF_FILE_NO_EXECUTION"})
            continue
        source_sha=_sha(plan_file)
        old=ledger["plans"].get(name)
        if old is not None:
            if old.get("sha256")!=source_sha:
                outcomes.append({"file":plan_file.name,
                                 "status":"CHANGED_PLAN_CONSUMED_NO_REPLAY"})
                continue
            if old.get("status")=="QUARANTINED_INVALID_PLAN":
                outcomes.append({"file":plan_file.name,
                                 "status":"PRIOR_INVALID_PLAN_QUARANTINED"})
                continue
        else:
            # The immutable claim is persisted BEFORE examining or dispatching
            # actions. A crash cannot admit another source under the same ID.
            ledger["plans"][name]={
                "sha256":source_sha,"status":"CLAIMED",
                "admitted_utc":datetime.now(timezone.utc).isoformat(),
            }
            _atomic_json(ledger_path,ledger)
        seen+=1
        try:
            _plan(plan_file)
            destination=state_dir/"handoffs"/name
            before=destination/"state.json"
            original=(_read_json(before) if before.is_file() else None)
            prior=sum(e.get("event")=="worker_started"
                      for e in original["events"]) if original else 0
            result=execute(plan_path=plan_file,state_dir=destination,
                           repo_root=repo_root)
            total=sum(e.get("event")=="worker_started"
                      for e in result["events"])
            if total < prior:
                raise ValueError("Handoff worker receipts regressed")
            delta=total-prior
            new_worker_starts+=delta
            ledger["plans"][name]["status"]=result["status"]
            ledger["plans"][name]["worker_starts"]=total
            ledger["plans"][name]["project_complete"]=result["project_complete"]
            _atomic_json(ledger_path,ledger)
            outcomes.append({"file":plan_file.name,
                "status":result["status"],"new_worker_starts":delta,
                "total_worker_starts":total,"local_plan_complete":
                    result["project_complete"],
                "student_publication_authorized":False})
        except (ValueError, RuntimeError, OSError, KeyError, TypeError) as exc:
            # Bad candidate cannot strand independent ready workstreams.
            # An uncertain child remains owned by the lower-level executor.
            ledger["plans"][name]["status"]="QUARANTINED_INVALID_PLAN"
            ledger["plans"][name]["error_class"]=type(exc).__name__
            _atomic_json(ledger_path,ledger)
            outcomes.append({"file":plan_file.name,
                "status":"QUARANTINED_INVALID_PLAN",
                "error_class":type(exc).__name__,"new_worker_starts":0})
    return {
        "schema_version":1,
        "status":("HANDOFF_DISPATCH_VERIFIED" if new_worker_starts else
                  "NO_NEW_HANDOFF_DISPATCH"),
        "discovered_plans":len(candidates),
        "source_admitted_plans":seen,
        "new_worker_starts":new_worker_starts,
        "outcomes":outcomes,
        "paid_model_requests":0,
        "code_authoring":False,
        "student_publication_authorized":False,
        "ledger":str(ledger_path),
    }
