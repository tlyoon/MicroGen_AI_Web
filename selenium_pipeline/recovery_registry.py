"""Fail-closed versioned recovery intelligence for the normal MicroGen pipeline.

This registry selects *only existing code-reviewed mechanisms*. It never
executes arbitrary registry code, resets retries, resubmits ambiguous Gemini
requests, overrides QA or authorizes paid operations. The stage's own claim,
source, authorization, and scientific acceptance checks remain authoritative.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

REGISTRY_PATH = Path(__file__).resolve().parent / "recovery_registry_v1.json"
_STATUS = "MICROGEN_EXECUTABLE_RECOVERY_REGISTRY_V1"
_HANDLERS = {
    "selection_action": "NORMAL_SOURCE_BOUND_G2_SUPERVISOR_AND_QUEUE",
    "supervisor_status": "NORMAL_SOURCE_BOUND_G2_SUPERVISOR_AND_QUEUE",
    "owned_transport_diagnostic": "OWNED_GEMINI_SELENIUM_RESPONSE_QUARANTINE",
    "offline_dependency": "NORMAL_G2_INDEPENDENT_SOURCE_READINESS",
    "source_mapping_repair": "NORMAL_VERIFIED_ELEMENT_RANKER",
    "slide_layout_repair": "NORMAL_BEAMER_HEADLINE_GEOMETRY_RECOVERY",
    "presend_capability_repair": "NORMAL_EXISTING_OWNED_GEMINI_ACCOUNT_CAPABILITY_PREFLIGHT",
    "transport_selection": "NORMAL_ACADEMIC_OWNED_ROUTE_AND_VERIFIED_MODEL_THINKING_PREFLIGHT",
    "tts_runtime_repair": "NORMAL_ISOLATED_TTS_WORKER_SDK_PREFLIGHT",
    "pr_stack_audit": "NORMAL_GITHUB_OPEN_PR_STACK_HEAD_CHAIN_AUDIT",
    "history_batch_inventory": "NORMAL_WINDOWS_HISTORICAL_STACK_BATCH_PLANNER",
    "history_test_root_inventory": "NORMAL_WINDOWS_HISTORICAL_STACK_BATCH_PLANNER",
    "historical_pdf_parser_abi": "NORMAL_ORIGINAL_SOURCE_E2E_READONLY_ABI_REVIEW",
    "historical_batch_execution": "NORMAL_WINDOWS_HISTORICAL_BATCH_EXECUTOR",
    "historical_format_disposition": "NORMAL_WINDOWS_SOURCE_BOUND_HISTORY_FORMAT_DISPOSITION",
    "test_helper_imports": "NORMAL_TEST_PACKAGE_SIBLING_IMPORT_RECOVERY",
    "offline_dev_autoforward": "NORMAL_WINDOWS_OFFLINE_CODE_DEVELOPMENT_CONTROLLER",
    "global_checkpoint_handoff": "NORMAL_V71_PROJECT_WIDE_OBSERVABLE_SUPERVISOR",
    "head_patch_format": "NORMAL_WINDOWS_CUMULATIVE_PATCH_FORMAT_PREFLIGHT",
}
_REQUIRED = {
    "id", "match_type", "signature", "mechanism", "classification",
    "handler", "preconditions", "verification_test", "last_verified_date",
    "environment", "retry_policy", "enabled",
}
_KINDS = frozenset(_HANDLERS)


def load_registry(path: Path | None = None) -> dict:
    target = Path(path or REGISTRY_PATH)
    if not target.is_file() or target.is_symlink():
        raise ValueError("Recovery registry absent or linked: stop before stage execution")
    if not 0 < target.stat().st_size <= 65536:
        raise ValueError("Invalid size of persistent recovery registry")
    obj = json.loads(target.read_text(encoding="utf8"))
    if (type(obj) is not dict or obj.get("schema_version") != 1
            or obj.get("status") != _STATUS or type(obj.get("entries")) is not list
            or not 1 <= len(obj["entries"]) <= 200):
        raise ValueError("Invalid persistent recovery registry structure")
    ids, names = set(), set()
    for e in obj["entries"]:
        if (type(e) is not dict or set(e) != _REQUIRED
                or type(e["enabled"]) is not bool
                or e["match_type"] not in _KINDS
                or e["handler"] != _HANDLERS.get(e["match_type"])
                or not all(type(e[field]) is str and 1 <= len(e[field]) <= 255
                           for field in _REQUIRED - {"enabled"})
                or not re.fullmatch(r"[A-Z][A-Z0-9_]{5,99}", e["id"])
                or not re.fullmatch(r"[A-Z][A-Z0-9_]{5,129}", e["signature"])
                or not re.fullmatch(r"[A-Z][A-Z0-9_]{5,129}", e["mechanism"])
                or e["last_verified_date"] > "2099-12-31"):
            raise ValueError("Unverified or unsafe recovery registry entry")
        k = (e["match_type"], e["signature"])
        if e["id"] in ids or k in names:
            raise ValueError("Duplicate or ambiguous recovery registry signature")
        ids.add(e["id"])
        names.add(k)
    return obj


def lookup_mechanism(match_type: str, signature: str,
                     *, path: Path | None = None) -> str | None:
    """Return one code-reviewed recovery label, never arbitrary executable."""
    if match_type not in _KINDS or type(signature) is not str:
        raise ValueError("Unrecognized recovery match type or signature")
    registry = load_registry(path)
    for entry in registry["entries"]:
        if entry["match_type"] == match_type and entry["signature"] == signature:
            # Disabled/retired remedies fail closed; never silently fall back
            # to a supposedly equivalent new provider retry.
            if not entry["enabled"]:
                raise ValueError("Recovery mechanism explicitly retired or disabled")
            return entry["mechanism"]
    return None
