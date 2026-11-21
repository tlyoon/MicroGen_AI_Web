"""Cross-PC published PDF-text ABI must never hide real content/audio drift."""
from __future__ import annotations
import copy
import hashlib
import json
import tempfile
import wave
from pathlib import Path
from unittest.mock import patch

import pytest
import pymupdf

from selenium_pipeline.slide_narration_sync import (
    inspect,verify,record_structural_alignment)
from selenium_pipeline.slide_narration_parser_parity_v1 import (
    verify_parser_text_abi)
from selenium_pipeline.cross_pc_artifact_recovery_registry import (
    require_cross_pc_handler,REGISTRY)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def completed(tmp_path):
    source=tmp_path/"source.pdf"
    source.write_bytes(b"%PDF-1.4 preserved immutable source PDF\n")
    doc=pymupdf.open()
    doc.new_page().insert_text((70,70),"Stable source-aligned physics statement")
    doc.save(tmp_path/"slides.pdf")
    (tmp_path/"script.txt").write_text(
        "**Slide 1 [10 sec]:\nNarration text**",encoding="utf8")
    with wave.open(str(tmp_path/"slide1.wav"),"wb") as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(8000)
        f.writeframes(b"\0\0"*8000)
    stable=record_structural_alignment(tmp_path)
    # Different PyMuPDF installed on a second PC may report a different
    # digest for *page text* extracted from identical immutable PDF bytes.
    drift=copy.deepcopy(stable)
    drift["page_text_sha256"][0]="a"*64
    assert drift["page_text_sha256"][0]!=stable["page_text_sha256"][0]
    (tmp_path/"slide_narration_sync.json").write_text(
        json.dumps(drift,indent=2)+"\n",encoding="utf8")
    manifest={"source_sha256":sha(source),
              "structural_sync_sha256":sha(tmp_path/"slide_narration_sync.json"),
              "final_sha256":{"slides.pdf":sha(tmp_path/"slides.pdf"),
                              "script.txt":sha(tmp_path/"script.txt")}}
    (tmp_path/".microgen_completion.json").write_text(
        json.dumps(manifest,indent=2)+"\n",encoding="utf8")
    assert inspect(tmp_path)==stable
    return tmp_path


def test_source_anchored_old_pdf_text_digest_is_accepted_readonly(completed):
    old=(completed/"slide_narration_sync.json").read_bytes()
    r=verify(completed)
    assert r["page_text_sha256"][0]=="a"*64
    assert (completed/"slide_narration_sync.json").read_bytes()==old
    proof=verify_parser_text_abi(
        folder=completed,saved=r,actual=inspect(completed),
        sync_receipt=completed/"slide_narration_sync.json")
    assert proof["changed_text_pages"]==[1]
    assert proof["student_publication_authorized"] is False


def test_changed_pdf_bytes_block_cross_version_recovery(completed):
    p=completed/"slides.pdf"
    p.write_bytes(p.read_bytes()+b"modification")
    with pytest.raises(ValueError):verify(completed)


def test_changed_script_blocks_fail_closed(completed):
    (completed/"script.txt").write_text(
        "**Slide 1 [10 sec]:\nDifferent text**",encoding="utf8")
    with pytest.raises(ValueError):verify(completed)


def test_changed_wav_fails_closed(completed):
    with (completed/"slide1.wav").open("ab") as f:f.write(b"x")
    with pytest.raises(ValueError):verify(completed)


def test_changed_source_pdf_fails_closed(completed):
    (completed/"source.pdf").write_bytes(b"source changed")
    with pytest.raises(ValueError):verify(completed)


def test_changed_published_structural_receipt_fails_closed(completed):
    saved=json.loads((completed/"slide_narration_sync.json").read_text())
    saved["page_text_sha256"][0]="b"*64
    (completed/"slide_narration_sync.json").write_text(
        json.dumps(saved),encoding="utf8")
    with pytest.raises(ValueError):verify(completed)


def test_missing_completion_receipt_fails_closed(completed):
    (completed/".microgen_completion.json").unlink()
    with pytest.raises(ValueError):verify(completed)


def test_forged_extra_receipt_field_is_not_compatible(completed):
    saved=json.loads((completed/"slide_narration_sync.json").read_text())
    saved["student_release"]=True
    (completed/"slide_narration_sync.json").write_text(
        json.dumps(saved),encoding="utf8")
    with pytest.raises(ValueError):verify(completed)


def test_unsupported_equal_parser_versions_fail_closed(completed):
    saved=json.loads((completed/"slide_narration_sync.json").read_text())
    actual=inspect(completed)
    saved["version"]=actual["version"]=2
    with pytest.raises(ValueError):
        verify_parser_text_abi(folder=completed,saved=saved,actual=actual,
                               sync_receipt=completed/"slide_narration_sync.json")


def test_changed_page_count_fails_closed(completed):
    saved=json.loads((completed/"slide_narration_sync.json").read_text())
    saved["pages"]=2
    (completed/"slide_narration_sync.json").write_text(
        json.dumps(saved),encoding="utf8")
    with pytest.raises(ValueError):verify(completed)


def test_unbounded_text_hash_drift_fails_closed(completed):
    saved=json.loads((completed/"slide_narration_sync.json").read_text())
    actual=inspect(completed)
    saved["pages"]=actual["pages"]=10
    saved["page_text_sha256"]=["a"*64]*10
    actual["page_text_sha256"]=["b"*64]*10
    with pytest.raises(ValueError,match="Unbounded"):
        verify_parser_text_abi(folder=completed,saved=saved,actual=actual,
                               sync_receipt=completed/"slide_narration_sync.json")


def test_disabled_or_unauthorized_recovery_registry_rejected(tmp_path):
    contents=json.loads(REGISTRY.read_text(encoding="utf8"))
    item=tmp_path/"registry.json"
    contents["max_model_sends"]=1
    item.write_text(json.dumps(contents),encoding="utf8")
    with pytest.raises(ValueError):
        require_cross_pc_handler(
            "PUBLISHED_PDF_TEXT_HASH_DIFFERS_ACROSS_RENDERERS",path=item)
    contents["max_model_sends"]=0
    contents["handlers"]["SOURCE_CROP_PIXELS_DIFFER_ACROSS_RENDERERS"] = \
        "IGNORE_PNG_INTEGRITY_AND_ACCEPT"
    item.write_text(json.dumps(contents),encoding="utf8")
    with pytest.raises(ValueError):
        require_cross_pc_handler(
            "SOURCE_CROP_PIXELS_DIFFER_ACROSS_RENDERERS",path=item)


def test_not_registered_response_sender_is_rejected():
    with pytest.raises(ValueError):
        require_cross_pc_handler("SEND_NEW_GEMINI_MODEL_REQUEST")
