"""Restart-safe, audited internal install of successfully repaired slide WAVs.

Only an already source-verified TTS QA candidate may enter. Protect original
audio in a durable, immutable-by-contract checkpoint; never touch source PDFs,
narration or published/subchapter audio. A partial install can be completed on
restart without requesting another model/TTS call. This is NOT student release.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import uuid

from .pcm_signal_integrity import inspect_pcm_signal
from .tts_qa_promotion import audit


class TTSRecoveryInstallBlocked(RuntimeError):
    pass


ROOT = ".tts_automatic_recovery"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(ok, reason):
    if not ok:
        raise TTSRecoveryInstallBlocked(reason)


def _regular_file(path: Path) -> bytes:
    require(path.is_file() and not path.is_symlink(),
            f"Missing or unsafe recovery file: {path.name}")
    return path.read_bytes()


def _write_exclusive(path: Path, data: bytes) -> None:
    with path.open("xb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())


def _atomic_write(path: Path, data: bytes) -> None:
    temp = path.parent / (".recovery_install_" + uuid.uuid4().hex)
    try:
        _write_exclusive(temp, data)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _journal_path(job: Path) -> Path:
    return job / "journal.json"


def _finish(folder: Path, job: Path) -> dict:
    record = json.loads(_regular_file(_journal_path(job)))
    require(record.get("schema_version") == 1
            and record.get("status") in ("READY", "COMPLETE")
            and record.get("student_publication_authorized") is False,
            "Untrusted automatic repair checkpoint")
    expected_job = sha((
        record["source_review_receipt_sha256"] +
        record["source_acoustic_report_sha256"] +
        record["script_sha256"] + record["manifest_sha256"]
    ).encode())
    require(job.name == expected_job,
            "Accepted repair journal does not match its SHA-bound identity")
    for key, filename in (("script_sha256", "script.txt"),
                          ("manifest_sha256", "tts_input_manifest.json")):
        require(sha(_regular_file(folder / filename)) == record[key],
                "Narration/provider provenance changed during automatic repair")
    unchanged = record.get("unchanged_wavs", {})
    require(isinstance(unchanged, dict)
            and all(name.startswith("slide") and name.endswith(".wav")
                    and name[5:-4].isdigit() for name in unchanged),
            "Invalid unchanged original audio checkpoint")
    for name, original_digest in unchanged.items():
        require(sha(_regular_file(folder / name)) == original_digest,
                "Unrepaired slide WAV changed during technical recovery")
    changed = record["changed_wavs"]
    require(isinstance(changed, dict) and bool(changed)
            and all(name.startswith("slide") and name.endswith(".wav")
                    and name[5:-4].isdigit() for name in changed),
            "Invalid selective repair inventory")
    require(record["report_json_sha256"] ==
            sha(_regular_file(job / "report.json"))
            and record["report_md_sha256"] ==
            sha(_regular_file(job / "report.md")),
            "Previously accepted acoustic QA receipt changed")
    for name, hashes in changed.items():
        original = _regular_file(job / "original" / name)
        repaired = _regular_file(job / "repaired" / name)
        require(sha(original) == hashes["original_sha256"]
                and sha(repaired) == hashes["repaired_sha256"],
                "Original or repaired checkpoint bytes changed")
        require(sha(_regular_file(folder / name)) in (
                hashes["original_sha256"], hashes["repaired_sha256"]),
                "Unexpected external WAV mutation during automatic recovery")
        inspect_pcm_signal(repaired, label=f"repaired {name}")
    # No modifications until every recorded original or already installed
    # candidate and both full QA reports have been SHA checked.
    for name, hashes in changed.items():
        dest = folder / name
        if sha(_regular_file(dest)) == hashes["original_sha256"]:
            _atomic_write(dest, _regular_file(job / "repaired" / name))
        require(sha(_regular_file(dest)) == hashes["repaired_sha256"],
                "Repaired WAV was not installed exactly")
    for destname, archive, digest in (
            ("tts_fidelity_report.json", "report.json", record["report_json_sha256"]),
            ("tts_fidelity_report.md", "report.md", record["report_md_sha256"])):
        _atomic_write(folder / destname, _regular_file(job / archive))
        require(sha(_regular_file(folder / destname)) == digest,
                "Acoustic QA report did not install exactly")
    record["status"] = "COMPLETE"
    record["automatic_pipeline_continuation_eligible"] = True
    record["acoustic_qa_already_verified_by_source_bound_report"] = True
    record["independent_human_listening_verified"] = False
    record["student_publication_authorized"] = False
    _atomic_write(_journal_path(job),
                  (json.dumps(record, indent=2, sort_keys=True)+"\n").encode())
    return record


def resume_pending(folder: Path) -> dict | None:
    """Roll forward a READY source-bound repair; zero provider calls."""
    folder = Path(folder).absolute()
    root = folder / ROOT
    if not root.exists():
        return None
    require(root.is_dir() and not root.is_symlink(),
            "Unsafe automatic TTS repair journal root")
    jobs = sorted(root.iterdir())
    require(all(x.is_dir() and not x.is_symlink()
                and (x / "journal.json").is_file()
                for x in jobs), "Incomplete untrusted auto-recovery checkpoint")
    pending = []
    for job in jobs:
        record = json.loads(_regular_file(_journal_path(job)))
        if record.get("status") == "READY":
            pending.append(job)
    require(len(pending) <= 1, "Multiple unfinished TTS recovery checkpoints")
    return _finish(folder, pending[0]) if pending else None


def install_verified(folder: Path, review: Path) -> dict:
    """Reuse existing strict tts_qa_promotion.audit before internal install."""
    folder = Path(folder).absolute()
    review = Path(review).absolute()
    require(folder.is_dir() and review.is_dir()
            and not folder.is_symlink() and not review.is_symlink(),
            "Missing original or source-verified review folder")
    require(resume_pending(folder) is None,
            "Earlier interrupted recovery was completed; recheck pipeline first")
    accepted = audit(folder, review, allow_original_pcm_repair=True)
    changed = accepted["changed_slide_numbers"]
    require(changed, "No actual selective WAV repairs to install")
    current = {}
    unchanged = {}
    # The strict phonetic audit covers all slides. Independently check the
    # actual signal of EVERY final WAV and guard unchanged slides against
    # mutation between the audit and the restart-safe installation.
    for name, expected in accepted["candidate_wav_sha256"].items():
        candidate = _regular_file(review / name)
        require(sha(candidate) == expected, "Final candidate WAV SHA changed")
        inspect_pcm_signal(candidate, label=f"candidate {name}")
        if int(name[5:-4]) not in changed:
            previous = _regular_file(folder / name)
            require(sha(previous) == accepted["original_wav_sha256"][name]
                    and previous == candidate,
                    "Unrepaired slide waveform differs from original source")
            unchanged[name] = sha(previous)
    for number in changed:
        name = f"slide{number}.wav"
        original = _regular_file(folder / name)
        replacement = _regular_file(review / name)
        require(sha(original) == accepted["original_wav_sha256"][name]
                and sha(replacement) == accepted["candidate_wav_sha256"][name]
                and original != replacement,
                "Selective candidate WAV does not match strict QA receipt")
        inspect_pcm_signal(replacement, label=f"repaired {name}")
        current[name] = {"original_sha256": sha(original),
                         "repaired_sha256": sha(replacement)}
    # No source writes before all repaired WAVs and source-bound Gemini QA pass.
    script = _regular_file(folder / "script.txt")
    manifest = _regular_file(folder / "tts_input_manifest.json")
    report = _regular_file(review / "tts_fidelity_report.json")
    report_md = _regular_file(review / "tts_fidelity_report.md")
    root = folder / ROOT
    require(not root.is_symlink(), "Unsafe automatic recovery root")
    root.mkdir(exist_ok=True)
    key = sha((accepted["receipt_sha256"]+accepted["fidelity_report_sha256"]
               +sha(script)+sha(manifest)).encode())
    job = root / key
    require(not job.exists(), "This repaired candidate was already installed or staged")
    temp = root / (".staging_" + uuid.uuid4().hex)
    temp.mkdir()
    try:
        (temp / "original").mkdir()
        (temp / "repaired").mkdir()
        for name in current:
            _write_exclusive(temp / "original" / name, _regular_file(folder / name))
            _write_exclusive(temp / "repaired" / name, _regular_file(review / name))
        _write_exclusive(temp / "report.json", report)
        _write_exclusive(temp / "report.md", report_md)
        record = {
            "schema_version": 1, "status": "READY",
            "script_sha256": sha(script), "manifest_sha256": sha(manifest),
            "source_review_receipt_sha256": accepted["receipt_sha256"],
            "source_acoustic_report_sha256": accepted["fidelity_report_sha256"],
            "report_json_sha256": sha(report),
            "report_md_sha256": sha(report_md),
            "changed_wavs": current,
            "unchanged_wavs": unchanged,
            "student_publication_authorized": False,
            "automatic_pipeline_continuation_eligible": False,
        }
        _write_exclusive(temp / "journal.json",
                         (json.dumps(record, indent=2, sort_keys=True)+"\n").encode())
        os.replace(temp, job)
    finally:
        if temp.exists():
            shutil.rmtree(temp)
    return _finish(folder, job)
