"""Real source stage-only ABI and forged source/approval fault injection."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from selenium_pipeline import ch11_stage_only_pdf_text_parity_v1 as repair
from selenium_pipeline import narrated_video_chain as video


REAL = Path(r"G:\My Drive\Serway\Serway_8_14\11")


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def write_json(path,data):
    path.write_text(json.dumps(data,indent=2),encoding="utf8")


def specimen(tmp,monkeypatch):
    folder=tmp/"11.1"
    preview=tmp/"original_previews"/"11.1"
    folder.mkdir()
    preview.mkdir(parents=True)
    for name,content in {
        "source.pdf":b"publisher original",
        "slides.pdf":b"original slide pdf",
        "slides.tex":b"slide original source",
        "script.txt":b"original spoken script",
        "slide1.wav":b"audio original waveform bytes",
    }.items():
        (folder/name).write_bytes(content)
    qa={"summary":{"slides":1,"passed":1,"review":0,"blocking_failures":0}}
    write_json(folder/"tts_fidelity_report.json",qa)
    saved={
        "version":1,
        "pdf_sha256":sha(folder/"slides.pdf"),
        "script_sha256":sha(folder/"script.txt"),
        "pages":1,
        "page_text_sha256":["a"*64],
        "narration_sha256":["c"*64],
        "wav":[{"file":"slide1.wav","sha256":sha(folder/"slide1.wav"),
                "duration_s":4.0}],
    }
    observed=copy.deepcopy(saved)
    observed["page_text_sha256"]=["b"*64]
    write_json(folder/"slide_narration_sync.json",saved)
    stage={
        "schema_version":1,"status":repair.STAGE_STATUS,
        "full_g3_release_accepted":False,
        "student_publication_authorized_by_this_receipt":False,
        "independent_visual_highlight_acceptance":"not_performed",
        "highlight_verification_scope":"explicitly_skipped_by_user",
        "narration_synced_structurally":True,
        "original_source_pdf_sha256":sha(folder/"source.pdf"),
        "slides_pdf_sha256":sha(folder/"slides.pdf"),
        "script_txt_sha256":sha(folder/"script.txt"),
    }
    write_json(folder/".microgen_narrated_video_chain.json",stage)
    names=("source.pdf","slides.pdf","script.txt",
           "slide_narration_sync.json","tts_fidelity_report.json")
    manifest={
        "status":repair.PREVIEW_STATUS,
        "preview_has_element_highlights":False,
        "independent_encoded_highlight_qa_passed":False,
        "student_published":False,
        "original_sha256":{n:sha(folder/n) for n in names},
        "original_wav_sha256":{"slide1.wav":sha(folder/"slide1.wav")},
        "parts":[{
            "index":1,"slides":[1],"wav_seconds":4.0,
            "video_audio_streams_verified":True,"decode_all_frames_passed":True,
            "filename":"preview_slide_sync_no_highlights_part_01.mp4",
        }],
    }
    write_json(preview/"preview_manifest.json",manifest)
    monkeypatch.setattr(repair,"inspect_sync",lambda source:copy.deepcopy(observed))
    def existing_strict(*args):
        raise ValueError("Unbounded/absent text parser ABI discrepancy")
    monkeypatch.setattr(video,"verify_slide_sync",existing_strict)
    return folder,preview


def test_registry_does_not_lower_full_lecture_validator():
    assert repair.lookup_mechanism(repair.KIND,repair.SIGNATURE)==repair.MECHANISM
    assert repair.require_cross_pc_handler(repair.CROSS_SIGNATURE)==(
        repair.CROSS_MECHANISM)


def test_video_only_fallback_passes_without_academic_or_release_approval(
        tmp_path,monkeypatch):
    folder,preview=specimen(tmp_path,monkeypatch)
    output=repair.verify_stage_only_parser_drift(folder=folder,preview=preview)
    assert output["status"].endswith("NOT_RELEASED")
    assert output["derived_text_hash_changed_pages"]==[1]
    assert output["student_publication_authorized"] is False
    assert output["independent_scientific_accepted"] is False
    assert output["independent_visual_highlight_accepted"] is False
    before={p.name:p.read_bytes() for p in folder.iterdir()}
    before_preview={p.name:p.read_bytes() for p in preview.iterdir()}
    synced,qa,parts=video._technical_input_proof(folder,preview)
    assert synced==output["technical_sync_original"]
    assert qa["summary"]["passed"]==1
    assert len(parts)==1
    assert before=={p.name:p.read_bytes() for p in folder.iterdir()}
    assert before_preview=={p.name:p.read_bytes() for p in preview.iterdir()}


@pytest.mark.parametrize("filename",[
    "slides.pdf","script.txt","source.pdf","slide1.wav",
    "tts_fidelity_report.json","slide_narration_sync.json",
])
def test_original_input_tampering_blocked(tmp_path,monkeypatch,filename):
    folder,preview=specimen(tmp_path,monkeypatch)
    (folder/filename).write_bytes((folder/filename).read_bytes()+b"forged")
    with pytest.raises((ValueError,KeyError)):
        repair.verify_stage_only_parser_drift(folder=folder,preview=preview)


@pytest.mark.parametrize("key,value",[
    ("student_published",True),
    ("preview_has_element_highlights",True),
    ("independent_encoded_highlight_qa_passed",True),
    ("status","RELEASED"),
])
def test_preview_claim_forgery_blocked(tmp_path,monkeypatch,key,value):
    folder,preview=specimen(tmp_path,monkeypatch)
    path=preview/"preview_manifest.json"
    obj=json.loads(path.read_text("utf8"))
    obj[key]=value
    write_json(path,obj)
    with pytest.raises(ValueError):
        video._technical_input_proof(folder,preview)


@pytest.mark.parametrize("key,value",[
    ("student_publication_authorized_by_this_receipt",True),
    ("full_g3_release_accepted",True),
    ("narration_synced_structurally",False),
    ("independent_visual_highlight_acceptance","passed"),
])
def test_stage_only_receipt_cannot_claim_scientific_completion(
        tmp_path,monkeypatch,key,value):
    folder,preview=specimen(tmp_path,monkeypatch)
    path=folder/".microgen_narrated_video_chain.json"
    obj=json.loads(path.read_text("utf8"))
    obj[key]=value
    write_json(path,obj)
    with pytest.raises(ValueError):
        repair.verify_stage_only_parser_drift(folder=folder,preview=preview)


def test_full_completion_receipt_disallows_stage_only_bypass(tmp_path,monkeypatch):
    folder,preview=specimen(tmp_path,monkeypatch)
    write_json(folder/".microgen_completion.json",{"status":"injected"})
    with pytest.raises(ValueError,match="Published completed lecture"):
        repair.verify_stage_only_parser_drift(folder=folder,preview=preview)


def test_absent_text_drift_is_not_a_recovery_case(tmp_path,monkeypatch):
    folder,preview=specimen(tmp_path,monkeypatch)
    stored=json.loads((folder/"slide_narration_sync.json").read_text("utf8"))
    monkeypatch.setattr(repair,"inspect_sync",lambda source:stored)
    with pytest.raises(ValueError,match="No derived"):
        repair.verify_stage_only_parser_drift(folder=folder,preview=preview)


def test_changed_narration_hash_is_not_only_parser_drift(tmp_path,monkeypatch):
    folder,preview=specimen(tmp_path,monkeypatch)
    stored=json.loads((folder/"slide_narration_sync.json").read_text("utf8"))
    actual=copy.deepcopy(stored)
    actual["narration_sha256"]=["f"*64]
    actual["page_text_sha256"]=["b"*64]
    monkeypatch.setattr(repair,"inspect_sync",lambda source:actual)
    with pytest.raises(ValueError,match="narration or WAV changed"):
        repair.verify_stage_only_parser_drift(folder=folder,preview=preview)


@pytest.mark.skipif(not REAL.is_dir(),reason="No original Dell Chapter 11 source")
@pytest.mark.parametrize("section,changes",[
    ("11.1",13),("11.3",6),("11.5",6)])
def test_real_ch11_all_three_sections_original_pdfs_wavs_unchanged(
        section,changes):
    from selenium_pipeline.slide_narration_sync import verify
    folder=REAL/section
    preview=REAL/"_review_only_video_previews"/section
    with pytest.raises(ValueError,match="Unbounded/absent text parser ABI"):
        verify(folder)
    proof=repair.verify_stage_only_parser_drift(folder=folder,preview=preview)
    assert len(proof["derived_text_hash_changed_pages"])==changes
    assert proof["student_publication_authorized"] is False
    synced,qa,parts=video._technical_input_proof(folder,preview)
    assert synced==proof["technical_sync_original"]
    assert qa["summary"]["passed"]==synced["pages"]
    assert len(parts)==(1 if section=="11.5" else 2)
