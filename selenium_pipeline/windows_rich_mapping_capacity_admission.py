"""Read-only rich Gemini capacity and uncertain-reply circuit before one-Send.

The old source-sized 1.2-3.0k browser canary proves owned transport only.
Original rich mapping prompts can exceed 17k characters. Before reserving
another real SHA-bound source claim, require an independently attributable
source-free canary whose payload size covers the actual prompt, plus absence
of a newer unresolved rich job after that proof. This applies across sources.
No model call, response reinterpretation, history mutation or paid fallback.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re

_LONG_PROFILE="source_sized_g2_rich_capacity_v7"
_MAX_GLOBAL_CLAIMS=1200


def _newer_uncertain_claims(*,latest:dict)->int:
    path_raw=latest.get("canary_path")
    if not isinstance(path_raw,str) or not path_raw:
        raise ValueError("RICH_CANARY_RESULT_PATH_UNVERIFIED")
    proof=Path(path_raw).absolute()
    if (proof.name!="browser_probe_result.json" or not proof.is_file()
            or proof.is_symlink() or proof.parent.is_symlink()):
        raise ValueError("RICH_CANARY_RESULT_FILE_UNTRUSTED")
    checkpoint=proof.parent.parent
    if checkpoint.name!="MicroGen_AI_Web_Checkpoints" or checkpoint.is_symlink():
        raise ValueError("RICH_CANARY_ROOT_UNTRUSTED")
    cutoff=proof.stat().st_mtime
    global_index=checkpoint/".microgen_rich_mapping_once"
    if not global_index.exists():
        return 0
    if not global_index.is_dir() or global_index.is_symlink():
        raise ValueError("RICH_GLOBAL_CLAIM_ROOT_UNTRUSTED")
    examined=0
    unresolved=0
    for source_dir in global_index.iterdir():
        if (not source_dir.is_dir() or source_dir.is_symlink()
                or re.fullmatch(r"[0-9a-f]{64}",source_dir.name) is None):
            raise ValueError("RICH_GLOBAL_CLAIM_SOURCE_UNTRUSTED")
        for path in source_dir.iterdir():
            examined+=1
            if examined>_MAX_GLOBAL_CLAIMS:
                raise ValueError("RICH_GLOBAL_CLAIM_INVENTORY_UNBOUNDED")
            if (not path.is_file() or path.is_symlink()
                    or re.fullmatch(r"slide_[0-9]{3}\.once\.json",path.name) is None
                    or path.stat().st_size>8192):
                raise ValueError("RICH_GLOBAL_CLAIM_FILE_UNTRUSTED")
            row=json.loads(path.read_text("utf8"))
            if (type(row) is not dict or row.get("schema_version")!=1
                    or row.get("global_original_source_slide_once") is not True
                    or row.get("source_inputs_sha256",{}).get("source.pdf")!=source_dir.name
                    or type(row.get("created_unix")) not in (int,float)
                    or int(row.get("slide",0))!=int(path.stem[6:9])
                    or row.get("status") not in (
                        "MAY_HAVE_SUBMITTED_RECONCILE_BEFORE_RESEND",
                        "CAPTURED_SOURCE_VERIFIED_REVIEW_ONLY")):
                raise ValueError("RICH_GLOBAL_CLAIM_EVIDENCE_UNTRUSTED")
            # An unresolved source job AFTER last successful synthetic proof
            # invalidates that proof as sufficient for another large send.
            # Already completed reviewed candidate jobs do not raise the
            # circuit. A claim can be in flight: block parallel new jobs.
            if (row["status"]=="MAY_HAVE_SUBMITTED_RECONCILE_BEFORE_RESEND"
                    and float(row["created_unix"])>=cutoff-2):
                unresolved+=1
    return unresolved


def inspect_rich_mapping_capacity(
    *, prompt_characters:int, base_admission:dict|None=None,
    latest_inspect=None, claim_risk_inspect=None,
)->dict:
    """Return a no-Send decision unless a comparable *recent* route is proven.

    The injected readers are solely for no-network fault-injection tests.
    Never mistake model request eligibility for scientific acceptance.
    """
    if type(prompt_characters) is not int or not 1<=prompt_characters<=250000:
        raise ValueError("RICH_PROMPT_LENGTH_INVALID")
    from .windows_new_source_browser_admission import (
        inspect_new_source_browser_admission,select_latest_claimed_browser_canary)
    base=(base_admission if base_admission is not None else
          inspect_new_source_browser_admission())
    if type(base) is not dict:
        raise ValueError("RICH_ROUTE_HEALTH_EVIDENCE_INVALID")
    eligible=base.get("new_source_stage_send_eligible") is True
    if not eligible:
        return {
            "status":"RICH_SOURCE_BROWSER_ROUTE_UNVERIFIED_NO_SEND",
            "rich_model_send_eligible":False,
            "requested_prompt_characters":prompt_characters,
            "rich_pending_claims_since_canary":None,
            "base_route_status":base.get("status"),
            "new_model_or_tts_calls":False,
            "student_publication_authorized":False,
        }
    latest=(latest_inspect or select_latest_claimed_browser_canary)()
    receipt=latest.get("canary") if type(latest) is dict else None
    if (latest.get("status")!="LATEST_IMMUTABLE_CANARY_IDENTIFIED"
            or type(receipt) is not dict
            or receipt.get("outcome")!="VALID_CANARY_RESPONSE"
            or receipt.get("gemini_new_user_turn_verified") is not True
            or receipt.get("source_pdf_transmitted") is not False):
        raise ValueError("RICH_SOURCE_FREE_CANARY_UNTRUSTED")
    observed=receipt.get("prompt_characters")
    profile=receipt.get("probe_profile")
    if type(observed) is not int:
        raise ValueError("RICH_CANARY_PROMPT_SIZE_UNTRUSTED")
    # A 2k canary MUST NOT green-light an 18k complex textbook request.
    # A subsequent v7 20k-capacity probe uses the same production
    # Pro/Medium owned browser transport but proves only input capacity.
    length_verified=(
        prompt_characters<=observed
        and (profile==_LONG_PROFILE if prompt_characters>3000
             else isinstance(profile,str) and profile.startswith("source_sized"))
    )
    risk=(claim_risk_inspect or _newer_uncertain_claims)(latest=latest)
    if type(risk) is not int or risk<0:
        raise ValueError("RICH_POST_CANARY_CLAIM_RISK_INVALID")
    allowed=bool(length_verified and risk==0)
    return {
        "status":(
            "RICH_SOURCE_BROWSER_CAPACITY_VERIFIED_FOR_ONE_STAGE"
            if allowed else
            "RICH_POST_CANARY_SOURCE_JOB_UNVERIFIED_NO_SEND"
            if risk else
            "RICH_PROMPT_EXCEEDS_VERIFIED_CANARY_NO_SEND"
        ),
        "rich_model_send_eligible":allowed,
        "requested_prompt_characters":prompt_characters,
        "latest_verified_canary_characters":observed,
        "latest_verified_canary_profile":profile,
        "rich_pending_claims_since_canary":risk,
        "new_model_or_tts_calls":False,
        "prior_source_claim_retry_authorized":False,
        "student_publication_authorized":False,
    }
