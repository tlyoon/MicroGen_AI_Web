"""One-source-at-a-time native Windows stage continuation with immutable receipts.

After a successful PR490/494 figure stage on a *new* source, process slides,
narration and deterministic script QA in separate bounded commands.
Never repeat a possible model send; TTS/video/publishing require their own
strict gates and cannot be invoked by this stage controller.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from .evidence_reuse_contract import file_sha256
from .original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked, _new_atomic, _verified_json, require,
)
from .windows_bounded_stage_process import run_bounded, WindowsStageRecoveryError


_ORDER = ("slides", "narration", "script_qa")
_EXPECTED_OUTPUTS = {
    "slides": ("slides.pdf", "slides.tex"),
    "narration": ("script.txt",),
    "script_qa": ("script_risk_report.json", "math_semantic_report.json"),
}


def _trial(trial_dir: Path) -> tuple[dict, Path, Path]:
    trial_dir = Path(trial_dir).absolute()
    require(os.name == "nt" and trial_dir.is_dir()
            and not trial_dir.is_symlink(), "Native Windows original trial required")
    contract = _verified_json(trial_dir / "fresh_trial_contract.json")
    require(contract.get("schema_version") == 1
            and contract.get("status") ==
            "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL"
            and contract.get("stage_goal") == "figures"
            and contract.get("paid_tts_authorized") is False
            and contract.get("student_publication_authorized") is False,
            "Only the prior immutable original-source trial may be continued")
    original = Path(contract["source_path"]).absolute()
    stage_source = Path(contract["staged_source_path"]).absolute()
    require(original.is_file() and stage_source.is_file()
            and not original.is_symlink() and not stage_source.is_symlink()
            and stage_source.is_relative_to(trial_dir)
            and not original.is_relative_to(trial_dir)
            and file_sha256(original) == file_sha256(stage_source)
            == contract["source_sha256"],
            "Wrong original publisher PDF version; reject stage continuation")
    return contract, original, stage_source


def run_stage(*, trial_dir: Path, stage: str, timeout_seconds: int = 480,
              stage_runner=None, communication_mode: str = "selenium",
              confirm_content_api_cost: bool = False) -> dict:
    require(stage in _ORDER, "Only vetted slides/narration/script QA stages supported")
    require(communication_mode in {"selenium", "api"},
            "Automatic API fallback prohibited after uncertain browser send")
    require(not confirm_content_api_cost or communication_mode == "api",
            "Paid content consent only applies to explicit API mode")
    require(communication_mode != "api" or stage == "script_qa"
            or confirm_content_api_cost,
            "Paid Gemini content API requires explicit per-stage cost approval")
    require(type(timeout_seconds) is int and 30 <= timeout_seconds <= 900,
            "Finite native Windows stage deadline required")
    contract, original, stage_source = _trial(trial_dir)
    trial_dir = Path(trial_dir).absolute()
    lecture = stage_source.parent
    workspace = lecture / ".microgen_work"
    require(workspace.is_dir() and not workspace.is_symlink()
            and (workspace / "source.pdf").is_file()
            and not (workspace / "source.pdf").is_symlink()
            and file_sha256(workspace / "source.pdf") ==
            contract["source_sha256"],
            "Source-bound execution workspace not physically verified")
    section = lecture.name
    require(re.fullmatch(r"[0-9]+\.[0-9]+", section) is not None
            and lecture.parent.name == section.split(".")[0],
            "Original source/staged hierarchy changed")
    from .runner import check_valid
    if stage == "slides":
        predecessor = trial_dir / "figures_attempt_result.json"
        source_proof = _verified_json(predecessor)
        require(source_proof.get("status") ==
                "FIGURES_STAGE_RETURNED_SUCCESS_NOT_FULL_LECTURE"
                and source_proof.get("figure_stage_exit_code") == 0
                and source_proof.get("original_source_sha256") ==
                contract["source_sha256"]
                and source_proof.get("staged_original_sha256") ==
                contract["source_sha256"]
                and source_proof.get("new_video_rendered") is False
                and source_proof.get("student_publication_authorized") is False,
                "Cannot generate slides from failed or ambiguous figure mapping")
        require(check_valid("figures", workspace),
                "Figure stage receipt exists but real source-map artifacts are invalid")
    else:
        previous = _ORDER[_ORDER.index(stage)-1]
        predecessor = trial_dir / ("stage_" + previous + "_result.json")
        source_proof = _verified_json(predecessor)
        require(source_proof.get("status") ==
                "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND"
                and source_proof.get("stage") == previous
                and source_proof.get("source_sha256") ==
                contract["source_sha256"],
                "Previous original stage incomplete or unsafe")
        for name in _EXPECTED_OUTPUTS[previous]:
            p = lecture / name
            require(p.is_file() and not p.is_symlink() and p.stat().st_size > 0
                    and file_sha256(p) == source_proof["output_sha256"].get(name),
                    "Previous-stage output missing or changed: " + name)
        require(check_valid(previous, workspace),
                "Previous-stage real technical QA did not pass")
    expected = _EXPECTED_OUTPUTS[stage]
    started = trial_dir / ("stage_" + stage + "_started.json")
    finished = trial_dir / ("stage_" + stage + "_result.json")
    intent = {
        "schema_version": 1,
        "stage": stage,
        "source_sha256": contract["source_sha256"],
        "predecessor_receipt_sha256": file_sha256(predecessor),
        "single_attempt_no_provider_resend": True,
        "paid_tts_authorized": False,
        "student_publication_authorized": False,
    }
    if communication_mode == "api" and stage != "script_qa":
        intent["communication_mode"] = "api"
        intent["paid_content_api_explicitly_authorized"] = True
    if started.exists() or started.is_symlink():
        require(_verified_json(started) == intent,
                "Stage attempt intent changed; do not reinterpret old provider work")
        if finished.exists() or finished.is_symlink():
            prior = _verified_json(finished)
            if (prior.get("stage") == stage
                    and prior.get("source_sha256") == contract["source_sha256"]
                    and prior.get("status") ==
                    "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND"):
                require(check_valid(stage, workspace)
                        and all((lecture / n).is_file()
                            and not (lecture / n).is_symlink()
                            and file_sha256(lecture / n) ==
                            prior["output_sha256"].get(n)
                            for n in expected),
                        "Accepted prior outputs changed; no automatic regeneration")
                return {**prior, "status": "REUSED_PREVIOUS_SOURCE_STAGE"}
        return {
            "status": "PREVIOUS_STAGE_ATTEMPT_NOT_RESENT",
            "stage": stage, "source_sha256": contract["source_sha256"],
            "new_model_or_tts_calls": False,
            "student_publication_authorized": False,
        }
    require(not finished.exists() and not finished.is_symlink()
            and all(not (lecture / n).exists()
                    and not (lecture / n).is_symlink() for n in expected),
            "Unexpected existing stage artifacts; preserve and review")
    _new_atomic(started, intent)
    command = [
        sys.executable, "-m", "selenium_pipeline",
        "--source-root", str(stage_source.parents[2]),
        "--subchapter", section, "--from-stage", stage,
        "--through-stage", stage,
        "--communication-mode", communication_mode,
    ]
    log = trial_dir / ("stage_" + stage + "_stdout.raw.log")
    report = {
        "schema_version": 1, "stage": stage,
        "source_sha256": contract["source_sha256"],
        "predecessor_receipt_sha256": file_sha256(predecessor),
        "log_path": str(log), "new_model_or_tts_calls": None
            if stage in ("slides", "narration") else False,
        "new_tts_calls": False, "new_video_rendered": False,
        "full_sourcebound_original_lecture_completed": False,
        "student_publication_authorized": False,
    }
    run = run_bounded if stage_runner is None else stage_runner
    try:
        output = run(command=command,
                     cwd=Path(__file__).resolve().parent.parent,
                     log_path=log, timeout_seconds=timeout_seconds)
        report["exit_code"] = output.returncode
        report["status"] = ("STAGE_COMPLETED_AND_SOURCE_SHA_BOUND"
            if output.returncode == 0 and all(
                (lecture / n).is_file()
                and not (lecture / n).is_symlink()
                and (lecture / n).stat().st_size > 0 for n in expected)
            and check_valid(stage, workspace)
            else "STAGE_FAILED_OR_OUTPUT_INCOMPLETE_NO_RETRY")
    except subprocess.TimeoutExpired:
        report["status"] = "STAGE_TIMEOUT_UNKNOWN_PROVIDER_SEND_NO_RETRY"
    except (OSError, WindowsStageRecoveryError):
        report["status"] = "STAGE_PROCESS_ERROR_NO_RETRY"
    report["output_sha256"] = {
        n: file_sha256(lecture / n) for n in expected
        if (lecture / n).is_file() and not (lecture / n).is_symlink()}
    require(file_sha256(original) == file_sha256(stage_source)
            == contract["source_sha256"],
            "Original source altered by stage; stop without authorizing reuse")
    _new_atomic(finished, report)
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trial-dir", type=Path, required=True)
    p.add_argument("--stage", choices=_ORDER, required=True)
    p.add_argument("--timeout-seconds", type=int, default=480)
    p.add_argument("--communication-mode", choices=("selenium", "api"),
                   default="selenium")
    p.add_argument("--confirm-content-api-cost", action="store_true",
                   help="Explicit approval for one newly attempted content API stage")
    args = p.parse_args(argv)
    try:
        outcome = run_stage(trial_dir=args.trial_dir, stage=args.stage,
                            timeout_seconds=args.timeout_seconds,
                            communication_mode=args.communication_mode,
                            confirm_content_api_cost=args.confirm_content_api_cost)
    except (CampaignRecoveryBlocked, OSError, ValueError) as exc:
        outcome = {
            "status": "STAGE_NOT_AUTHORIZED",
            "reason": str(exc),
            "student_publication_authorized": False,
        }
    print(json.dumps(outcome, indent=2))
    return 0 if outcome["status"] in {
        "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND",
        "REUSED_PREVIOUS_SOURCE_STAGE",
        "PREVIOUS_STAGE_ATTEMPT_NOT_RESENT",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
