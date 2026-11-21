"""Source-bound historical no-click recovery; NEVER test a live provider Send."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import wave

import pytest

from test_original_packet_evidence_audit import fixture
from selenium_pipeline import academic_review_checkpoint as checkpoint
from selenium_pipeline import ai_academic_review_queue as review_queue
from selenium_pipeline import source_review_eligibility_preflight as preflight
from selenium_pipeline import review_retry_plan
from selenium_pipeline import recovery_registry
from selenium_pipeline.ai_academic_web_review import (
    build_review_job, review_instructions)
from selenium_pipeline.gemini_selenium_only_policy import (
    GeminiSeleniumTemporaryFailure)


def original_with_one_failed_claim(tmp_path, *, certified=True):
    original=tmp_path/"original"
    fixture(original)
    (original/"script.txt").write_text(
        "**Slide 1 [1 sec]:\nA visible equation**\n", encoding="utf8")
    with wave.open(str(original/"slide1.wav"),"wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(b"\x00\x02"*24000)
    queue=tmp_path/"review_queue"
    review_queue.prepare_resumable_review(
        folder=original, output_root=queue, slide_numbers=[1])
    job=build_review_job(folder=original,slide_numbers=[1])
    prompt=review_instructions(job,mode="INITIAL_REVIEW")
    original_hashes={
        "source.pdf":job["source_sha256"],
        "slides.pdf":job["slides_sha256"],
        "script.txt":job["script_sha256"],
    }
    request=queue/"slide_001_initial_review_attempt_01_request"
    first=checkpoint.prepare(
        checkpoint=request, original_folder=original,
        request_text=prompt,source_hashes=original_hashes,
        review_mode="INITIAL_REVIEW")
    checkpoint.mark_submission_maybe(
        request,expected_fingerprint=first["request_fingerprint"])
    if certified:
        checkpoint.certify_unsent_preparation_failure(
            request, expected_fingerprint=first["request_fingerprint"],
            error=GeminiSeleniumTemporaryFailure(
                "Verified browser unavailable before Send boundary",
                attempts_used=1,
                failure_phase="GEMINI_BROWSER_OR_WEBDRIVER_NOT_READY"))
    old=queue/"slide_001_initial_review_attempt_01.json"
    old.write_text(json.dumps({
        "slide":1, "mode":"INITIAL_REVIEW", "attempt":1,
        "status":"FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED",
        "provider_submission_state":"UNKNOWN_AFTER_POSSIBLE_SUBMISSION",
        "manual_retry_eligible":False,
        "student_publication_authorized":False,
    }),encoding="utf8")
    return original,queue,request,old


def file_sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def test_typed_original_witness_admitted_only_as_same_claim_no_send(tmp_path):
    original,queue,request,old=original_with_one_failed_claim(tmp_path)
    initial_sha=file_sha(old)
    planned=review_retry_plan.plan_manual_review_attempt(
        queue,slide=1,mode="INITIAL_REVIEW")
    assert planned["status"]=="CERTIFIED_PRESEND_ORIGINAL_CLAIM_SAME_WINDOW_RECOVERY"
    assert planned["certified_presend_count"]==1
    assert planned["next_possible_attempt"]==1
    assert planned["dispatch_authorized"] is False
    scoped=preflight.inspect_original_review_eligibility(
        folder=original,queue_root=queue,slide=1)
    assert scoped["certified_presend_same_claim_recovery_ready"] is True
    assert scoped["fresh_claimed_internal_selenium_review_ready"] is False
    assert scoped["review_model_request_sent"] is False
    choice=review_queue.select_next_safe_review(
        queue_root=queue,folder=original)
    assert choice["action"]=="RESUME_CERTIFIED_UNSENT_ORIGINAL_CLAIM"
    assert choice["next_slide"]==1
    assert choice["original_failed_attempt_sha256"]==initial_sha
    assert choice["original_request_replay_authorized"] is False
    assert choice["new_model_requests"] is False
    assert file_sha(old)==initial_sha
    assert checkpoint._load(request)["status"]=="CERTIFIED_PRESEND_UNSENT"


def test_provenance_unchanged_when_simulated_transport_fails_no_send(
        tmp_path,monkeypatch):
    original,queue,request,old=original_with_one_failed_claim(tmp_path)
    original_sha=file_sha(old)
    calls=[]
    def transport_disabled(**kwargs):
        calls.append(kwargs)
        raise RuntimeError("Simulated model request unavailable; no network")
    monkeypatch.setattr(review_queue,"run_web_review",transport_disabled)
    outcome=review_queue.advance_one_safe_review(
        queue_root=queue,folder=original,execute=True)
    assert outcome["status"]=="ONE_AUTONOMOUS_ACADEMIC_REVIEW_ATTEMPT_FINISHED"
    assert outcome["review"]["status"]=="FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED"
    assert len(calls)==1
    successor=queue/"slide_001_initial_review_certified_presend_resumed_after_attempt_01.json"
    assert successor.is_file()
    assert file_sha(old)==original_sha
    assert checkpoint._load(request)["status"]=="CERTIFIED_PRESEND_UNSENT"
    assert not (queue/"slide_001_initial_review.json").exists()
    blocked=review_queue.select_next_safe_review(queue_root=queue,folder=original)
    assert blocked["status"]=="NO_SAFE_REVIEW_UNIT_REMAINING"
    assert blocked["new_model_requests"] is False
    assert len(calls)==1
    assert successor.is_file()


def test_uncertain_request_without_typed_witness_stays_blocked(tmp_path):
    original,queue,request,old=original_with_one_failed_claim(
        tmp_path,certified=False)
    p=review_retry_plan.plan_manual_review_attempt(
        queue,slide=1,mode="INITIAL_REVIEW")
    assert p["status"]=="BLOCKED_AMBIGUOUS_PROVIDER_REQUEST_NEEDS_RECONCILIATION"
    choice=review_queue.select_next_safe_review(queue_root=queue,folder=original)
    assert choice["status"]=="NO_SAFE_REVIEW_UNIT_REMAINING"
    assert checkpoint._load(request)["status"]=="SUBMITTED_OR_UNCERTAIN"


def test_exact_source_drift_never_admits_recovery(tmp_path):
    original,queue,request,old=original_with_one_failed_claim(tmp_path)
    (original/"script.txt").write_text("changed script",encoding="utf8")
    with pytest.raises((ValueError,RuntimeError)):
        review_queue.select_next_safe_review(queue_root=queue,folder=original)


def test_disabled_recovery_registry_never_admits_send(tmp_path,monkeypatch):
    original,queue,request,old=original_with_one_failed_claim(tmp_path)
    registry=json.loads(recovery_registry.REGISTRY_PATH.read_text(encoding="utf8"))
    for row in registry["entries"]:
        if row["signature"]=="G2_TYPED_PRESEND_UNSENT_REUSE_EXACT_ORIGINAL_WINDOW":
            row["enabled"]=False
            break
    else:
        pytest.fail("Missing recovery registry signature")
    path=tmp_path/"disabled_registry.json"
    path.write_text(json.dumps(registry),encoding="utf8")
    monkeypatch.setattr(recovery_registry,"REGISTRY_PATH",path)
    with pytest.raises(ValueError,match="retired or disabled"):
        review_queue.select_next_safe_review(queue_root=queue,folder=original)


def test_tampered_certified_no_click_witness_fails_closed(tmp_path):
    original,queue,request,old=original_with_one_failed_claim(tmp_path)
    witness=request/"certified_presend_unsent_01.json"
    evidence=json.loads(witness.read_text(encoding="utf8"))
    evidence["send_boundary_entered"]=True
    witness.write_text(json.dumps(evidence),encoding="utf8")
    with pytest.raises((ValueError,RuntimeError)):
        review_queue.select_next_safe_review(queue_root=queue,folder=original)


def test_certified_resume_does_not_use_injected_transport(tmp_path):
    original,queue,request,old=original_with_one_failed_claim(tmp_path)
    def fake_send(*args,**kwargs):
        pytest.fail("Injected provider Send forbidden for historical recovery")
    with pytest.raises((ValueError,RuntimeError),match="original owned browser"):
        review_queue.advance_one_safe_review(
            queue_root=queue,folder=original,execute=True,transport=fake_send)
    assert file_sha(old)
    assert checkpoint._load(request)["status"]=="CERTIFIED_PRESEND_UNSENT"


def test_fault_injection_crash_after_original_claim_resume_never_resends(
        tmp_path,monkeypatch):
    original,queue,request,old=original_with_one_failed_claim(tmp_path)
    original_sha=file_sha(old)
    calls=[]
    def crash_after_claim(**kwargs):
        calls.append("claim_started")
        state=checkpoint._load(request)
        checkpoint.resume_certified_unsent(
            request,expected_fingerprint=state["request_fingerprint"])
        raise RuntimeError("simulated crash after original Send boundary was entered")
    monkeypatch.setattr(review_queue,"run_web_review",crash_after_claim)
    outcome=review_queue.advance_one_safe_review(
        queue_root=queue,folder=original,execute=True)
    assert outcome["review"]["status"]=="FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED"
    assert checkpoint._load(request)["status"]=="SUBMITTED_OR_UNCERTAIN"
    assert file_sha(old)==original_sha
    again=review_queue.select_next_safe_review(queue_root=queue,folder=original)
    assert again["status"]=="NO_SAFE_REVIEW_UNIT_REMAINING"
    assert len(calls)==1
    assert not (queue/"slide_001_initial_review.json").exists()


def test_fault_injection_another_typed_preclick_no_send_still_bounded(
        tmp_path,monkeypatch):
    original,queue,request,old=original_with_one_failed_claim(tmp_path)
    old_sha=file_sha(old)
    def another_typed_presend(**kwargs):
        state=checkpoint._load(request)
        checkpoint.resume_certified_unsent(
            request,expected_fingerprint=state["request_fingerprint"])
        failure=GeminiSeleniumTemporaryFailure(
            "browser unavailable before Send",attempts_used=1,
            failure_phase="GEMINI_BROWSER_OR_WEBDRIVER_NOT_READY")
        checkpoint.certify_unsent_preparation_failure(
            request,expected_fingerprint=state["request_fingerprint"],
            error=failure)
        raise failure
    monkeypatch.setattr(review_queue,"run_web_review",another_typed_presend)
    outcome=review_queue.advance_one_safe_review(
        queue_root=queue,folder=original,execute=True)
    assert outcome["review"]["status"]=="FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED"
    assert checkpoint._verify_certified_unsent(
        request,checkpoint._load(request))==2
    assert file_sha(old)==old_sha
    after=review_queue.select_next_safe_review(queue_root=queue,folder=original)
    assert after["status"]=="NO_SAFE_REVIEW_UNIT_REMAINING"
    assert not (queue/"slide_001_initial_review.json").exists()


def test_missing_global_claim_or_untrusted_historical_receipt_holds(
        tmp_path):
    original,queue,request,old=original_with_one_failed_claim(tmp_path)
    state=checkpoint._load(request)
    global_claim=queue/".microgen_academic_review_once"/(
        state["request_fingerprint"]+".claim")
    global_claim.unlink()
    assert review_retry_plan.plan_manual_review_attempt(
        queue,slide=1,mode="INITIAL_REVIEW")["status"]==(
            "BLOCKED_AMBIGUOUS_PROVIDER_REQUEST_NEEDS_RECONCILIATION")
    assert review_queue.select_next_safe_review(
        queue_root=queue,folder=original)["status"]==(
            "NO_SAFE_REVIEW_UNIT_REMAINING")


def test_certified_retry_limit_never_resets_global_claim(tmp_path,monkeypatch):
    original,queue,request,old=original_with_one_failed_claim(tmp_path)
    monkeypatch.setattr(checkpoint,"MAX_CERTIFIED_PRESEND_RECOVERIES",1)
    assert review_retry_plan.plan_manual_review_attempt(
        queue,slide=1,mode="INITIAL_REVIEW")["status"]==(
            "BLOCKED_AMBIGUOUS_PROVIDER_REQUEST_NEEDS_RECONCILIATION")
    assert review_queue.select_next_safe_review(
        queue_root=queue,folder=original)["status"]==(
            "NO_SAFE_REVIEW_UNIT_REMAINING")
