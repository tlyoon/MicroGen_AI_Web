"""Read-only source-agnostic Gemini/Selenium failure-phase triage.

Separates local figure work, Chrome attachment, registered owned-model send,
and terminal stage acceptance. Does NOT infer a Gemini outage from a timeout.
Never retries a failed source, creates another attempt, exposes prompt/key
content, or calls the paid provider.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from .original_multisource_recovery_campaign import _verified_json
from .windows_gemini_differential_probe import _local_only
from .windows_gemini_provider_halt import _SEND_PROOF, ACCEPTED, FAILED

STAGES = frozenset(("figures", "slides", "narration"))
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ATTACH = re.compile(
    r"(?i)(?:Selenium attached successfully|"
    r"\[gemini\] reusing active debug session on port 9222)")
_LOCAL_EXTRACTION = re.compile(
    r"(?i)Figure extraction completed successfully\.")
# No raw stdout, prompts, paths to credentials or provider error arguments.
MAX_LOG_BYTES = 4_000_000


def diagnose(*, trial_dir: Path, stage: str = "figures") -> dict:
    if stage not in STAGES:
        raise ValueError("Expected one Gemini source generation stage")
    trial = _local_only(trial_dir)
    if not trial.is_dir() or trial.is_symlink():
        raise ValueError("Missing isolated original stage trial")
    contract = _verified_json(trial / "fresh_trial_contract.json")
    sha = contract.get("source_sha256")
    if (contract.get("status") != "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL"
            or not isinstance(sha, str) or not _SHA.fullmatch(sha)
            or contract.get("student_publication_authorized") is not False):
        raise ValueError("Untrusted original-source stage contract")
    prefix = "figures_attempt" if stage == "figures" else "stage_" + stage
    started_path = trial / (prefix + "_started.json")
    result_path = trial / (prefix + "_result.json")
    log_path = trial / (
        "figures_stage_stdout.raw.log" if stage == "figures"
        else f"stage_{stage}_stdout.raw.log")
    started_exists = started_path.exists() or started_path.is_symlink()
    result_exists = result_path.exists() or result_path.is_symlink()
    if result_exists and not started_exists:
        raise ValueError("Result without pre-send intent: untrusted stage")
    if not started_exists:
        return {
            "schema_version": 1, "stage": stage,
            "status": "NO_STORED_STAGE_SEND_INTENT",
            "owned_browser_send_registered": False,
            "provider_outage_proven": False,
            "original_submission_resend_authorized": False,
            "new_model_or_tts_calls": False,
            "student_publication_authorized": False,
        }
    started = _verified_json(started_path)
    backend = started.get("communication_mode", "selenium")
    if (started.get("stage") != stage
            or started.get("source_sha256") != sha
            or backend not in ("selenium", "api")
            or (backend == "api" and
                started.get("paid_content_api_explicitly_authorized") is not True)):
        raise ValueError("Stage pre-send intent does not match source")
    result = _verified_json(result_path) if result_exists else None
    if result is not None:
        result_sha = (result.get("original_source_sha256")
                      if stage == "figures" else result.get("source_sha256"))
        if (result_sha != sha or result.get("status") not in ACCEPTED | FAILED
                or result.get("student_publication_authorized") is not False):
            raise ValueError("Untrusted stage result or original SHA")
    raw = ""
    if log_path.exists() or log_path.is_symlink():
        if (not log_path.is_file() or log_path.is_symlink()
                or log_path.stat().st_size > MAX_LOG_BYTES):
            raise ValueError("Untrusted original-stage evidence log")
        raw = log_path.read_text(encoding="utf8", errors="replace")
    session = bool(_ATTACH.search(raw)) if backend == "selenium" else False
    local_extract = bool(_LOCAL_EXTRACTION.search(raw))
    send = bool(_SEND_PROOF.search(raw)) if backend == "selenium" else False
    state = result.get("status") if result is not None else None
    if state in ACCEPTED:
        label = "TECHNICAL_STAGE_RECEIPT_SUCCESS_NOT_FULL_LECTURE"
    elif send:
        label = "REGISTERED_BROWSER_SEND_BUT_NO_ACCEPTED_STAGE"
    elif result is None:
        label = "PRE_SEND_INTENT_WITH_NO_FINAL_RESULT_REVIEW_REQUIRED"
    elif local_extract and session:
        label = "LOCAL_EXTRACTION_DONE_BROWSER_SESSION_SEEN_SEND_UNVERIFIED"
    elif session:
        label = "BROWSER_SESSION_SEEN_SEND_UNVERIFIED"
    elif backend == "api":
        label = "API_STAGE_TERMINAL_WITHOUT_VERIFIED_RESPONSE"
    else:
        label = "SOURCE_STAGE_HALTED_NO_REGISTERED_SEND"
    return {
        "schema_version": 1, "stage": stage, "backend": backend,
        "source_sha256": sha,
        "status": label,
        "terminal_stage_receipt_status": state or "MISSING_UNRESOLVED",
        "local_figure_extraction_finished_in_log": local_extract,
        "browser_debug_session_seen_in_log": session,
        "owned_browser_send_registered": send,
        "stage_accepted_receipt_present": state in ACCEPTED,
        "api_generation_status_observed": "NOT_CHECKED" if backend == "selenium"
                                          else "CONTENT_GENERATION_NOT_INFERRED_FROM_LOG",
        "provider_outage_proven": False,
        "browser_automation_or_capture_failure_proven": False,
        "user_prompt_or_provider_secret_logged_in_report": False,
        "original_submission_resend_authorized": False,
        "new_model_or_tts_calls": False,
        "student_publication_authorized": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial-dir", required=True, type=Path)
    parser.add_argument("--stage", choices=sorted(STAGES), default="figures")
    args = parser.parse_args(argv)
    try:
        output = diagnose(trial_dir=args.trial_dir, stage=args.stage)
    except (ValueError, OSError, TypeError, KeyError) as exc:
        output = {
            "status": "STAGE_TRANSPORT_TRIAGE_EVIDENCE_REJECTED",
            "reason_type": type(exc).__name__,
            "original_submission_resend_authorized": False,
            "student_publication_authorized": False,
        }
        print(json.dumps(output, indent=2))
        return 2
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
