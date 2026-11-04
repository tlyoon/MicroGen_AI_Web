"""Unified read-only Windows recovery board: source jobs + uncertain model send.

PR491 generalizes crash recovery across independently versioned source inputs.
No PDF scientific re-audit, provider retry, TTS, video render or publication.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .evidence_reuse_contract import file_sha256
from .original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked, _digest, _verified_json, require,
)
from .original_windows_batch_controller import _section_receipt_name
from .original_windows_release import inspect_campaign


def audit(*, jobs_dir: Path, fresh_trial_dir: Path) -> dict:
    require(os.name == "nt", "Windows-only recovery qualification")
    jobs_dir = Path(jobs_dir).absolute()
    fresh_trial_dir = Path(fresh_trial_dir).absolute()
    require(jobs_dir.is_dir() and fresh_trial_dir.is_dir()
            and not jobs_dir.is_symlink() and not fresh_trial_dir.is_symlink()
            and not jobs_dir.is_relative_to(fresh_trial_dir)
            and not fresh_trial_dir.is_relative_to(jobs_dir),
            "Independent external job and fresh-trial directories required")
    lock = _verified_json(jobs_dir / "windows_multisource_job_contract.json")
    require(lock.get("schema_version") == 1
            and lock.get("status") == "WINDOWS_ORIGINAL_MULTISOURCE_READ_ONLY_JOB"
            and lock.get("automatic_model_tts_or_video_execution") is False
            and lock.get("student_publication_authorized") is False,
            "Job controller contract changed or unauthorized")
    campaign = Path(lock["campaign"]).absolute()
    require(campaign.is_dir() and not campaign.is_symlink()
            and file_sha256(campaign / "original_campaign_contract.json") ==
            lock["immutable_campaign_contract_sha256"],
            "Original source campaign changed after job recording")
    canonical = _verified_json(campaign / "original_campaign_contract.json")
    require([x["section"] for x in canonical["sections"]] == lock["sections"],
            "Job controller source list changed")
    results = []
    reused_valid = 0
    missing = 0
    tampered = 0
    for entry in canonical["sections"]:
        section = entry["section"]
        target = jobs_dir / _section_receipt_name(section)
        if not target.exists() and not target.is_symlink():
            try:
                # Even a missing job needs current SHA-bound PR487 evidence.
                current = inspect_campaign(campaign=campaign, section=section)
                require(current["selected_sections"] == 1
                        and current["executed_original_sections"] == 0
                        and current["new_model_or_tts_calls"] is False
                        and current["student_publication_authorized"] is False,
                        "Missing-job original source is no longer valid")
                missing += 1
                results.append({
                    "section": section, "state": "INTERRUPTED_BEFORE_JOB_RECEIPT",
                    "safe_to_resume_read_only_status": True})
            except (CampaignRecoveryBlocked, KeyError, TypeError, ValueError,
                    OSError) as exc:
                tampered += 1
                results.append({
                    "section": section,
                    "state": "SECURITY_OR_VERSION_RECONCILIATION_REQUIRED",
                    "reason": str(exc),
                    "safe_to_resume_read_only_status": False,
                    "ready_for_single_source_render": False,
                })
            continue
        try:
            old = _verified_json(target)
            body = {k: v for k, v in old.items()
                    if k != "immutable_payload_sha256"}
            require(old.get("immutable_payload_sha256") == _digest(body)
                    and old.get("section") == section
                    and old.get("immutable_campaign_contract_sha256") ==
                    lock["immutable_campaign_contract_sha256"]
                    and old.get("original_section_fingerprint_sha256") ==
                    _digest(entry)
                    and old.get("new_scientific_review_or_paid_calls") is False
                    and old.get("student_publication_authorized") is False,
                    "Source job changed or source evidence mismatched")
            # Authenticates CURRENT originals and receipts, no figure/math re-review.
            actual = inspect_campaign(campaign=campaign, section=section)
            require(actual["selected_sections"] == 1
                    and actual["executed_original_sections"] == 0
                    and actual["new_model_or_tts_calls"] is False
                    and actual["student_publication_authorized"] is False
                    and old["readiness"] == actual["sections"][0],
                    "Original source/current readiness no longer matches ledger")
            reused_valid += 1
            results.append({
                "section": section, "state": "CURRENT_SOURCE_SHA_MATCHES_JOB",
                "safe_to_resume_read_only_status": True,
                "ready_for_single_source_render":
                    old["readiness"]["eligible_for_explicit_prepared_execution"],
            })
        except (CampaignRecoveryBlocked, KeyError, TypeError, ValueError,
                OSError) as exc:
            tampered += 1
            results.append({
                "section": section,
                "state": "SECURITY_OR_VERSION_RECONCILIATION_REQUIRED",
                "reason": str(exc),
                "safe_to_resume_read_only_status": False,
                "ready_for_single_source_render": False,
            })
    fresh = _verified_json(fresh_trial_dir / "fresh_trial_contract.json")
    require(fresh.get("schema_version") == 1
            and fresh.get("status") ==
            "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL"
            and fresh.get("paid_tts_authorized") is False
            and fresh.get("student_publication_authorized") is False,
            "Wrong original fresh-source trial contract")
    first_source = Path(fresh["source_path"])
    staged_source = Path(fresh["staged_source_path"])
    require(not first_source.is_symlink() and not staged_source.is_symlink()
            and first_source.is_file() and staged_source.is_file()
            and file_sha256(first_source) == fresh["source_sha256"]
            and file_sha256(staged_source) == fresh["source_sha256"],
            "Fresh original source/staged version changed")
    attempt_path = fresh_trial_dir / "figures_attempt_started.json"
    result_path = fresh_trial_dir / "figures_attempt_result.json"
    if attempt_path.exists() or attempt_path.is_symlink():
        started = _verified_json(attempt_path)
        require(started == {
            "schema_version": 1,
            "source_sha256": fresh["source_sha256"],
            "stage": "figures",
            "single_provider_attempt_only": True,
        }, "Ambiguous provider attempt-ledger tampering")
        if result_path.exists() or result_path.is_symlink():
            state = _verified_json(result_path)
            require(state.get("source_section") ==
                    first_source.parent.name
                    and state.get("original_source_sha256") ==
                    fresh["source_sha256"]
                    and state.get("staged_original_sha256") ==
                    fresh["source_sha256"]
                    and state.get("genuine_full_original_e2e_accepted") is False
                    and state.get("student_publication_authorized") is False
                    and state.get("new_video_rendered") is False,
                    "Invalid or falsely accepted original browser trial result")
            figure_state = state["status"]
        else:
            figure_state = "AMBIGUOUS_INTERRUPTED_PROVIDER_CALL"
        retry_allowed = False
    else:
        require(not result_path.exists() and not result_path.is_symlink(),
                "Trial result exists without immutable prior-send intent")
        figure_state = "NO_BROWSER_ATTEMPT_RECORDED"
        retry_allowed = False  # Only an explicit new approved attempt may send.

    return {
        "schema_version": 1,
        "status": ("SOURCE_JOB_RECONCILIATION_REQUIRED" if tampered else
                   "WINDOWS_RECOVERY_AUDITED_WITH_INPUT_BLOCKERS"),
        "source_job_receipts_current_and_sha_verified": reused_valid,
        "source_job_receipts_missing_due_to_possible_interruption": missing,
        "source_job_receipts_security_or_version_rejected": tampered,
        "fresh_original_publisher_and_stage_sha_verified": True,
        "fresh_original_figure_attempt_state": figure_state,
        "automatic_provider_retry_authorized": retry_allowed,
        "new_scientific_reinspection_performed": False,
        "new_model_or_tts_calls_during_this_audit": False,
        "previous_provider_submission_may_have_occurred":
            figure_state != "NO_BROWSER_ATTEMPT_RECORDED",
        "new_video_rendered": False,
        "genuine_full_source_to_video_completed": False,
        "eligible_for_student_publication": False,
        "next_development_action": (
            "Advance general release integration; separately reconcile "
            "blocked input evidence, no blind provider resend"),
        "sections": results,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs-dir", type=Path, required=True)
    parser.add_argument("--fresh-trial-dir", type=Path, required=True)
    a = parser.parse_args(argv)
    try:
        outcome = audit(jobs_dir=a.jobs_dir, fresh_trial_dir=a.fresh_trial_dir)
    except (CampaignRecoveryBlocked, OSError, ValueError) as exc:
        print(json.dumps({"status": "RECOVERY_EVIDENCE_REJECTED",
                          "reason": str(exc),
                          "eligible_for_student_publication": False}, indent=2))
        return 2
    print(json.dumps(outcome, indent=2))
    return 2 if outcome["source_job_receipts_security_or_version_rejected"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
