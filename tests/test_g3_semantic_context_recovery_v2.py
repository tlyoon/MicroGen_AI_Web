"""Historical double-unresolved G3 science QA safely retrieves original context."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pymupdf
import pytest

from tests.test_g3_semantic_source_repair_v1 import sample
from tests.test_g3_distinct_semantic_science_v1 import (
    ready,run,transport_for)
from selenium_pipeline import g3_semantic_context_recovery_v2 as context
from selenium_pipeline.recovery_registry import lookup_mechanism


def test_registered_publisher_context_recovery_mechanism():
    assert lookup_mechanism(context.KIND,context.SIGNATURE)==context.MECHANISM


def test_two_actual_unresolved_reviews_generate_no_send_versioned_context(
        ready):
    spec,worklists,task,state,quote=ready
    calls=[]
    result=run(ready,name="two_unresolved_original_science",
               transport=transport_for(quote,calls,both_unresolved=True))
    assert result["status"]=="G3_DISTINCT_SEMANTIC_SOURCE_AI_DISPUTED_NO_PROMOTION"
    assert result["possible_sends_reserved"]==2
    recovery=result["semantic_context_recovery"]
    assert recovery["status"]==context.STATUS
    assert recovery["original_two_model_verdicts"]==["UNRESOLVED","UNRESOLVED"]
    assert recovery["additional_context_snippets_are_semantic_proof"] is False
    assert recovery["new_gemini_browser_sends"]==0
    assert recovery["original_G3_semantic_mappings_promoted"]==0
    assert recovery["student_publication_authorized"] is False
    original=json.loads(task.read_text("utf8"))
    scope=state/"g3_distinct_semantic_science_reviews_v1"/original["scope_sha256"]
    receipt=scope/"semantic_context_recovery_v3.json"
    evidence=scope/"two_pass_science_evidence.json"
    first_receipt=evidence.read_bytes()
    assert receipt.is_file()
    assert json.loads(receipt.read_text("utf8"))==recovery
    restart=run(ready,name="two_unresolved_original_science",
                transport=lambda *args:pytest.fail("No duplicate browser Send"))
    assert restart["possible_sends_reserved"]==2
    assert restart["semantic_context_recovery"]==recovery
    assert evidence.read_bytes()==first_receipt
    assert len(calls)==2


def test_review_witness_tamper_never_yields_new_source_proof(
        ready):
    spec,worklists,task,state,quote=ready
    calls=[]
    initial=run(ready,name="tamper_model_witness",
                transport=transport_for(quote,calls,both_unresolved=True))
    scope=state/"g3_distinct_semantic_science_reviews_v1"/initial[
        "source_scope_sha256"]
    witness=scope/"challenge_request"/"neon_high_owned_model_witness.json"
    assert witness.is_file()
    witness.unlink()
    with pytest.raises(Exception):
        context.recover(
            folder=spec["source_folder"],
            task=json.loads(task.read_text("utf8")),
            review_root=scope)
    assert len(calls)==2


def test_original_science_source_context_from_pdf_is_physically_verifiable(
        tmp_path):
    folder=tmp_path/"original_serway_synthetic"
    folder.mkdir()
    with pymupdf.open() as pdf:
        first=pdf.new_page()
        first.insert_text((45,80),
            "Frictional potential energy may change when the cable moves.")
        second=pdf.new_page()
        second.insert_text((45,85),
            "The radius of the circular path scales with cable length.")
        second.insert_text((45,104),
            "The gravitational potential energy drop also scales with cable length.")
        second.insert_text((45,124),
            "Therefore the final expression becomes independent of cable length.")
        pdf.save(folder/"source.pdf")
    source_hash=hashlib.sha256((folder/"source.pdf").read_bytes()).hexdigest()
    job={
        "source_sha256":source_hash,
        "slides":[{
            "slide":15,
            "utterances":[{
                "id":"s015.utterance.003",
                "spoken_text":(
                    "Gravitational potential energy drop and circular path "
                    "radius scale with cable length.")}],
            "visual_targets":[{
                "id":"s015.text.002",
                "visible_text":"Why cable length cancels from the final expression"}],
        }],
    }
    hits=context._context(folder=folder,job=job,previous_quotes=set())
    assert hits
    assert any(x["source_page"]==2 and
               "cable length" in x["verbatim_source_quote"]
               for x in hits)
    assert all(x["physically_witnessed_original_PDF"] is True
               and x["source_semantic_support_verified"] is False
               and len(x["original_spoken_overlap"])>=2 for x in hits)
    assert len(hits)<=context.MAX_QUOTES
    assert max(sum(x["source_page"]==p for x in hits) for p in (1,2))<=2


def test_source_context_receipts_cannot_be_forged_or_overwritten(tmp_path):
    path=tmp_path/"semantic_context_recovery_v3.json"
    payload={"status":"NEEDS_INDEPENDENT_REVIEW",
             "student_publication_authorized":False}
    from selenium_pipeline.g3_semantic_source_repair_v1 import _write_once
    _write_once(path,payload)
    assert json.loads(path.read_text("utf8"))==payload
    path.write_text('{"forged":"academic acceptance"}')
    with pytest.raises(ValueError):
        _write_once(path,payload)
