"""New publisher-backed G3 prepass science task; two saved real-source passes."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import pytest

from tests.test_g3_semantic_source_repair_v1 import sample
from tests.test_g3_distinct_semantic_science_v1 import transport_for
from selenium_pipeline import g3_prepass_source_gap_repair_v1 as repair
from selenium_pipeline.g3_distinct_semantic_science_v1 import run_one
from selenium_pipeline.g3_source_rejected_offline_repair_v1 import _canon


@pytest.fixture
def prepass(sample,monkeypatch,tmp_path):
    spec,root,file,request,packet,quote=sample
    original=copy.deepcopy(packet)
    original["publisher_quote_worklist"][0][
        "source_excerpt_candidates"]=[]
    file.write_bytes(_canon(original))
    # Previous fixture already patches the immutable reviewer lookup.
    from selenium_pipeline import g3_semantic_source_repair_v1 as sem
    monkeypatch.setattr(sem,"rejected_packet",
                        lambda **kw:copy.deepcopy(original))
    # The mock transport is not the real Neon browser. In this isolated
    # test only, supply a synthetic health receipt; production must verify
    # its actual owned browser provenance before any Send.
    from selenium_pipeline import g3_distinct_semantic_science_v1 as science
    monkeypatch.setattr(science,"qualified_health",lambda **kw:{
        "fresh_neon_high_source_free_health":True})
    monkeypatch.setattr(science,"_after_incident",lambda **kw:0.0)
    state=tmp_path/"state"
    source_root=state/"offline_source_quote_worklists_v2"/spec["section"]
    source_root.mkdir(parents=True)
    source_file=source_root/"slide_003.json"
    source_file.write_bytes(_canon(original))
    report=repair.materialize(
        specs=[spec],
        worklist_root=state/"offline_source_quote_worklists_v2",
        state_root=state)
    assert report["genuine_source_derived_review_jobs"]==1
    selected=next((state/repair.ROOT/spec["section"]).glob("*.json"))
    assert repair.pinned(spec=spec,state_root=state,
                         task_file=selected)==json.loads(
                             selected.read_text("utf8"))
    return spec,state,selected,quote


def test_two_science_reviews_are_new_claims_and_original_rejection_remains(
        prepass):
    spec,state,selected,quote=prepass
    calls=[]
    result=run_one(
        spec=spec,task_file=selected,
        worklist_root=state/"offline_source_quote_worklists_v2",
        state_root=state,campaign_id="new_prepass_science_one",
        max_possible_sends=2,execute=True,
        transport=transport_for(quote,calls))
    assert result["status"] in (
        "G3_DISTINCT_SEMANTIC_TWO_PASS_SCIENCE_AI_EVIDENCE_NO_ORIGINAL_PROMOTION",
        "G3_DISTINCT_SEMANTIC_SOURCE_AI_DISPUTED_NO_PROMOTION")
    assert result["possible_sends_reserved"]==2
    assert len(calls)==2
    assert result["original_historical_request_replayed"] is False
    assert result["old_G3_semantic_mappings_promoted"]==0
    assert result["student_publication_authorized"] is False
    assert result["paid_gemini_API_calls"]==0
    repeat=run_one(
        spec=spec,task_file=selected,
        worklist_root=state/"offline_source_quote_worklists_v2",
        state_root=state,campaign_id="new_prepass_science_one",
        max_possible_sends=2,execute=True,
        transport=lambda *a:pytest.fail("Never replay saved source claim"))
    assert repeat["status"]==result["status"]
    assert repeat["possible_sends_reserved"]==2


def test_original_source_tamper_refuses_new_send(prepass):
    spec,state,selected,quote=prepass
    (spec["source_folder"]/"source.pdf").write_bytes(b"changed!")
    with pytest.raises(Exception):
        run_one(
            spec=spec,task_file=selected,
            worklist_root=state/"offline_source_quote_worklists_v2",
            state_root=state,campaign_id="tampered_new_prepass",
            max_possible_sends=2,execute=True,
            transport=lambda *a:pytest.fail("Cannot issue source Send"))


def test_tampered_prepass_context_cannot_be_promoted(prepass):
    spec,state,selected,quote=prepass
    payload=json.loads(selected.read_text("utf8"))
    payload["student_publication_authorized"]=True
    selected.write_text(json.dumps(payload))
    with pytest.raises(Exception):
        run_one(
            spec=spec,task_file=selected,
            worklist_root=state/"offline_source_quote_worklists_v2",
            state_root=state,campaign_id="tampered_prepass",
            max_possible_sends=2,execute=True,
            transport=lambda *a:pytest.fail("Cannot issue altered source task"))
