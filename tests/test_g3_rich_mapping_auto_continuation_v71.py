"""Crash/replay regression for the prior source-bound Selenium reviewer."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from selenium_pipeline import g3_rich_mapping_auto_continuation_v71 as g3
from selenium_pipeline.recovery_registry import lookup_mechanism


def fixture(tmp_path,monkeypatch,slides=4):
    source=tmp_path/"serway_original"
    checkpoint=tmp_path/"immutable_rich_map"
    source.mkdir()
    checkpoint.mkdir()
    (checkpoint/"mapping_checkpoint.json").write_text(
        json.dumps({"mapping_detector_revision":5}),encoding="utf8")
    root=tmp_path/"output"/"unique_source_review"
    root.parent.mkdir()
    hashes={"source.pdf":"a"*64,"slides.pdf":"b"*64,"script.txt":"c"*64}
    meta={"slide_count":slides,"source_inputs_sha256":hashes}
    monkeypatch.setattr(g3,"load_accepted_checkpoint",lambda **_:(
        meta,{"slides":[{"slide_number":i} for i in range(1,slides+1)]}))
    monkeypatch.setattr(g3,"request_for_slide",lambda **kw:{
        "slide":kw["slide_number"],
        "request_sha256":str(kw["slide_number"])*64,
        "source_inputs_sha256":hashes,
    })
    monkeypatch.setattr(g3,"assess_response",lambda **kw:{
        "status":"SOURCEBOUND_AI_MAPPING_INDEPENDENTLY_AUDITED_REVIEW_ONLY",
        "slide":kw["slide_number"],"utterances_total":4,
        "text_source_and_author_anchors_passed":2,
        "remaining_review_items":2,
        "student_publication_authorized":False,
    })
    return source,checkpoint,root


def save_response(root,n,status="CAPTURED_SOURCE_AUDITED_REVIEW_ONLY"):
    files=g3._files(root,n)
    model={"slide":n,"request_sha256":str(n)*64}
    capture=json.dumps(model)
    files["capture"].write_text(capture,encoding="utf8")
    g3._new_json(files["response"],model)
    audit={"status":"SOURCEBOUND_AI_MAPPING_INDEPENDENTLY_AUDITED_REVIEW_ONLY",
        "slide":n,"utterances_total":4,
        "text_source_and_author_anchors_passed":2,
        "remaining_review_items":2,"student_publication_authorized":False}
    g3._new_json(files["audit"],audit)
    g3._new_json(files["claim"],{
        "status":status,"request_sha256":str(n)*64,
        "raw_model_response_sha256":g3._sha(files["response"]),
        "technical_audit_sha256":g3._sha(files["audit"]),
    })
    return files


def test_mechanism_is_in_executable_registry():
    assert lookup_mechanism(g3.KIND,g3.SIGNATURE)==g3.REPAIR


def test_read_only_builds_stable_source_identity_and_reuses_without_send(
        tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch)
    report=g3.run(source_folder=source,checkpoint=checkpoint,review_root=root)
    assert report["remaining_unreviewed_slides"]==4
    assert report["new_browser_dispatch_attempts_this_run"]==0
    assert report["independent_scientific_QA_complete"] is False
    saved=g3._sha(root/"g3_auto_mapping_identity.json")
    assert g3.run(source_folder=source,checkpoint=checkpoint,
                  review_root=root)["new_browser_dispatch_attempts_this_run"]==0
    assert g3._sha(root/"g3_auto_mapping_identity.json")==saved


def test_saved_original_reply_is_revalidated_and_never_sent_again(tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch)
    g3.prepare(source_folder=source,checkpoint=checkpoint,review_root=root)
    save_response(root,2)
    with patch("selenium_pipeline.rich_element_model_alignment.main") as model:
        report=g3.run(source_folder=source,checkpoint=checkpoint,
                      review_root=root,max_new_sends=0)
    model.assert_not_called()
    assert report["original_reviewed_slides_reused"]==1
    assert report["original_textbook_and_rendered_text_anchors_proven"]==2
    assert report["remaining_unreviewed_slides"]==3


def test_claim_without_capture_never_retry_and_next_slide_can_advance(
        tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch)
    g3.prepare(source_folder=source,checkpoint=checkpoint,review_root=root)
    g3._new_json(g3._files(root,1)["claim"],{
        "status":"MAY_HAVE_SENT_AWAIT_RECONCILIATION",
        "request_sha256":"1"*64})
    result=g3.run(source_folder=source,checkpoint=checkpoint,review_root=root)
    assert result["quarantined_or_uncertain_slides"]==1
    assert result["remaining_unreviewed_slides"]==3
    assert result["slides"][0]["status"]=="CLAIMED_OR_UNKNOWN_SEND_NO_REPLAY"


def test_crash_after_original_model_capture_reconciles_without_send(
        tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch)
    g3.prepare(source_folder=source,checkpoint=checkpoint,review_root=root)
    files=g3._files(root,1)
    g3._new_json(files["claim"],{
        "status":"MAY_HAVE_SENT_AWAIT_RECONCILIATION",
        "request_sha256":"1"*64})
    files["capture"].write_text(json.dumps({
        "slide":1,"request_sha256":"1"*64}),encoding="utf8")
    first=g3.run(source_folder=source,checkpoint=checkpoint,review_root=root)
    assert first["original_reviewed_slides_reused"]==1
    assert files["response"].exists() and files["audit"].exists()
    assert g3.run(source_folder=source,checkpoint=checkpoint,
                  review_root=root)["original_reviewed_slides_reused"]==1


def test_malformed_prior_reply_quarantined_not_promoted(tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch)
    g3.prepare(source_folder=source,checkpoint=checkpoint,review_root=root)
    files=g3._files(root,2)
    g3._new_json(files["claim"],{
        "status":"MAY_HAVE_SENT_AWAIT_RECONCILIATION",
        "request_sha256":"2"*64})
    files["capture"].write_text("not complete JSON",encoding="utf8")
    out=g3.run(source_folder=source,checkpoint=checkpoint,review_root=root)
    assert out["slides"][1]["status"]=="SAVED_SOURCE_REPLY_UNTRUSTED_NO_REPLAY"
    assert not files["audit"].exists()


def test_tampered_saved_reply_disallowed_no_release(tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch)
    g3.prepare(source_folder=source,checkpoint=checkpoint,review_root=root)
    files=save_response(root,1)
    files["response"].write_text('{"forged":true}',encoding="utf8")
    out=g3.run(source_folder=source,checkpoint=checkpoint,review_root=root)
    assert out["slides"][0]["status"]=="SAVED_SOURCE_REPLY_UNTRUSTED_NO_REPLAY"
    assert out["original_reviewed_slides_reused"]==0
    assert out["student_publication_authorized"] is False


def test_adopt_existing_owned_model_reply_is_idempotent(tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch)
    original=tmp_path/"original_attested"
    original.mkdir()
    g3.prepare(source_folder=source,checkpoint=checkpoint,review_root=root)
    refs=save_response(root,3)
    old={}
    for k,v in refs.items():
        (original/k).mkdir()
        dest=original/k/v.name
        dest.write_bytes(v.read_bytes())
        old[k]=dest
        v.unlink()
    adopted=g3.adopt_prior_owned_review(
        source_folder=source,checkpoint=checkpoint,review_root=root,
        slide=3,previous=old)
    assert adopted["slide"]==3
    assert adopted["source_text_anchors"]==2
    resumed=g3.adopt_prior_owned_review(
        source_folder=source,checkpoint=checkpoint,review_root=root,
        slide=3,previous=old)
    assert resumed==adopted  # same original SHA bytes; zero new model Sends


def test_worker_rejects_excess_requests_and_invalid_source(tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch)
    with pytest.raises(g3.RichMappingError,match="Unbounded"):
        g3.run(source_folder=source,checkpoint=checkpoint,
               review_root=root,max_new_sends=4)
    with pytest.raises(g3.RichMappingError,match="Unbounded"):
        g3.run(source_folder=source,checkpoint=checkpoint,
               review_root=root,max_new_sends=True)
    g3.prepare(source_folder=source,checkpoint=checkpoint,review_root=root)
    with pytest.raises(g3.RichMappingError,match="source or checkpoint identity changed"):
        monkeypatch.setattr(g3,"load_accepted_checkpoint",
            lambda **_:({"slide_count":4,
                "source_inputs_sha256":{"source.pdf":"f"*64}},{}))
        g3.prepare(source_folder=source,checkpoint=checkpoint,review_root=root)


def test_run_dispatches_at_most_two_before_uncertain_transport_stop(
        tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch,slides=5)
    called=[]
    def failure(args):
        n=int(args[args.index("--slide")+1])
        called.append(n)
        files=g3._files(root,n)
        g3._new_json(files["claim"],{
            "status":"MAY_HAVE_SENT_AWAIT_RECONCILIATION",
            "request_sha256":str(n)*64})
        raise RuntimeError("No response after registered browser Send")
    with patch("selenium_pipeline.rich_element_model_alignment.main",
               side_effect=failure):
        out=g3.run(source_folder=source,checkpoint=checkpoint,
                   review_root=root,max_new_sends=3)
    assert called==[1,2]
    assert out["quarantined_or_uncertain_slides"]==2
    assert out["new_browser_dispatch_attempts_this_run"]==2
    assert out["remaining_unreviewed_slides"]==3


def test_run_skip_reused_and_advance_next_safe_slide(tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch)
    g3.prepare(source_folder=source,checkpoint=checkpoint,review_root=root)
    save_response(root,1)
    called=[]
    def success(args):
        n=int(args[args.index("--slide")+1])
        called.append(n)
        save_response(root,n)
    with patch("selenium_pipeline.rich_element_model_alignment.main",
               side_effect=success):
        out=g3.run(source_folder=source,checkpoint=checkpoint,
                   review_root=root,max_new_sends=2)
    assert called==[2,3]
    assert out["original_reviewed_slides_reused"]==3
    assert out["remaining_unreviewed_slides"]==1
    assert out["paid_gemini_api_requests"]==0


def test_scheduler_prioritizes_most_ambiguous_original_slide(tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch)
    # Source-bounded priority is based only on frozen original candidate
    # counts; it can reorder work but NEVER promote lexical hints as proof.
    meta={"slide_count":4,"source_inputs_sha256":{
        "source.pdf":"a"*64,"slides.pdf":"b"*64,"script.txt":"c"*64}}
    draft={"slides":[
       {"slide_number":1,"proposed_utterances":[{"mapping_ambiguous":False}]},
       {"slide_number":2,"proposed_utterances":[{"mapping_ambiguous":True}]},
       {"slide_number":3,"proposed_utterances":[{"mapping_ambiguous":True},
                                                {"mapping_ambiguous":True}]},
       {"slide_number":4,"proposed_utterances":[{"mapping_ambiguous":True},
                                                {"mapping_ambiguous":True},
                                                {"mapping_ambiguous":True}]},
    ]}
    monkeypatch.setattr(g3,"load_accepted_checkpoint",lambda **_:(meta,draft))
    selected=[]
    def fake_model(args):
        n=int(args[args.index("--slide")+1])
        selected.append(n)
        save_response(root,n)
    with patch("selenium_pipeline.rich_element_model_alignment.main",
               side_effect=fake_model):
        result=g3.run(source_folder=source,checkpoint=checkpoint,
                      review_root=root,max_new_sends=2)
    assert selected==[4,3]
    assert result["original_reviewed_slides_reused"]==2


def test_worker_cannot_hold_duplicate_source_queue_os_lock(tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch)
    g3.prepare(source_folder=source,checkpoint=checkpoint,review_root=root)
    with g3._exclusive(root):
        with pytest.raises(g3.RichMappingError,
                           match="Another G3 source-review owner"):
            with g3._exclusive(root):
                pass
    # Native OS lock automatically releases without removing the checkpoint.
    assert g3.run(source_folder=source,checkpoint=checkpoint,
                  review_root=root)["remaining_unreviewed_slides"]==4


def test_two_old_uncertain_browser_claims_block_fresh_sends_across_restart(
        tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch,slides=5)
    g3.prepare(source_folder=source,checkpoint=checkpoint,review_root=root)
    for n in (1,2):
        g3._new_json(g3._files(root,n)["claim"],{
            "status":"MAY_HAVE_SENT_AWAIT_RECONCILIATION",
            "request_sha256":str(n)*64})
    with patch("selenium_pipeline.rich_element_model_alignment.main") as sends:
        for _ in range(2):
            result=g3.run(source_folder=source,checkpoint=checkpoint,
                          review_root=root,max_new_sends=3)
            assert result["new_browser_dispatch_attempts_this_run"]==0
            assert result["quarantined_or_uncertain_slides"]==2
            assert result["remaining_unreviewed_slides"]==3
    sends.assert_not_called()


def test_prior_untrusted_captured_reply_also_counts_against_new_send_budget(
        tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch,slides=4)
    g3.prepare(source_folder=source,checkpoint=checkpoint,review_root=root)
    files=g3._files(root,1)
    g3._new_json(files["claim"],{
        "status":"MAY_HAVE_SENT_AWAIT_RECONCILIATION",
        "request_sha256":"1"*64})
    files["capture"].write_text("untrusted broken original",encoding="utf8")
    g3._new_json(g3._files(root,2)["claim"],{
        "status":"MAY_HAVE_SENT_AWAIT_RECONCILIATION",
        "request_sha256":"2"*64})
    with patch("selenium_pipeline.rich_element_model_alignment.main") as sends:
        out=g3.run(source_folder=source,checkpoint=checkpoint,
                   review_root=root,max_new_sends=3)
    sends.assert_not_called()
    assert out["new_browser_dispatch_attempts_this_run"]==0


def test_crash_during_prior_source_reply_adoption_resumes_exact_original_bytes(
        tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch)
    g3.prepare(source_folder=source,checkpoint=checkpoint,review_root=root)
    historical=tmp_path/"old_owned_browser_capture"
    historical.mkdir()
    original=save_response(root,2)
    old={}
    for kind,file in original.items():
        folder=historical/kind
        folder.mkdir()
        target=folder/file.name
        target.write_bytes(file.read_bytes())
        old[kind]=target
        file.unlink()
    # Fault injection: worker terminated after copying two original files,
    # before the source audit or claim copied. Must resume the SAME bytes.
    now=g3._files(root,2)
    for kind in ("response","capture"):
        now[kind].write_bytes(old[kind].read_bytes())
    adopted=g3.adopt_prior_owned_review(
        source_folder=source,checkpoint=checkpoint,review_root=root,
        slide=2,previous=old)
    assert adopted["status"]=="SAVED_BROWSER_REVIEW_REVALIDATED_NO_SEND"
    assert all(g3._sha(now[k])==g3._sha(old[k]) for k in old)
    assert g3.run(source_folder=source,checkpoint=checkpoint,
                  review_root=root)["original_reviewed_slides_reused"]==1


def test_prior_reply_adoption_rejects_conflicting_existing_bytes(
        tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch)
    g3.prepare(source_folder=source,checkpoint=checkpoint,review_root=root)
    historical=tmp_path/"old"
    historical.mkdir()
    originals=save_response(root,1)
    old={}
    for kind,file in originals.items():
        folder=historical/kind
        folder.mkdir()
        dest=folder/file.name
        dest.write_bytes(file.read_bytes())
        old[kind]=dest
    originals["capture"].write_text("forged prior returned bytes",encoding="utf8")
    with pytest.raises(g3.RichMappingError,
                       match="Existing adoption conflicts"):
        g3.adopt_prior_owned_review(
            source_folder=source,checkpoint=checkpoint,review_root=root,
            slide=1,previous=old)


def _source_rejected_claim(root,n):
    f=save_response(root,n)
    f["claim"].unlink()
    g3._new_json(f["claim"],{
        "status":"CAPTURED_SOURCE_REJECTED_NO_REPLAY",
        "request_sha256":str(n)*64,
        "source_inputs_sha256":{
            "source.pdf":"a"*64,"slides.pdf":"b"*64,"script.txt":"c"*64},
        "verbatim_capture_sha256":g3._sha(f["capture"]),
        "parsed_model_response_sha256":g3._sha(f["response"]),
        "source_rejection_type":"RichMappingError",
        "source_rejection_reason":"Missing exact publisher citation",
        "model_response_accepted":False,
        "academic_approval":False,
        "paid_tts_authorized":False,
        "student_publication_authorized":False,
    })
    f["audit"].unlink()
    return f


def test_authentic_source_rejection_has_distinct_no_replay_status(
        tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch)
    g3.prepare(source_folder=source,checkpoint=checkpoint,review_root=root)
    f=_source_rejected_claim(root,1)
    original=g3.assess_response
    def source_grounding(**kw):
        if kw["slide_number"]==1:
            raise g3.RichMappingError("Missing exact publisher citation")
        return original(**kw)
    monkeypatch.setattr(g3,"assess_response",source_grounding)
    with patch("selenium_pipeline.rich_element_model_alignment.main") as browser:
        outcome=g3.run(source_folder=source,checkpoint=checkpoint,
                       review_root=root,max_new_sends=0)
    browser.assert_not_called()
    assert outcome["source_rejected_slides"]==1
    assert outcome["quarantined_or_uncertain_slides"]==0
    assert outcome["remaining_unreviewed_slides"]==3
    assert outcome["slides"][0]["status"]=="SOURCE_QUOTE_REJECTED_NO_REPLAY"
    assert outcome["student_publication_authorized"] is False
    assert not f["audit"].exists()


def test_two_source_rejections_leave_other_untouched_slides_dispatch_eligible(
        tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch)
    g3.prepare(source_folder=source,checkpoint=checkpoint,review_root=root)
    for n in (1,2):
        _source_rejected_claim(root,n)
    original=g3.assess_response
    def source_grounding(**kw):
        if kw["slide_number"] in (1,2):
            raise g3.RichMappingError("Missing exact publisher citation")
        return original(**kw)
    monkeypatch.setattr(g3,"assess_response",source_grounding)
    submitted=[]
    def fake_send(args):
        n=int(args[args.index("--slide")+1])
        submitted.append(n)
        save_response(root,n)
    with patch("selenium_pipeline.rich_element_model_alignment.main",
               side_effect=fake_send):
        result=g3.run(source_folder=source,checkpoint=checkpoint,
                      review_root=root,max_new_sends=2)
    assert sorted(submitted)==[3,4]
    assert result["source_rejected_slides"]==2
    assert result["quarantined_or_uncertain_slides"]==0
    assert result["original_reviewed_slides_reused"]==2
    assert result["student_publication_authorized"] is False
    assert all(g3._files(root,n)["claim"].exists() for n in (1,2))
    assert not any(g3._files(root,n)["audit"].exists() for n in (1,2))


def test_forged_source_rejection_capture_treated_as_unknown_and_never_trusted(
        tmp_path,monkeypatch):
    source,checkpoint,root=fixture(tmp_path,monkeypatch)
    g3.prepare(source_folder=source,checkpoint=checkpoint,review_root=root)
    files=_source_rejected_claim(root,1)
    files["capture"].write_text("tampered original browser capture",
                                encoding="utf8")
    original=g3.assess_response
    monkeypatch.setattr(g3,"assess_response",
       lambda **kw: (_ for _ in ()).throw(
           AssertionError("Tampered rejected evidence reached publisher audit")))
    out=g3.run(source_folder=source,checkpoint=checkpoint,review_root=root)
    assert out["source_rejected_slides"]==0
    assert out["quarantined_or_uncertain_slides"]==1
    assert out["slides"][0]["status"]=="SAVED_SOURCE_REPLY_UNTRUSTED_NO_REPLAY"
    assert out["student_publication_authorized"] is False


def test_source_rejection_reclassification_is_registered_executable_recovery():
    assert g3.lookup_mechanism(
        "g3_rejected_content_continuation",
        "CAPTURED_REJECTED_PUBLISHER_QUOTE_COUNTED_AS_PROVIDER_UNCERTAINTY",
    )=="REVERIFY_ORIGINAL_REJECTED_BYTES_QUARANTINE_SLIDE_ADVANCE_OTHER_SLIDES"
