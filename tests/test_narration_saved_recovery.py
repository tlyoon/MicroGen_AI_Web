"""Narration recovery must be source-bound and require full current QA."""
import hashlib
import json
import os
from pathlib import Path

import pytest

from selenium_pipeline.narration_saved_recovery import recover_saved_narration
from selenium_pipeline.narration_transport_guard import narration_api_claim, IndeterminateSend


def prepare(tmp_path):
    source = tmp_path / "source.pdf"
    slides = tmp_path / "slides.pdf"
    prompt = tmp_path / "rendered.txt"
    source.write_bytes(b"%PDF-1.7\nsource")
    slides.write_bytes(b"%PDF-1.7\nslides")
    prompt.write_text("Prompt")
    state = {
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "failed_stage": "narration",
        "completed": {"slides": {"model": "gemini-3.8-flash"}},
    }
    (tmp_path / ".selenium_pipeline_state.json").write_text(json.dumps(state))
    candidate = tmp_path / "script.rejected_api_attempt_1.txt"
    candidate.write_text("**Slide 1 [Intro]:** The physically identified point labeled A has moved." * 6)
    return source, slides, prompt, candidate


def test_only_full_current_qa_recovers_without_new_model_request(tmp_path):
    source, slides, _, candidate = prepare(tmp_path)
    calls = []
    def validator(path):
        calls.append(path.name)
        return []
    result = recover_saved_narration(tmp_path, source_pdf=source, slides_pdf=slides,
                                     check_warnings=validator)
    assert result["status"] == "accepted_saved_narration"
    assert result["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert (tmp_path / "script.txt").read_bytes() == candidate.read_bytes()
    assert calls == [candidate.name, "script.txt.recovering"]


def test_reject_tampered_source_stale_slide_or_validation_warning(tmp_path):
    source, slides, _, candidate = prepare(tmp_path)
    original_source = source.read_bytes()
    source.write_bytes(b"%PDF-1.7\nchanged")
    assert recover_saved_narration(tmp_path, source_pdf=source, slides_pdf=slides,
                                   check_warnings=lambda _: []) is None
    source.write_bytes(original_source)
    slides.write_bytes(b"%PDF-1.7\nrecompiled after candidate")
    os.utime(slides, ns=(candidate.stat().st_mtime_ns + 2_000_000_000,)*2)
    assert recover_saved_narration(tmp_path, source_pdf=source, slides_pdf=slides,
                                   check_warnings=lambda _: []) is None
    os.utime(slides, ns=(candidate.stat().st_mtime_ns - 2_000_000_000,)*2)
    assert recover_saved_narration(tmp_path, source_pdf=source, slides_pdf=slides,
                                   check_warnings=lambda _: ["title mismatch"]) is None
    assert not (tmp_path / "script.txt").exists()


def test_narration_claim_binds_original_source_as_well_as_slides(tmp_path):
    source, slides, prompt, _ = prepare(tmp_path)
    root = tmp_path / "claims"
    a = narration_api_claim(source, slides, prompt, "Request", root=root)
    assert a.read_existing() is None
    a.mark_send_may_have_occurred()
    with pytest.raises(IndeterminateSend):
        a.read_existing()
    with pytest.raises(IndeterminateSend):
        a.mark_send_may_have_occurred()
    source.write_bytes(b"%PDF-1.7\nchanged")
    b = narration_api_claim(source, slides, prompt, "Request", root=root)
    assert b.read_existing() is None


def test_saved_narration_claim_reuses_response_and_tamper_blocks(tmp_path):
    source, slides, prompt, _ = prepare(tmp_path)
    root = tmp_path / "claims"
    a = narration_api_claim(source, slides, prompt, "Request", root=root)
    a.mark_send_may_have_occurred()
    a.capture("A valid numbered narration response")
    b = narration_api_claim(source, slides, prompt, "Request", root=root)
    assert b.read_existing() == "A valid numbered narration response"
    b.raw_path.write_text("tampered")
    with pytest.raises(IndeterminateSend, match="checksum"):
        b.read_existing()
