"""Stage-isolated Gemini browser-route environment for runner child processes.

One pipeline stage may successfully select a model and leave
MICROGEN_DYNAMIC_ROUTE_PENDING for its *own* task. A subsequent stage cannot
inherit that stage's pending identity. This helper never selects a model,
changes a Thinking radio, or authorizes a provider Send.
"""
from __future__ import annotations

import json
import os
from collections.abc import MutableMapping

_PENDING="MICROGEN_DYNAMIC_ROUTE_PENDING"
_STAGE_META=(
    "MICROGEN_MODEL_ROUTE_REASON",
    "MICROGEN_MODEL_ROUTE_REQUESTED",
    "MICROGEN_MODEL_ROUTE_OFFERED",
    "MICROGEN_ACADEMIC_SOURCE_MODEL_REQUALIFICATION_PENDING",
)
_VALID=frozenset(("figures","slides","narration","rich_mapping",
                  "academic_review","script_qa","tts","tts_qa","video"))

class StageRouteHandoffError(RuntimeError):
    pass

def sync_stage_route_env(
    stage:str,
    child_env:MutableMapping[str,str],
    parent_env:MutableMapping[str,str]|None=None,
)->bool:
    """Copy only a well-formed pending model route for the current stage.

    The parent may have a route left by the previous verified stage. Drop it
    rather than inheriting it into a new child, then allow the current stage's
    *own* ensure_mode() invocation to create a fresh request-bound identity.
    Both caller sites (stage entry and after ensure_mode) must invoke this.
    """
    if stage not in _VALID:
        raise StageRouteHandoffError("UNKNOWN_MODEL_ROUTE_STAGE_NO_SEND")
    if parent_env is None:
        parent_env=os.environ
    pending=parent_env.get(_PENDING,"")
    record=None
    if pending:
        try:
            record=json.loads(pending)
        except (ValueError,TypeError) as exc:
            raise StageRouteHandoffError("MALFORMED_PENDING_ROUTE_NO_SEND") from exc
        if (not isinstance(record,dict)
            or record.get("schema_version")!=1
            or record.get("stage") not in _VALID
            or not isinstance(record.get("family"),str)
            or not isinstance(record.get("catalog_sha256"),str)
            or len(record["catalog_sha256"])!=64):
            raise StageRouteHandoffError("INVALID_PENDING_ROUTE_IDENTITY_NO_SEND")
    current=record is not None and record["stage"]==stage
    # Even if the current stage has no dynamic route, it must never inherit a
    # stale stage's route identity or old model availability metadata.
    child_env.pop(_PENDING,None)
    for key in _STAGE_META:
        child_env.pop(key,None)
    if not current:
        if record is not None:
            parent_env.pop(_PENDING,None)
            for key in _STAGE_META:
                parent_env.pop(key,None)
        return False
    child_env[_PENDING]=pending
    for key in _STAGE_META:
        if key in parent_env:
            child_env[key]=parent_env[key]
    return True
