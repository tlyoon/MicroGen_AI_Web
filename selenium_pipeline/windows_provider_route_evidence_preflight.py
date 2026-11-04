"""Windows provider route preflight: observable evidence, never an automatic retry.

Read-only optional checks of Gemini and ChatGPT browser readiness, Gemini API
model metadata, a *prior* immutable source-free browser canary and existing
quarantined visible model UI error. An authenticated composer proves neither
model generation nor a ready fallback. No new user prompt, source PDF,
generate_content, account login, media render, or billed call occurs here.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

_BAD_CANARY = frozenset((
    "NO_VERIFIED_RESPONSE", "RESPONSE_RETURNED_BUT_NONCONFORMING",
    "UNRESOLVED_CLAIM",
))


def recommend_routes(*, gemini_browser: dict, chatgpt_browser: dict,
                     api_preflight: dict, browser_canary: dict | None,
                     owned_ui_error: dict | None,
                     browser_halt: dict, api_halt: dict) -> dict:
    """Qualify *future independent* requests without sending or credential use."""
    if any(type(x) is not dict for x in (
            gemini_browser, chatgpt_browser, api_preflight,
            browser_halt, api_halt)):
        raise ValueError("Only complete read-only provider evidence accepted")
    if browser_canary is not None and type(browser_canary) is not dict:
        raise ValueError("Canary evidence must be a verified object")
    if owned_ui_error is not None and type(owned_ui_error) is not dict:
        raise ValueError("Owned UI error evidence must be verified")
    gemini_ready = (
        gemini_browser.get("provider") == "gemini"
        and gemini_browser.get("authenticated_ui_ready") is True
        and gemini_browser.get("status") == "AUTHENTICATED_COMPOSER_READY"
        and gemini_browser.get("model_submission_performed") is False
    )
    chatgpt_ready = (
        chatgpt_browser.get("provider") == "chatgpt"
        and chatgpt_browser.get("authenticated_ui_ready") is True
        and chatgpt_browser.get("status") == "AUTHENTICATED_COMPOSER_READY"
        and chatgpt_browser.get("model_submission_performed") is False
    )
    prior_response_failed = (
        browser_canary is not None
        and browser_canary.get("backend") == "browser"
        and browser_canary.get("outcome") in _BAD_CANARY
        and browser_canary.get("student_publication_authorized") is False
    )
    ui_error_observed = (
        owned_ui_error is not None
        and owned_ui_error.get("known_gemini_ui_error_text_observed") is True
        and owned_ui_error.get("quarantine_payload_sha256_verified") is True
        and owned_ui_error.get("new_model_or_tts_calls") is False
        and owned_ui_error.get("original_source_retry_authorized") is False
    )
    gemini_not_healthy_enough_to_select = (
        prior_response_failed or ui_error_observed
        or browser_halt.get("new_generation_dispatch_allowed_by_health_policy")
            is not True
    )
    api_model_reachable = (
        api_preflight.get("status") ==
            "PROVIDER_READINESS_NOT_A_LESSON_GENERATION"
        and api_preflight.get("api_model_metadata") ==
            "VETTED_MODEL_METADATA_REACHABLE"
        and api_preflight.get("api_key_count_nonsecret", 0) > 0
        and api_preflight.get("paid_api_content_generation_performed") is False
        and api_preflight.get("new_model_generation_calls") == 0
    )
    api_new_source_candidate = (
        api_model_reachable
        and api_halt.get("new_generation_dispatch_allowed_by_health_policy")
            is True
    )
    if chatgpt_ready and gemini_not_healthy_enough_to_select:
        route = "CHATGPT_BROWSER_AVAILABLE_FOR_A_DISTINCT_NEW_JOB_ONLY"
    elif gemini_ready and not gemini_not_healthy_enough_to_select:
        route = "GEMINI_BROWSER_COMPOSER_READY_GENERATION_NOT_CERTIFIED"
    elif api_new_source_candidate:
        route = "GEMINI_API_METADATA_REACHABLE_COST_APPROVAL_REQUIRED"
    else:
        route = "NO_GENERATION_TRANSPORT_CERTIFIED_FOR_AUTOMATIC_DISPATCH"
    return {
        "schema_version": 1,
        "status": "SOURCE_FREE_PROVIDER_ROUTE_PREFLIGHT_ONLY",
        "suggested_new_unsent_job_route": route,
        "gemini_browser_authenticated": gemini_ready,
        "chatgpt_browser_authenticated": chatgpt_ready,
        "prior_source_free_browser_canary_unverified": bool(prior_response_failed),
        "owned_gemini_ui_error_sha_verified": bool(ui_error_observed),
        "gemini_browser_auto_selection_suppressed_by_prior_evidence":
            bool(gemini_not_healthy_enough_to_select),
        "api_model_metadata_reachable_not_generation_proven":
            bool(api_model_reachable),
        "api_distinct_new_source_candidate_with_separate_cost_authorization":
            bool(api_new_source_candidate),
        "gemini_browser_generation_proven_healthy": False,
        "gemini_api_content_generation_proven_healthy": False,
        "old_uncertain_lecture_retry_authorized": False,
        "automatic_browser_to_api_fallback_authorized": False,
        "paid_api_generation_authorized": False,
        "automatic_new_model_generation_authorized": False,
        "new_model_or_tts_calls": False,
        "original_pdf_content_modified": False,
        "student_publication_authorized": False,
    }


def inspect(*, inspect_browsers: bool = False,
            check_api_metadata: bool = False,
            prior_canary_root: Path | None = None,
            prior_owned_ui_quarantine: Path | None = None) -> dict:
    """Trusted read-only collectors; do not infer an API success from models.get."""
    from .rich_mapping_provider_readiness import inspect_provider
    from .windows_provider_readiness_probe import inspect as api_inspect
    from .windows_gemini_provider_halt import inspect_halt
    from .windows_gemini_differential_probe import _read, _local_only
    from .gemini_provider_ui_terminal_error import inspect_quarantine
    blank = lambda provider: {
        "provider": provider, "authenticated_ui_ready": False,
        "model_submission_performed": False,
        "status": "NOT_INSPECTED_NO_BROWSER_ATTACH",
    }
    gemini = inspect_provider("gemini") if inspect_browsers else blank("gemini")
    chatgpt = inspect_provider("chatgpt") if inspect_browsers else blank("chatgpt")
    api = api_inspect(metadata_probe=check_api_metadata)
    canary = None
    if prior_canary_root is not None:
        root = _local_only(Path(prior_canary_root))
        canary = _read(root / "browser_probe_result.json")
        if canary is None or canary.get("backend") != "browser":
            raise ValueError("No trusted prior source-free browser canary")
    owned_ui = (inspect_quarantine(metadata_path=prior_owned_ui_quarantine)
                if prior_owned_ui_quarantine is not None else None)
    return recommend_routes(
        gemini_browser=gemini, chatgpt_browser=chatgpt,
        api_preflight=api, browser_canary=canary,
        owned_ui_error=owned_ui,
        browser_halt=inspect_halt(backend="selenium"),
        api_halt=inspect_halt(backend="api"),
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inspect-browsers", action="store_true",
                   help="Read existing Chrome sessions only; do not send or login")
    p.add_argument("--check-api-model-metadata", action="store_true",
                   help="One Gemini models.get only; not generate_content")
    p.add_argument("--prior-browser-canary-root", type=Path)
    p.add_argument("--prior-owned-ui-quarantine-meta", type=Path)
    a = p.parse_args(argv)
    try:
        report = inspect(
            inspect_browsers=a.inspect_browsers,
            check_api_metadata=a.check_api_model_metadata,
            prior_canary_root=a.prior_browser_canary_root,
            prior_owned_ui_quarantine=a.prior_owned_ui_quarantine_meta)
    except (ValueError, OSError, TypeError, KeyError, UnicodeError) as exc:
        report = {
            "status": "PROVIDER_PREFLIGHT_EVIDENCE_REJECTED",
            "reason_type": type(exc).__name__,
            "automatic_new_model_generation_authorized": False,
            "student_publication_authorized": False,
        }
        print(json.dumps(report, indent=2))
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
