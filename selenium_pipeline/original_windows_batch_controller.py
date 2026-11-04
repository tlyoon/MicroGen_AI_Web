"""Resumable native-Windows multi-source job ledger for immutable original campaigns.

This intentionally schedules READINESS/status only, never batch renders or
reissues uncertain provider requests. PR487 remains the sole explicit
single-section gate for downstream prepared rendering.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Callable

from .evidence_reuse_contract import file_sha256
from .original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked, _digest, _new_atomic, _verified_json, require,
)
from .original_windows_release import inspect_campaign


def _section_receipt_name(section: str) -> str:
    require(type(section) is str and section
            and len(section) <= 30
            and section.replace(".", "").replace("-", "").isalnum(),
            "Invalid original-section identifier")
    return "section_" + section.replace(".", "_") + "_job.json"


def _job_contract(*, campaign: Path, original: dict) -> dict:
    return {
        "schema_version": 1,
        "status": "WINDOWS_ORIGINAL_MULTISOURCE_READ_ONLY_JOB",
        "campaign": str(campaign),
        "immutable_campaign_contract_sha256":
            file_sha256(campaign / "original_campaign_contract.json"),
        "sections": [item["section"] for item in original["sections"]],
        "automatic_model_tts_or_video_execution": False,
        "student_publication_authorized": False,
    }


def run_batch(*, campaign: Path, jobs_dir: Path,
              sections: list[str] | None = None,
              after_record: Callable[[str], None] | None = None) -> dict:
    """Persist independently verified per-section status; restart without redo.

    A blocked source is a legitimate status, not a system-wide failure. A
    stale/tampered accepted job receipt fails closed for that section.
    """
    campaign = Path(campaign).absolute()
    jobs_dir = Path(jobs_dir).absolute()
    require(os.name == "nt", "Native Windows is required")
    require(campaign.is_dir() and not campaign.is_symlink()
            and jobs_dir.is_dir() and not jobs_dir.is_symlink(),
            "Existing, non-symlink campaign and external jobs directories required")
    require(campaign != jobs_dir
            and not jobs_dir.is_relative_to(campaign)
            and not campaign.is_relative_to(jobs_dir),
            "Never store job receipts inside an immutable original campaign")
    original = _verified_json(campaign / "original_campaign_contract.json")
    require(original.get("schema_version") == 1
            and original.get("status") ==
            "SOURCEBOUND_WINDOWS_MULTISOURCE_ORIGINAL_VERSIONED_CAMPAIGN"
            and original.get("new_model_tts_or_video_generation_permitted") is False
            and original.get("student_publication_authorized") is False,
            "Only safe immutable source campaigns can be scheduled")
    entries = original.get("sections")
    require(type(entries) is list and 1 <= len(entries) <= 12,
            "Expected 1-12 canonical original source sections")
    available = [entry["section"] for entry in entries]
    names = [_section_receipt_name(section) for section in available]
    require(len(set(names)) == len(names), "Ambiguous source job receipt names")
    lectures = [Path(entry["lecture"]).absolute() for entry in entries]
    require(all(not jobs_dir.is_relative_to(lecture)
                and not lecture.is_relative_to(jobs_dir) for lecture in lectures),
            "The job directory must be outside frozen publisher/author inputs")
    if sections is not None:
        require(type(sections) is list and len(sections) > 0
                and len(set(sections)) == len(sections)
                and set(sections).issubset(available),
                "Requested source job sections must be unique and in campaign")
    chosen = set(sections) if sections is not None else set(available)
    lock = _job_contract(campaign=campaign, original=original)
    lock_path = jobs_dir / "windows_multisource_job_contract.json"
    if lock_path.exists() or lock_path.is_symlink():
        require(_verified_json(lock_path) == lock,
                "Different immutable campaign; start a NEW versioned Windows job")
    else:
        _new_atomic(lock_path, lock)

    records = []
    newly_recorded = 0
    reused = 0
    rejected = 0
    for entry in entries:
        section = entry["section"]
        if section not in chosen:
            continue
        # Each inspection hashes the current original + mapping evidence but
        # NEVER re-runs PDF academic analysis or calls providers.
        try:
            current = inspect_campaign(campaign=campaign, section=section)
            require(current["selected_sections"] == 1
                    and current["executed_original_sections"] == 0
                    and current["new_model_or_tts_calls"] is False
                    and current["student_publication_authorized"] is False
                    and len(current["sections"]) == 1,
                    "Unsafe or incomplete original-section status")
            row = current["sections"][0]
            require(row["section"] == section
                    and row["student_publication_authorized"] is False
                    and row["new_model_or_tts_calls"] is False,
                    "Untrusted original-section inspection")
            body = {
                "schema_version": 1,
                "section": section,
                "immutable_campaign_contract_sha256":
                    lock["immutable_campaign_contract_sha256"],
                "original_section_fingerprint_sha256": _digest(entry),
                "readiness": row,
                "new_scientific_review_or_paid_calls": False,
                "student_publication_authorized": False,
            }
            receipt = {**body, "immutable_payload_sha256": _digest(body)}
            path = jobs_dir / _section_receipt_name(section)
            if path.exists() or path.is_symlink():
                saved = _verified_json(path)
                require(saved == receipt,
                        "Previously accepted section job receipt stale or tampered")
                reused += 1
                record_state = "REUSED_SAME_SOURCE_VERIFIED_JOB"
            else:
                _new_atomic(path, receipt)
                newly_recorded += 1
                record_state = "NEW_SOURCE_VERIFIED_JOB"
            records.append({
                "section": section,
                "job_state": record_state,
                "source_status": row["status"],
                "eligible_for_prepared_single_section_execution":
                    row["eligible_for_explicit_prepared_execution"],
                "remaining_unresolved_mappings":
                    row.get("remaining_unresolved_mappings"),
            })
            if after_record is not None:
                after_record(section)
        except CampaignRecoveryBlocked as exc:
            # One damaged original section MUST NOT erase accepted others.
            # No tainted receipt is written; caller gets a nonzero exit code.
            rejected += 1
            records.append({"section": section, "job_state": "SECURITY_REJECTED",
                            "reason": str(exc),
                            "eligible_for_prepared_single_section_execution": False})
    return {
        "schema_version": 1,
        "status": ("SOURCE_SECURITY_REJECTED" if rejected else
                   "WINDOWS_MULTISOURCE_STATUS_RECORDED"),
        "selected_source_sections": len(records),
        "new_job_receipts": newly_recorded,
        "reused_job_receipts": reused,
        "security_rejected_sections": rejected,
        "blocked_input_sections": sum(
            not r["eligible_for_prepared_single_section_execution"]
            and r["job_state"] != "SECURITY_REJECTED" for r in records),
        "automatically_rendered_original_sections": 0,
        "new_model_or_tts_calls": False,
        "student_publication_authorized": False,
        "sections": records,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--jobs-dir", type=Path, required=True)
    parser.add_argument("--section", action="append",
                        help="Optional exact section; repeat to select a subset")
    args = parser.parse_args(argv)
    try:
        result = run_batch(campaign=args.campaign, jobs_dir=args.jobs_dir,
                           sections=args.section)
    except CampaignRecoveryBlocked as exc:
        print(json.dumps({"status": "WINDOWS_JOB_REJECTED", "reason": str(exc),
                          "new_model_or_tts_calls": False,
                          "student_publication_authorized": False}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 2 if result["security_rejected_sections"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
