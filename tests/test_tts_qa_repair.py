import json
from pathlib import Path

import pytest

from selenium_pipeline import tts_qa_repair


def seed_provenance(folder: Path, texts, *, model="gemini-3.8-flash-lite-tts",
                    provider="gemini", voice="Kore"):
    data = {
        "version": 2,
        "primary": {"provider": provider, "model": model, "voice": voice},
        "slides": [
            {"slide": number, "source_text": text, "tts_text": text,
             "provider": provider, "model": model, "voice": voice,
             "fallback_used": False}
            for number, text in texts
        ],
    }
    (folder / "tts_input_manifest.json").write_text(json.dumps(data), encoding="utf-8")


def test_failing_slides_selects_only_nonpass():
    assert tts_qa_repair.failing_slides({"slides": [
        {"slide": 1, "status": "pass"},
        {"slide": 2, "status": "review"},
        {"slide": 3, "status": "pass"},
    ]}) == [2]


def test_selective_repair_stages_review_only_and_preserves_originals(tmp_path, monkeypatch):
    texts=[(1, "Good."), (2, "Bad.")]
    (tmp_path / "script.txt").write_text(
        "**Slide 1 [1 min]:\nGood.\n**Slide 2 [1 min]:\nBad.", encoding="utf-8")
    seed_provenance(tmp_path, texts)
    for n in (1, 2):
        (tmp_path / f"slide{n}.wav").write_bytes(b"RIFF" + bytes([n]) * 64)
    original1 = (tmp_path / "slide1.wav").read_bytes()
    original2 = (tmp_path / "slide2.wav").read_bytes()
    checked=[]

    def fake_report(folder, **kwargs):
        checked.append(folder)
        return {"slides": [
            {"slide": 1, "status": "pass"},
            {"slide": 2, "status": "review" if len(checked) == 1 else "pass"},
        ]}
    monkeypatch.setattr(tts_qa_repair, "build_report", fake_report)
    monkeypatch.setattr(tts_qa_repair, "write_report", lambda *args: None)
    requests=[]
    monkeypatch.setattr(tts_qa_repair, "_gemini_say_with_watchdog",
                        lambda *args: requests.append(args) or b"RIFF" + b"z"*64)
    with pytest.raises(RuntimeError, match="requires independent review"):
        tts_qa_repair.repair(tmp_path, model="flash", threshold=99, provider="gemini",
                             tts_model="gemini-3.8-flash-lite-tts", voice="Kore")
    assert len(requests) == 1
    assert (tmp_path / "slide1.wav").read_bytes() == original1
    assert (tmp_path / "slide2.wav").read_bytes() == original2
    assert len(checked) == 2
    assert checked[0] == tmp_path
    assert checked[1] != tmp_path
    review=checked[1]
    assert (review / "slide1.wav").read_bytes() == original1
    assert (review / "slide2.wav").read_bytes() == b"RIFF" + b"z"*64
    assert (review / "attempt1_slide2.wav").read_bytes() == b"RIFF" + b"z"*64
    receipt=json.loads((review / "review_only_receipt.json").read_text())
    assert receipt["status"] == "REVIEW_ONLY_UNPUBLISHED"
    assert receipt["original_audio_modified"] is False
    assert receipt["academic_approved"] is False
    assert receipt["video_publication_approved"] is False
    assert len(receipt["proposed_replacements"]) == 1
    assert not (tmp_path / ".tts.lock").exists()


def test_repair_exhaustion_preserves_original_and_blocks_video(tmp_path, monkeypatch):
    (tmp_path / "script.txt").write_text("**Slide 1 [1 min]:\nBad.", encoding="utf-8")
    seed_provenance(tmp_path, [(1, "Bad.")])
    original=b"RIFF" + b"a"*64
    (tmp_path / "slide1.wav").write_bytes(original)
    monkeypatch.setattr(tts_qa_repair, "build_report",
                        lambda *args, **kwargs: {"slides": [{"slide": 1, "status": "review"}]})
    monkeypatch.setattr(tts_qa_repair, "write_report", lambda *args: None)
    monkeypatch.setattr(tts_qa_repair, "_gemini_say_with_watchdog",
                        lambda *args: b"RIFF" + b"b"*64)
    monkeypatch.setenv("MICROGEN_TTS_QA_REPAIR_DELAY_SECONDS", "0")
    with pytest.raises(RuntimeError, match="still blocked"):
        tts_qa_repair.repair(tmp_path, model="flash", threshold=99, provider="gemini",
                             tts_model="gemini-3.8-flash-lite-tts", voice="Kore", max_repairs=2)
    assert (tmp_path / "slide1.wav").read_bytes() == original
    roots=list((tmp_path / ".tts_qa_review_candidates").iterdir())
    assert len(roots) == 1
    assert (roots[0] / "attempt1_slide1.wav").exists()
    assert (roots[0] / "attempt2_slide1.wav").exists()
    receipt=json.loads((roots[0] / "review_only_receipt.json").read_text())
    assert receipt["proposed_remaining_failures"] == [1]
    assert receipt["original_audio_modified"] is False


def test_wrong_voice_model_or_script_blocks_before_paid_synthesis(tmp_path, monkeypatch):
    (tmp_path / "script.txt").write_text("**Slide 1 [1 min]:\nCorrect.", encoding="utf-8")
    seed_provenance(tmp_path, [(1, "Different narration.")])
    original=b"RIFF"+b"a"*64
    (tmp_path / "slide1.wav").write_bytes(original)
    monkeypatch.setattr(tts_qa_repair, "build_report",
                        lambda *args, **kwargs: {"slides":[{"slide":1,"status":"review"}]})
    monkeypatch.setattr(tts_qa_repair, "write_report",lambda *args: None)
    invoked=[]
    monkeypatch.setattr(tts_qa_repair, "_gemini_say_with_watchdog",
                        lambda *args: invoked.append(args) or b"RIFF"+b"b"*64)
    with pytest.raises(RuntimeError, match="provenance mismatch"):
        tts_qa_repair.repair(tmp_path,model="flash",threshold=99,provider="gemini",
                             tts_model="gemini-3.8-flash-lite-tts",voice="Kore")
    assert invoked == []
    assert (tmp_path / "slide1.wav").read_bytes() == original
    assert not (tmp_path / ".tts_qa_review_candidates").exists()


def test_wrong_provider_or_voice_blocks_before_new_audio(tmp_path, monkeypatch):
    (tmp_path / "script.txt").write_text("**Slide 1 [1 min]:\nText.", encoding="utf-8")
    seed_provenance(tmp_path, [(1, "Text.")])
    (tmp_path / "slide1.wav").write_bytes(b"RIFF"+b"a"*64)
    monkeypatch.setattr(tts_qa_repair, "build_report",
                        lambda *args, **kwargs: {"slides":[{"slide":1,"status":"review"}]})
    monkeypatch.setattr(tts_qa_repair, "write_report",lambda *args: None)
    for provider,voice,model in [
        ("chirp3","Kore","gemini-3.8-flash-lite-tts"),
        ("gemini","Other","gemini-3.8-flash-lite-tts"),
        ("gemini","Kore","gemini-3.8-flash-tts"),
    ]:
        with pytest.raises(RuntimeError, match="provider/model/voice"):
            tts_qa_repair.repair(tmp_path,model="flash",threshold=99,
                                 provider=provider,voice=voice,tts_model=model)
    assert not (tmp_path / ".tts_qa_review_candidates").exists()


def test_already_passing_original_does_not_call_tts(tmp_path, monkeypatch):
    (tmp_path / "script.txt").write_text("**Slide 1 [1 min]:\nGood.", encoding="utf-8")
    old=b"RIFF"+b"a"*64
    (tmp_path / "slide1.wav").write_bytes(old)
    monkeypatch.setattr(tts_qa_repair, "build_report",
                        lambda *args, **kwargs: {"slides":[{"slide":1,"status":"pass"}]})
    monkeypatch.setattr(tts_qa_repair, "write_report",lambda *args: None)
    requests=[]
    monkeypatch.setattr(tts_qa_repair, "_gemini_say_with_watchdog",
                        lambda *args: requests.append(args))
    result=tts_qa_repair.repair(tmp_path,model="flash",threshold=99,provider="gemini",
                                tts_model="gemini-3.8-flash-lite-tts",voice="Kore")
    assert result["slides"][0]["status"] == "pass"
    assert requests == []
    assert (tmp_path / "slide1.wav").read_bytes() == old
    assert not (tmp_path / ".tts_qa_review_candidates").exists()
