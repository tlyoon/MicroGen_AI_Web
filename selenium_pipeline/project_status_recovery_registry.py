"""Allowlisted, no-Send recovery hook for honest project status monitoring."""
from __future__ import annotations
import json
from pathlib import Path

REGISTRY=Path(__file__).with_name("project_status_recovery_registry_v1.json")
_ENTRY={
  "match_type":"development_status_watchdog",
  "signature":"V71_PROJECT_TASK_DISABLED_STALE_OR_HEARTBEAT_MISSING",
  "mechanism":"INSPECT_NATIVE_TASK_AND_REPORT_VERIFIED_STALL_WITHOUT_UNSAFE_REPLAY",
  "handler":"NORMAL_WINDOWS_PROJECT_STATUS_MONITOR",
  "enabled":True,
  "retry_limit":0,
}
def lookup_mechanism(match_type: str, signature: str, *, path: Path|None=None) -> str|None:
    target=Path(path or REGISTRY)
    if (not target.is_file() or target.is_symlink()
        or not 1 <= target.stat().st_size <= 4096):
        raise ValueError("Unsafe or missing project status recovery registry")
    obj=json.loads(target.read_text(encoding="utf8"))
    if (type(obj) is not dict or set(obj)!={"schema_version","status","entries"}
        or obj["schema_version"]!=1
        or obj["status"]!="SOURCE_BOUND_PROJECT_STATUS_RECOVERY_V1"
        or type(obj["entries"]) is not list or len(obj["entries"])!=1
        or obj["entries"][0]!=_ENTRY):
        raise ValueError("Unregistered, disabled or modified project status handler")
    if match_type!=_ENTRY["match_type"] or signature!=_ENTRY["signature"]:
        return None
    return _ENTRY["mechanism"]
