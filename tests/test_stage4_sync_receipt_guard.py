"""Regression: a hashed MP4 receipt cannot mask stale slide/script/WAV alignment."""
from __future__ import annotations

import wave

import pymupdf
import pytest

from selenium_pipeline.cleanup import (
    _final_hashes, _sha256, _write_receipt, cleanup_completed_lecture,
    completed_lecture,
)
from selenium_pipeline.reliability_audit import inspect_campaign
from selenium_pipeline.slide_narration_sync import record_structural_alignment


def _fixture(tmp_path):
    folder = tmp_path / "8" / "8.1"
    folder.mkdir(parents=True)
    (folder / "source.pdf").write_bytes(b"source-original")
    (folder / "slides.tex").write_text(r"\\documentclass{beamer}", encoding="utf-8")
    doc = pymupdf.open()
    doc.new_page().insert_text((70, 70), "Unchanged slide")
    doc.save(folder / "slides.pdf")
    doc.close()
    (folder / "script.txt").write_text(
        "**Slide 1 [10 sec]:\nSpoken content**", encoding="utf-8"
    )
    (folder / "slides.mp4").write_bytes(b"previous playable video for test")
    _write_wav(folder / "slide1.wav", 0)
    record_structural_alignment(folder)
    return folder


def _write_wav(path, sample):
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(8000)
        stream.writeframes(bytes([sample, 0]) * 8000)


def test_valid_sync_receipt_rejects_later_wav_drift(tmp_path):
    folder = _fixture(tmp_path)
    source = folder / "source.pdf"
    published = (folder / "slides.mp4").read_bytes()
    cleanup_completed_lecture(source, pipeline="selenium")
    assert completed_lecture(source)
    _write_wav(folder / "slide1.wav", 1)
    assert not completed_lecture(source)
    record = inspect_campaign(tmp_path, expected_count=1)["jobs"][0]
    assert record["category"] == "published_requires_reconciliation"
    assert record["structural_sync"] == "invalid"
    assert (folder / "slides.mp4").read_bytes() == published


def test_deleted_alignment_file_invalidates_new_receipt(tmp_path):
    folder = _fixture(tmp_path)
    source = folder / "source.pdf"
    cleanup_completed_lecture(source, pipeline="selenium")
    assert completed_lecture(source)
    (folder / "slide_narration_sync.json").unlink()
    assert not completed_lecture(source)


def test_precleanup_refuses_stale_alignment_without_losing_files(tmp_path):
    folder = _fixture(tmp_path)
    source = folder / "source.pdf"
    video = (folder / "slides.mp4").read_bytes()
    _write_wav(folder / "slide1.wav", 2)
    with pytest.raises(ValueError, match="synchronization requires review"):
        cleanup_completed_lecture(source, pipeline="selenium")
    assert not (folder / ".microgen_completion.json").exists()
    assert (folder / "slides.mp4").read_bytes() == video


def test_legacy_receipt_with_present_invalid_alignment_is_rejected(tmp_path):
    folder = _fixture(tmp_path)
    source = folder / "source.pdf"
    _write_receipt(source, {
        "source_sha256": _sha256(source),
        "final_sha256": _final_hashes(folder),
    })
    assert completed_lecture(source)
    _write_wav(folder / "slide1.wav", 3)
    assert not completed_lecture(source)
