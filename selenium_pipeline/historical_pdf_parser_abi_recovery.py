"""Read-only legacy PDF extraction ABI recovery for immutable source reviews.

Never re-submit a model request, regenerate audio, approve mathematics or
call a renderer. The only eligible recovery is a known, already installed
local Python rechecking the exact SAME saved SHA-bound historical review.
A failed child, changed source, untrusted receipt or new response cannot pass.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from .evidence_reuse_contract import file_sha256

SIGNATURE = "HISTORICAL_SOURCE_PDF_TEXT_PARSER_ABI_CHANGED"
MECHANISM = "REVERIFY_SAME_IMMUTABLE_SOURCE_REVIEW_IN_EXISTING_COMPATIBLE_PYTHON"
MISMATCH = "Model answer does not belong to this exact source/slides/narration request"
ROOT = "historical_pdf_parser_abi_recovery_v1"
MAX_RESULT_BYTES = 200_000


class HistoricalParserABIBlocked(ValueError):
    pass


def _require(ok: bool, why: str) -> None:
    if not ok:
        raise HistoricalParserABIBlocked(why)


def _read_manifest(path: Path) -> dict:
    _require(path.is_file() and not path.is_symlink()
             and 0 < path.stat().st_size <= 300_000,
             "Unsafe or missing original saved source manifest")
    obj = json.loads(path.read_text(encoding="utf8"))
    _require(type(obj) is dict
             and obj.get("status") ==
                 "DETERMINISTIC_SOURCE_GROUNDED_SAFE_PROSE_CANDIDATES_REVIEW_ONLY",
             "Saved historical review manifest is not a proven source fallback")
    return obj


def recover_readonly(*, cause: Exception, lecture: Path,
                     checkpoint: Path | None, fallback_dir: Path | None,
                     queue_dir: Path | None,
                     model_responses: Path | None,
                     expected_publisher_sha256: str | None,
                     localappdata: Path | None = None,
                     run_child=None) -> dict:
    _require(type(cause).__name__ == "RichMappingError"
             and type(cause).__module__.endswith(".rich_element_model_alignment")
             and str(cause) == MISMATCH,
             "Not an eligible historical PDF text extraction ABI error")
    _require(model_responses is None and checkpoint is not None
             and fallback_dir is not None and queue_dir is not None,
             "Only saved source-fallback READ-ONLY review can switch parser ABI")
    lecture, checkpoint, fallback_dir, queue_dir = (
        Path(x).absolute() for x in
        (lecture, checkpoint, fallback_dir, queue_dir))
    _require(all(x.is_dir() and not x.is_symlink() for x in
                 (lecture, checkpoint, fallback_dir, queue_dir)),
             "Unsafe or absent immutable source review paths")
    inputs = {}
    for name in ("source.pdf", "slides.pdf", "script.txt"):
        f = lecture / name
        _require(f.is_file() and not f.is_symlink(),
                 "Original immutable source triad unavailable")
        inputs[name] = file_sha256(f)
    if expected_publisher_sha256 is not None:
        _require(inputs["source.pdf"] == expected_publisher_sha256,
                 "Expected publisher SHA changed; no parser fallback")
    saved = fallback_dir / "SAFE_PROSE_FALLBACK_MANIFEST.json"
    manifest = _read_manifest(saved)
    manifest_sha = file_sha256(saved)
    _require(manifest.get("source_inputs_sha256") == inputs
             and manifest.get("model_provider_invoked") is False
             and manifest.get("student_publication_authorized") is False
             and manifest.get("paid_tts_authorized") is False,
             "Saved source review cannot be reinterpreted for a different source")
    from .recovery_registry import lookup_mechanism
    _require(lookup_mechanism("historical_pdf_parser_abi", SIGNATURE) == MECHANISM,
             "Registered historical PDF parser recovery missing or retired")
    local = Path(localappdata if localappdata is not None
                 else os.environ.get("LOCALAPPDATA", "")).absolute()
    _require(local.is_dir() and not local.is_symlink(),
             "Existing user-local parser recovery root missing")
    compatible = local / "miniconda3" / "python.exe"
    _require(compatible.is_file() and not compatible.is_symlink()
             and not compatible.parent.is_symlink()
             and compatible.resolve().is_relative_to(local.resolve())
             and compatible.resolve() != Path(sys.executable).resolve(),
             "No independently installed compatible historical PDF parser")
    _require(os.environ.get("MICROGEN_PARSER_ABI_CHILD") != "1",
             "Nested parser fallback forbidden")
    module_root = Path(__file__).resolve().parent.parent
    args = [str(compatible), "-m",
            "selenium_pipeline.original_source_e2e_acceptance",
            "--lecture", str(lecture), "--checkpoint", str(checkpoint),
            "--fallback-dir", str(fallback_dir),
            "--queue-dir", str(queue_dir),
            "--readonly-parser-abi-child"]
    environment = dict(os.environ)
    environment["MICROGEN_PARSER_ABI_CHILD"] = "1"
    try:
        if run_child is None:
            child = subprocess.run(
                args, cwd=module_root, env=environment,
                capture_output=True, text=True, timeout=120, check=False)
        else:
            child = run_child(args, cwd=module_root, env=environment,
                              capture_output=True, text=True, timeout=120,
                              check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HistoricalParserABIBlocked(
            "Compatible source-only parser subprocess unavailable") from exc
    _require(child.returncode == 0
             and isinstance(child.stdout, str)
             and 2 < len(child.stdout.encode("utf8")) <= MAX_RESULT_BYTES,
             "Compatible parser did not return bounded source proof")
    try:
        report = json.loads(child.stdout)
    except (ValueError, UnicodeError) as exc:
        raise HistoricalParserABIBlocked(
            "Compatible parser output was not strict JSON") from exc
    _require(type(report) is dict
             and report.get("schema_version") == 1
             and report.get("status") ==
                 "BLOCKED_UNRESOLVED_SOURCE_VISUAL_NARRATION"
             and report.get("source_inputs_sha256") == inputs
             and report.get("new_model_or_tts_calls") is False
             and report.get("student_publication_authorized") is False
             and report.get("original_source_assets_modified") is False
             and report.get("existing_per_element_recorded_audio_available") is False
             and report.get("execution_allowed_without_new_paid_or_model_calls") is False,
             "Incompatible parser must never promote a saved review or media")
    _require(all(file_sha256(lecture / n) == h for n, h in inputs.items())
             and file_sha256(saved) == manifest_sha,
             "Source or fallback manifest changed during compatibility verification")
    key = hashlib.sha256(
        (str(lecture) + "|" + str(checkpoint) + "|" + str(fallback_dir)
         + "|" + manifest_sha + "|" + inputs["source.pdf"]).encode("utf8")
    ).hexdigest()
    home = local / "MicroGen_AI_Web_Checkpoints" / ROOT
    _require(not home.is_symlink() and not home.parent.is_symlink(),
             "Unsafe historical parser recovery receipt root")
    home.mkdir(parents=True, exist_ok=True)
    receipt_path = home / (key + ".json")
    receipt = {
        "schema_version": 1,
        "status": "VERIFIED_COMPATIBLE_PARSER_READONLY_SAVED_SOURCE_REUSE",
        "source_inputs_sha256": inputs,
        "saved_manifest_sha256": manifest_sha,
        "original_lecture_path": str(lecture),
        "original_checkpoint_path": str(checkpoint),
        "compatible_interpreter": str(compatible),
        "recovery_mechanism": MECHANISM,
        "read_only_saved_model_request": True,
        "model_or_tts_requests": 0,
        "rendering_or_publication_authorized": False,
        "result_sha256": hashlib.sha256(
            json.dumps(report, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False).encode("utf8")).hexdigest(),
    }
    raw = (json.dumps(receipt, indent=2, sort_keys=True,
                      ensure_ascii=False) + "\n").encode("utf8")
    _require(not receipt_path.is_symlink(),
             "Linked historical parser recovery receipt forbidden")
    if receipt_path.exists():
        _require(not receipt_path.is_symlink()
                 and receipt_path.is_file()
                 and receipt_path.read_bytes() == raw,
                 "Persisted parser recovery decision disagrees with source")
    else:
        try:
            with receipt_path.open("xb") as f:
                f.write(raw)
                f.flush()
                os.fsync(f.fileno())
        except FileExistsError:
            _require(receipt_path.read_bytes() == raw,
                     "Concurrent historical parser recovery receipt changed")
    return {**report,
            "historical_pdf_parser_abi_recovery": "VERIFIED_READONLY_NO_SEND",
            "historical_pdf_parser_abi_receipt": str(receipt_path)}
