"""One conclusive Gemini Selenium-only G1 attempt and readable stop receipt.

Never sends ChatGPT or Gemini content API. Requires an explicit fresh external
LOCALAPPDATA canary root. Re-invocation reuses the claim and terminal evidence,
not the model Send. This source-sized synthetic test cannot approve a lecture.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROFILE = "source_sized_selenium_only_v2"
SHORT_PROFILE = "short_g1_selenium_only_v3"
LONG_PROFILE = "source_sized_g1_selenium_only_v3"
REGISTRATION_PROFILE = "short_g1_registered_turn_v4"
OWNED_SOURCE_SIZED_PROFILE = "source_sized_g1_owned_turn_v5"
RICH_ROUTE_SOURCE_SIZED_PROFILE = "source_sized_g2_rich_route_v6"
APPROVED_PROFILES = (PROFILE, SHORT_PROFILE, LONG_PROFILE,
                     REGISTRATION_PROFILE, OWNED_SOURCE_SIZED_PROFILE,
                     RICH_ROUTE_SOURCE_SIZED_PROFILE)


def summarize(result: dict) -> dict:
    """Evidence-based G1 transport conclusion; do not invent provider outages."""
    from .gemini_selenium_only_policy import temporary_failure_message
    outcome = str(result.get("outcome", "UNKNOWN"))
    previous = result.get("status") in (
        "PRIOR_CANARY_RECEIPT_REUSED",
        "PRIOR_CANARY_MAY_HAVE_SUBMITTED_NO_RESEND")
    if outcome == "VALID_CANARY_RESPONSE" and (
            result.get("probe_profile") in APPROVED_PROFILES):
        short = result.get("probe_profile") in (SHORT_PROFILE, REGISTRATION_PROFILE)
        status = (
            "G1_SHORT_GEMINI_RESPONSE_VERIFIED_LONG_FORM_UNTESTED"
            if short else
            "G1_SOURCE_FREE_GEMINI_SELENIUM_SIZED_RESPONSE_VERIFIED")
        reason = (
            "The fresh short Gemini Selenium prompt returned the exact "
            "authenticated model JSON; this does NOT certify source-sized "
            "generation or an accepted academic lecture."
            if short else
            "One distinct source-sized synthetic Gemini Selenium response "
            "matched the strict owned-browser JSON receipt. This does NOT "
            "verify original PDF science or a full lecture.")
        exit_code = 0
    elif outcome == "NO_SUBMISSION_PRECHECK":
        status = "G1_BLOCKED_GEMINI_BROWSER_NOT_READY_NO_SEND"
        reason = temporary_failure_message(
            "authenticated Gemini composer unavailable",
            may_have_submitted=False)
        exit_code = 2
    elif outcome == "UNRESOLVED_CLAIM":
        status = "G1_BLOCKED_PRIOR_UNKNOWN_SUBMISSION_NO_RESEND"
        reason = temporary_failure_message(
            "an earlier immutable diagnostic claim has no terminal reply",
            may_have_submitted=True)
        exit_code = 2
    else:
        status = "G1_BLOCKED_GEMINI_SELENIUM_TEMPORARY_FAILURE"
        safe = result.get("browser_bridge_stage")
        # Always render guidance from the current verified policy. A saved
        # SHA-bound receipt is immutable and may contain superseded wording
        # (e.g., advice to revisit an owned tab closed at shutdown).
        reason = temporary_failure_message(
            safe if isinstance(safe, str) and len(safe) < 130
            else "no verified complete model response",
            may_have_submitted=(
                result.get("request_may_have_been_submitted") is not False))
        exit_code = 2
    return {
        "schema_version": 1,
        "g1_status": status,
        "gemini_selenium_only": True,
        "source_sized_synthetic_test":
            str(result.get("probe_profile","")).startswith("source_sized"),
        "outcome": outcome,
        "exact_model_answer_verified": outcome == "VALID_CANARY_RESPONSE",
        "academic_original_lecture_accepted": False,
        "request_may_have_been_submitted":
            result.get("request_may_have_been_submitted"),
        "gemini_browser_failure_phase":
            result.get("gemini_browser_failure_phase"),
        "gemini_browser_presend_attempts_used":
            result.get("gemini_browser_presend_attempts_used"),
        "gemini_send_registration_status":
            result.get("gemini_send_registration_status"),
        "gemini_new_user_turn_verified":
            result.get("gemini_new_user_turn_verified"),
        "gemini_visible_model_chars_at_stop":
            result.get("gemini_visible_model_chars_at_stop"),
        "gemini_generation_active_at_stop":
            result.get("gemini_generation_active_at_stop"),
        "browser_bridge_stage": result.get("browser_bridge_stage"),
        "prior_claim_reused_without_resend": previous,
        "model_or_browser_error_is_api_outage_proof": False,
        "chatgpt_generation_fallback": False,
        "gemini_api_generation_fallback": False,
        "old_uncertain_job_auto_retry_allowed": False,
        "reason": reason,
        "exit_code": exit_code,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--canary-root", type=Path, required=True)
    p.add_argument("--run-one-new-selenium-probe", action="store_true")
    p.add_argument("--probe-profile", choices=APPROVED_PROFILES,
                   default=PROFILE,
                   help="Explicit bounded diagnostic profile; new SHA claim required")
    a = p.parse_args(argv)
    if not a.run_one_new_selenium_probe:
        p.error("Explicit --run-one-new-selenium-probe required; no implicit Send")
    from .windows_gemini_differential_probe import run_canary
    try:
        result = run_canary(checkpoint_dir=a.canary_root,
                            backend="browser", profile=a.probe_profile)
        report = summarize(result)
    except Exception as error:
        # Bad receipts or inaccessible browser must never lead to a second
        # invocation. Report the error CLASS, never private exception args.
        from .gemini_selenium_only_policy import temporary_failure_message
        report = {
            "g1_status": "G1_BLOCKED_DIAGNOSTIC_ERROR_NO_RESEND",
            "gemini_selenium_only": True,
            "academic_original_lecture_accepted": False,
            "old_uncertain_job_auto_retry_allowed": False,
            "error_type": type(error).__name__,
            "reason": temporary_failure_message(
                "G1 local diagnostic evidence could not be trusted; "
                "inspect the existing immutable claim before running again",
                may_have_submitted=True),
            "exit_code": 2,
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    print(report["reason"], file=sys.stderr, flush=True)
    return report["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
