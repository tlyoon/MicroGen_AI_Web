"""Automatically reuse SHA-proven historical content instead of resending Gemini."""
from __future__ import annotations
from pathlib import Path
import hashlib
import os
import shutil

from .evidence_reuse_contract import file_sha256
from .original_multisource_recovery_campaign import _verified_json, _new_atomic, require
from .figures_failed_source_only_resume import verify_recovery_receipt
from .windows_source_stage_reuse import adopt_accepted_slides
from .windows_original_stage_sequence import _EXPECTED_OUTPUTS
from .runner import check_valid


def reuse_following(*, prior_trial: Path, new_trial: Path, stage: str) -> dict:
    require(os.name == "nt" and stage in ("narration", "script_qa"),
            "Only narration and script QA reuse supported")
    old, new = Path(prior_trial).absolute(), Path(new_trial).absolute()
    require(old != new and old.parent == new.parent
            and old.is_dir() and new.is_dir()
            and not old.is_symlink() and not new.is_symlink(),
            "Distinct sibling trials required")
    a = _verified_json(old / "fresh_trial_contract.json")
    b = _verified_json(new / "fresh_trial_contract.json")
    sha = a.get("source_sha256")
    require(sha == b.get("source_sha256")
            and a.get("source_path") == b.get("source_path")
            and b.get("paid_tts_authorized") is False
            and b.get("student_publication_authorized") is False,
            "Original source/permission identity mismatch")
    verify_recovery_receipt(old)
    verify_recovery_receipt(new)
    predecessor = "slides" if stage == "narration" else "narration"
    old_prev = old / f"stage_{predecessor}_result.json"
    new_prev = new / f"stage_{predecessor}_result.json"
    old_p = _verified_json(old_prev)
    new_p = _verified_json(new_prev)
    require(old_p.get("status") == new_p.get("status") ==
                "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND"
            and old_p.get("source_sha256") ==
                new_p.get("source_sha256") == sha
            and old_p.get("output_sha256") == new_p.get("output_sha256"),
            "Predecessor content does not match")
    started = _verified_json(old / f"stage_{stage}_started.json")
    receipt_path = old / f"stage_{stage}_result.json"
    receipt = _verified_json(receipt_path)
    require(started.get("stage") == stage
            and started.get("source_sha256") == sha
            and started.get("single_attempt_no_provider_resend") is True
            and started.get("predecessor_receipt_sha256") == file_sha256(old_prev)
            and receipt.get("stage") == stage
            and receipt.get("status") == "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND"
            and receipt.get("source_sha256") == sha
            and receipt.get("predecessor_receipt_sha256") == file_sha256(old_prev)
            and receipt.get("exit_code") == 0
            and receipt.get("new_video_rendered") is False
            and receipt.get("student_publication_authorized") is False,
            "Historical stage not actually accepted")
    if stage == "narration":
        from .windows_lecture_progression_coordinator import _source_locked_ui_contract_breach
        require(not _source_locked_ui_contract_breach(old, "narration"),
                "Historical narration has UI/Thinking breach")
    old_dir = Path(a["staged_source_path"]).parent
    new_dir = Path(b["staged_source_path"]).parent
    old_work = old_dir / ".microgen_work"
    new_work = new_dir / ".microgen_work"
    require(check_valid(stage, old_work)
            and check_valid(predecessor, new_work)
            and file_sha256(old_work / "source.pdf") ==
                file_sha256(new_work / "source.pdf") == sha,
            "Historical or successor technical stage invalid")
    beg = new / f"stage_{stage}_started.json"
    fin = new / f"stage_{stage}_result.json"
    require(not beg.exists() and not fin.exists()
            and not beg.is_symlink() and not fin.is_symlink(),
            "Successor already claimed stage")
    if stage == "narration":
        require(not any(new.glob("stage_script_qa_*")),
                "Later stage already claimed")
    hashes = receipt.get("output_sha256")
    require(type(hashes) is dict, "Historical output SHA missing")
    for name in _EXPECTED_OUTPUTS[stage]:
        require(type(hashes.get(name)) is str
                and (old_dir / name).is_file()
                and (old_work / name).is_file()
                and not (old_dir / name).is_symlink()
                and not (old_work / name).is_symlink()
                and file_sha256(old_dir / name) ==
                    file_sha256(old_work / name) == hashes[name]
                and not (new_dir / name).exists()
                and not (new_work / name).exists(),
                "Untrusted stage output or occupied successor " + name)
    companions = (("script_risk_report.md", "math_semantic_repair_prompt.json",
                   "microgen_script_qa.log") if stage == "script_qa" else ())
    for name in companions:
        for src, dest in ((old_dir / name, new_dir / name),
                          (old_work / name, new_work / name)):
            require(not src.is_symlink() and not dest.exists()
                    and not dest.is_symlink(), "Unsafe QA companion destination")
    for name in _EXPECTED_OUTPUTS[stage]:
        shutil.copy2(old_dir / name, new_dir / name)
        shutil.copy2(old_work / name, new_work / name)
    for name in companions:
        for src, dest in ((old_dir / name, new_dir / name),
                          (old_work / name, new_work / name)):
            if src.is_file():
                shutil.copy2(src, dest)
    require(check_valid(stage, new_work)
            and all(file_sha256(new_dir / name) ==
                    file_sha256(new_work / name) == hashes[name]
                    for name in _EXPECTED_OUTPUTS[stage]),
            "Reused source-only stage fails final technical QA")
    _new_atomic(beg, {
        "schema_version": 1, "stage": stage, "source_sha256": sha,
        "predecessor_receipt_sha256": file_sha256(new_prev),
        "single_attempt_no_provider_resend": True,
        "student_publication_authorized": False,
        "reused_source_artifacts_only": True,
        "new_model_sends": 0,
        "prior_accepted_stage_receipt_sha256": file_sha256(receipt_path),
    })
    result = {
        "schema_version": 1, "stage": stage,
        "source_sha256": sha,
        "predecessor_receipt_sha256": file_sha256(new_prev),
        "status": "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND",
        "exit_code": 0,
        "output_sha256": {n: hashes[n] for n in _EXPECTED_OUTPUTS[stage]},
        "new_model_or_tts_calls": False, "new_tts_calls": False,
        "new_video_rendered": False, "student_publication_authorized": False,
        "reused_source_artifacts_only": True,
        "prior_accepted_stage_receipt_sha256": file_sha256(receipt_path),
        "independent_academic_or_media_qa_verified": False,
    }
    _new_atomic(fin, result)
    return result


def _auto_reuse_unlocked(*, trial_dir: Path, stage: str,
                         max_candidates: int = 200) -> dict:
    """Scan bounded sibling history; verify each and reuse one exact match."""
    target = Path(trial_dir).absolute()
    require(os.name == "nt" and target.is_dir() and not target.is_symlink()
            and stage in ("slides", "narration", "script_qa"),
            "Unsafe automatic source-stage reuse scope")
    contract = _verified_json(target / "fresh_trial_contract.json")
    local = Path(os.environ.get("LOCALAPPDATA", "")).absolute()
    require(local.is_dir() and target.is_relative_to(local),
            "Historical stage reuse must be Windows-local")
    candidates = sorted((p for p in target.parent.iterdir()
                         if p.is_dir() and not p.is_symlink()
                         and p != target and
                         (p / f"stage_{stage}_result.json").is_file()),
                        key=lambda p: p.name, reverse=True)
    require(len(candidates) <= max_candidates, "Too many candidates to trust automatic scan")
    for prior in candidates:
        try:
            previous = _verified_json(prior / "fresh_trial_contract.json")
            if (previous.get("source_sha256") != contract.get("source_sha256")
                    or previous.get("source_path") != contract.get("source_path")):
                continue
            outcome = (adopt_accepted_slides(prior_trial=prior, new_trial=target)
                       if stage == "slides" else
                       reuse_following(prior_trial=prior, new_trial=target, stage=stage))
            return {"status": "AUTO_REUSED_ACCEPTED_SOURCE_STAGE",
                    "stage": stage, "prior_trial": str(prior),
                    "source_sha256": contract["source_sha256"],
                    "new_model_sends": 0, "receipt": outcome}
        except (ValueError, OSError, KeyError, TypeError):
            continue
    return {"status": "NO_VERIFIED_REUSABLE_HISTORICAL_STAGE",
            "stage": stage, "new_model_sends": 0}


def auto_reuse_accepted_stage(*, trial_dir: Path, stage: str,
                              max_candidates: int = 200) -> dict:
    """One native Windows target lease across model-sparing source reuse."""
    import msvcrt
    target = Path(trial_dir).absolute()
    require(os.name == "nt" and target.is_dir() and not target.is_symlink()
            and stage in ("slides", "narration", "script_qa"),
            "Unsafe auto-reuse target or stage")
    local = Path(os.environ.get("LOCALAPPDATA", "")).absolute()
    require(local.is_dir() and target.is_relative_to(local),
            "Source reuse lock must reside under LOCALAPPDATA")
    identity = hashlib.sha256(str(target).casefold().encode("utf-8")).hexdigest()[:20]
    lock = target.parent / (".stage_auto_reuse_" + identity + ".lock")
    require(not lock.is_symlink()
            and (not lock.exists() or
                 lock.is_file() and lock.stat().st_size <= 1),
            "Untrusted historical stage lock")
    with lock.open("a+b") as stream:
        if lock.stat().st_size == 0:
            stream.write(b"1")
            stream.flush()
            os.fsync(stream.fileno())
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            from .original_multisource_recovery_campaign import CampaignRecoveryBlocked
            raise CampaignRecoveryBlocked("Another source-stage reuse is active") from exc
        try:
            return _auto_reuse_unlocked(
                trial_dir=target, stage=stage, max_candidates=max_candidates)
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
