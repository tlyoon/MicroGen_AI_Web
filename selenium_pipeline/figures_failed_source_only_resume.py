"""Salvage a verified captionless crop from an immutable failed figure trial.

Never resubmit a claimed source or rewrite the failed trial. The result is a
separate source-only technical recovery candidate, NOT a new provider success,
academic QA, completed lecture, or release authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

from .evidence_reuse_contract import file_sha256
from .figure_composites import validate_and_prepare_mappings, require_non_destructive_destination
from .figure_mapping_checkpoints import checkpoint_can_resume, save_checkpoint
from .figure_uncaptioned_source_recovery import recover_source_uncaptioned_crop


def _load(path: Path) -> dict:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 200_000:
        raise ValueError("Missing or unsafe immutable receipt: " + path.name)
    data = json.loads(path.read_text(encoding="utf-8"))
    if type(data) is not dict:
        raise ValueError("Invalid receipt")
    return data


def _new_json(path: Path, data: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _new_bytes(path: Path, content: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def recover(*, previous_trial: Path, new_trial: Path) -> dict:
    previous_trial = Path(previous_trial).absolute()
    new_trial = Path(new_trial).absolute()
    if (not previous_trial.is_dir() or previous_trial.is_symlink()
            or not new_trial.is_dir() or new_trial.is_symlink()
            or previous_trial == new_trial or
            previous_trial.parent != new_trial.parent):
        raise ValueError("Recovery must use a separate existing sibling trial")
    old = _load(previous_trial / "fresh_trial_contract.json")
    new = _load(new_trial / "fresh_trial_contract.json")
    sha = old.get("source_sha256")
    if not (type(sha) is str and len(sha) == 64
            and old.get("status") == new.get("status") ==
                "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL"
            and new.get("source_sha256") == sha
            and old.get("source_path") == new.get("source_path")
            and new.get("paid_tts_authorized") is False
            and new.get("student_publication_authorized") is False):
        raise ValueError("Original source trial identities or publication guard differ")
    intent = _load(previous_trial / "figures_attempt_started.json")
    outcome = _load(previous_trial / "figures_attempt_result.json")
    triage = _load(previous_trial / "figures_transport_triage.json")
    log = previous_trial / "figures_stage_stdout.raw.log"
    if not (intent.get("source_sha256") == sha
            and intent.get("stage") == "figures"
            and intent.get("single_provider_attempt_only") is True
            and outcome.get("status") == "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY"
            and outcome.get("original_source_sha256") == sha
            and outcome.get("figure_stage_exit_code") != 0
            and triage.get("terminal_log_sha256") == file_sha256(log)
            and triage.get("terminal_result_sha256") ==
                file_sha256(previous_trial / "figures_attempt_result.json")
            and triage.get("source_sha256") == sha
            and triage.get("owned_browser_send_registered") is True):
        raise ValueError("Historical failure attribution is incomplete or altered")
    previous_work = (previous_trial / "source_tree" / Path(old["source_path"]).parent.parent.name
                     / Path(old["source_path"]).parent.name / ".microgen_work")
    new_source = Path(new["staged_source_path"])
    new_work = new_source.parent / ".microgen_work"
    if not (previous_work.is_dir() and not previous_work.is_symlink()
            and new_source.is_file() and file_sha256(new_source) == sha
            and (previous_work / "source.pdf").is_file()
            and file_sha256(previous_work / "source.pdf") == sha
            and not new_work.exists()):
        raise ValueError("Source or candidate workspace unsafe / already used")
    for path in previous_work.rglob("*"):
        if path.is_symlink():
            raise ValueError("Symlink in original workspace")
    crop_pages = []
    for folder in (previous_work / "crops").glob("page_*"):
        if folder.is_dir() and any(folder.glob("fig_*.png")):
            if not folder.name[5:].isdigit() or folder.is_symlink():
                raise ValueError("Unsafe original crop page")
            crop_pages.append(int(folder.name[5:]))
    if not crop_pages or len(crop_pages) != len(set(crop_pages)):
        raise ValueError("No unique original crop-page inventory")
    accepted = [page for page in crop_pages
                if checkpoint_can_resume(previous_work, page, copy_to_root=True)]
    unresolved = [page for page in crop_pages if page not in accepted]
    if len(unresolved) != 1:
        raise ValueError("Exactly one failed caption mapping required")
    page_number = unresolved[0]
    original_page = (previous_work / "pages" / f"page_{page_number}"
                     / f"page_{page_number}.png")
    original_mapping = original_page.with_name(f"page_{page_number}_mapping.txt")
    old_log_text = (previous_work / "microgen_figures.log").read_text(
        encoding="utf-8", errors="replace")
    if (not original_mapping.is_file() or original_mapping.is_symlink()
            or original_mapping.read_bytes() not in
                (b"MAPPING_REVIEW_REQUIRED\n", b"MAPPING_REVIEW_REQUIRED\r\n")
            or "model_txt_first_400 attempt 1/1='MAPPING_REVIEW_REQUIRED'"
                not in old_log_text
            or f"Figure mapping halted at page {page_number}" not in old_log_text):
        raise ValueError("Original owned refusal was not independently corroborated")
    old_refusal_sha = file_sha256(original_mapping)
    # Validate original material BEFORE first copy; no Gemini or API calls.
    original_crops = previous_work / "crops" / f"page_{page_number}"
    rows, witness = recover_source_uncaptioned_crop(
        response="MAPPING_REVIEW_REQUIRED",
        source_pdf=previous_work / "source.pdf",
        page_png=original_page, crops_dir=original_crops,
        geometry_manifest=original_crops / f"page_{page_number}_crop_geometry.json")
    rows = validate_and_prepare_mappings(rows)
    if len(rows) != 1:
        raise ValueError("Expected exactly one source-backed graphic")
    shutil.copytree(previous_work, new_work, copy_function=shutil.copy2)
    page = (new_work / "pages" / f"page_{page_number}"
            / f"page_{page_number}.png")
    crops = new_work / "crops" / f"page_{page_number}"
    mapping = page.with_name(f"page_{page_number}_mapping.txt")
    original_trace = crops / "gemini_transport_attempts.json"
    _new_bytes(page.with_name("page_6_mapping.original_refusal.txt"),
               mapping.read_bytes())
    _new_bytes(crops / "gemini_transport_attempts.original_failure.json",
               original_trace.read_bytes())
    raw = page.with_name("page_6_uncaptioned_model_reply.raw.txt")
    _new_bytes(raw, b"MAPPING_REVIEW_REQUIRED\n")
    witness["saved_model_reply_sha256"] = file_sha256(raw)
    _new_json(page.with_name("page_6_uncaptioned_source_evidence.json"), witness)
    crop_name, label, target = rows[0]
    crop = crops / crop_name
    dest = crops / target
    require_non_destructive_destination(crop, dest)
    shutil.copy2(crop, dest)
    root_target = new_work / target
    require_non_destructive_destination(crop, root_target)
    shutil.copy2(crop, root_target)
    mapping.write_text(f'{crop_name} : "{label}" : {target}\n', encoding="utf-8")
    original_transport = _load(crops / "gemini_transport_attempts.original_failure.json")
    trace = dict(original_transport)
    trace["completed"] = True
    trace["attempts"] = list(original_transport["attempts"]) + [{
        "backend": "source_only_local_recovery",
        "attempt": 0, "status": "validated",
        "model_send": False,
        "original_refusal_sha256": old_refusal_sha,
    }]
    trace["provider_rejection_remains_historical"] = True
    trace["new_provider_sends"] = 0
    original_trace.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
    saved = save_checkpoint(new_work, page_number, copy_to_root=True)
    from .runner import valid
    if not (checkpoint_can_resume(new_work, page_number, copy_to_root=True)
            and all(checkpoint_can_resume(new_work, n, copy_to_root=True)
                    for n in accepted)
            and valid("figures", new_work)):
        raise ValueError("Complete source-only figure structural gate not accepted")
    receipt = {
        "schema_version": 1,
        "status": "FIGURES_SOURCE_ONLY_LOCAL_RECOVERY_STRUCTURALLY_VALID",
        "source_sha256": sha,
        "previous_trial": str(previous_trial),
        "prior_failed_result_sha256": file_sha256(
            previous_trial / "figures_attempt_result.json"),
        "prior_failed_log_sha256": file_sha256(log),
        "original_refusal_sha256": old_refusal_sha,
        "new_trial": str(new_trial),
        "new_workspace": str(new_work),
        "source_page_recovered": page_number,
        "new_mapping_checkpoint_sha256": file_sha256(saved),
        "new_provider_sends": 0,
        "prior_failure_rewritten": False,
        "full_original_figures_stage_provider_success": False,
        "structural_figure_check_valid": True,
        "independent_diagram_science_qa_verified": False,
        "slides_narration_audio_video_complete": False,
        "student_publication_authorized": False,
    }
    _new_json(new_trial / "figures_source_only_local_recovery.json", receipt)
    return receipt


def verify_recovery_receipt(trial_dir: Path) -> Path:
    """Read-only, fail-closed acceptance of separate no-Send figure rescue.

    This is NOT a provider figure success or scientific approval. It only
    unlocks an untouched separate slides attempt after locally validated
    mappings, retaining the original failed provider result in full.
    """
    trial_dir = Path(trial_dir).absolute()
    receipt_path = trial_dir / "figures_source_only_local_recovery.json"
    report = _load(receipt_path)
    contract = _load(trial_dir / "fresh_trial_contract.json")
    old_dir = Path(report.get("previous_trial", "")).absolute()
    sha = contract.get("source_sha256")
    if not (old_dir != trial_dir and old_dir.parent == trial_dir.parent
            and old_dir.is_dir() and not old_dir.is_symlink()
            and report.get("schema_version") == 1
            and report.get("status") ==
                "FIGURES_SOURCE_ONLY_LOCAL_RECOVERY_STRUCTURALLY_VALID"
            and report.get("source_sha256") == sha
            and report.get("new_provider_sends") == 0
            and report.get("prior_failure_rewritten") is False
            and report.get("full_original_figures_stage_provider_success") is False
            and report.get("structural_figure_check_valid") is True
            and report.get("student_publication_authorized") is False
            and report.get("new_trial") == str(trial_dir)
            and contract.get("paid_tts_authorized") is False):
        raise ValueError("No trusted local figure-recovery receipt")
    old_result = _load(old_dir / "figures_attempt_result.json")
    old_start = _load(old_dir / "figures_attempt_started.json")
    triage = _load(old_dir / "figures_transport_triage.json")
    logfile = old_dir / "figures_stage_stdout.raw.log"
    if not (old_start.get("source_sha256") == sha
            and old_start.get("single_provider_attempt_only") is True
            and old_result.get("status") == "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY"
            and old_result.get("original_source_sha256") == sha
            and file_sha256(old_dir / "figures_attempt_result.json") ==
                report.get("prior_failed_result_sha256")
            and file_sha256(logfile) == report.get("prior_failed_log_sha256")
            == triage.get("terminal_log_sha256")
            and triage.get("terminal_result_sha256") ==
                report.get("prior_failed_result_sha256")
            and triage.get("owned_browser_send_registered") is True):
        raise ValueError("Original source-failure witness has changed")
    page_number = report.get("source_page_recovered")
    if type(page_number) is not int or page_number < 1:
        raise ValueError("Recovered source-page number invalid")
    old_source = Path(_load(old_dir / "fresh_trial_contract.json")["staged_source_path"])
    new_source = Path(contract["staged_source_path"])
    old_mapping = (old_source.parent / ".microgen_work" / "pages"
                   / f"page_{page_number}" / f"page_{page_number}_mapping.txt")
    workspace = new_source.parent / ".microgen_work"
    saved = (workspace / "crops" / f"page_{page_number}"
             / "source_bound_mapping_checkpoint.json")
    from .runner import valid
    if not (file_sha256(old_source) == sha
            and file_sha256(new_source) == sha
            and file_sha256(workspace / "source.pdf") == sha
            and old_mapping.is_file() and not old_mapping.is_symlink()
            and old_mapping.read_bytes() in
                (b"MAPPING_REVIEW_REQUIRED\n", b"MAPPING_REVIEW_REQUIRED\r\n")
            and file_sha256(old_mapping) == report.get("original_refusal_sha256")
            and checkpoint_can_resume(workspace, page_number, copy_to_root=True)
            and file_sha256(saved) ==
                report.get("new_mapping_checkpoint_sha256")
            and valid("figures", workspace)):
        raise ValueError("Local figure recovery content no longer valid")
    return receipt_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior-trial", type=Path, required=True)
    parser.add_argument("--new-trial", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = recover(previous_trial=args.prior_trial, new_trial=args.new_trial)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"status": "SOURCE_ONLY_RECOVERY_REJECTED",
                  "reason": str(exc), "new_provider_sends": 0}
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "FIGURES_SOURCE_ONLY_LOCAL_RECOVERY_STRUCTURALLY_VALID" else 2


if __name__ == "__main__":
    raise SystemExit(main())
