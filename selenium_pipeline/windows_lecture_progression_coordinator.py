"""Single-stage Windows lecture progression from original PDF to media handoff.

This is the canonical *operator* bridge between the existing immutable
original-source trial and individually bounded figures/slides/narration/QA.
It executes at most ONE explicitly authorized stage per invocation, never
loops to repair a source PDF, and never synthesizes audio or publishes video.
All prior source-locked receipts and actual output bytes are read again.

The older multi-retry sourcebound_e2e_orchestrator is not invoked here.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re

from .evidence_reuse_contract import file_sha256
from .original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked, _verified_json, require,
)
from .windows_fresh_source_trial import _source_paths
from .windows_original_stage_sequence import _ORDER, _EXPECTED_OUTPUTS


def _report(*, status: str, source_sha256: str, section: str,
            next_stage: str | None = None, **extra) -> dict:
    return {
        "schema_version": 1,
        "status": status,
        "source_sha256": source_sha256,
        "section": section,
        "next_stage": next_stage,
        "model_requests_per_operator_invocation_limit": 1,
        "new_model_or_tts_calls": False,
        "automatic_retry_or_fallback": False,
        "reviewed_tts_or_video_generated": False,
        "student_publication_authorized": False,
        **extra,
    }


def inspect_progress(*, source_root: Path, section: str, trial_dir: Path,
                     communication_mode: str = "selenium",
                     technical_check=None, provider_inspect=None) -> dict:
    """Read-only, SHA-verifying state machine. Never runs any provider."""
    require(os.name == "nt", "Only native Windows source progression supported")
    require(communication_mode in ("selenium", "api"),
            "Explicit vetted Gemini communication mode required")
    source_root = Path(source_root).absolute()
    trial_dir = Path(trial_dir).absolute()
    require(source_root.is_dir() and not source_root.is_symlink(),
            "Publisher source root missing or unsafe")
    require(trial_dir.is_dir() and not trial_dir.is_symlink()
            and not trial_dir.is_relative_to(source_root)
            and not source_root.is_relative_to(trial_dir),
            "Existing external trial directory must not overlap publisher")
    source, _ = _source_paths(source_root, section)
    sha = file_sha256(source)
    contract_path = trial_dir / "fresh_trial_contract.json"
    if not contract_path.exists():
        require(not contract_path.is_symlink() and not any(trial_dir.iterdir()),
                "Nonempty unclaimed original trial; preserve for review, do not regenerate")
        next_stage = "figures"
    else:
        contract = _verified_json(contract_path)
        expected = trial_dir / "source_tree" / section.split(".")[0] / section / "source.pdf"
        require(
            contract.get("schema_version") == 1
            and contract.get("status") == "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL"
            and contract.get("stage_goal") == "figures"
            and contract.get("paid_tts_authorized") is False
            and contract.get("student_publication_authorized") is False
            and Path(contract.get("source_path", "")).absolute() == source
            and Path(contract.get("staged_source_path", "")).absolute() == expected
            and contract.get("source_sha256") == sha
            and expected.is_file() and not expected.is_symlink()
            and file_sha256(expected) == sha,
            "Immutable original-source contract or staged PDF changed")
        started = trial_dir / "figures_attempt_started.json"
        result = trial_dir / "figures_attempt_result.json"
        if started.exists() or started.is_symlink():
            intent = _verified_json(started)
            require(intent.get("schema_version") == 1
                    and intent.get("source_sha256") == sha
                    and intent.get("stage") == "figures"
                    and intent.get("single_provider_attempt_only") is True,
                    "Prior figure attempt claim identity changed")
            if not result.exists() and not result.is_symlink():
                return _report(
                    status="HALTED_PRIOR_FIGURES_SEND_UNRESOLVED",
                    source_sha256=sha, section=section,
                    reason="Pre-send claim exists; never send this stage again")
        elif result.exists() or result.is_symlink():
            raise CampaignRecoveryBlocked("Figure result without original send intent")
        if not result.exists():
            require(not any(trial_dir.glob("stage_*_started.json"))
                    and not any(trial_dir.glob("stage_*_result.json")),
                    "Orphan later-stage send without accepted figure result")
            require(contract.get("communication_mode", "selenium") == communication_mode,
                    "Original figure communication mode immutable; do not reinterpret")
            next_stage = "figures"
        else:
            data = _verified_json(result)
            require(data.get("original_source_sha256") == sha
                    and data.get("staged_original_sha256") == sha
                    and data.get("student_publication_authorized") is False,
                    "Figure stage SHA or publication guard changed")
            if (data.get("status") != "FIGURES_STAGE_RETURNED_SUCCESS_NOT_FULL_LECTURE"
                    or data.get("figure_stage_exit_code") != 0
                    or data.get("new_video_rendered") is not False):
                return _report(
                    status="HALTED_PREVIOUS_FIGURES_FAILED_NO_RESEND",
                    source_sha256=sha, section=section,
                    prior_status=data.get("status"))
            lecture = expected.parent
            workspace = lecture / ".microgen_work"
            require(workspace.is_dir() and not workspace.is_symlink()
                    and (workspace / "source.pdf").is_file()
                    and not (workspace / "source.pdf").is_symlink()
                    and file_sha256(workspace / "source.pdf") == sha,
                    "Figure execution workspace source is missing or changed")
            if technical_check is None:
                from .runner import check_valid
                technical_check = check_valid
            if not technical_check("figures", workspace):
                return _report(
                    status="HALTED_FIGURES_TECHNICAL_QA_INCOMPLETE",
                    source_sha256=sha, section=section,
                    reason="No resend or source-specific PDF repair")
            predecessor = result
            next_stage = None
            for stage in _ORDER:
                began = trial_dir / f"stage_{stage}_started.json"
                finished = trial_dir / f"stage_{stage}_result.json"
                if began.exists() or began.is_symlink():
                    intent = _verified_json(began)
                    require(intent.get("schema_version") == 1
                            and intent.get("stage") == stage
                            and intent.get("source_sha256") == sha
                            and intent.get("single_attempt_no_provider_resend") is True
                            and intent.get("predecessor_receipt_sha256")
                                == file_sha256(predecessor),
                            "Stage original send intent or predecessor SHA invalid")
                    if not finished.exists() and not finished.is_symlink():
                        return _report(
                            status="HALTED_PRIOR_STAGE_SEND_UNRESOLVED",
                            source_sha256=sha, section=section,
                            next_stage=None, halted_stage=stage)
                elif finished.exists() or finished.is_symlink():
                    raise CampaignRecoveryBlocked(
                        "Stage result without an immutable pre-send claim")
                if not finished.exists():
                    next_stage = stage
                    break
                receipt = _verified_json(finished)
                require(receipt.get("schema_version") == 1
                        and receipt.get("stage") == stage
                        and receipt.get("source_sha256") == sha
                        and receipt.get("student_publication_authorized") is False
                        and receipt.get("predecessor_receipt_sha256")
                            == file_sha256(predecessor),
                        "Stage output receipt source/predecessor mismatch")
                if receipt.get("status") != "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND":
                    return _report(
                        status="HALTED_PREVIOUS_STAGE_FAILED_NO_RESEND",
                        source_sha256=sha, section=section,
                        halted_stage=stage,
                        prior_status=receipt.get("status"))
                outputs = receipt.get("output_sha256")
                require(type(outputs) is dict,
                        "Accepted original stage has no immutable output hashes")
                for name in _EXPECTED_OUTPUTS[stage]:
                    path = lecture / name
                    require(path.is_file() and not path.is_symlink()
                            and path.stat().st_size > 0
                            and outputs.get(name) == file_sha256(path),
                            f"Accepted {stage} output byte identity changed: {name}")
                if not technical_check(stage, workspace):
                    return _report(
                        status="HALTED_ACCEPTED_STAGE_TECHNICAL_QA_CHANGED",
                        source_sha256=sha, section=section, halted_stage=stage)
                predecessor = finished
            if next_stage is None:
                return _report(
                    status="REVIEWED_AUDIO_HANDOFF_REQUIRED_NO_AUTOMATIC_TTS",
                    source_sha256=sha, section=section,
                    source=str(expected),
                    publisher_source=str(source),
                    staged_source_sha256=file_sha256(expected),
                    slides_pdf=str(lecture / "slides.pdf"),
                    slides_pdf_sha256=file_sha256(lecture / "slides.pdf"),
                    script=str(lecture / "script.txt"),
                    script_sha256=file_sha256(lecture / "script.txt"),
                    required_following_steps=[
                        "Review original-source slide, figure, script and math meaning",
                        "Produce and approve source-matched reviewed element plan",
                        "Authorize and verify exact per-element WAV audio separately",
                        "Use reviewed-element sourcebound media bridge to encode/QA MP4",
                        "Perform independent academic and voice acceptance",
                        "Obtain separate explicit release and publication approval",
                    ],
                )

    if next_stage in ("figures", "slides", "narration"):
        if provider_inspect is None:
            from .windows_gemini_provider_halt import inspect_halt
            provider_inspect = inspect_halt
        health = provider_inspect(backend=communication_mode)
        if not health.get("new_generation_dispatch_allowed_by_health_policy"):
            return _report(
                status="HALTED_PROVIDER_CAPACITY_NO_NEW_SUBMISSION",
                source_sha256=sha, section=section,
                next_stage=next_stage,
                provider_health=health)
    return _report(
        status="NEXT_SOURCE_STAGE_READY_EXPLICIT_ONE_SHOT_ONLY",
        source_sha256=sha, section=section,
        next_stage=next_stage,
        requires_explicit_live_authorization=True,
        requires_explicit_paid_api_cost_for_api_mode=True,
    )


def advance_one(*, source_root: Path, section: str, trial_dir: Path,
                execute_next: bool = False, communication_mode: str = "selenium",
                confirm_content_api_cost: bool = False,
                technical_check=None, provider_inspect=None,
                figure_runner=None, stage_runner=None) -> dict:
    """Never dispatch more than one stage, even when a stage succeeds."""
    state = inspect_progress(
        source_root=source_root, section=section, trial_dir=trial_dir,
        communication_mode=communication_mode,
        technical_check=technical_check, provider_inspect=provider_inspect)
    if not execute_next:
        return state
    if state["status"] != "NEXT_SOURCE_STAGE_READY_EXPLICIT_ONE_SHOT_ONLY":
        return state
    require(communication_mode in ("selenium", "api"),
            "Only explicit vetted Selenium or API mode permitted")
    require(not confirm_content_api_cost or communication_mode == "api",
            "Paid API cost consent cannot transfer to browser")
    require(communication_mode != "api" or confirm_content_api_cost,
            "API content generation needs explicit per-invocation authorization")
    stage = state["next_stage"]
    if stage == "figures":
        from .windows_fresh_source_trial import run_trial
        args = {
            "source_root": Path(source_root), "section": section,
            "trial_dir": Path(trial_dir), "attempt_figures": True,
            "communication_mode": communication_mode,
            "confirm_content_api_cost": confirm_content_api_cost,
        }
        if figure_runner is not None:
            args["subprocess_run"] = figure_runner
        result = run_trial(**args)
    else:
        from .windows_original_stage_sequence import run_stage
        args = {
            "trial_dir": Path(trial_dir), "stage": stage,
            "communication_mode": communication_mode,
            "confirm_content_api_cost": confirm_content_api_cost,
        }
        if stage_runner is not None:
            args["stage_runner"] = stage_runner
        result = run_stage(**args)
    return _report(
        status="EXACTLY_ONE_SOURCE_STAGE_ATTEMPT_FINISHED_NO_AUTO_CHAIN",
        source_sha256=state["source_sha256"], section=section,
        attempted_stage=stage,
        attempted_stage_status=result["status"],
        source_stage_receipt=result,
        new_model_or_tts_calls=(
            None if stage in ("figures", "slides", "narration") else False),
        next_invocation_requires_fresh_read_only_sha_review=True,
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--section", required=True)
    ap.add_argument("--trial-dir", type=Path, required=True)
    ap.add_argument("--execute-next-one-stage", action="store_true")
    ap.add_argument("--communication-mode", choices=("selenium", "api"),
                    default="selenium")
    ap.add_argument("--confirm-content-api-cost", action="store_true")
    a = ap.parse_args(argv)
    try:
        output = advance_one(
            source_root=a.source_root, section=a.section,
            trial_dir=a.trial_dir,
            execute_next=a.execute_next_one_stage,
            communication_mode=a.communication_mode,
            confirm_content_api_cost=a.confirm_content_api_cost)
    except (CampaignRecoveryBlocked, OSError, ValueError) as exc:
        output = {"schema_version": 1,
                  "status": "ORIGINAL_LECTURE_PROGRESSION_REJECTED",
                  "reason": str(exc), "new_model_or_tts_calls": False,
                  "student_publication_authorized": False}
    print(json.dumps(output, indent=2))
    return 0 if output["status"] in (
        "NEXT_SOURCE_STAGE_READY_EXPLICIT_ONE_SHOT_ONLY",
        "EXACTLY_ONE_SOURCE_STAGE_ATTEMPT_FINISHED_NO_AUTO_CHAIN",
        "REVIEWED_AUDIO_HANDOFF_REQUIRED_NO_AUTOMATIC_TTS",
    ) else 2


if __name__ == "__main__":
    raise SystemExit(main())
