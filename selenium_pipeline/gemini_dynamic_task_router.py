"""Gemini App browser model router: official catalog ∩ live UI ∩ task needs.

The router never clicks Send or accepts a model by name alone. External
documentation proposes candidates; exact owned Selenium menu controls prove
availability; separately checked thinking radios prove effort. A persisted
default is advisory and can be invalidated without losing source claims.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path

from .gemini_official_catalog import MODEL_TIERS,LEGACY,official_ui_catalog

STAGES=frozenset(("figures","slides","narration","rich_mapping",
                  "academic_review","acoustic_qa","repair_analysis"))
LEVELS=("low","medium","high")

class DynamicGeminiRouteError(ValueError):
    pass

@dataclass(frozen=True)
class Decision:
    stage:str
    family:str
    visible_label:str
    requested_family:str
    reason:str
    required_thinking:str|None
    observed_families:tuple[str,...]
    catalog_state:str
    catalog_source_sha:str

def profiles():
    file=Path(__file__).with_name("gemini_task_profiles.json")
    obj=json.loads(file.read_text("utf8"))
    if obj.get("schema_version")!=1 or set(obj["profiles"])!=STAGES:
        raise DynamicGeminiRouteError("Invalid reviewed task profile manifest")
    return obj["profiles"]

def task_policy(stage):
    if stage not in STAGES:raise DynamicGeminiRouteError("Unknown Gemini task kind")
    return dict(profiles()[stage])

def _defaults_path():
    root=Path(os.getenv("LOCALAPPDATA") or Path.home()/".cache")
    return root/"MicroGen_AI_Web_Checkpoints"/"gemini_task_defaults_v1.json"

def _read_defaults(path):
    path=Path(path)
    if not path.exists():
        return {"schema_version":1,"task_defaults":{}}
    if path.is_symlink() or path.stat().st_size>60_000:
        raise DynamicGeminiRouteError("Unsafe task-default checkpoint")
    data=json.loads(path.read_text("utf8"))
    if (data.get("schema_version")!=1
            or not isinstance(data.get("task_defaults"),dict)):
        raise DynamicGeminiRouteError("Invalid task-default checkpoint")
    return data

def _scope(scope):
    if scope not in ("primary","alternate"):
        raise DynamicGeminiRouteError("Unrecognized authorized browser identity")
    return scope

def read_task_default(stage,*,scope="primary",path=None):
    task_policy(stage)
    slot=stage+"@"+_scope(scope)
    obj=_read_defaults(path or _defaults_path())["task_defaults"].get(slot)
    if not isinstance(obj,dict):
        return None
    if (obj.get("schema_version")!=1
            or obj.get("family") not in MODEL_TIERS
            or obj.get("thinking_level") not in (*LEVELS,"not_required")
            or obj.get("status")!="EXACT_UI_MODEL_AND_TASK_THINKING_VERIFIED"
            or obj.get("source_approval") is not False
            or obj.get("provider_send") is not False):
        return None
    return dict(obj)

def _normalize_rows(rows):
    if not isinstance(rows,(list,tuple)):
        raise DynamicGeminiRouteError("No atomic model menu evidence")
    unique={}
    for x in rows:
        if not isinstance(x,dict):raise DynamicGeminiRouteError("Invalid menu item")
        family=x.get("family")
        label=x.get("label")
        if (family not in MODEL_TIERS
                or not isinstance(label,str) or not 1<=len(label)<=230
                or type(x.get("disabled")) is not bool):
            continue
        if not x["disabled"]:
            # Do not let two selectable options for one normalized identity
            # collapse silently into an arbitrary clickable target.
            unique.setdefault(family,[]).append(label)
    return {key:values[0] for key,values in unique.items() if len(values)==1}

def choose_task_model(*,stage,requested_family,visible_rows,catalog,
                      saved=None):
    profile=task_policy(stage)
    present=_normalize_rows(visible_rows)
    verified=set(catalog.get("verified_app_families",[]))
    if (catalog.get("source_state") not in (
            "FRESH_OFFICIAL_HELP","FRESH_VERIFIED_CACHE",
            "BOUNDED_STALE_VERIFIED_CACHE")
            or not isinstance(catalog.get("help_sha256"),str)
            or len(catalog["help_sha256"])!=64):
        raise DynamicGeminiRouteError("Official Gemini Apps catalog not verified")
    candidates={name for name in present if name in verified or name in LEGACY}
    candidates={name for name in candidates
                if MODEL_TIERS[name]>=profile["minimum_tier"]}
    if not candidates:
        raise DynamicGeminiRouteError("NO_ELIGIBLE_VERIFIED_GEMINI_UI_MODEL_NO_SEND")
    if profile.get("source_bound_route_requires_independent_requalification"):
        # A changed identity for source-bound academic review needs a fresh
        # separately approved source-free transport proof; never rewrite an
        # already claimed scientific unit or silently raise its confidence.
        if requested_family not in candidates:
            raise DynamicGeminiRouteError(
                "ACADEMIC_ROUTE_CHANGED_REQUALIFICATION_REQUIRED_NO_SEND")
    preferred=list(profile["preferred"])
    if (saved and saved.get("family") in candidates
            and saved["family"] in preferred):
        chosen=saved["family"]
        why="PREVIOUS_VERIFIED_TASK_DEFAULT_REOBSERVED"
    elif requested_family in candidates:
        chosen=requested_family
        why="CURRENT_TASK_DEFAULT_AVAILABLE"
    else:
        chosen=next((name for name in preferred if name in candidates),None)
        if chosen is None:
            raise DynamicGeminiRouteError("NO_CAPABILITY_COMPATIBLE_UI_MODEL_NO_SEND")
        why="PREFERRED_MODEL_MISSING_OFFICIAL_AND_LIVE_UI_FALLBACK"
    # Stored name and current screen both refer to the same family; changing
    # version/description requires new live selection and radio verification.
    return Decision(stage,chosen,present[chosen],requested_family,why,
                    (None if chosen=="flash-lite" and stage=="figures"
                     else profile["preferred_thinking"]),
                    tuple(sorted(present)),catalog["source_state"],
                    catalog["help_sha256"])

def select_task_thinking(stage,offered,*,mode=None):
    profile=task_policy(stage)
    if stage=="figures" and mode=="flash-lite":
        return "not_required"
    if (not isinstance(offered,(list,tuple))
            or any(x not in LEVELS for x in offered)):
        raise DynamicGeminiRouteError("Unverified Thinking menu options")
    available=set(offered)
    preferred=profile["preferred_thinking"]
    floor=profile["minimum_thinking"]
    allowed={x for x in LEVELS if LEVELS.index(x)>=LEVELS.index(floor)}
    preferred_order=[preferred]+[x for x in LEVELS
                 if x!=preferred and LEVELS.index(x)>=LEVELS.index(preferred)]
    picked=next((x for x in preferred_order if x in available and x in allowed),None)
    if not picked:
        raise DynamicGeminiRouteError(
            "NO_EXPLICIT_VERIFIABLE_TASK_THINKING_LEVEL_NO_SEND")
    return picked

def save_verified_task_default(*,stage,family,visible_label,thinking_level,
                               scope="primary",path=None,
                               ui_model_verified=False,thinking_verified=False,
                               catalog_sha=None,reason=""):
    policy=task_policy(stage)
    scope=_scope(scope)
    if (family not in MODEL_TIERS or MODEL_TIERS[family]<policy["minimum_tier"]
            or not isinstance(visible_label,str) or not visible_label.strip()
            or len(visible_label)>230 or not ui_model_verified
            or not thinking_verified
            or thinking_level not in (*LEVELS,"not_required")
            or ((stage=="figures" and family=="flash-lite")
                != (thinking_level=="not_required"))
            or (thinking_level in LEVELS
                and LEVELS.index(thinking_level)<
                    LEVELS.index(policy["minimum_thinking"]))
            or not isinstance(catalog_sha,str) or len(catalog_sha)!=64
            or not isinstance(reason,str) or len(reason)>140):
        raise DynamicGeminiRouteError(
            "Cannot persist unverified UI/Thinking task default")
    dest=Path(path or _defaults_path())
    if dest.is_symlink():
        raise DynamicGeminiRouteError("Unsafe task defaults path")
    from .three_pc_worker import LocalInstanceLock
    # This is a LOCAL task-settings transaction, not a scientific receipt.
    # Serialize writers across independently launched Selenium workers; a
    # failed/conflicting writer must never lose another task's default.
    with LocalInstanceLock("gemini_task_defaults",dest.parent/"locks"):
        data=_read_defaults(dest)
        slot=stage+"@"+scope
        record={"schema_version":1,
                "status":"EXACT_UI_MODEL_AND_TASK_THINKING_VERIFIED",
                "family":family,"visible_model_label":visible_label,
                "thinking_level":thinking_level,
                "verified_at":datetime.now(timezone.utc).isoformat(),
                "catalog_sha256":catalog_sha,"route_reason":reason,
                "model_id_verified":False,"provider_send":False,
                "source_approval":False}
        # All writes after both model and actual radio proof.
        data["task_defaults"][slot]=record
        dest.parent.mkdir(parents=True,exist_ok=True)
        pending=dest.with_suffix(".new")
        if pending.exists():
            raise DynamicGeminiRouteError("Torn or concurrent defaults update")
        with pending.open("x",encoding="utf8") as f:
            json.dump(data,f,indent=2,sort_keys=True)
            f.flush();os.fsync(f.fileno())
        os.replace(pending,dest)
    return record

def dynamic_route_registered():
    """Exact historical recovery registry entry controls new-model routing."""
    try:
        from .recovery_registry import lookup_mechanism
        return lookup_mechanism(
            "presend_capability_repair",
            "TASK_DEFAULT_GEMINI_UI_MODEL_ABSENT_OFFICIAL_REPLACEMENT_REQUIRED"
        )=="OFFICIAL_GEMINI_APPS_HELP_AND_ATOMIC_OWNED_UI_TASK_POLICY_ROUTING"
    except (OSError,ValueError):
        return False


def find_dynamic_replacement(*,stage,requested_family,visible_rows,
                             scope="primary",fetch=None,cache_path=None,
                             defaults_path=None):
    """Invoked only after positive absence of the old task default."""
    if not dynamic_route_registered():
        raise DynamicGeminiRouteError("TASK_DYNAMIC_ROUTING_REGISTRY_DISABLED_NO_SEND")
    saved=read_task_default(stage,scope=scope,path=defaults_path)
    catalog=official_ui_catalog(fetch=fetch,cache_path=cache_path)
    return choose_task_model(stage=stage,requested_family=requested_family,
                             visible_rows=visible_rows,catalog=catalog,
                             saved=saved)

def commit_verified_pending_route(*,stage,owned_selected_label,
                                  thinking_level,port=9222,
                                  model_ui_checked=False,
                                  thinking_radio_checked=False):
    """Publish the next task default only after *both* owned UI proofs.

    The vendor calls this exclusively after New chat and a fresh picker plus
    exact Thinking radio verification. Never infer radio proof from a
    marketing model whose name contains "Thinking".
    """
    pending=os.getenv("MICROGEN_DYNAMIC_ROUTE_PENDING","").strip()
    if not pending:
        return None
    try:
        entry=json.loads(pending)
        if (entry.get("schema_version")!=1 or entry.get("stage")!=stage
                or entry.get("family") not in MODEL_TIERS
                or not isinstance(entry.get("catalog_sha256"),str)):
            raise DynamicGeminiRouteError("Pending dynamic route identity changed")
        from .gemini_model import _matches_mode
        family=entry["family"]
        if not _matches_mode(owned_selected_label,family):
            raise DynamicGeminiRouteError("Selected picker mismatches pending task model")
        saved=save_verified_task_default(
            stage=stage,family=family,visible_label=owned_selected_label,
            thinking_level=thinking_level,
            scope=("alternate" if port==9225 else "primary"),
            catalog_sha=entry["catalog_sha256"],
            reason=entry.get("reason",""),ui_model_verified=model_ui_checked,
            thinking_verified=thinking_radio_checked)
        os.environ.pop("MICROGEN_DYNAMIC_ROUTE_PENDING",None)
        return saved
    except (KeyError,ValueError,TypeError) as exc:
        raise DynamicGeminiRouteError(
            "Dynamic task route could not be persisted; do not Send") from exc
