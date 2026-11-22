"""Fault-injection source/media tests of the original legacy static G3 gate."""
import hashlib
import json
import wave
from pathlib import Path

import pytest

from selenium_pipeline import g3_legacy_visual_recovery_v71 as g3
from selenium_pipeline.recovery_registry import lookup_mechanism

FRAME_A=b"\x28"*g3.SAMPLE_SIZE
FRAME_B=b"\xd0"*g3.SAMPLE_SIZE


def _save(path: Path, contents: bytes):
    path.write_bytes(contents)
    return hashlib.sha256(contents).hexdigest()


def fixture(tmp_path):
    root=tmp_path/"original_source"
    root.mkdir()
    src={name:_save(root/name,("Serway original "+name).encode())
         for name in g3.SOURCE_NAMES}
    n=8
    wav=[]
    for i in range(1,n+1):
        file=root/f"slide{i}.wav"
        with wave.open(str(file),"wb") as snd:
            snd.setnchannels(1)
            snd.setsampwidth(2)
            snd.setframerate(24000)
            snd.writeframes(b"\x00\x00"*(24000*15))
        wav.append({"file":file.name,"sha256":g3.sha(file),
                    "duration_s":15.0})
    sync={"pdf_sha256":src["slides.pdf"],
          "script_sha256":src["script.txt"],
          "pages":n,"wav":wav}
    (root/"slide_narration_sync.json").write_text(
        json.dumps(sync),encoding="utf8")
    parts=[]
    for j,(a,b) in enumerate(((1,4),(5,8)),1):
        name=f"slides_part{j:02d}.mp4"
        h=_save(root/name,("encoded original part "+str(j)).encode())
        parts.append({"file":name,"sha256":h,"duration_seconds":60.3,
                      "slides":[a,b]})
    total=_save(root/"slides.mp4",b"archived full video original")
    manifest={
        "source_slides_pdf_sha256":src["slides.pdf"],
        "split_method":"per_slide_boundary_with_separate_encoder_outputs",
        "active_deliverables":[x["file"] for x in parts],
        "verified_full_sha256":total,
        "parts":parts,
    }
    (root/"slides_parts_manifest.json").write_text(
        json.dumps(manifest),encoding="utf8")
    staging=tmp_path/"isolated_staging"
    staging.mkdir()
    return root,staging


def _static(path,seconds):
    return FRAME_A


def _movement(path,seconds):
    # 3 samples span 0.18, 0.48, 0.78 of each 15s slide.
    return FRAME_A if round(seconds*10)%2 else FRAME_B


def _meta(path):
    return {"duration_s":60.3,"video":True,"audio":True}


def test_g3_recovery_registry_has_real_executable_handler():
    assert lookup_mechanism(g3.KIND,g3.SIGNATURE)==g3.MECHANISM


def test_static_two_part_video_requires_new_highlight_candidate(tmp_path):
    source,stage=fixture(tmp_path)
    report=g3.inspect_legacy(folder=source,sampler=_static,probe=_meta)
    assert report["status"]=="G3_LEGACY_STATIC_VIDEO_REBUILD_REQUIRED"
    assert report["sampled_encoded_frames"]>=12
    assert report["moving_slides"]==0
    assert report["independent_video_acceptance"] is False
    assert report["independent_acoustic_acceptance"] is False
    assert report["student_publication_authorized"] is False
    proof=g3.stage_recovery(report=report,staging_root=stage)
    row=json.loads(proof.read_text(encoding="utf8"))
    assert row["status"]=="G3_ISOLATED_SOURCE_BOUND_HIGHLIGHT_REBUILD_WORKLIST"
    assert row["original_wavs_must_be_preserved"] is True
    assert row["no_overwrite_of_legacy_mp4"] is True
    assert row["auto_acceptance"] is False
    assert row["next_action"]=="BUILD_NEW_ELEMENT_SYNCHRONIZED_VIDEO_IN_ISOLATED_STAGING_ONLY"
    assert g3.stage_recovery(report=report,staging_root=stage)==proof
    assert len(list(stage.glob("*.json")))==1


def test_motion_does_not_imply_source_bound_acoustic_or_video_approval(tmp_path):
    source,stage=fixture(tmp_path)
    out=g3.inspect_legacy(folder=source,sampler=_movement,probe=_meta)
    assert out["status"]=="G3_MOTION_OBSERVED_HIGHLIGHT_STILL_UNATTESTED"
    assert out["independent_video_acceptance"] is False
    with pytest.raises(ValueError,match="Only a source-verified legacy"):
        g3.stage_recovery(report=out,staging_root=stage)
    assert not list(stage.iterdir())


def test_changed_original_source_hash_blocks_before_video_sampling(tmp_path):
    source,stage=fixture(tmp_path)
    (source/"script.txt").write_bytes(b"modified script")
    with pytest.raises(ValueError,match="Source/slides/script WAV identity"):
        g3.inspect_legacy(
            folder=source,sampler=lambda *_:pytest.fail("no decode"),
            probe=lambda *_:pytest.fail("no probe"))
    assert not list(stage.iterdir())


def test_changed_real_encoded_mp4_blocks_before_any_acceptance(tmp_path):
    source,stage=fixture(tmp_path)
    (source/"slides_part01.mp4").write_bytes(b"new MP4 not signed")
    with pytest.raises(ValueError,match="differs from signed"):
        g3.inspect_legacy(
            folder=source,sampler=lambda *_:pytest.fail("no sampling"),
            probe=lambda *_:pytest.fail("no probe"))
    assert not list(stage.iterdir())


def test_staging_does_not_modify_original_and_refuses_symlink(tmp_path):
    source,stage=fixture(tmp_path)
    original_files={p.name:g3.sha(p) for p in source.iterdir()}
    report=g3.inspect_legacy(folder=source,sampler=_static,probe=_meta)
    g3.stage_recovery(report=report,staging_root=stage)
    assert original_files=={p.name:g3.sha(p) for p in source.iterdir()}
    with pytest.raises(ValueError,match="independently isolated"):
        g3.stage_recovery(report=report,staging_root=source)


def test_manifest_missing_part_rejects_gap(tmp_path):
    source,_=fixture(tmp_path)
    path=source/"slides_parts_manifest.json"
    data=json.loads(path.read_text(encoding="utf8"))
    data["parts"][1]["slides"]=[6,8]
    path.write_text(json.dumps(data),encoding="utf8")
    with pytest.raises(ValueError,match="consecutive original slides"):
        g3.inspect_legacy(folder=source,sampler=_static,probe=_meta)


def test_late_source_mutation_prevents_recovery_worklist(tmp_path):
    source,stage=fixture(tmp_path)
    report=g3.inspect_legacy(folder=source,sampler=_static,probe=_meta)
    (source/"source.pdf").write_bytes(b"changed after physical pixel review")
    with pytest.raises(ValueError,match="changed after audit"):
        g3.stage_recovery(report=report,staging_root=stage)
    assert not list(stage.iterdir())


def test_original_wav_hash_change_rejected(tmp_path):
    source,stage=fixture(tmp_path)
    with (source/"slide3.wav").open("ab") as f:
        f.write(b"unexpected WAV byte")
    with pytest.raises(ValueError,match="signed sync manifest changed"):
        g3.inspect_legacy(folder=source,sampler=_static,probe=_meta)
    assert not list(stage.iterdir())


def test_frame_change_threshold_detects_real_change_and_static_variance():
    assert g3.pixel_difference(FRAME_A,FRAME_A)==0
    assert g3.pixel_difference(FRAME_A,FRAME_B)>g3.PIXEL_DIFF_THRESHOLD
    with pytest.raises(ValueError,match="Malformed actual decoded"):
        g3.pixel_difference(b"short",FRAME_A)


def test_normal_video_handoff_stages_static_legacy_without_reusing_it(
        tmp_path,monkeypatch):
    source,isolated=fixture(tmp_path)
    from selenium_pipeline import full_pipeline_video_handoff as handoff
    from selenium_pipeline import g3_legacy_visual_recovery_v71 as mod
    actual=mod.inspect_legacy(folder=source,sampler=_static,probe=_meta)
    monkeypatch.setenv("LOCALAPPDATA",str(tmp_path))
    monkeypatch.setattr(mod,"inspect_legacy",lambda **_:actual)
    with pytest.raises(handoff.VideoHandoffBlocked,
                       match="Verified legacy static-slide MP4"):
        handoff.complete_from_published(source=source/"source.pdf")
    staging=tmp_path/"MicroGen_AI_Web_Checkpoints"/"G3_Legacy_Video_Rebuild_V71"
    files=list(staging.glob("g3_legacy_static_*.json"))
    assert len(files)==1
    assert json.loads(files[0].read_text(encoding="utf8"))[
        "student_release"] is False


def test_normal_video_handoff_requires_real_series_contract_even_if_mp4_exists(
        tmp_path,monkeypatch):
    from selenium_pipeline import full_pipeline_video_handoff as handoff
    from selenium_pipeline import production_video_contract as contract
    folder=tmp_path/"source"
    folder.mkdir()
    (folder/"source.pdf").write_bytes(b"textbook")
    (folder/"slides.mp4").write_bytes(b"historical video")
    (folder/"lecture_completion.json").write_text("{}",encoding="utf8")
    monkeypatch.setattr(
        contract,"verify_series",
        lambda _: (_ for _ in ()).throw(
            contract.VideoContractError("No accepted synchronized parts")))
    with pytest.raises(contract.VideoContractError,
                       match="No accepted synchronized"):
        handoff.complete_from_published(source=folder/"source.pdf")


def test_full_series_may_be_reused_only_after_independent_verified_media_contract(
        tmp_path,monkeypatch):
    from selenium_pipeline import full_pipeline_video_handoff as handoff
    from selenium_pipeline import production_video_contract as contract
    folder=tmp_path/"source"
    folder.mkdir()
    (folder/"source.pdf").write_bytes(b"textbook")
    (folder/"lecture_completion.json").write_text("{}",encoding="utf8")
    monkeypatch.setattr(contract,"verify_series",lambda _: {
        "status":"accepted_synchronized_series",
        "verification_scope":"technical_media_only",
        "student_publication_permitted":False,
    })
    result=handoff.complete_from_published(source=folder/"source.pdf")
    assert result["status"]=="REUSED_TECHNICALLY_ACCEPTED_MULTIPART_VIDEO"
    assert result["student_publication_authorized"] is False


def test_original_wav_modified_after_real_video_audit_cannot_stage(tmp_path):
    source,staging=fixture(tmp_path)
    audited=g3.inspect_legacy(folder=source,sampler=_static,probe=_meta)
    with (source/"slide6.wav").open("ab") as stream:
        stream.write(b"modification")
    with pytest.raises(ValueError,match="Original WAV changed after"):
        g3.stage_recovery(report=audited,staging_root=staging)
    assert not list(staging.iterdir())


def test_manifests_modified_after_source_scan_cannot_stage(tmp_path):
    source,staging=fixture(tmp_path)
    audited=g3.inspect_legacy(folder=source,sampler=_static,probe=_meta)
    manifest=source/"slides_parts_manifest.json"
    manifest.write_text(manifest.read_text(encoding="utf8")+" ",
                        encoding="utf8")
    with pytest.raises(ValueError,match="manifest or video changed"):
        g3.stage_recovery(report=audited,staging_root=staging)
    assert not list(staging.iterdir())
