"""No-highlight MP4 completion is strictly technical and checksum-pinned."""
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import pytest

from selenium_pipeline.narrated_video_chain import (
    _guarded_copy, _technical_input_proof, _duration_and_decode,
    _validate_existing_legacy, NEW_SECTIONS, STATUS,
)

ROOT=Path(r"G:\My Drive\Serway\Serway_8_14\11")


def test_hash_equal_existing_is_reused_without_overwrite(tmp_path):
    src=tmp_path/"src.mp4";src.write_bytes(b"actual media")
    dest=tmp_path/"slides.mp4";dest.write_bytes(b"actual media")
    digest=hashlib.sha256(src.read_bytes()).hexdigest()
    before=dest.stat().st_mtime_ns
    _guarded_copy(src,dest,digest)
    assert dest.read_bytes()==src.read_bytes()
    assert dest.stat().st_mtime_ns==before


def test_conflicting_video_is_never_overwritten(tmp_path):
    src=tmp_path/"src.mp4";src.write_bytes(b"correct")
    dest=tmp_path/"slides.mp4";dest.write_bytes(b"unrelated")
    digest=hashlib.sha256(src.read_bytes()).hexdigest()
    with pytest.raises(RuntimeError,match="do not overwrite"):
        _guarded_copy(src,dest,digest)
    assert dest.read_bytes()==b"unrelated"


def test_hash_mismatch_never_creates_canonical(tmp_path):
    src=tmp_path/"src.mp4";src.write_bytes(b"tampered")
    dest=tmp_path/"slides.mp4"
    with pytest.raises(RuntimeError,match="Input changed"):
        _guarded_copy(src,dest,"0"*64)
    assert not dest.exists()


def test_symbolic_link_input_never_published(tmp_path):
    src=tmp_path/"src.mp4";src.write_bytes(b"actual")
    link=tmp_path/"linked.mp4"
    try:
        link.symlink_to(src)
    except (OSError,NotImplementedError):
        pytest.skip("Creating symlinks unsupported")
    digest=hashlib.sha256(src.read_bytes()).hexdigest()
    with pytest.raises(RuntimeError,match="Invalid preview input"):
        _guarded_copy(link,tmp_path/"slides.mp4",digest)


def test_preview_missing_qa_is_not_promoted(tmp_path):
    from selenium_pipeline.narrated_video_chain import _audio_qa
    folder=tmp_path
    (folder/"tts_fidelity_report.json").write_text(json.dumps({
        "summary":{"slides":15,"passed":14,"review":1,"blocking_failures":1}
    }),encoding="utf8")
    with pytest.raises(RuntimeError,match="Acoustic QA"):
        _audio_qa(folder,15)


def test_preview_video_duration_above_600_is_rejected_without_ffmpeg(tmp_path):
    file=tmp_path/"video.mp4";file.write_bytes(b"placeholder")
    with patch("selenium_pipeline.narrated_video_chain.validate_video") as called:
        with pytest.raises(RuntimeError,match="600s"):
            _duration_and_decode(file,600,"ffmpeg")
    called.assert_not_called()


@pytest.mark.skipif(not ROOT.is_dir(),reason="Real Dell-115 Drive Chapter 11 unavailable")
@pytest.mark.parametrize("sec",NEW_SECTIONS)
def test_real_pinned_source_wav_pdf_qa_preview_consistency(sec):
    folder=ROOT/sec
    preview=ROOT/"_review_only_video_previews"/sec
    synced,qa,parts=_technical_input_proof(folder,preview)
    assert qa["summary"]["passed"]==synced["pages"]
    assert sorted(p["index"] for p in parts)==list(range(1,len(parts)+1))
    assert all(0<p["wav_seconds"]<600 for p in parts)
    assert len(parts)==(1 if sec=="11.5" else 2)


@pytest.mark.skipif(not ROOT.is_dir(),reason="Real Dell-115 Drive Chapter 11 unavailable")
@pytest.mark.parametrize("sec",("11.2","11.4"))
def test_real_historical_completion_assets_are_preserved(sec):
    folder=ROOT/sec
    manifest=json.loads((folder/"lecture_parts_manifest.json").read_text(encoding="utf8"))
    receipt=json.loads((folder/".microgen_completion.json").read_text(encoding="utf8"))
    assert manifest["source_sha256"]==receipt["source_sha256"]
    assert len(manifest["parts"])==3
    assert all((folder/part["filename"]).is_file() for part in manifest["parts"])


def test_disabled_narrated_scope_registry_blocks_publication(tmp_path):
    from selenium_pipeline.narrated_video_chain import run
    with patch("selenium_pipeline.recovery_registry.lookup_mechanism", return_value=None), \
         pytest.raises(RuntimeError,match="not registered"):
        run(tmp_path/"11",("11.1",))
    assert not list(tmp_path.rglob("*.mp4"))


@pytest.mark.skipif(not ROOT.is_dir(),reason="Real Dell-115 Drive Chapter 11 unavailable")
def test_actual_stage_only_receipts_are_complete_without_false_highlights():
    status_file=ROOT/".microgen_ch11_narrated_mp4_chain_status.json"
    if not status_file.is_file():
        pytest.skip("Real publication not executed in this test environment")
    chapter=json.loads(status_file.read_text(encoding="utf8"))
    assert chapter["technical_video_chain_completed"] is True
    assert chapter["highlight_verification_skipped_not_passed"] is True
    assert chapter["all_source_grounded_visual_highlights_accepted"] is False
    assert chapter["paid_gemini_api_requests_in_this_operation"]==0
    assert chapter["total_mp4_parts"]==11
    for section in NEW_SECTIONS:
        folder=ROOT/section
        receipt=json.loads(
            (folder/".microgen_narrated_video_chain.json").read_text(encoding="utf8"))
        assert receipt["status"]==STATUS
        assert receipt["full_g3_release_accepted"] is False
        assert receipt["independent_visual_highlight_acceptance"]=="not_performed"
        assert not (folder/".microgen_completion.json").exists()
        for part in receipt["video_parts"]:
            file=folder/part["filename"]
            assert file.is_file()
            assert hashlib.sha256(file.read_bytes()).hexdigest()==part["sha256"]
            assert 0<part["duration_seconds"]<600
