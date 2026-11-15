"""Canonical source-free historical Gemini route gate for NEW Windows jobs.

Normal figure/slides/narration stage admission must use this read-only gate
as well as the temporary health/capacity circuit. No new model prompt,
credential lookup, account switching, PDF upload, API call or retry happens
here. A successful JSON canary is not sufficient proof unless an actual
owned new user turn was positively verified by that same immutable claim.
"""
from __future__ import annotations

import os
from pathlib import Path

_MAX_CANARY_FOLDERS = 500


def select_latest_claimed_browser_canary(
    *, checkpoint_root: Path | None = None,
) -> dict:
    """Read latest previously claimed canary; verify its immutable source.

    Limit discovery to direct children of the established private checkpoint
    root. A newer failed/nonconforming canary cannot be bypassed by selecting
    an older successful one. A malformed latest receipt fails closed.
    """
    if checkpoint_root is None:
        local = os.environ.get("LOCALAPPDATA")
        if not local:
            raise ValueError("MICROGEN_CANARY_LOCALAPPDATA_MISSING")
        checkpoint_root = Path(local) / "MicroGen_AI_Web_Checkpoints"
    root = Path(checkpoint_root).absolute()
    if not root.is_dir() or root.is_symlink():
        return {"status": "NO_TRUSTED_SOURCE_FREE_CANARY",
                "canary": None, "canary_path": None}
    folders = list(root.iterdir())
    if len(folders) > _MAX_CANARY_FOLDERS + 2000:
        raise ValueError("MICROGEN_CANARY_INVENTORY_UNBOUNDED")
    candidates = []
    for folder in folders:
        if not folder.is_dir() or folder.is_symlink():
            continue
        proof = folder / "browser_probe_result.json"
        if proof.is_symlink():
            raise ValueError("MICROGEN_CANARY_SYMLINK_REJECTED")
        if proof.is_file():
            if proof.stat().st_size > 4096:
                raise ValueError("MICROGEN_CANARY_OVERSIZE_REJECTED")
            candidates.append(proof)
    if len(candidates) > _MAX_CANARY_FOLDERS:
        raise ValueError("MICROGEN_CANARY_PROOF_LIMIT_EXCEEDED")
    if not candidates:
        return {"status": "NO_TRUSTED_SOURCE_FREE_CANARY",
                "canary": None, "canary_path": None}
    candidates.sort(key=lambda p: (p.stat().st_mtime_ns,p.parent.name),
                    reverse=True)
    latest = candidates[0]
    from .windows_gemini_differential_probe import _read
    receipt = _read(latest)  # validates immutable prompt, claim identity/SHA
    if receipt is None or receipt.get("source_pdf_transmitted") is not False:
        raise ValueError("MICROGEN_CANARY_SOURCE_FREE_EVIDENCE_INVALID")
    return {"status": "LATEST_IMMUTABLE_CANARY_IDENTIFIED",
            "canary": receipt, "canary_path": str(latest)}


def evaluate_new_source_browser_admission(
    *, latest: dict, browser: dict, health: dict,
) -> dict:
    """Structural qualification; no inferred PASS from a raw valid response."""
    receipt = latest.get("canary")
    profile = receipt.get("probe_profile", "") if isinstance(receipt,dict) else ""
    sufficient = (
        isinstance(receipt,dict)
        and receipt.get("backend") == "browser"
        and receipt.get("status") == "GENERIC_CANARY_TERMINAL"
        and receipt.get("outcome") == "VALID_CANARY_RESPONSE"
        and isinstance(profile,str) and profile.startswith("source_sized")
        and type(receipt.get("prompt_characters")) is int
        and (1200 <= receipt["prompt_characters"] <= 3000
             or (profile == "source_sized_g2_rich_capacity_v7"
                 and 18000 <= receipt["prompt_characters"] <= 24000))
        and receipt.get("source_pdf_transmitted") is False
        and receipt.get("new_model_generation_calls") == 1
        and receipt.get("gemini_new_user_turn_verified") is True
        and receipt.get("existing_original_source_retry_permitted") is False
        and receipt.get("student_publication_authorized") is False
    )
    browser_ready = (
        isinstance(browser,dict)
        and browser.get("provider") == "gemini"
        and browser.get("status") == "AUTHENTICATED_COMPOSER_READY"
        and browser.get("authenticated_ui_ready") is True
        and browser.get("model_submission_performed") is False
    )
    health_ok = (
        isinstance(health,dict)
        and health.get("new_generation_dispatch_allowed_by_health_policy") is True
    )
    allowed = bool(sufficient and browser_ready and health_ok)
    return {
        "schema_version": 1,
        "status": ("NEW_SOURCE_GEMINI_ROUTE_VERIFIED_FOR_ONE_STAGE"
                   if allowed else
                   "NEW_SOURCE_GEMINI_ROUTE_UNVERIFIED_STOP_NO_SEND"),
        "new_source_stage_send_eligible": allowed,
        "new_source_canary_outcome": (
            receipt.get("outcome") if isinstance(receipt,dict) else None),
        "new_source_canary_profile": profile or None,
        "owned_new_user_turn_verified": (
            receipt.get("gemini_new_user_turn_verified") is True
            if isinstance(receipt,dict) else False),
        "gemini_browser_authenticated": bool(browser_ready),
        "provider_capacity_allows_new_job": bool(health_ok),
        "historical_canary_claim_verified": (
            latest.get("status") == "LATEST_IMMUTABLE_CANARY_IDENTIFIED"),
        "new_model_or_tts_calls": False,
        "old_source_retry_authorized": False,
        "automatic_api_fallback_authorized": False,
        "student_publication_authorized": False,
    }


def inspect_new_source_browser_admission(*, latest_inspect=None,
                                        browser_inspect=None,
                                        health_inspect=None) -> dict:
    """One read-only normal-stage gate; error means no model dispatch."""
    from .rich_mapping_provider_readiness import inspect_provider
    from .windows_gemini_provider_halt import inspect_halt
    latest = (latest_inspect or select_latest_claimed_browser_canary)()
    browser = (browser_inspect or (lambda: inspect_provider("gemini")))()
    health = (health_inspect or
              (lambda: inspect_halt(backend="selenium")))()
    return evaluate_new_source_browser_admission(
        latest=latest,browser=browser,health=health)
