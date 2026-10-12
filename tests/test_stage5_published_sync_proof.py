"""Stage 5 regression: published alignment receipt must survive transient cleanup.

The live three-PC campaign exposed a gap: a valid slide_narration_sync.json was
created in .microgen_work, but was never copied beside source.pdf. Cleanup
then deleted the only synchronization proof while still stamping success.
"""
from __future__ import annotations

import ast
import json
import wave
from pathlib import Path

import pymupdf
import pytest

from selenium_pipeline.cleanup import cleanup_completed_lecture, completed_lecture
from selenium_pipeline.output_paths import publish_stage_outputs
from selenium_pipeline.slide_narration_sync import record_structural_alignment, verify


def _make_workspace(tmp_path):
    folder = tmp_path / "8" / "8.2"
    folder.mkdir(parents=True)
    source = folder / "source.pdf"
    source.write_bytes(b"synthetic source, leave unchanged")
    work = folder / ".microgen_work"
    work.mkdir()
    (work / "source.pdf").write_bytes(source.read_bytes())
    (work / ".selenium_pipeline_state.json").write_text(
        json.dumps({"completed": {"tts_qa": {"model": "verified"}}})
    )
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Wave equation and boundary conditions")
    doc.save(work / "slides.pdf")
    doc.close()
    (work / "slides.tex").write_text(r"\\documentclass{beamer}")
    (work / "script.txt").write_text(
        "**Slide 1 [10 sec]:**\nThe wave equation describes propagation.\n"
    )
    with wave.open(str(work / "slide1.wav"), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(8000)
        out.writeframes(b"\x00\x00" * 8000)
    (work / "slides.mp4").write_bytes(b"synthetic-validated-MP4-placeholder")
    return source, work


def test_tts_qa_publishes_structural_proof_and_final_receipt_binds_it(tmp_path):
    source, work = _make_workspace(tmp_path)
    for stage in ("slides", "narration", "tts"):
        publish_stage_outputs(work, source, stage)
    record_structural_alignment(work)
    published = publish_stage_outputs(work, source, "tts_qa")
    proof = source.parent / "slide_narration_sync.json"
    assert proof in published
    assert verify(source.parent) == verify(work)
    publish_stage_outputs(work, source, "video")
    cleanup_completed_lecture(source, workspace=work, pipeline="selenium")
    assert not work.exists()
    assert proof.exists()
    receipt = json.loads((source.parent / ".microgen_completion.json").read_text())
    assert receipt["structural_sync_sha256"]
    assert completed_lecture(source)
    with wave.open(str(source.parent / "slide1.wav"), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(8000)
        out.writeframes(b"\x01\x00" * 8000)
    assert not completed_lecture(source)


def test_missing_publication_proof_fails_verification(tmp_path):
    source, work = _make_workspace(tmp_path)
    for stage in ("slides", "narration", "tts"):
        publish_stage_outputs(work, source, stage)
    record_structural_alignment(work)
    assert verify(work)
    with pytest.raises(ValueError, match="No verified slide/narration"):
        verify(source.parent)


def test_runner_prevideo_verifies_published_proof(tmp_path):
    runner_path = Path(__file__).resolve().parents[1] / "selenium_pipeline" / "runner.py"
    tree = ast.parse(runner_path.read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == "verify"]
    assert any(ast.unparse(c) == "verify(source.parent)" for c in calls), (
        "Staged-only verification must not permit an MP4 to be published"
    )
