"""Historical real G3 pixel recovery is automatically forwarded per section."""
from __future__ import annotations
from pathlib import Path
import pytest

from selenium_pipeline import acceptance_completion_scheduler_v1 as controller
from selenium_pipeline import g3_original_video_page_parity_v1 as parity
from selenium_pipeline import g3_multisection_autoforward_v71 as original
from selenium_pipeline import g3_legacy_visual_recovery_v71 as historical


def install(tmp_path,monkeypatch,*,changed=(),broken=(),drift=()):
    state=tmp_path/"immutable_state";state.mkdir()
    media=tmp_path/"original_media";media.mkdir()
    for section in ("8.2","8.3"):
        (media/section).mkdir()
    manifest=tmp_path/"manifest.json";manifest.write_text("{}")
    source_fields={
        "source.pdf":"a"*64,"slides.pdf":"b"*64,"script.txt":"c"*64}
    specs=[
        {"section":"Serway_8_2",
         "identity":{"source_inputs_sha256":dict(source_fields)}},
        {"section":"Serway_8_3",
         "identity":{"source_inputs_sha256":dict(source_fields)}}]
    calls=[]
    monkeypatch.setattr(original,"_verified_specs",
                        lambda path:(None,specs))
    receipts={}
    for section in ("Serway_8_2","Serway_8_3"):
        receipt=state/(section+".json")
        receipt.write_text('{"original_verified_page":true}\\n')
        receipts[section]=str(receipt)
    monkeypatch.setattr(parity,"materialize",lambda **kw:{
        "original_slides_pixel_witnessed":32,
        "all_original_visual_page_order_matched":True,
        "source_scientific_QA_complete":False,
        "independent_acoustic_QA_complete":False,
        "independent_video_highlight_QA_complete":False,
        "new_browser_sends":0,"new_paid_gemini_API_calls":0,
        "student_publication_authorized":False,
        "sections":[{"section":x["section"],
                     "receipt":receipts[x["section"]]} for x in specs]})
    def diagnose(*,folder):
        name=folder.name
        calls.append(("review_original_MP4_pixels",name))
        if name in broken:
            raise RuntimeError("Historical source WAV/manifests unavailable")
        wrong=dict(source_fields)
        if name in drift:wrong["source.pdf"]="f"*64
        return {
            "status":(
                "G3_MOTION_OBSERVED_HIGHLIGHT_STILL_UNATTESTED"
                if name in changed else "G3_LEGACY_STATIC_VIDEO_REBUILD_REQUIRED"),
            "original_sha256":wrong,
            "student_publication_authorized":False,
            "model_requests":0,"paid_api_requests":0,
            "original_slide_count":15 if name=="8.2" else 17,
            "moving_slides":2 if name in changed else 0,
            "sampled_encoded_frames":18,
            "original_full_video_sha256":("8" if name=="8.2" else "9")*64,
        }
    monkeypatch.setattr(historical,"inspect_legacy",diagnose)
    def stage(*,report,staging_root):
        folder=Path(report["source_folder"]) if "source_folder" in report else None
        name=folder.name if folder else (
            "8.2" if report["original_slide_count"]==15 else "8.3")
        calls.append(("source_pinned_isolated_highlight_rebuild",name))
        target=staging_root/("legacy_"+name.replace(".","_")+".json")
        if not target.exists():
            target.write_text('{"source_pinned":true}\n')
        return target
    monkeypatch.setattr(historical,"stage_recovery",stage)
    return state,media,manifest,calls


def test_both_real_static_original_sections_auto_stage_isolated_rebuilds(
        tmp_path,monkeypatch):
    state,media,manifest,calls=install(tmp_path,monkeypatch)
    result=controller._g3_media_zero_send(
        manifest=manifest,state=state,media=media)
    assert result["source_video_pages_pixel_witnessed"]==32
    assert result["original_subsections_checked"]==2
    assert result["original_static_video_rebuilds_staged"]==2
    assert result["independent_video_highlight_QA_complete"] is False
    assert result["student_publication_authorized"] is False
    assert result["new_browser_sends"]==result["new_paid_gemini_API_calls"]==0
    assert [x["section"] for x in result[
        "source_bound_actual_highlight_recovery"]]==[
            "Serway_8_2","Serway_8_3"]
    for x in result["source_bound_actual_highlight_recovery"]:
        assert x["status"]=="G3_LEGACY_STATIC_VIDEO_REBUILD_REQUIRED"
        assert Path(x["isolation_rebuild_worklist"]).is_file()
        assert x["independent_within_slide_highlight_QA"] is False
    assert calls==[
        ("review_original_MP4_pixels","8.2"),
        ("source_pinned_isolated_highlight_rebuild","8.2"),
        ("review_original_MP4_pixels","8.3"),
        ("source_pinned_isolated_highlight_rebuild","8.3")]
    replay=controller._g3_media_zero_send(
        manifest=manifest,state=state,media=media)
    assert replay==result


def test_failure_of_first_legacy_source_continues_second_section(
        tmp_path,monkeypatch):
    state,media,manifest,calls=install(
        tmp_path,monkeypatch,broken=("8.2",))
    result=controller._g3_media_zero_send(
        manifest=manifest,state=state,media=media)
    assert result["original_static_video_rebuilds_staged"]==1
    assert result["source_bound_actual_highlight_recovery"][0][
        "status"]=="G3_STATIC_REBUILD_SOURCE_HELD"
    assert result["source_bound_actual_highlight_recovery"][1][
        "status"]=="G3_LEGACY_STATIC_VIDEO_REBUILD_REQUIRED"
    assert calls==[
        ("review_original_MP4_pixels","8.2"),
        ("review_original_MP4_pixels","8.3"),
        ("source_pinned_isolated_highlight_rebuild","8.3")]


def test_any_motion_is_not_equivalent_to_scientific_highlight_acceptance(
        tmp_path,monkeypatch):
    state,media,manifest,calls=install(
        tmp_path,monkeypatch,changed=("8.2","8.3"))
    result=controller._g3_media_zero_send(
        manifest=manifest,state=state,media=media)
    assert result["original_static_video_rebuilds_staged"]==0
    assert all(x["status"]==
        "G3_MOTION_OBSERVED_HIGHLIGHT_STILL_UNATTESTED"
        for x in result["source_bound_actual_highlight_recovery"])
    assert result["independent_video_highlight_QA_complete"] is False
    assert result["student_publication_authorized"] is False
    assert all(x["isolation_rebuild_worklist"] is None for x in result[
        "source_bound_actual_highlight_recovery"])


def test_mismatched_first_textbook_source_does_not_stop_second_healthy_section(
        tmp_path,monkeypatch):
    state,media,manifest,calls=install(
        tmp_path,monkeypatch,drift=("8.2",))
    result=controller._g3_media_zero_send(
        manifest=manifest,state=state,media=media)
    assert result["original_static_video_rebuilds_staged"]==1
    assert result["source_bound_actual_highlight_recovery"][0][
        "status"]=="G3_STATIC_REBUILD_SOURCE_HELD"
    assert result["source_bound_actual_highlight_recovery"][1][
        "status"]=="G3_LEGACY_STATIC_VIDEO_REBUILD_REQUIRED"
    assert result["new_browser_sends"]==0


def test_registered_historical_recovery_is_required_not_reimplemented():
    from selenium_pipeline.recovery_registry import lookup_mechanism
    assert lookup_mechanism(historical.KIND,historical.SIGNATURE)==(
        historical.MECHANISM)
