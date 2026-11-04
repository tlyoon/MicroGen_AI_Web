"""Safe native Windows operator entry point for original-source campaigns.

Doctor is offline/read-only. Campaign inspection delegates to PR487's locked
source and receipt verification. Paid model/TTS and publication are never
triggered here. Rendering requires an explicit SHA-ready original section.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys


_GENERATION_MODULES = {
    "pymupdf": "fitz",
    "selenium": "selenium",
    "pypdf": "pypdf",
    "pillow": "PIL",
    "google_genai": "google.genai",
    "google_cloud_tts": "google.cloud.texttospeech",
}


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ModuleNotFoundError, ValueError):
        return False


def diagnose(*, platform_name: str | None = None,
             python_version: tuple[int, int] | None = None,
             root: Path | None = None) -> dict:
    """Describe capability without importing providers or touching originals."""
    platform_name = sys.platform if platform_name is None else platform_name
    python_version = tuple(sys.version_info[:2]) if python_version is None else python_version
    root = Path(__file__).resolve().parent.parent if root is None else Path(root)
    windows = platform_name == "win32"
    supported_python = (3, 11) <= python_version < (3, 14)
    project_present = all((root / p).is_file() for p in (
        "selenium_pipeline/original_windows_release.py",
        "requirements-worker.txt",
        "selenium_pipeline/runner.py",
    ))
    packages = {key: _module_available(name)
                for key, name in _GENERATION_MODULES.items()}
    status = ("OPERATOR_AVAILABLE_FOR_READ_ONLY_INSPECTION"
              if windows and supported_python and project_present
              else "OPERATOR_PREREQUISITES_INCOMPLETE")
    return {
        "schema_version": 1,
        "status": status,
        "windows_native": windows,
        "python_version": ".".join(map(str, python_version)),
        "python_version_supported": supported_python,
        "project_layout_present": project_present,
        "generation_dependency_presence": packages,
        "generation_dependencies_complete": all(packages.values()),
        "ffmpeg_on_path": shutil.which("ffmpeg") is not None,
        "ffprobe_on_path": shutil.which("ffprobe") is not None,
        "generation_readiness_certified": False,
        "source_academic_readiness_certified": False,
        "new_model_or_tts_calls": False,
        "student_publication_authorized": False,
        "note": ("Informational dependencies and FFmpeg PATH are not a substitute "
                 "for strict source-bound production acceptance."),
    }


def operate(*, doctor: bool = False, campaign: Path | None = None,
            section: str | None = None, jobs_dir: Path | None = None,
            execute_prepared: bool = False) -> tuple[int, dict]:
    if doctor:
        if (campaign is not None or section is not None
                or execute_prepared or jobs_dir is not None):
            return 2, {"status": "INVALID_MIXED_DOCTOR_AND_CAMPAIGN_OPTIONS"}
        report = diagnose()
        return (0 if report["status"] ==
                "OPERATOR_AVAILABLE_FOR_READ_ONLY_INSPECTION" else 2), report
    if campaign is None:
        return 2, {"status": "CAMPAIGN_REQUIRED_OR_USE_DOCTOR"}
    if execute_prepared and not section:
        return 2, {"status": "EXPLICIT_SECTION_REQUIRED_FOR_RENDER"}
    if sys.platform != "win32":
        return 2, {"status": "WINDOWS_ONLY_OPERATOR"}
    if jobs_dir is not None:
        if execute_prepared:
            return 2, {"status": "BATCH_RENDERING_NOT_AUTHORIZED"}
        from .original_windows_batch_controller import run_batch
        from .original_multisource_recovery_campaign import CampaignRecoveryBlocked
        try:
            batch = run_batch(campaign=Path(campaign), jobs_dir=Path(jobs_dir),
                              sections=[section] if section else None)
        except (CampaignRecoveryBlocked, OSError, ValueError) as exc:
            return 2, {"status": "WINDOWS_JOB_REJECTED",
                       "reason": str(exc),
                       "new_model_or_tts_calls": False,
                       "student_publication_authorized": False}
        return (2 if batch["security_rejected_sections"] else 0), batch
    # Do not reinterpret failed SHA/source checks or blocked rendering as success.
    from .original_windows_release import inspect_campaign
    from .original_multisource_recovery_campaign import CampaignRecoveryBlocked
    try:
        report = inspect_campaign(campaign=Path(campaign),
                                  section=section,
                                  execute_prepared=execute_prepared)
    except (CampaignRecoveryBlocked, OSError, ValueError) as exc:
        return 2, {"status": "CAMPAIGN_REJECTED",
                   "reason": str(exc),
                   "new_model_or_tts_calls": False,
                   "student_publication_authorized": False}
    blocked = any(item.get("execution_status") ==
                  "BLOCKED_BY_SOURCE_OR_MEDIA_GATE"
                  for item in report["sections"])
    return (2 if blocked else 0), report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doctor", action="store_true",
                        help="Offline native Windows deployment diagnostics")
    parser.add_argument("--campaign", type=Path,
                        help="Immutable, already-reviewed original campaign")
    parser.add_argument("--section",
                        help="Select one section (mandatory for rendering)")
    parser.add_argument("--jobs-dir", type=Path,
                        help="External immutable status-job folder (read-only batch)")
    parser.add_argument("--execute-prepared", action="store_true",
                        help="Strict recorded-audio execution; never batch")
    args = parser.parse_args(argv)
    code, report = operate(doctor=args.doctor, campaign=args.campaign,
                           section=args.section, jobs_dir=args.jobs_dir,
                           execute_prepared=args.execute_prepared)
    print(json.dumps(report, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
