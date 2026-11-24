"""Original G3 PDF slide page vs actual encoded video QA: no automatic release."""
from __future__ import annotations
import json
from pathlib import Path

import pytest

from selenium_pipeline import g3_original_video_page_parity_v1 as video
from selenium_pipeline.recovery_registry import lookup_mechanism
from tests.test_g3_source_media_technical_preflight_v1 import media


def _good(**kwargs):
    assert kwargs["slide"] in (1,2)
    assert kwargs["second"]>0
    assert isinstance(kwargs["scratch"],Path)
    return 0.281 if kwargs["slide"]==1 else 0.384


def test_source_bound_page_frame_registry_is_executable():
    assert lookup_mechanism(video.KIND,video.SIGNATURE)==video.MECHANISM


def test_real_pdf_fixture_and_source_video_sampled_without_academic_acceptance(
        media):
    spec,root,state,dst,probe=media
    got=video.inspect(
        spec=spec,media_root=root,state_root=state,
        compare=_good,technical_probe=probe)
    assert got["original_slide_frames_verified"]==2
    assert got["maximum_frame_RGB_MAE"]==0.384
    assert got["new_browser_sends"]==0
    assert got["new_paid_gemini_API_calls"]==0
    assert got["source_scientific_QA_complete"] is False
    assert got["independent_acoustic_QA_complete"] is False
    assert got["independent_video_highlight_QA_complete"] is False
    assert got["student_publication_authorized"] is False
    receipt=Path(got["receipt"])
    proof=json.loads(receipt.read_text("utf8"))
    assert proof["original_page_order_pixel_evidence_complete"] is True
    assert proof["one_narration_midpoint_sample_per_original_slide"] is True
    assert proof["original_slide_count"]==2
    assert [x["original_slide"] for x in proof[
        "original_page_witness_samples"]]==[1,2]
    assert proof["independent_full_video_QA_complete"] is False
    assert proof["independent_video_highlight_QA_complete"] is False
    assert proof["source_PDF_semantic_science_QA_complete"] is False
    saved=receipt.read_bytes()
    assert video.inspect(spec=spec,media_root=root,state_root=state,
                         compare=_good,technical_probe=probe)==got
    assert receipt.read_bytes()==saved


def test_wrong_encoded_page_frame_is_not_accepted(media):
    spec,root,state,dst,probe=media
    def swapped(**kw):
        return 0.2 if kw["slide"]==1 else 47.0
    with pytest.raises(ValueError,match="differs from original PDF"):
        video.inspect(spec=spec,media_root=root,state_root=state,
                      compare=swapped,technical_probe=probe)
    assert not (state/video.ROOT).exists()


def test_original_publisher_source_drift_blocks_before_frame_decode(media):
    spec,root,state,dst,probe=media
    with (dst/"slides.pdf").open("ab") as out:
        out.write(b"foreign source frame")
    with pytest.raises(ValueError,match="source input differs"):
        video.inspect(spec=spec,media_root=root,state_root=state,
                      compare=lambda **kw: pytest.fail("No frame extraction"),
                      technical_probe=probe)


def test_failed_physical_audio_video_decode_blocks_source_parity(media):
    spec,root,state,dst,probe=media
    def broken(path):
        row=probe(path)
        if path.name=="slides_part02.mp4":
            row["full_video_stream_decoded"]=False
        return row
    with pytest.raises(ValueError,match="independently decoded"):
        video.inspect(spec=spec,media_root=root,state_root=state,
                      compare=lambda **kw:pytest.fail("Media not complete"),
                      technical_probe=broken)


def test_altered_immutable_source_page_video_proof_fails_restart(media):
    spec,root,state,dst,probe=media
    initial=video.inspect(spec=spec,media_root=root,state_root=state,
                          compare=_good,technical_probe=probe)
    path=Path(initial["receipt"])
    data=json.loads(path.read_text("utf8"))
    data["student_publication_authorized"]=True
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match="changed after checkpoint"):
        video.inspect(spec=spec,media_root=root,state_root=state,
                      compare=_good,technical_probe=probe)


def test_normal_g3_entrypoint_requires_technical_media_gate_for_visual_parity(
        tmp_path):
    from selenium_pipeline import g3_multisection_autoforward_v71 as normal
    manifest=tmp_path/"source_manifest.json"
    manifest.write_text("{}")
    state=tmp_path/"state";state.mkdir()
    with pytest.raises(ValueError,match="prior no-Send technical media QA"):
        normal.main(["--manifest",str(manifest),"--state-dir",str(state),
                     "--auto-offline-visual-page-parity"])


def test_normal_g3_controller_executes_technical_then_original_page_parity(
        tmp_path,monkeypatch,capsys):
    from selenium_pipeline import g3_multisection_autoforward_v71 as normal
    from selenium_pipeline import g3_source_media_technical_preflight_v1 as tech
    manifest=tmp_path/"source_manifest.json";manifest.write_text("{}")
    state=tmp_path/"state";state.mkdir()
    media=tmp_path/"media";media.mkdir()
    stages=[]
    monkeypatch.setattr(normal,"run_campaign",lambda **kw:
        (stages.append("source") or {
            "status":"G3_SOURCE_ONLY_NO_SEND",
            "new_browser_dispatch_attempts_this_run":0,
            "student_publication_authorized":False}))
    monkeypatch.setattr(tech,"materialize",lambda **kw:
        (stages.append("technical") or {
            "status":"G3_TWO_ORIGINAL_SUBSECTIONS_MEDIA_TECHNICALLY_CHECKED_NO_RELEASE",
            "new_browser_sends":0,"new_paid_gemini_API_calls":0,
            "independent_scientific_QA_complete":False,
            "independent_acoustic_QA_complete":False,
            "independent_video_QA_complete":False,
            "student_publication_authorized":False}))
    monkeypatch.setattr(video,"materialize",lambda **kw:
        (stages.append("original_video_pages") or {
            "status":"G3_ORIGINAL_VIDEO_SOURCE_FRAME_PAGE_ORDER_WITNESSED_NO_RELEASE",
            "new_browser_sends":0,"new_paid_gemini_API_calls":0,
            "source_scientific_QA_complete":False,
            "independent_acoustic_QA_complete":False,
            "independent_video_highlight_QA_complete":False,
            "student_publication_authorized":False}))
    assert normal.main([
        "--manifest",str(manifest),"--state-dir",str(state),
        "--auto-offline-media-qa","--auto-offline-visual-page-parity",
        "--media-root",str(media),"--max-new-sends","0"])==0
    result=json.loads(capsys.readouterr().out)
    assert stages==["source","technical","original_video_pages"]
    assert result["original_encoded_video_source_page_QA"][
        "independent_video_highlight_QA_complete"] is False
    assert result["student_publication_authorized"] is False
