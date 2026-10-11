import json
import wave
from pathlib import Path

import pytest

from selenium_pipeline import tts_qa_repair


def test_failing_slides_selects_only_nonpass():
    assert tts_qa_repair.failing_slides({"slides": [
        {"slide": 1, "status": "pass"},
        {"slide": 2, "status": "review"},
        {"slide": 3, "status": "pass"},
    ]}) == [2]


def test_selective_repair_and_recheck(tmp_path, monkeypatch):
    (tmp_path / "script.txt").write_text(
        "**Slide 1 [1 min]:\nGood.\n**Slide 2 [1 min]:\nBad.",
        encoding="utf-8",
    )
    for n in (1, 2):
        (tmp_path / f"slide{n}.wav").write_bytes(b"RIFF" + bytes([n]) * 64)
    initial = (tmp_path / "slide1.wav").read_bytes()
    checked = []

    def fake_report(folder, **kwargs):
        checked.append(True)
        return {"slides": [
            {"slide": 1, "status": "pass"},
            {"slide": 2, "status": "review" if len(checked) == 1 else "pass"},
        ]}

    monkeypatch.setattr(tts_qa_repair, "build_report", fake_report)
    monkeypatch.setattr(tts_qa_repair, "write_report", lambda *args: None)
    monkeypatch.setattr(tts_qa_repair, "_gemini_say_with_watchdog",
                        lambda *args: b"RIFF" + b"z" * 64)
    tts_qa_repair.repair(tmp_path, model="flash", threshold=99, provider="gemini",
                         tts_model="flash-tts", voice="Kore")
    assert (tmp_path / "slide1.wav").read_bytes() == initial
    assert (tmp_path / "slide2.wav").read_bytes() == b"RIFF" + b"z" * 64
    assert len(checked) == 2


def test_repair_exhaustion_blocks_video(tmp_path, monkeypatch):
    (tmp_path / "script.txt").write_text("**Slide 1 [1 min]:\nBad.", encoding="utf-8")
    (tmp_path / "slide1.wav").write_bytes(b"RIFF" + b"a" * 64)
    monkeypatch.setattr(tts_qa_repair, "build_report",
                        lambda *args, **kwargs: {"slides": [{"slide": 1, "status": "review"}]})
    monkeypatch.setattr(tts_qa_repair, "write_report", lambda *args: None)
    monkeypatch.setattr(tts_qa_repair, "_gemini_say_with_watchdog",
                        lambda *args: b"RIFF" + b"b" * 64)
    monkeypatch.setenv("MICROGEN_TTS_QA_REPAIR_DELAY_SECONDS", "0")
    with pytest.raises(RuntimeError, match="still blocked"):
        tts_qa_repair.repair(tmp_path, model="flash", threshold=99, provider="gemini",
                             tts_model="flash-tts", voice="Kore", max_repairs=2)
