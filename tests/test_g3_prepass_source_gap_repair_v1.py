"""Original Serway source gaps: navigation is not physics, claims need real PDF."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import pytest

from tests.test_g3_semantic_source_repair_v1 import sample
from selenium_pipeline import g3_prepass_source_gap_repair_v1 as repair
from selenium_pipeline import g3_semantic_source_repair_v1 as semantic
from selenium_pipeline.recovery_registry import lookup_mechanism
from selenium_pipeline.g3_source_rejected_offline_repair_v1 import _canon


def sha(text:str)->str:
    return hashlib.sha256(text.encode("utf8")).hexdigest()


def test_production_recovery_registry():
    assert lookup_mechanism(repair.KIND,repair.SIGNATURE)==repair.MECHANISM


@pytest.mark.parametrize("spoken,target,expected",[
    ("Finally, we will review the key concepts with summary points and conceptual questions.",
     "Summary and Review Questions",True),
    ("To conclude, consider these two review questions.",
     "1 In Example 8.3, why did cable length R cancel? 2 What is gravity?",True),
    ("Finally, Newton's law includes the force of kinetic friction.",
     "Summary and Review Questions",False),
    ("We conclude that the kinetic friction work equals minus fk times d.",
     "Summary and Review Questions",False),
])
def test_only_exact_bounded_navigational_sentences_get_exception(spoken,target,expected):
    assert repair._nav_type(spoken,target) is expected


def test_real_physical_pdf_excerpt_creates_new_unapproved_science_request(sample):
    spec,root,file,req,packet,quote=sample
    row=copy.deepcopy(packet["publisher_quote_worklist"][0])
    row["source_excerpt_candidates"]=[]
    orig={"scope_sha256":"e"*64}
    repaired=repair._repair_unit(
        spec=spec,packet=packet,request=req,
        worklist_sha="a"*64,row=row,old=orig)
    assert repaired["status"]==repair.STATUS_SCI
    assert repaired["physically_witnessed_new_quote_count"]>=1
    job=repaired["new_scientific_source_review_job"]
    assert job["utterance_count"]==1
    assert job["selected_original_slides"]==[3]
    citations=job["verified_source_quote_candidates_v1"][
        "utterances"][0]["allowed_citations"]
    assert any(x["verbatim_source_quote"]==quote for x in citations)
    assert repaired["original_model_rejection_promoted"] is False
    assert repaired["student_publication_authorized"] is False
    assert repaired["new_browser_sends"]==0
    assert job["g3_prepass_source_science_v1"][
        "old_worklist_sha256"]=="a"*64
    assert job["g3_prepass_source_science_v1"][
        "two_independent_passes_required"] is True


def test_transition_is_not_approved_math_or_waived_visual_QA(sample,monkeypatch):
    spec,root,file,req,packet,quote=sample
    original=copy.deepcopy(req)
    original["original_utterances"][0]["verbatim_text"]=(
        "Finally, we will review the key concepts with summary points "
        "and conceptual questions.")
    original["visible_targets"][0]["visible_text"]="Summary and Review Questions"
    row=copy.deepcopy(packet["publisher_quote_worklist"][0])
    row["verbatim_utterance_sha256"]=sha(
        original["original_utterances"][0]["verbatim_text"])
    row["original_visible_text_sha256"]=sha(
        original["visible_targets"][0]["visible_text"])
    monkeypatch.setattr(repair,"_context",
                        lambda **kw:pytest.fail("Narration transition is not source physics"))
    data=repair._repair_unit(
        spec=spec,packet=packet,request=original,
        worklist_sha="b"*64,row=row,old={"scope_sha256":"f"*64})
    assert data["status"]==repair.STATUS_NAV
    assert data["navigation_only_no_physics_utterance"] is True
    assert data["new_scientific_source_review_job"] is None
    assert data["rendered_visual_question_science_QA_required"] is True
    assert data["independent_visual_QA_complete"] is False
    assert data["independent_scientific_QA_complete"] is False
    assert data["student_publication_authorized"] is False


def test_quote_imagination_or_tampered_pdf_cannot_become_reviewer_task(
        sample):
    spec,root,file,req,packet,quote=sample
    row=copy.deepcopy(packet["publisher_quote_worklist"][0])
    row["source_excerpt_candidates"]=[]
    (spec["source_folder"]/"source.pdf").write_bytes(b"fake PDF")
    with pytest.raises(Exception):
        repair._repair_unit(
            spec=spec,packet=packet,request=req,
            worklist_sha="c"*64,row=row,old={"scope_sha256":"f"*64})


def test_save_once_prevents_mutating_existing_science_evidence(tmp_path):
    target=tmp_path/"g3.json"
    data={"original_source_unapproved":True,
          "student_publication_authorized":False}
    repair._write_once(target,data)
    assert json.loads(target.read_text("utf8"))==data
    target.write_text('{"student_publication_authorized":true}')
    with pytest.raises(ValueError,match="modified"):
        repair._write_once(target,data)
