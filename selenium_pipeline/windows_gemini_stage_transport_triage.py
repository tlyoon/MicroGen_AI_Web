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

from .original_multisource_recovery_campaign import _new_atomic, _verified_json
from .evidence_reuse_contract import file_sha256
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
_CROP_HEARTBEAT = re.compile(
    r"(?m)^\[microgen-phase\] (LOCAL_FIGURE_[A-Z_]+)"
    r"(?: (?:page|pages)=\d+)?\s*$")


def _local_crop_evidence(trial: Path, contract: dict) -> dict:
    """Safe phase-only observation from the staged, source-bound crop log.

    The nested Docling worker writes in .microgen_work and may not emit any
    lines to the outer subprocess's captured log before being terminated.
    Report only phase tokens and hashes, never raw textbook/path/model data.
    """
    observed = {
        "local_crop_process_seen_in_workspace": False,
        "local_crop_phase": "NOT_OBSERVED",
        "local_crop_heartbeat_present": False,
        "local_crop_log_sha256": None,
    }
    source = contract.get("staged_source_path")
    if type(source) is not str or not source:
        return observed
    staged = Path(source)
    if (not staged.is_absolute() or
            not staged.resolve(strict=False).is_relative_to(trial) or
            staged.is_symlink() or staged.parent.is_symlink()):
        return observed
    work = staged.parent / ".microgen_work"
    log = work / "microgen_figures.log"
    if (work.is_symlink() or log.is_symlink() or not log.is_file()):
        return observed
    if log.stat().st_size > MAX_LOG_BYTES:
        raise ValueError("Untrusted nested local figure crop log")
    raw = log.read_text(encoding="utf-8", errors="replace")
    phases = _CROP_HEARTBEAT.findall(raw)
    observed["local_crop_log_sha256"] = file_sha256(log)
    observed["local_crop_process_seen_in_workspace"] = (
        "crop_figs_v3.py" in raw or bool(phases))
    observed["local_crop_heartbeat_present"] = bool(phases)
    if phases:
        observed["local_crop_phase"] = phases[-1]
    elif observed["local_crop_process_seen_in_workspace"]:
        observed["local_crop_phase"] = "CROP_PROCESS_STARTED_NO_HEARTBEAT"
    if "Figure extraction completed successfully." in raw:
        observed["local_crop_phase"] = "LOCAL_FIGURE_CROP_COMPLETED"
    return observed


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
    crop = (_local_crop_evidence(trial, contract) if stage == "figures"
            else {"local_crop_process_seen_in_workspace": False,
                  "local_crop_phase": "NOT_APPLICABLE",
                  "local_crop_heartbeat_present": False,
                  "local_crop_log_sha256": None})
    session = bool(_ATTACH.search(raw)) if backend == "selenium" else False
    local_extract = (bool(_LOCAL_EXTRACTION.search(raw)) or
                     crop["local_crop_phase"] == "LOCAL_FIGURE_CROP_COMPLETED")
    send = bool(_SEND_PROOF.search(raw)) if backend == "selenium" else False
    supervisor_timeout = (
        "[microgen-supervisor] OWNED_STAGE_TIMEOUT" in raw)
    supervisor_completed = (
        "[microgen-supervisor] OWNED_STAGE_EXIT_CODE=" in raw)
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
    elif crop["local_crop_process_seen_in_workspace"]:
        label = "LOCAL_PDF_FIGURE_CROP_PROGRESSED_SEND_UNVERIFIED"
    elif supervisor_timeout:
        label = "OWNED_STAGE_TIMEOUT_WITHOUT_VERIFIED_BROWSER_SEND"
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
        **crop,
        "browser_debug_session_seen_in_log": session,
        "owned_browser_send_registered": send,
        "owned_stage_supervisor_timeout_recorded": supervisor_timeout,
        "owned_stage_supervisor_exit_recorded": supervisor_completed,
        "unbuffered_child_output_evidence_present": (
            supervisor_timeout or supervisor_completed),
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


def persist_terminal_triage(*, trial_dir: Path, stage: str) -> dict:
    """Automatically capture a safe, immutable diagnostic after ONE stage.

    Reads existing source/claim/result/log, writes one separate SHA-bound
    classification receipt. It never uses a browser, sends a provider request,
    retries a job, or overwrites original stage records.
    """
    if stage not in STAGES:
        raise ValueError("Only original model stages may be diagnosed")
    trial = _local_only(trial_dir)
    result_file = trial / ("figures_attempt_result.json" if stage == "figures"
                           else f"stage_{stage}_result.json")
    diagnostic_file = trial / ("figures_transport_triage.json" if stage == "figures"
                               else f"stage_{stage}_transport_triage.json")
    if (not result_file.is_file() or result_file.is_symlink()
            or result_file.stat().st_size > MAX_LOG_BYTES):
        raise ValueError("Exact immutable terminal stage result required")
    result_hash = file_sha256(result_file)
    log_file = trial / ("figures_stage_stdout.raw.log" if stage == "figures"
                        else f"stage_{stage}_stdout.raw.log")
    if log_file.exists() or log_file.is_symlink():
        if (not log_file.is_file() or log_file.is_symlink()
                or log_file.stat().st_size > MAX_LOG_BYTES):
            raise ValueError("Unsafe original terminal stage log")
        log_hash = file_sha256(log_file)
    else:
        log_hash = None
    diagnostic = diagnose(trial_dir=trial, stage=stage)
    report = {
        **diagnostic,
        "terminal_result_sha256": result_hash,
        "terminal_log_sha256": log_hash,
        "automatic_terminal_diagnosis": True,
        "automatic_resubmission_authorized": False,
        "model_requests_during_diagnosis": 0,
        "original_source_pdf_modified": False,
        "student_publication_authorized": False,
    }
    if diagnostic_file.exists() or diagnostic_file.is_symlink():
        prior = _verified_json(diagnostic_file)
        if prior != report:
            # Older evidence was recorded before optional nested Docling phase
            # inspection existed. Keep its original classification immutable,
            # but safely expose the newly observed phase on read-only reuse.
            # Exact original-result/log SHA and all historical fields must
            # still agree: an actual change to either receipt remains fatal.
            new_fields = {
                "local_crop_process_seen_in_workspace", "local_crop_phase",
                "local_crop_heartbeat_present", "local_crop_log_sha256",
            }
            only_new_fields = set(report) - set(prior)
            compatible_status = (
                prior.get("status") == report["status"] or
                (prior.get("status") == "SOURCE_STAGE_HALTED_NO_REGISTERED_SEND"
                 and report["status"] ==
                    "LOCAL_PDF_FIGURE_CROP_PROGRESSED_SEND_UNVERIFIED"))
            old_claim_safe = (
                prior.get("automatic_resubmission_authorized") is False
                and prior.get("model_requests_during_diagnosis") == 0
                and prior.get("automatic_terminal_diagnosis") is True
                and prior.get("student_publication_authorized") is False)
            compatible = (
                old_claim_safe and compatible_status
                and only_new_fields.issubset(new_fields)
                and set(prior).issubset(report)
                and all(prior[k] == report[k] for k in prior if k != "status"))
            if compatible:
                return {**prior, "status": "PRIOR_SHA_BOUND_TRIAGE_REUSED_NO_SEND",
                        "new_readonly_classification": report["status"]}
            raise ValueError("Historical stage diagnosis or evidence changed")
        return {**prior, "status": "PRIOR_SHA_BOUND_TRIAGE_REUSED_NO_SEND"}
    _new_atomic(diagnostic_file, report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial-dir", required=True, type=Path)
    parser.add_argument("--stage", choices=sorted(STAGES), default="figures")
    parser.add_argument("--persist-terminal-triage", action="store_true",
                        help="Save a separate immutable diagnostic of an existing result; never resend")
    args = parser.parse_args(argv)
    try:
        output = (persist_terminal_triage(trial_dir=args.trial_dir, stage=args.stage)
                  if args.persist_terminal_triage else
                  diagnose(trial_dir=args.trial_dir, stage=args.stage))
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
