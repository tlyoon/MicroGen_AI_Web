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
# This marker is emitted by the owned local figure_composites gate, not by
# the model text. Do not classify generic model phrases or an ordinary stage
# failure as source geometry; the original Send remains permanently claimed.
_OWNED_FIGURE_COMPOSITE_REVIEW = re.compile(
    r"(?m)^\[\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\] "
    r"\[ERR\] \[FIGURE REVIEW\] Unsafe multipart mapping for page_\d+\.png:"
)
_DUPLICATE_TARGET_REASON = "ambiguous_duplicate_target_no_layout_provenance"
# Exact Python-local traceback, not a substring of model prose. The local
# worker failed during import before it could crop or click Gemini Send.
_ISOLATED_PACKAGE_IMPORT_FAILURE = re.compile(
    r"(?m)^ModuleNotFoundError: No module named 'selenium_pipeline'$"
)
# Trusted local Python exception from the exact pre-Send model verifier, not
# an ordinary Gemini message. Never infer a provider outage from this.
_PRE_SEND_OWNED_PICKER_TRACEBACK = re.compile(
    r"(?m)^selenium_pipeline\.gemini_model\.GeminiModelError: "
    r"PRE_SEND_MODE_PICKER_NOT_UNIQUE_OR_MISSING\s*$"
)
# Only trust the real vendor's anchored, timestamped own-tab picker marker,
# together with this runner's explicitly requested mode. Never infer a UI
# selection from arbitrary Gemini response text or a parent-tab preflight.
_EXPECTED_UI_MODE = re.compile(
    r"(?m)^\[microgen\] browser UI model: (flash|pro)\s*$")
_VENDOR_OWNED_MODE = re.compile(
    r"(?m)^\[\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\] \[INFO\] "
    r"Selected Gemini tab via mode picker: "
    r"(Open mode picker, currently [^\r\n]+?) \(phase=[^)]*\)\s*$")
_VERIFIED_OWNED_PRE_SEND = re.compile(
    r"(?m)^\[\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\] \[INFO\] "
    r"\[GEMINI-MODE\] PRE_SEND_OWNED_FAMILY_VERIFIED "
    r"(Open mode picker, currently [^\r\n]+)\s*$")
_EXPECTED_THINKING = re.compile(
    r"(?m)^\[microgen\] browser thinking level: (low|medium|high)\s*$")
_VERIFIED_THINKING = re.compile(
    r"(?m)^\[\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\] \[INFO\] "
    r"\[GEMINI-THINKING\] PRE_SEND_OWNED_LEVEL_VERIFIED "
    r"(low|medium|high)\s*$")


def audit_original_stage_model_family(raw: str, *, registered_send: bool) -> dict:
    """Source-log only: detect a bad owned model family, never infer outage."""
    from .gemini_model import _matches_mode
    requested = _EXPECTED_UI_MODE.search(raw)
    mode = requested.group(1) if requested else None
    selected = _VENDOR_OWNED_MODE.findall(raw)
    verified = _VERIFIED_OWNED_PRE_SEND.findall(raw)
    wrong = bool(
        registered_send and mode and selected
        and any(not _matches_mode(label, mode) for label in selected))
    valid_pre_send = bool(
        registered_send and mode and verified
        and all(_matches_mode(label, mode) for label in verified))
    expected_thinking_match = _EXPECTED_THINKING.search(raw)
    expected_thinking = (expected_thinking_match.group(1)
                         if expected_thinking_match else None)
    verified_thinking = _VERIFIED_THINKING.findall(raw)
    # Historical stages lacking an explicit expected thinking level are
    # informational only; do not rewrite old receipts to pretend they were
    # generated with Medium. New attempts have a runner-owned expectation,
    # and a missing/mismatched pre-Send proof invalidates acceptance.
    thinking_contract_breach = bool(
        registered_send and expected_thinking and
        (not verified_thinking or any(
            observed != expected_thinking for observed in verified_thinking)))
    return {
        "expected_ui_family_from_owned_stage_log": mode or "UNVERIFIED",
        "owned_worker_picker_observation_count": len(selected),
        "owned_worker_wrong_ui_family_observed": wrong,
        "owned_worker_requested_family_verified_immediately_before_send":
            valid_pre_send,
        "model_family_recovery_route": (
            "CORRECT_OWNED_TAB_MODEL_SELECTION_AND_USE_DISTINCT_SOURCE_NO_RESEND"
            if wrong else "NO_MODEL_FAMILY_MISMATCH_PROVEN"),
        "provider_generation_caused_by_model_mismatch_proven": False,
        "expected_thinking_level_from_owned_stage_log":
            expected_thinking or "UNVERIFIED_HISTORICAL",
        "owned_worker_thinking_pre_send_proof_count": len(verified_thinking),
        "owned_worker_thinking_contract_breach_observed":
            thinking_contract_breach,
        "owned_worker_requested_thinking_verified_before_send": bool(
            registered_send and expected_thinking and verified_thinking
            and not thinking_contract_breach),
        "thinking_contract_recovery_route": (
            "ADAPT_OWNED_TAB_THINKING_MENU_ON_DISTINCT_SOURCE_NO_RESEND"
            if thinking_contract_breach else
            "NO_THINKING_LEVEL_BREACH_PROVEN"),
    }


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
    # Both operands must be canonicalized identically: Windows CI may
    # expose LOCALAPPDATA and TemporaryDirectory through different aliases.
    # Comparing Path.resolve() against Path.absolute() silently hides valid
    # nested crop evidence on those hosts.
    if (not staged.is_absolute() or
            not staged.resolve(strict=False).is_relative_to(
                trial.resolve(strict=True)) or
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
    # The canonical shared proof recognises both older Send markers and the
    # current vendor [TIMING] ... registered=True evidence. Count distinct
    # anchored markers only; never inspect arbitrary prompt or model text.
    registered_send_count = (len(_SEND_PROOF.findall(raw))
                             if backend == "selenium" else 0)
    send = registered_send_count > 0
    response_unverified = (
        "[GEMINI-RESPONSE] POST_SUBMIT_NO_ATTRIBUTED_RESPONSE_NO_RESEND"
        in raw)
    owned_ui_terminal = (
        "[GEMINI-RESPONSE] OWNED_VISIBLE_UI_TERMINAL_ERROR_NO_RESEND"
        in raw)
    supervisor_timeout = (
        "[microgen-supervisor] OWNED_STAGE_TIMEOUT" in raw)
    supervisor_completed = (
        "[microgen-supervisor] OWNED_STAGE_EXIT_CODE=" in raw)
    composite_gate = (
        stage == "figures" and
        bool(_OWNED_FIGURE_COMPOSITE_REVIEW.search(raw)))
    duplicate_target_geometry = (
        composite_gate and _DUPLICATE_TARGET_REASON in raw)
    local_worker_import_failure = (
        stage == "figures" and not send
        and bool(_ISOLATED_PACKAGE_IMPORT_FAILURE.search(raw)))
    pre_send_picker_failure = bool(
        backend == "selenium" and not send
        and "[GEMINI-MODE] OWNED_FAMILY_VERIFIED_AFTER_NEW_CHAT" in raw
        and "gemini_model.py" in raw
        and _PRE_SEND_OWNED_PICKER_TRACEBACK.search(raw))
    family_audit = audit_original_stage_model_family(
        raw, registered_send=send if backend == "selenium" else False)
    state = result.get("status") if result is not None else None
    if state in ACCEPTED:
        label = "TECHNICAL_STAGE_RECEIPT_SUCCESS_NOT_FULL_LECTURE"
    elif send and owned_ui_terminal:
        label = "REGISTERED_BROWSER_SEND_OWNED_UI_ERROR_NO_RESEND"
    elif send and response_unverified:
        label = "REGISTERED_BROWSER_SEND_NO_ATTRIBUTED_REPLY_NO_RESEND"
    elif send and composite_gate:
        label = ("SOURCE_FIGURE_DUPLICATE_TARGET_GEOMETRY_REQUIRED_NO_RESEND"
                 if duplicate_target_geometry else
                 "SOURCE_FIGURE_COMPOSITE_PROVENANCE_REQUIRED_NO_RESEND")
    elif send:
        label = "REGISTERED_BROWSER_SEND_BUT_NO_ACCEPTED_STAGE"
    elif local_worker_import_failure:
        label = "ISOLATED_WINDOWS_WORKER_IMPORT_FAILED_BEFORE_MODEL_SEND"
    elif pre_send_picker_failure:
        label = "GEMINI_UI_PICKER_UNVERIFIED_BEFORE_SEND_NO_RESEND"
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
        "registered_browser_send_count_in_stage_log": registered_send_count,
        "post_submit_model_reply_attribution_unverified": response_unverified,
        "owned_visible_ui_terminal_error_verified": (send and owned_ui_terminal),
        "figure_composite_local_gate_observed": composite_gate,
        "local_worker_package_import_failed": local_worker_import_failure,
        "owned_picker_rejected_before_send": pre_send_picker_failure,
        "local_worker_import_remedy": (
            "INCLUDE_CHECKED_OUT_REPO_IN_ISOLATED_WORKER_PYTHONPATH"
            if local_worker_import_failure else "NOT_APPLICABLE"),
        **family_audit,
        "source_figure_geometry_blocker": (
            "DUPLICATE_TARGET_WITHOUT_SOURCE_LAYOUT"
            if duplicate_target_geometry else
            "UNSAFE_COMPOSITE_WITHOUT_SOURCE_PROVENANCE"
            if composite_gate else "NOT_OBSERVED"),
        "safe_recovery_route": (
            "INDEPENDENT_SOURCE_SPACE_GEOMETRY_EVIDENCE_NO_MODEL_RESEND"
            if composite_gate else
            "ATOMIC_OWNED_PICKER_SNAPSHOT_AND_BOUNDED_PRE_SEND_RECHECK"
            if pre_send_picker_failure else
            "NORMAL_STAGE_GATE_REMAINS_IN_FORCE"),
        "owned_stage_supervisor_timeout_recorded": supervisor_timeout,
        "owned_stage_supervisor_exit_recorded": supervisor_completed,
        "unbuffered_child_output_evidence_present": (
            supervisor_timeout or supervisor_completed),
        "stage_accepted_receipt_present": state in ACCEPTED,
        "api_generation_status_observed": "NOT_CHECKED" if backend == "selenium"
                                          else "CONTENT_GENERATION_NOT_INFERRED_FROM_LOG",
        "provider_outage_proven": False,
        "browser_automation_or_capture_failure_proven": pre_send_picker_failure,
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
    pre_send_picker_failure = report.get("owned_picker_rejected_before_send") is True
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
                "post_submit_model_reply_attribution_unverified",
                "owned_visible_ui_terminal_error_verified",
                "registered_browser_send_count_in_stage_log",
                "figure_composite_local_gate_observed",
                "source_figure_geometry_blocker",
                "safe_recovery_route",
                "local_worker_package_import_failed",
                "local_worker_import_remedy",
                "owned_picker_rejected_before_send",
                "expected_ui_family_from_owned_stage_log",
                "owned_worker_picker_observation_count",
                "owned_worker_wrong_ui_family_observed",
                "owned_worker_requested_family_verified_immediately_before_send",
                "model_family_recovery_route",
                "provider_generation_caused_by_model_mismatch_proven",
                "expected_thinking_level_from_owned_stage_log",
                "owned_worker_thinking_pre_send_proof_count",
                "owned_worker_thinking_contract_breach_observed",
                "owned_worker_requested_thinking_verified_before_send",
                "thinking_contract_recovery_route",
            }
            only_new_fields = set(report) - set(prior)
            compatible_status = (
                prior.get("status") == report["status"] or
                (prior.get("status") == "SOURCE_STAGE_HALTED_NO_REGISTERED_SEND"
                 and report["status"] ==
                    "LOCAL_PDF_FIGURE_CROP_PROGRESSED_SEND_UNVERIFIED") or
                (prior.get("status") == "REGISTERED_BROWSER_SEND_BUT_NO_ACCEPTED_STAGE"
                 and report["status"] ==
                    "REGISTERED_BROWSER_SEND_NO_ATTRIBUTED_REPLY_NO_RESEND") or
                (prior.get("status") == "REGISTERED_BROWSER_SEND_BUT_NO_ACCEPTED_STAGE"
                 and report["status"] in {
                    "SOURCE_FIGURE_DUPLICATE_TARGET_GEOMETRY_REQUIRED_NO_RESEND",
                    "SOURCE_FIGURE_COMPOSITE_PROVENANCE_REQUIRED_NO_RESEND"}) or
                (prior.get("status") == "BROWSER_SESSION_SEEN_SEND_UNVERIFIED"
                 and report["status"] ==
                    "ISOLATED_WINDOWS_WORKER_IMPORT_FAILED_BEFORE_MODEL_SEND") or
                (prior.get("status") ==
                    "LOCAL_EXTRACTION_DONE_BROWSER_SESSION_SEEN_SEND_UNVERIFIED"
                 and report["status"] ==
                    "GEMINI_UI_PICKER_UNVERIFIED_BEFORE_SEND_NO_RESEND"))
            old_claim_safe = (
                prior.get("automatic_resubmission_authorized") is False
                and prior.get("model_requests_during_diagnosis") == 0
                and prior.get("automatic_terminal_diagnosis") is True
                and prior.get("student_publication_authorized") is False)
            # A previously immutable SUCCESS receipt may have been saved
            # before the current vendor's positive registered=True marker was
            # understood. Never rewrite its false historical observation;
            # expose a strictly same-hash, read-only upward reconciliation.
            send_upgrade = (
                prior.get("stage_accepted_receipt_present") is True
                and report.get("stage_accepted_receipt_present") is True
                and prior.get("owned_browser_send_registered") is False
                and report["owned_browser_send_registered"] is True
                and report["registered_browser_send_count_in_stage_log"] > 0
                and prior.get("terminal_result_sha256") == result_hash
                and prior.get("terminal_log_sha256") == log_hash)
            compatible = (
                old_claim_safe and compatible_status
                and only_new_fields.issubset(new_fields)
                and set(prior).issubset(report)
                and all(prior[k] == report[k] or
                        (k == "owned_browser_send_registered" and send_upgrade) or
                        (k == "registered_browser_send_count_in_stage_log"
                         and send_upgrade and prior[k] == 0) or
                        (k == "safe_recovery_route" and pre_send_picker_failure
                         and prior[k] == "NORMAL_STAGE_GATE_REMAINS_IN_FORCE"
                         and report[k] ==
                         "ATOMIC_OWNED_PICKER_SNAPSHOT_AND_BOUNDED_PRE_SEND_RECHECK") or
                        (k in ("browser_automation_or_capture_failure_proven",
                               "owned_picker_rejected_before_send")
                         and pre_send_picker_failure
                         and prior[k] is False and report[k] is True)
                        for k in prior if k != "status"))
            if compatible:
                update = ({"new_readonly_owned_browser_send_registered": True,
                           "new_readonly_registered_browser_send_count":
                               report["registered_browser_send_count_in_stage_log"]}
                          if send_upgrade else {})
                return {**prior, "status": "PRIOR_SHA_BOUND_TRIAGE_REUSED_NO_SEND",
                        "new_readonly_classification": report["status"],
                        "new_readonly_owned_worker_wrong_ui_family_observed":
                            report["owned_worker_wrong_ui_family_observed"],
                        "new_readonly_model_family_recovery_route":
                            report["model_family_recovery_route"],
                        "new_readonly_owned_worker_thinking_contract_breach_observed":
                            report["owned_worker_thinking_contract_breach_observed"],
                        "new_readonly_thinking_contract_recovery_route":
                            report["thinking_contract_recovery_route"],
                        "new_readonly_safe_recovery_route":
                            report["safe_recovery_route"],
                        **update}
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
