"""Stage 5 explicit legacy completion repair: dry-run first, never change media."""
from __future__ import annotations

import json
import wave
from unittest.mock import patch

import pymupdf
import pytest

from selenium_pipeline.cleanup import (
    _final_hashes, _sha256, _write_receipt, completed_lecture,
)
from selenium_pipeline.reconcile_structural_sync import reconcile


def make_legacy(tmp_path):
    folder = tmp_path / "8" / "8.2"
    folder.mkdir(parents=True)
    source = folder / "source.pdf"
    source.write_bytes(b"%PDF synthetic source only")
    doc = pymupdf.open()
    doc.new_page().insert_text((70, 70), "Potential energy")
    doc.save(folder / "slides.pdf")
    doc.close()
    (folder / "slides.tex").write_text(r"\\documentclass{beamer}")
    (folder / "script.txt").write_text("**Slide 1 [10 sec]:**\nPotential energy.")
    (folder / "slides.mp4").write_bytes(b"synthetic MP4 placeholder" * 200)
    with wave.open(str(folder / "slide1.wav"), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\\x00\\x00" * 8000)
    (folder / "tts_fidelity_report.json").write_text(json.dumps({
        "threshold_percent": 99.0,
        "summary": {"slides": 1, "passed": 1, "review": 0,
                    "blocking_failures": 0, "minimum_fidelity_percent": 100.0},
        "slides": [{"slide": 1, "status": "pass", "fidelity_percent": 100.0}],
    }))
    (folder / "script_risk_report.json").write_text(json.dumps({
        "summary": {"blocking": 0, "warnings": 1}
    }))
    _write_receipt(source, {
        "pipeline": "selenium", "cleanup": "complete",
        "source_sha256": _sha256(source),
        "final_sha256": _final_hashes(folder),
    })
    assert completed_lecture(source)
    return folder


def test_explicit_repair_preserves_media_and_binds_sync_sha(tmp_path):
    folder = make_legacy(tmp_path)
    media_names = ("source.pdf", "slides.tex", "slides.pdf", "script.txt", "slides.mp4", "slide1.wav")
    before = {name: _sha256(folder / name) for name in media_names}
    with patch("selenium_pipeline.reconcile_structural_sync.ffmpeg_executable", return_value="mock-ffmpeg"):
        with patch("selenium_pipeline.reconcile_structural_sync.validate_video") as video:
            dry = reconcile(folder)
            assert dry["status"] == "eligible"
            assert not (folder / "slide_narration_sync.json").exists()
            assert not (folder / ".history").exists()
            result = reconcile(folder, apply=True)
            assert result["status"] == "reconciled"
            assert video.call_count == 2
    assert all(_sha256(folder / name) == before[name] for name in media_names)
    assert completed_lecture(folder / "source.pdf")
    assert (folder / "slide_narration_sync.json").is_file()
    assert (folder / ".history").is_dir()
    assert reconcile(folder)["status"] == "already_certified"
    with wave.open(str(folder / "slide1.wav"), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(b"\\x01\\x00" * 8000)
    assert not completed_lecture(folder / "source.pdf")


def test_fail_closed_on_pending_audio_review(tmp_path):
    folder = make_legacy(tmp_path)
    path = folder / "tts_fidelity_report.json"
    qa = json.loads(path.read_text())
    qa["summary"]["review"] = 1
    path.write_text(json.dumps(qa))
    with pytest.raises(ValueError, match="fidelity report"):
        reconcile(folder, apply=True)
    assert not (folder / "slide_narration_sync.json").exists()
    assert not (folder / ".history").exists()


def test_fail_closed_on_unverified_mp4(tmp_path):
    folder = make_legacy(tmp_path)
    with patch("selenium_pipeline.reconcile_structural_sync.ffmpeg_executable", return_value="mock-ffmpeg"):
        with patch("selenium_pipeline.reconcile_structural_sync.validate_video",
                   side_effect=RuntimeError("bad video streams")):
            with pytest.raises(RuntimeError, match="bad video"):
                reconcile(folder, apply=True)
    assert not (folder / "slide_narration_sync.json").exists()
    assert not (folder / ".history").exists()


def test_fail_closed_on_existing_stale_alignment_record(tmp_path):
    folder = make_legacy(tmp_path)
    (folder / "slide_narration_sync.json").write_text('{"version": -1}')
    with pytest.raises(ValueError, match="changed since synchronization"):
        reconcile(folder, apply=True)
    assert not (folder / ".history").exists()
