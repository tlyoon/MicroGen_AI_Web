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
                     browser_halt: dict, api_halt: dict,
                     api_key_pool: dict | None = None,
                     chatgpt_canary: dict | None = None) -> dict:
    """Qualify *future independent* requests without sending or credential use."""
    if any(type(x) is not dict for x in (
            gemini_browser, chatgpt_browser, api_preflight,
            browser_halt, api_halt)):
        raise ValueError("Only complete read-only provider evidence accepted")
    if browser_canary is not None and type(browser_canary) is not dict:
        raise ValueError("Canary evidence must be a verified object")
    if owned_ui_error is not None and type(owned_ui_error) is not dict:
        raise ValueError("Owned UI error evidence must be verified")
    if api_key_pool is not None and type(api_key_pool) is not dict:
        raise ValueError("API key pool evidence must be an object")
    if chatgpt_canary is not None and type(chatgpt_canary) is not dict:
        raise ValueError("ChatGPT canary evidence must be a verified object")
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
    # Read-only collector independently verifies the exact immutable
    # ChatGPT source-free Send claim and terminal receipt. An existing login
    # does not prove that a NEW tab can accept a new unsent prompt.
    chatgpt_editor_pre_send_blocked = (
        chatgpt_canary is not None
        and chatgpt_canary.get("status") ==
            "CHATGPT_OWNED_EDITOR_INPUT_NOT_VERIFIED_NO_SEND"
        and chatgpt_canary.get("pre_send_editor_failure_independently_verified")
            is True
        and chatgpt_canary.get("browser_submission_proven_successful") is False
        and chatgpt_canary.get("new_model_or_tts_calls") is False
        and chatgpt_canary.get("old_source_retry_authorized") is False
        and chatgpt_canary.get("student_publication_authorized") is False
    )
    prior_response_failed = (
        browser_canary is not None
        and browser_canary.get("backend") == "browser"
        and browser_canary.get("outcome") in _BAD_CANARY
        and browser_canary.get("student_publication_authorized") is False
    )
    # A successful *historical* short canary is independently verified by
    # inspect() via the immutable on-disk Send claim and response digest.
    # It proves only that one source-free model response was captured, not
    # current long-form capacity or authorization to dispatch textbooks.
    verified_browser_response_observed = (
        browser_canary is not None
        and browser_canary.get("schema_version") == 1
        and browser_canary.get("backend") == "browser"
        and browser_canary.get("outcome") == "VALID_CANARY_RESPONSE"
        and browser_canary.get("status") == "GENERIC_CANARY_TERMINAL"
        and type(browser_canary.get("response_character_count")) is int
        and 0 < browser_canary["response_character_count"] <= 5000
        and browser_canary.get("new_model_generation_calls") == 1
        and browser_canary.get("paid_api_content_may_have_occurred") is False
        and browser_canary.get("source_pdf_transmitted") is False
        and browser_canary.get("student_publication_authorized") is False
    )
    short_browser_response_observed = (
        verified_browser_response_observed
        and browser_canary.get("probe_profile", "short") == "short"
    )
    source_sized_browser_response_observed = (
        verified_browser_response_observed
        and browser_canary.get("probe_profile") == "source_sized"
        and type(browser_canary.get("prompt_characters")) is int
        and 1200 <= browser_canary["prompt_characters"] <= 3000
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
    # An opt-in independent models.get check of EACH numbered key can
    # qualify a fallback as metadata-reachable even when key #1 fails.
    # It never proves generate_content quota or grants billing consent.
    pool_ordinals = []
    if (api_key_pool is not None
            and api_key_pool.get("status") ==
                "KEY_POOL_METADATA_CHECKED_AT_LEAST_ONE_REACHABLE"
            and api_key_pool.get("model_generate_content_calls") == 0
            and api_key_pool.get("paid_api_content_generation_authorized") is False):
        entries = api_key_pool.get("metadata_eligible_new_source_key_ordinals")
        if (type(entries) is list and all(type(x) is int and 1 <= x <= 6
                                          for x in entries)
                and len(set(entries)) == len(entries)):
            pool_ordinals = entries
    api_new_source_candidate = (
        (api_model_reachable or bool(pool_ordinals))
        and api_halt.get("new_generation_dispatch_allowed_by_health_policy")
            is True
    )
    # Owner override: Gemini Selenium is the ONLY generation transport.
    # ChatGPT and Gemini API metadata are diagnostics, never fallback choices.
    if gemini_ready and not gemini_not_healthy_enough_to_select:
        route = (
            "GEMINI_BROWSER_PRIOR_SOURCE_SIZED_INPUT_OK_FULL_LESSON_UNTESTED"
            if source_sized_browser_response_observed else
            "GEMINI_BROWSER_PRIOR_SHORT_CANARY_OK_LONG_FORM_UNTESTED"
            if short_browser_response_observed else
            "GEMINI_BROWSER_COMPOSER_READY_GENERATION_NOT_CERTIFIED"
        )
    else:
        route = "GEMINI_SELENIUM_TEMPORARY_FAILURE_STOP"
    return {
        "schema_version": 1,
        "status": "SOURCE_FREE_PROVIDER_ROUTE_PREFLIGHT_ONLY",
        "suggested_new_unsent_job_route": route,
        "gemini_browser_authenticated": gemini_ready,
        "chatgpt_browser_authenticated": chatgpt_ready,
        "chatgpt_browser_editor_unverified_by_sha_bound_canary":
            bool(chatgpt_editor_pre_send_blocked),
        "chatgpt_login_not_evidence_of_new_prompt_submission": True,
        "prior_source_free_browser_canary_unverified": bool(prior_response_failed),
        "prior_short_browser_generation_success_recorded":
            bool(short_browser_response_observed),
        "prior_source_sized_text_input_success_recorded":
            bool(source_sized_browser_response_observed),
        "prior_short_success_never_certifies_current_long_form": True,
        "prior_source_sized_input_never_certifies_full_lecture": True,
        "owned_gemini_ui_error_sha_verified": bool(ui_error_observed),
        "gemini_browser_auto_selection_suppressed_by_prior_evidence":
            bool(gemini_not_healthy_enough_to_select),
        "api_model_metadata_reachable_not_generation_proven":
            bool(api_model_reachable),
        "api_distinct_new_source_candidate_with_separate_cost_authorization":
            False,  # No API generation route under Gemini Selenium-only policy.
        "api_key_pool_metadata_verified_candidate_ordinals": list(pool_ordinals),
        "api_key_rotation_metadata_checked_not_content_proven":
            api_key_pool is not None,
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
            prior_owned_ui_quarantine: Path | None = None,
            inspect_all_api_keys_metadata: bool = False,
            prior_chatgpt_canary_root: Path | None = None) -> dict:
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
    # Gemini Selenium ONLY: do not inspect ChatGPT sessions or perform even
    # read-only Gemini API metadata probes in the normal G1 route checker.
    chatgpt = blank("chatgpt")
    api = api_inspect(metadata_probe=False)
    pool = None
    canary = None
    if prior_canary_root is not None:
        root = _local_only(Path(prior_canary_root))
        canary = _read(root / "browser_probe_result.json")
        if canary is None or canary.get("backend") != "browser":
            raise ValueError("No trusted prior source-free browser canary")
    owned_ui = (inspect_quarantine(metadata_path=prior_owned_ui_quarantine)
                if prior_owned_ui_quarantine is not None else None)
    chatgpt_canary = None
    if prior_chatgpt_canary_root is not None:
        from .windows_chatgpt_sourcefree_canary import inspect_existing_no_send
        chatgpt_canary = inspect_existing_no_send(
            root=Path(prior_chatgpt_canary_root))
    return recommend_routes(
        gemini_browser=gemini, chatgpt_browser=chatgpt,
        api_preflight=api, browser_canary=canary,
        owned_ui_error=owned_ui,
        browser_halt=inspect_halt(backend="selenium"),
        api_halt=inspect_halt(backend="api"),
        api_key_pool=pool, chatgpt_canary=chatgpt_canary,
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inspect-browsers", action="store_true",
                   help="Read existing Chrome sessions only; do not send or login")
    p.add_argument("--check-api-model-metadata", action="store_true",
                   help="One Gemini models.get only; not generate_content")
    p.add_argument("--verify-all-api-key-metadata", action="store_true",
                   help="Read-only models.get once per configured key; no generation")
    p.add_argument("--prior-browser-canary-root", type=Path)
    p.add_argument("--prior-chatgpt-canary-root", type=Path,
                   help="Read-only verify previous source-free editor failure; no Send")
    p.add_argument("--prior-owned-ui-quarantine-meta", type=Path)
    a = p.parse_args(argv)
    try:
        report = inspect(
            inspect_browsers=a.inspect_browsers,
            check_api_metadata=a.check_api_model_metadata,
            prior_canary_root=a.prior_browser_canary_root,
            prior_chatgpt_canary_root=a.prior_chatgpt_canary_root,
            prior_owned_ui_quarantine=a.prior_owned_ui_quarantine_meta,
            inspect_all_api_keys_metadata=a.verify_all_api_key_metadata)
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
