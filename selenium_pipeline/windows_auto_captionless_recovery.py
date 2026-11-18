"""Normal Windows on-flight salvage for a previously failed captionless figure.

Source-only: no Gemini Send, TTS, or publication. The prior failed trial
and all original source bytes remain immutable. The recovery successor
is deterministic and uses a Windows kernel lease across processes.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil

from .evidence_reuse_contract import file_sha256
from .original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked, _new_atomic, _verified_json, require,
)
from .windows_fresh_source_trial import _source_paths
from .figures_failed_source_only_resume import recover, verify_recovery_receipt


def _is_safe_local(path: Path) -> bool:
    local = Path(os.environ.get("LOCALAPPDATA", "")).absolute()
    return local.is_dir() and path.is_relative_to(local)


def recover_failed_captionless_on_flight(
    *, source_root: Path, section: str, previous_trial: Path,
) -> dict:
    """Atomically claim/reuse one separate successor; never replay prior Send."""
    require(os.name == "nt", "Windows-only source recovery")
    source_root = Path(source_root).absolute()
    previous_trial = Path(previous_trial).absolute()
    require(source_root.is_dir() and not source_root.is_symlink()
            and previous_trial.is_dir() and not previous_trial.is_symlink()
            and _is_safe_local(previous_trial)
            and not previous_trial.is_relative_to(source_root)
            and not source_root.is_relative_to(previous_trial),
            "Original source and local immutable trial roots invalid")
    source, _ = _source_paths(source_root, section)
    old = _verified_json(previous_trial / "fresh_trial_contract.json")
    sha = file_sha256(source)
    require(old.get("source_sha256") == sha
            and old.get("source_path") == str(source)
            and old.get("status") == "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL"
            and old.get("stage_goal") == "figures"
            and old.get("student_publication_authorized") is False
            and old.get("paid_tts_authorized") is False,
            "Historical trial no longer matches original source")
    result_path = previous_trial / "figures_attempt_result.json"
    old_result = _verified_json(result_path)
    require(old_result.get("status") == "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY"
            and old_result.get("figure_stage_exit_code") != 0
            and old_result.get("original_source_sha256") == sha,
            "Only an actual terminal figure failure can be salvaged")
    identity = hashlib.sha256(str(previous_trial).casefold().encode("utf-8")).hexdigest()[:20]
    successor = previous_trial.parent / ("auto_captionless_" + identity)
    require(not successor.is_symlink() and _is_safe_local(successor),
            "Unsafe deterministic successor path")
    lock = previous_trial.parent / (".auto_captionless_" + identity + ".lock")
    require(not lock.is_symlink() and
            (not lock.exists() or lock.is_file() and lock.stat().st_size <= 1),
            "Unsafe automatic captionless recovery lock")
    import msvcrt
    with lock.open("a+b") as stream:
        if lock.stat().st_size == 0:
            stream.write(b"1")
            stream.flush()
            os.fsync(stream.fileno())
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise CampaignRecoveryBlocked("Recovery already owned by another worker") from exc
        try:
            intention = {
                "schema_version": 1,
                "status": "AUTO_CAPTIONLESS_RECOVERY_ONCE",
                "previous_trial": str(previous_trial),
                "previous_failure_sha256": file_sha256(result_path),
                "original_source": str(source),
                "source_sha256": sha,
                "section": section,
                "new_model_sends": 0,
                "publication_authorized": False,
            }
            marker = successor / "auto_captionless_recovery_intent.json"
            if successor.exists():
                require(successor.is_dir() and not successor.is_symlink()
                        and _verified_json(marker) == intention,
                        "Existing automatic recovery is not same immutable claim")
            else:
                successor.mkdir()
                _new_atomic(marker, intention)
            receipt = successor / "figures_source_only_local_recovery.json"
            if receipt.exists() or receipt.is_symlink():
                verify_recovery_receipt(successor)
                return {
                    "status": "AUTO_CAPTIONLESS_RECOVERY_REUSED",
                    "recovery_trial": str(successor),
                    "source_sha256": sha,
                    "new_model_sends": 0,
                    "student_publication_authorized": False,
                }
            # A crash can leave a copied local work tree. Restart only when
            # this exact successor is owner-marked and has NO possible Send.
            for name in ("figures_attempt_started.json", "figures_attempt_result.json",
                         "stage_slides_started.json", "stage_slides_result.json",
                         "stage_narration_started.json", "stage_narration_result.json",
                         "stage_script_qa_started.json", "stage_script_qa_result.json"):
                p = successor / name
                require(not p.exists() and not p.is_symlink(),
                        "Recovery successor acquired a stage Send; no reset")
            staged_root = successor / "source_tree"
            staged_chapter = staged_root / section.split(".")[0]
            staged = staged_chapter / section
            for folder in (staged_root, staged_chapter, staged):
                require(not folder.is_symlink() and not folder.is_junction(),
                        "Recovery successor contains a redirected source directory")
            staged_source = staged / "source.pdf"
            workspace = staged / ".microgen_work"
            if workspace.exists() or workspace.is_symlink():
                require(workspace.is_dir() and not workspace.is_symlink()
                        and not workspace.is_junction()
                        and staged_source.is_file() and not staged_source.is_symlink()
                        and file_sha256(staged_source) == sha
                        and all(not p.is_symlink() and not p.is_junction()
                                for p in workspace.rglob("*")),
                        "Unsafe interrupted recovery workspace; preserve for review")
                # Owned, no-send recovery copy only. Never touch historical trial.
                shutil.rmtree(workspace)
            staged.mkdir(parents=True, exist_ok=True)
            if not staged_source.exists():
                with source.open("rb") as src, staged_source.open("xb") as dest:
                    shutil.copyfileobj(src, dest)
            require(staged_source.is_file() and not staged_source.is_symlink()
                    and file_sha256(staged_source) == sha,
                    "Staged immutable PDF changed")
            new_contract = {
                "schema_version": 1,
                "status": "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL",
                "source_path": str(source),
                "source_sha256": sha,
                "staged_source_path": str(staged_source),
                "stage_goal": "figures",
                "paid_tts_authorized": False,
                "student_publication_authorized": False,
            }
            contract_path = successor / "fresh_trial_contract.json"
            if contract_path.exists() or contract_path.is_symlink():
                require(_verified_json(contract_path) == new_contract,
                        "Interrupted successor contract changed")
            else:
                _new_atomic(contract_path, new_contract)
            recover(previous_trial=previous_trial, new_trial=successor)
            verify_recovery_receipt(successor)
            require(file_sha256(source) == sha,
                    "Publisher PDF changed during automatic recovery")
            return {
                "status": "AUTO_CAPTIONLESS_RECOVERY_COMPLETED",
                "recovery_trial": str(successor),
                "source_sha256": sha,
                "new_model_sends": 0,
                "student_publication_authorized": False,
            }
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
