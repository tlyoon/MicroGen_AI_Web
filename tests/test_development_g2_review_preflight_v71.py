"""Offline, source-bound G2 preflight fan-out: no model Send or approval."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from selenium_pipeline import development_continuity_executor_v71 as executor
from selenium_pipeline import source_review_eligibility_preflight as preflight

ROOT = Path(__file__).resolve().parents[1]


def task(name, action, params, *, deps=()):
    return {"id":name, "workstream":"g2", "action":action,
            "params":params, "depends_on":list(deps),
            "max_attempts":1, "authorized":True}


def plan(tmp, tasks):
    file = tmp/"plan.json"
    file.write_text(json.dumps({"schema_version":1, "project":"MicroGen_AI_Web",
                                "tasks":tasks}), encoding="utf8")
    return file


def g2_task(tmp, *, slide=1):
    return task("preflight", "g2_review_preflight", {
        "folder":str(tmp/"source"), "queue_root":str(tmp/"queue"),
        "slide":slide,
    })


def good_report(slide):
    return {
        "status":"SOURCE_BOUND_ACADEMIC_REVIEW_SCOPE_PREFLIGHT_NO_SEND",
        "slide":slide,
        "planning_result":"RECONCILE_OLD_PROVIDER_ATTEMPTS_BEFORE_ANY_SEND",
        "fresh_claimed_internal_selenium_review_ready":False,
        "review_model_request_sent":False,
        "automatic_retry_authorized":False,
        "independent_source_mathematics_approved":False,
        "student_publication_authorized":False,
    }


@pytest.mark.parametrize("slide", [0, -1, 201, "1", True, None])
def test_malformed_g2_slide_rejected_before_worker(tmp_path, slide):
    file=plan(tmp_path,[g2_task(tmp_path,slide=slide)])
    with pytest.raises(ValueError,match="Invalid exact G2"):
        executor._plan(file)


def test_preflight_rejects_unknown_extra_parameters(tmp_path):
    unit=g2_task(tmp_path)
    unit["params"]["execute_model_request"]=True
    with pytest.raises(ValueError,match="Unregistered worker input"):
        executor._plan(plan(tmp_path,[unit]))


def invoke_mocked(tmp_path, monkeypatch, response):
    file=plan(tmp_path,[g2_task(tmp_path)])
    state=tmp_path/"state"
    monkeypatch.setenv("MICROGEN_V71_PINNED_EXECUTOR_SHA256",
                       executor._sha(Path(executor.__file__)))
    monkeypatch.setenv("MICROGEN_V71_PINNED_PLAN_SHA256",
                       executor._sha(file))
    monkeypatch.setattr(preflight, "inspect_original_review_eligibility",
                        lambda **kwargs:response)
    result=executor._worker(file,state,"preflight","source_bound_token",ROOT)
    receipt=json.loads((state/"results"/"source_bound_token.json").read_text())
    return result,receipt


def test_source_bound_offline_preflight_is_not_scientific_acceptance(tmp_path,monkeypatch):
    code,receipt=invoke_mocked(tmp_path,monkeypatch,good_report(1))
    assert code==0
    assert receipt["status"]=="passed"
    assert receipt["evidence"]["model_requests"]==0
    assert receipt["evidence"]["scientific_acceptance"] is False
    assert receipt["evidence"]["student_release"] is False
    assert receipt["evidence"]["planning_result"]=="RECONCILE_OLD_PROVIDER_ATTEMPTS_BEFORE_ANY_SEND"


@pytest.mark.parametrize("tampered", [
    {"review_model_request_sent":True},
    {"automatic_retry_authorized":True},
    {"student_publication_authorized":True},
    {"independent_source_mathematics_approved":True},
    {"status":"AI_SOURCE_APPROVED"},
    {"slide":2},
    {"planning_result":None},
])
def test_forged_source_review_or_release_is_never_accepted(tmp_path,monkeypatch,tampered):
    forged=good_report(1)
    forged.update(tampered)
    code,receipt=invoke_mocked(tmp_path,monkeypatch,forged)
    assert code==1
    assert receipt["status"]=="failed"
    assert receipt["evidence"]["error_class"]=="ValueError"


def test_real_subprocess_quarantines_missing_g2_queue_and_fans_out(tmp_path):
    payload=tmp_path/"independent.txt"
    payload.write_text("Offline independent source witness",encoding="utf8")
    source_hash=hashlib.sha256(payload.read_bytes()).hexdigest()
    file=plan(tmp_path,[
        g2_task(tmp_path),
        task("independent", "verify_file_sha256",
             {"path":str(payload),"sha256":source_hash}),
    ])
    state=tmp_path/"state"
    cmd=[sys.executable,"-B","-m",
         "selenium_pipeline.development_continuity_executor_v71",
         "run","--plan",str(file),"--state-dir",str(state),
         "--repo-root",str(ROOT)]
    env=os.environ.copy()
    env.pop("MICROGEN_V71_TEST_EXIT_AFTER_CLAIM",None)
    env.pop("MICROGEN_V71_TEST_EXIT_AFTER_CHILD_START",None)
    first=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,
                         text=True,timeout=50)
    assert first.returncode==2,first.stderr+first.stdout
    evidence=json.loads((state/"state.json").read_text())
    assert evidence["tasks"]["preflight"]["status"]=="quarantined"
    assert evidence["tasks"]["independent"]["status"]=="passed"
    started=[row["task"] for row in evidence["events"]
             if row["event"]=="worker_started"]
    assert started==["preflight","independent"]
    second=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,
                          text=True,timeout=50)
    assert second.returncode==2
    after=json.loads((state/"state.json").read_text())
    assert [row["task"] for row in after["events"]
            if row["event"]=="worker_started"]==started


def original_scope_fixture(tmp_path, monkeypatch):
    """Synthetic source only; actual Serway source is tested separately."""
    original=tmp_path/"original"
    queue=tmp_path/"queue"
    original.mkdir()
    queue.mkdir()
    for name in ("source.pdf","slides.pdf","script.txt"):
        (original/name).write_bytes(("synthetic "+name).encode())
    (queue/"queue.json").write_text("{}")
    hashes={name:hashlib.sha256((original/name).read_bytes()).hexdigest()
            for name in ("source.pdf","slides.pdf","script.txt")}
    monkeypatch.setattr(preflight,"_check_queue",
                        lambda **kwargs:{"utterance_count":7})
    monkeypatch.setattr(preflight,"build_review_job",
                        lambda **kwargs:{
                            "utterance_count":7,
                            "source_sha256":hashes["source.pdf"],
                            "slides_sha256":hashes["slides.pdf"],
                            "script_sha256":hashes["script.txt"],
                        })
    def fake_attempt(q, *, slide, mode):
        assert slide==4
        status=("ALREADY_COMPLETED_NO_RESUBMISSION"
                if mode=="INITIAL_REVIEW"
                else "NEW_ATTEMPT_REQUIRES_EXPLICIT_REQUEST")
        return {"status":status,
                "observed_attempts":1 if mode=="INITIAL_REVIEW" else 0,
                "next_possible_attempt":1 if mode=="INDEPENDENT_CHALLENGE" else None}
    monkeypatch.setattr(preflight,"plan_manual_review_attempt",fake_attempt)
    return original,queue


def test_prior_dispatch_claim_overrides_false_fresh_review(tmp_path,monkeypatch):
    from selenium_pipeline import academic_review_checkpoint as checkpoints
    original,queue=original_scope_fixture(tmp_path,monkeypatch)
    checkpoint=queue/"slide_004_independent_challenge_attempt_01_request"
    checkpoint.mkdir()
    (checkpoint/"dispatch_attempted.claim").write_text("historical claim")
    monkeypatch.setattr(checkpoints,"_load",
                        lambda path:{"status":"SUBMITTED_OR_UNCERTAIN"})
    result=preflight.inspect_original_review_eligibility(
        folder=original,queue_root=queue,slide=4)
    assert result["planning_result"]=="AMBIGUOUS_OLD_SEND_NO_RESUBMISSION"
    assert result["fresh_claimed_internal_selenium_review_ready"] is False
    assert result["review_model_request_sent"] is False
    assert result["review_stages"]["INDEPENDENT_CHALLENGE"][
        "historical_dispatch_claim_present"] is True


def test_proven_prepared_unsubmitted_request_stays_eligible(tmp_path,monkeypatch):
    from selenium_pipeline import academic_review_checkpoint as checkpoints
    original,queue=original_scope_fixture(tmp_path,monkeypatch)
    checkpoint=queue/"slide_004_independent_challenge_attempt_01_request"
    checkpoint.mkdir()
    monkeypatch.setattr(checkpoints,"_load",
                        lambda path:{"status":"PREPARED_NOT_SENT"})
    result=preflight.inspect_original_review_eligibility(
        folder=original,queue_root=queue,slide=4)
    assert result["fresh_claimed_internal_selenium_review_ready"] is True
    assert result["review_model_request_sent"] is False


def test_prepared_claim_with_dispatch_marker_is_quarantined(tmp_path,monkeypatch):
    from selenium_pipeline import academic_review_checkpoint as checkpoints
    original,queue=original_scope_fixture(tmp_path,monkeypatch)
    checkpoint=queue/"slide_004_independent_challenge_attempt_01_request"
    checkpoint.mkdir()
    (checkpoint/"dispatch_attempted.claim").write_text("attempted")
    monkeypatch.setattr(checkpoints,"_load",
                        lambda path:{"status":"PREPARED_NOT_SENT"})
    result=preflight.inspect_original_review_eligibility(
        folder=original,queue_root=queue,slide=4)
    assert result["planning_result"]=="AMBIGUOUS_OLD_SEND_NO_RESUBMISSION"
    assert result["fresh_claimed_internal_selenium_review_ready"] is False


def test_prior_request_window_symlink_fails_closed(tmp_path,monkeypatch):
    original,queue=original_scope_fixture(tmp_path,monkeypatch)
    foreign=tmp_path/"foreign"
    foreign.mkdir()
    alias=queue/"slide_004_independent_challenge_attempt_01_request"
    try:
        alias.symlink_to(foreign,target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation restricted by Windows policy")
    with pytest.raises(ValueError,match="Unsafe historical academic request"):
        preflight.inspect_original_review_eligibility(
            folder=original,queue_root=queue,slide=4)


def test_completed_review_cannot_be_reselected_for_reconciliation(tmp_path,monkeypatch):
    """A saved completed receipt outranks its older owned request window."""
    from selenium_pipeline import academic_review_checkpoint as checkpoints
    original,queue=original_scope_fixture(tmp_path,monkeypatch)
    checkpoint=queue/"slide_004_independent_challenge_attempt_01_request"
    checkpoint.mkdir()
    (checkpoint/"dispatch_attempted.claim").write_text("old valid claim")
    monkeypatch.setattr(checkpoints,"_load",
                        lambda path:{"status":"SOURCE_VALIDATED_ONE_PASS_UNAPPROVED"})
    def already_done(q, *, slide, mode):
        return {"status":"ALREADY_COMPLETED_NO_RESUBMISSION",
                "observed_attempts":1,"next_possible_attempt":None}
    monkeypatch.setattr(preflight,"plan_manual_review_attempt",already_done)
    result=preflight.inspect_original_review_eligibility(
        folder=original,queue_root=queue,slide=4)
    assert result["planning_result"]=="EXISTING_PASS_MUST_NOT_BE_REPEATED"
    assert result["fresh_claimed_internal_selenium_review_ready"] is False
    assert result["review_model_request_sent"] is False


def test_ambiguous_claim_requires_live_registered_recovery(tmp_path,monkeypatch):
    from selenium_pipeline import academic_review_checkpoint as checkpoints
    from selenium_pipeline import recovery_registry
    original,queue=original_scope_fixture(tmp_path,monkeypatch)
    checkpoint=queue/"slide_004_independent_challenge_attempt_01_request"
    checkpoint.mkdir()
    (checkpoint/"dispatch_attempted.claim").write_text("previous claim")
    monkeypatch.setattr(checkpoints,"_load",
                        lambda path:{"status":"SUBMITTED_OR_UNCERTAIN"})
    monkeypatch.setattr(recovery_registry,"lookup_mechanism",
                        lambda *args,**kwargs:None)
    with pytest.raises(ValueError,match="No verified recovery"):
        preflight.inspect_original_review_eligibility(
            folder=original,queue_root=queue,slide=4)


def test_source_claim_recovery_registry_is_exact_and_disable_fails_closed(tmp_path):
    from selenium_pipeline.recovery_registry import (
        REGISTRY_PATH,lookup_mechanism)
    kind="source_review_claim"
    signature="G2_PREFLIGHT_FALSE_FRESH_WITH_HISTORICAL_REQUEST_WINDOW"
    assert lookup_mechanism(kind,signature)==(
        "RECONCILE_OWNED_CLAIM_BEFORE_ANY_NEW_SOURCE_SEND")
    forged=json.loads(REGISTRY_PATH.read_text(encoding="utf8"))
    for entry in forged["entries"]:
        if (entry["match_type"],entry["signature"])==(kind,signature):
            entry["enabled"]=False
            break
    else:
        pytest.fail("Actual source-bound recovery entry not found")
    changed=tmp_path/"registry.json"
    changed.write_text(json.dumps(forged),encoding="utf8")
    with pytest.raises(ValueError,match="retired or disabled"):
        lookup_mechanism(kind,signature,path=changed)


def invoke_mocked_consensus(tmp_path,monkeypatch,response):
    from selenium_pipeline import ai_academic_review_consensus as consensus
    file=plan(tmp_path,[task("consensus","g2_source_reconciliation",
                             {"queue_root":str(tmp_path/"q"),
                              "folder":str(tmp_path/"source")})])
    state=tmp_path/"state"
    monkeypatch.setenv("MICROGEN_V71_PINNED_EXECUTOR_SHA256",
                       executor._sha(Path(executor.__file__)))
    monkeypatch.setenv("MICROGEN_V71_PINNED_PLAN_SHA256",executor._sha(file))
    monkeypatch.setattr(consensus,"reconcile_actual_review_queue",
                        lambda **kwargs:response)
    exitcode=executor._worker(file,state,"consensus","consensus_token",ROOT)
    receipt=json.loads((state/"results"/"consensus_token.json").read_text())
    return exitcode,receipt


def test_consensus_preflight_requires_full_source_count_not_false_g2_acceptance(
        tmp_path,monkeypatch):
    good={"status":"INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE",
          "accepted_ai_evidence":[{},{}],"original_utterances":3,
          "pending_or_disputed":1,"student_publication_authorized":False}
    code,receipt=invoke_mocked_consensus(tmp_path,monkeypatch,good)
    assert code==0
    assert receipt["evidence"]["scientific_review_complete"] is False
    assert receipt["evidence"]["student_release"] is False
    assert receipt["evidence"]["no_provider_requests"] is True


@pytest.mark.parametrize("changed",[
    {"original_utterances":85},
    {"pending_or_disputed":-1},
    {"status":"G2_ACADEMIC_ACCEPTED"},
    {"student_publication_authorized":True},
])
def test_fake_g2_consensus_reports_are_never_accepted(tmp_path,monkeypatch,changed):
    fake={"status":"INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE",
          "accepted_ai_evidence":[{},{}],"original_utterances":3,
          "pending_or_disputed":1,"student_publication_authorized":False}
    fake.update(changed)
    code,receipt=invoke_mocked_consensus(tmp_path,monkeypatch,fake)
    assert code==1
    assert receipt["status"]=="failed"
    assert receipt["evidence"]["error_class"]=="ValueError"
