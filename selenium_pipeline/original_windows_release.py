"""Native Windows release entry point for an existing original-source campaign.

This bridges PR486's immutable, resumed section receipts to PR485's *strict*
pre-recorded-element renderer. The default operation is read-only: it reuses
the accepted source/academic verdicts without running PDF semantic checks,
opening Chrome, spending TTS/model credits, or rendering video.

An explicitly selected --execute-prepared section is still independently
rechecked by the existing source E2E gate before its strict renderer may run.
No input from a PR486 observation-only campaign authorizes publication.
New evidence requires a new versioned PR486 campaign, not a mutated receipt.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked, _digest, _fingerprint, _verified_json, require,
)


def _spec_from_contract(entry: dict) -> dict:
    """Reconstruct only paths explicitly locked by an immutable campaign."""
    evidence = entry["original_mapping_evidence"]
    spec = {
        "section": entry["section"],
        "lecture": entry["lecture"],
        "checkpoint": evidence["checkpoint"]["path"],
        "fallback_dir": evidence["fallback_dir"]["path"],
        "queue_dir": evidence["queue_dir"]["path"],
    }
    if "model_responses" in evidence:
        spec["model_responses"] = evidence["model_responses"]["path"]
    return spec


def _receipt(campaign: Path, entry: dict) -> dict:
    section = entry["section"]
    require(type(section) is str and section and len(section) <= 30
            and section.replace(".", "").replace("-", "").isalnum(),
            "Untrusted source campaign section name")
    path = campaign / ("section_" + section.replace(".", "_") + "_e2e.json")
    receipt = _verified_json(path)
    body = {k: v for k, v in receipt.items()
            if k != "immutable_payload_sha256"}
    require(receipt.get("immutable_payload_sha256") == _digest(body)
            and receipt.get("section") == section
            and receipt.get("source_fingerprint_sha256") == _digest(entry)
            and receipt.get("new_paid_generation_attempted") is False
            and receipt.get("student_publication_authorized") is False,
            "Tampered, stale or unsafe real original-section checkpoint")
    report = receipt.get("actual_readiness")
    require(type(report) is dict
            and report.get("new_model_or_tts_calls") is False
            and report.get("student_publication_authorized") is False
            and report.get("source_inputs_sha256",
                           report.get("input_sha256"))
            == entry["original_files_sha256"],
            "Unsafe or unbound source release readiness")
    return report


def _new_media_after_receipt(lecture: Path, report: dict) -> bool:
    """A cached blocked verdict must not be silently treated as current."""
    if report["status"] == "REUSED_PHYSICALLY_VERIFIED_MULTIPART_TECHNICAL_ONLY":
        return False  # Existing completion must be reverified before execution.
    evidence = (lecture / "element_narration_plan.json",
                lecture / "element_wav",
                lecture / "element_tts_manifest.json")
    was_recorded = report.get("existing_per_element_recorded_audio_available")
    if type(was_recorded) is bool:
        now_recorded = tuple(p.exists() or p.is_symlink() for p in evidence)
        if any(now_recorded) != was_recorded or (
                any(now_recorded) and not all(now_recorded)):
            return True
    return (lecture / "lecture_completion.json").exists()


def inspect_campaign(*, campaign: Path, section: str | None = None,
                     execute_prepared: bool = False) -> dict:
    """Inspect exact physical receipts; execute ONE ready section only on opt-in."""
    campaign = Path(campaign).absolute()
    require(campaign.is_dir() and not campaign.is_symlink(),
            "Existing immutable Windows campaign folder required")
    contract = _verified_json(campaign / "original_campaign_contract.json")
    require(contract.get("schema_version") == 1
            and contract.get("status")
            == "SOURCEBOUND_WINDOWS_MULTISOURCE_ORIGINAL_VERSIONED_CAMPAIGN"
            and contract.get("new_model_tts_or_video_generation_permitted")
            is False
            and contract.get("student_publication_authorized") is False,
            "Only the immutable canonical PR486 campaign contract is supported")
    entries = contract.get("sections")
    require(type(entries) is list and 1 <= len(entries) <= 12
            and all(type(x) is dict and type(x.get("section")) is str
                    for x in entries)
            and len({x["section"] for x in entries}) == len(entries),
            "Original sections must be unique and bounded")
    if section is not None:
        require(section in {x["section"] for x in entries},
                "Selected section is not in this immutable campaign")
    require(not execute_prepared or section is not None,
            "Rendering requires one explicit --section; never render a batch")
    result = []
    executed = 0
    for entry in entries:
        if section is not None and entry["section"] != section:
            continue
        spec = _spec_from_contract(entry)
        # SHA checks are fast and do NOT redo PDF mathematical/figure reviews.
        require(_fingerprint(spec) == entry,
                "The original source or external evidence changed: "
                "start a NEW versioned PR486 campaign")
        saved = _receipt(campaign, entry)
        new_media = _new_media_after_receipt(Path(entry["lecture"]), saved)
        prior_status = saved["status"]
        status = ("NEW_DOWNSTREAM_EVIDENCE_REQUIRES_VERSIONED_CAMPAIGN"
                  if new_media else prior_status)
        ready = (not new_media and prior_status in {
            "READY_FOR_STRICT_RECORDED_AUDIO_MULTIPART_RENDER",
            "REUSED_PHYSICALLY_VERIFIED_MULTIPART_TECHNICAL_ONLY"})
        row = {
            "section": entry["section"],
            "status": status,
            "original_status": prior_status,
            "previously_accepted_text_links":
                saved.get("independently_previously_verified_text_links"),
            "remaining_unresolved_mappings":
                saved.get("unresolved_source_element_mappings"),
            "eligible_for_explicit_prepared_execution": ready,
            "new_original_source_review_performed": False,
            "new_model_or_tts_calls": False,
            "student_publication_authorized": False,
            "next_action": (
                "Create a new immutable source-evidence campaign"
                if new_media else saved.get("next_action",
                                            "Inspect original readiness")),
        }
        if execute_prepared:
            if not ready:
                row["execution_status"] = "BLOCKED_BY_SOURCE_OR_MEDIA_GATE"
            else:
                require(os.name == "nt",
                        "Original production rendering is native Windows only")
                require("model_responses" in spec,
                        "Full source-verified response evidence required")
                from .original_source_e2e_acceptance import execute_prepared as render
                fresh = render(
                    lecture=Path(spec["lecture"]),
                    checkpoint=Path(spec["checkpoint"]),
                    fallback_dir=Path(spec["fallback_dir"]),
                    queue_dir=Path(spec["queue_dir"]),
                    model_responses=Path(spec["model_responses"]),
                )
                row["execution_status"] = fresh["status"]
                row["execution_result"] = fresh
                executed += 1
        result.append(row)
    return {
        "schema_version": 1,
        "status": ("EXPLICIT_PREPARED_EXECUTION_COMPLETED" if executed else
                   "ORIGINAL_WINDOWS_CAMPAIGN_READINESS_ONLY"),
        "selected_sections": len(result),
        "executed_original_sections": executed,
        "source_and_evidence_sha_verified_without_semantic_reaudit": True,
        "new_model_or_tts_calls": False,
        "student_publication_authorized": False,
        "sections": result,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--campaign", type=Path, required=True)
    ap.add_argument("--section", help="Exact accepted section, e.g. 8.4")
    ap.add_argument("--execute-prepared", action="store_true",
                    help="Use existing strict renderer ONLY for a ready section")
    args = ap.parse_args(argv)
    report = inspect_campaign(campaign=args.campaign, section=args.section,
                              execute_prepared=args.execute_prepared)
    print(json.dumps(report, indent=2))
    return 0 if all(not x.get("execution_status") or
                    x["execution_status"] != "BLOCKED_BY_SOURCE_OR_MEDIA_GATE"
                    for x in report["sections"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
