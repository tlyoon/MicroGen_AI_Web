"""G3 authentic textbook/media source binding and unapproved technical QA."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import wave

import pymupdf
import pytest

from selenium_pipeline import g3_source_media_technical_preflight_v1 as tech
from selenium_pipeline.recovery_registry import lookup_mechanism


def _sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def media(tmp_path):
    source=tmp_path/"original"
    source.mkdir()
    root=tmp_path/"media"
    root.mkdir()
    dst=root/"8.2"
    dst.mkdir()
    state=tmp_path/"state"
    state.mkdir()
    with pymupdf.open() as doc:
        for index in (1,2):
            doc.new_page().insert_text((30,40),f"Original physics slide {index}")
        doc.save(source/"slides.pdf")
    with pymupdf.open() as doc:
        doc.new_page().insert_text((30,40),"Original textbook physical passage")
        doc.save(source/"source.pdf")
    (source/"script.txt").write_text("The original source-script narration",encoding="utf8")
    sha={n:_sha(source/n) for n in ("source.pdf","slides.pdf","script.txt")}
    for n in sha:
        shutil.copy2(source/n,dst/n)
    for n in (1,2):
        with wave.open(str(dst/f"slide{n}.wav"),"wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(b"\x00\x00"*12000)
    for n in tech.MP4:
        (dst/n).write_bytes(b"valid tagged container placeholder"*500)
    spec={"section":"Serway_8_2",
          "source_folder":str(source),
          "identity":{"source_inputs_sha256":sha}}
    def probe(path):
        return {"duration_seconds":{
            "slides.mp4":1.2,"slides_part01.mp4":0.5,
            "slides_part02.mp4":0.7}[path.name],
            "video_codec":"h264","audio_codec":"aac",
            "full_video_stream_decoded":True,
            "full_audio_stream_decoded":True}
    return spec,root,state,dst,probe


def test_executable_registry_no_release():
    assert lookup_mechanism(tech.KIND,tech.SIGNATURE)==tech.MECHANISM


def test_same_original_source_technical_wav_and_multipart_immutable(media):
    spec,root,state,dst,probe=media
    result=tech.inspect(spec=spec,media_root=root,
                        state_root=state,probe=probe)
    assert result["status"]==tech.STATUS
    assert result["slide_count"]==2
    assert result["wav_duration_seconds"]==1.0
    assert result["video_duration_seconds"]==1.2
    assert result["part1_duration_seconds"]==0.5
    assert result["part2_duration_seconds"]==0.7
    assert result["stream_decode_errors"]==0
    assert result["new_browser_sends"]==0
    assert result["new_paid_gemini_API_calls"]==0
    assert result["independent_video_QA_complete"] is False
    assert result["independent_acoustic_QA_complete"] is False
    assert result["source_scientific_QA_complete"] is False
    assert result["student_publication_authorized"] is False
    file=Path(result["receipt"])
    packet=json.loads(file.read_text("utf8"))
    assert packet["independent_video_audio_decoding_complete"] is True
    assert packet["spoken_content_fidelity_verified"] is False
    assert packet["scientific_source_QA_complete"] is False
    saved=file.read_bytes()
    assert tech.inspect(spec=spec,media_root=root,
                        state_root=state,probe=probe)==result
    assert file.read_bytes()==saved


def test_real_original_pdf_hash_drift_blocks_technical_pass(media):
    spec,root,state,dst,probe=media
    with (dst/"script.txt").open("a",encoding="utf8") as f:
        f.write("foreign narration")
    with pytest.raises(ValueError,match="source input differs"):
        tech.inspect(spec=spec,media_root=root,
                     state_root=state,probe=probe)


def test_missing_middle_slide_wav_is_not_media_acceptance(media):
    spec,root,state,dst,probe=media
    (dst/"slide2.wav").unlink()
    with pytest.raises(ValueError,match="misnumbered"):
        tech.inspect(spec=spec,media_root=root,
                     state_root=state,probe=probe)


def test_wrong_wav_format_does_not_pass_as_real_narration(media):
    spec,root,state,dst,probe=media
    with wave.open(str(dst/"slide2.wav"),"wb") as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(24000)
        w.writeframes(b"\x00\x00"*24000)
    with pytest.raises(ValueError,match="channel/rate/PCM"):
        tech.inspect(spec=spec,media_root=root,
                     state_root=state,probe=probe)


def test_audio_stream_decode_failure_blocks_entire_media_packet(media):
    spec,root,state,dst,probe=media
    def bad(path):
        x=probe(path)
        if path.name=="slides_part02.mp4":
            x["full_audio_stream_decoded"]=False
        return x
    with pytest.raises(ValueError,match="independently decoded"):
        tech.inspect(spec=spec,media_root=root,
                     state_root=state,probe=bad)
    assert not (state/tech.ROOT).exists()


def test_multipart_duration_mismatch_fails_closed(media):
    spec,root,state,dst,probe=media
    def bad(path):
        x=probe(path)
        if path.name=="slides_part02.mp4":
            x["duration_seconds"]=12.0
        return x
    with pytest.raises(ValueError,match="duration parity"):
        tech.inspect(spec=spec,media_root=root,
                     state_root=state,probe=bad)


def test_saved_technical_packet_tampering_fails_on_restart(media):
    spec,root,state,dst,probe=media
    x=tech.inspect(spec=spec,media_root=root,
                   state_root=state,probe=probe)
    file=Path(x["receipt"])
    packet=json.loads(file.read_text("utf8"))
    packet["student_publication_authorized"]=True
    file.write_text(json.dumps(packet))
    with pytest.raises(ValueError,match="changed after checkpoint"):
        tech.inspect(spec=spec,media_root=root,
                     state_root=state,probe=probe)


def test_normal_cli_requires_original_media_root_and_no_old_sends(
        tmp_path,monkeypatch):
    from selenium_pipeline import g3_multisection_autoforward_v71 as normal
    manifest=tmp_path/"original_manifest.json"
    manifest.write_text("{}")
    state=tmp_path/"state";state.mkdir()
    with pytest.raises(ValueError,match="media root"):
        normal.main(["--manifest",str(manifest),"--state-dir",str(state),
                     "--auto-offline-media-qa"])
    with pytest.raises(ValueError,match="zero original Sends"):
        normal.main(["--manifest",str(manifest),"--state-dir",str(state),
                     "--auto-offline-media-qa","--media-root",str(tmp_path),
                     "--max-new-sends","1"])


def test_normal_g3_entrypoint_runs_separate_technical_gate_with_no_sends(
        tmp_path,monkeypatch,capsys):
    from selenium_pipeline import g3_multisection_autoforward_v71 as normal
    original=tmp_path/"original_source_manifest.json"
    original.write_text("{}")
    state=tmp_path/"state";state.mkdir()
    media=tmp_path/"media";media.mkdir()
    observed=[]
    monkeypatch.setattr(normal,"run_campaign",lambda **kwargs:
        (observed.append(kwargs) or {
            "status":"G3_SOURCE_ONLY_NO_SEND",
            "new_browser_dispatch_attempts_this_run":0,
            "student_publication_authorized":False}))
    def technical(**kwargs):
        observed.append(kwargs)
        return {
            "status":"G3_TWO_ORIGINAL_SUBSECTIONS_MEDIA_TECHNICALLY_CHECKED_NO_RELEASE",
            "new_browser_sends":0,"new_paid_gemini_API_calls":0,
            "independent_scientific_QA_complete":False,
            "independent_acoustic_QA_complete":False,
            "independent_video_QA_complete":False,
            "student_publication_authorized":False}
    monkeypatch.setattr(tech,"materialize",technical)
    assert normal.main([
        "--manifest",str(original),"--state-dir",str(state),
        "--auto-offline-media-qa","--media-root",str(media),
        "--max-new-sends","0"])==0
    result=json.loads(capsys.readouterr().out)
    assert result["source_science_progress"]["new_browser_dispatch_attempts_this_run"]==0
    assert result["source_bound_technical_media_QA"][
        "independent_video_QA_complete"] is False
    assert result["student_publication_authorized"] is False
    assert len(observed)==2
    assert observed[0]["max_new_sends"]==0
    assert Path(observed[1]["media_root"])==media
