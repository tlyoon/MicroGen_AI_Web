"""Historical G2 owned source / claimed model request no-replay faults."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from selenium_pipeline.g2_owned_request_outcome_reconciliation_v1 import (
    reconcile, KIND, SIGNATURE, MECHANISM, STATUS,
)
from selenium_pipeline.development_g2g3_eligible_dispatch_v1 import (
    CONFIG_NAME, STATUS as BACKLOG_STATUS,
)
from selenium_pipeline.recovery_registry import lookup_mechanism


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def owned(tmp_path):
    original = tmp_path / "original_source"
    queue = tmp_path / "old_queue"
    quarantine = tmp_path / "old_capture"
    inbox = tmp_path / "offline_inbox"
    progress = tmp_path / "g3_progress.json"
    for p in (original, queue, quarantine, inbox):
        p.mkdir()
    for name in ("source.pdf", "slides.pdf", "script.txt"):
        (original / name).write_bytes(("ORIGINAL:" + name).encode())
    hashes = {name: sha(original / name)
              for name in ("source.pdf", "slides.pdf", "script.txt")}
    progress.write_text(json.dumps({
        "schema_version":1, "source_only_completed":True,
        "source_scientific_QA_complete":False,
        "independent_acoustic_QA_complete":False,
        "independent_video_highlight_QA_complete":False,
        "new_browser_sends":0,"new_paid_gemini_API_calls":0,
        "student_publication_authorized":False,
        "source_sections":{
            s:{"status":"SOURCE_SCOPE_COMPLETE","remaining":0}
            for s in ("Serway_8_2", "Serway_8_3")},
    }))
    jobs = []
    for slide, mode in ((3,"INITIAL_REVIEW"),
                        (4,"INDEPENDENT_CHALLENGE"),
                        (10,"INITIAL_REVIEW")):
        jobs.append({
            "slide":slide,"utterance_count":1,
            "original_source_sha256":hashes["source.pdf"],
            "original_slides_sha256":hashes["slides.pdf"],
            "original_script_sha256":hashes["script.txt"],
        })
        if slide == 4:
            (queue / "slide_004_initial_review.json").write_text(
                '{"one_pass":true}')
        stem = f"slide_{slide:03d}_{mode.lower()}"
        window = queue / (stem + "_attempt_01_request")
        window.mkdir()
        fingerprint = hashlib.sha256(stem.encode()).hexdigest()
        state = {
            "schema_version":1,"status":"SUBMITTED_OR_UNCERTAIN",
            "review_mode":mode,
            "request_fingerprint":fingerprint,
            "source_sha256":hashes["source.pdf"],
            "slides_sha256":hashes["slides.pdf"],
            "script_sha256":hashes["script.txt"],
            "submission_may_have_occurred":True,
            "student_publication_authorized":False,
        }
        (window / "request_state.json").write_text(json.dumps(state))
        (window / "dispatch_attempted.claim").write_text(fingerprint+"\n")
        if slide in (3,10):
            filename = f"gemini_20261115T07180{slide%10}Z_aabbccddeeff.raw.txt"
            raw = quarantine / filename
            raw.write_bytes(b"")
            meta = {
                "schema_version":1,"status":"incomplete_untrusted",
                "raw_filename":filename,"raw_sha256":sha(raw),
                "model_response_chars":0,
                "original_source_retry_authorized":False,
                "provider_server_outage_proven":False,
            }
            (quarantine / filename.replace(".raw.txt", ".meta.json")).write_text(
                json.dumps(meta))
            reason = "No stable JSON; untrusted response quarantined at "+str(raw)
        else:
            reason = "Original challenge reply missing; no stable capture"
        attempt = {
            "slide":slide,"mode":mode,"attempt":1,
            "status":"FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED",
            "provider_submission_state":"UNKNOWN_AFTER_POSSIBLE_SUBMISSION",
            "manual_retry_eligible":False,
            "reason":reason,
        }
        (queue / (stem + "_attempt_01.json")).write_text(json.dumps(attempt))
    q = {"original_source_folder":str(original),
         "provider_requests_performed":0,
         "student_publication_authorized":False,
         "slide_jobs":jobs}
    (queue / "queue.json").write_text(json.dumps(q))
    config = {
        "schema_version":1,"status":BACKLOG_STATUS,
        "g2_queue":str(queue),"g2_queue_sha256":sha(queue / "queue.json"),
        "g2_source":str(original),"g2_inputs_sha256":hashes,
        "g3_progress":str(progress),"g3_progress_sha256":sha(progress),
        "max_slides":8,"provider_requests_authorized":0,
        "student_publication_authorized":False,
    }
    backlog = inbox / CONFIG_NAME
    backlog.write_text(json.dumps(config))
    state = tmp_path / "receipt_state"
    return {"original_folder":original,"queue_root":queue,
            "quarantine_root":quarantine,"state_root":state,
            "source_backlog":backlog,"slides":[3,4,10]}


def test_registered_no_replay_mechanism():
    assert lookup_mechanism(KIND,SIGNATURE) == MECHANISM


def test_real_old_claims_zero_bytes_and_challenge_hold(owned):
    r = reconcile(**owned)
    assert r["status"] == STATUS
    assert r["new_browser_sends"] == 0
    assert r["new_paid_gemini_API_calls"] == 0
    assert r["independent_scientific_QA_complete"] is False
    assert r["dispositions"]["3"] == (
        "EMPTY_QUARANTINE_BUT_SEND_STILL_UNCERTAIN_NO_REPLAY")
    assert r["dispositions"]["10"] == r["dispositions"]["3"]
    assert r["dispositions"]["4"] == (
        "SUBMITTED_OR_UNCERTAIN_HISTORICAL_SEND_NO_REPLAY")
    report = json.loads(Path(r["receipt"]).read_text())
    assert len(report["slides"]) == 3
    assert report["slides"][0]["original_quarantine"]["raw_bytes"] == 0
    assert all(x["old_request_replay_authorized"] is False
               and x["fresh_model_send_authorized"] is False
               and x["accepted_scientific_review"] is False
               for x in report["slides"])


def test_restart_preserves_exact_immutable_receipt(owned):
    first = reconcile(**owned)
    path = Path(first["receipt"])
    content = path.read_bytes()
    again = reconcile(**owned)
    assert again == first
    assert path.read_bytes() == content
    assert len(list(path.parent.glob("*.json"))) == 1


@pytest.mark.parametrize("what", [
    "queue", "source.pdf", "slides.pdf", "script.txt", "g3_progress"])
def test_source_or_original_queue_drift_blocks_new_receipt(owned,what):
    config = json.loads(owned["source_backlog"].read_text())
    if what == "queue":
        path = owned["queue_root"] / "queue.json"
    elif what == "g3_progress":
        path = Path(config["g3_progress"])
    else:
        path = owned["original_folder"] / what
    with path.open("ab") as stream:
        stream.write(b" ")
    with pytest.raises(ValueError,match="identity changed"):
        reconcile(**owned)
    assert not owned["state_root"].exists()


@pytest.mark.parametrize("what", ["claim","request_state","attempt"])
def test_malformed_or_changed_original_ownership_blocks(owned,what):
    root = owned["queue_root"]
    stem = "slide_003_initial_review_attempt_01"
    if what == "attempt":
        path = root / (stem + ".json")
    else:
        path = root / (stem + "_request") / (
            "dispatch_attempted.claim" if what == "claim"
            else "request_state.json")
    path.write_bytes(b"invalid replacement")
    with pytest.raises((ValueError,json.JSONDecodeError)):
        reconcile(**owned)
    assert not owned["state_root"].exists()


def test_original_response_quarantine_tamper_can_never_be_accepted(owned):
    raw = next(owned["quarantine_root"].glob("*.raw.txt"))
    raw.write_bytes(b"model-like but not accepted")
    result = reconcile(**owned)
    saved = json.loads(Path(result["receipt"]).read_text())
    assert all(x["accepted_scientific_review"] is False for x in saved["slides"])
    assert all(x["old_request_replay_authorized"] is False for x in saved["slides"])
    assert all(x["fresh_model_send_authorized"] is False for x in saved["slides"])
    assert "EMPTY_QUARANTINE_BUT" not in result["dispositions"]["3"] or (
        "EMPTY_QUARANTINE_BUT" not in result["dispositions"]["10"])


def test_saved_disposition_change_detected(owned):
    r = reconcile(**owned)
    Path(r["receipt"]).write_text('{"forged":true}')
    with pytest.raises(ValueError,match="receipt was modified"):
        reconcile(**owned)


def test_unauthorized_queue_contract_never_runs(owned):
    config = json.loads(owned["source_backlog"].read_text())
    config["provider_requests_authorized"] = 1
    owned["source_backlog"].write_text(json.dumps(config))
    with pytest.raises(ValueError,match="unsafe"):
        reconcile(**owned)
    assert not owned["state_root"].exists()


def test_no_fabricated_fresh_send_from_missing_old_claim(owned):
    claim = owned["queue_root"] / (
        "slide_003_initial_review_attempt_01_request" /
        Path("dispatch_attempted.claim"))
    claim.unlink()
    with pytest.raises(ValueError,match="claim"):
        reconcile(**owned)


def test_no_implicit_new_mode_for_unreviewed_slide(owned):
    initial=owned["queue_root"] / "slide_004_initial_review.json"
    initial.unlink()
    with pytest.raises(ValueError,match="No attributable"):
        reconcile(**owned)


def _prepared_completed_handoff(owned):
    """Genuine v7.1 ledger+worker shape; fake source/checkpoint only."""
    from selenium_pipeline.development_continuity_executor_v71 import _plan
    config = json.loads(owned["source_backlog"].read_text())
    name = "next_g2_source_preflight_" + config["g2_queue_sha256"][:16]
    items = [{
        "id":f"g2_original_source_preflight_{slide:03d}",
        "workstream":"g2", "action":"g2_review_preflight",
        "params":{"queue_root":str(owned["queue_root"]),
                  "folder":str(owned["original_folder"]),
                  "slide":slide},
        "depends_on":[], "authorized":True, "max_attempts":1,
    } for slide in owned["slides"]]
    plan_path = owned["source_backlog"].parent / (name + ".json")
    plan_path.write_text(json.dumps({
        "schema_version":1,"project":"MicroGen_AI_Web",
        "tasks":items,
    }))
    _plan(plan_path)
    state = owned["state_root"]
    state.mkdir()
    ledger = {
        "schema_version":1,
        "status":"SOURCE_PINNED_GLOBAL_OFFLINE_HANDOFF",
        "plans":{name:{
            "sha256":sha(plan_path),"status":"VERIFIED_TASK_PLAN_COMPLETE",
            "project_complete":True,"worker_starts":len(items)}}}
    (state / "handoff_intake_v1.json").write_text(json.dumps(ledger))
    work = state / "handoffs" / name
    work.mkdir(parents=True)
    (work / "state.json").write_text(json.dumps({
        "project_complete":True,
        "tasks":{task["id"]:{"status":"passed"} for task in items},
    }))
    return name, plan_path, ledger, work


def test_daemon_bridge_actually_consumes_completed_owned_preflight(owned,monkeypatch):
    from selenium_pipeline.g2_owned_request_outcome_reconciliation_v1 import (
        auto_audit_completed_handoff)
    from selenium_pipeline import gemini_response_recovery
    monkeypatch.setattr(gemini_response_recovery,"default_quarantine_dir",
                        lambda:owned["quarantine_root"])
    _prepared_completed_handoff(owned)
    args={"handoff_dir":owned["source_backlog"].parent,
          "state_dir":owned["state_root"]}
    first=auto_audit_completed_handoff(**args)
    assert first["status"] == STATUS
    assert first["slides_inspected"] == owned["slides"]
    assert first["new_browser_sends"] == 0
    assert auto_audit_completed_handoff(**args) == first
    assert len(list((owned["state_root"] /
                     "g2_owned_no_replay_dispositions_v1").glob("*.json"))) == 1


def test_daemon_bridge_missing_finished_plan_waits_no_send(owned):
    from selenium_pipeline.g2_owned_request_outcome_reconciliation_v1 import (
        auto_audit_completed_handoff)
    r=auto_audit_completed_handoff(
        handoff_dir=owned["source_backlog"].parent,
        state_dir=owned["state_root"])
    assert r["status"] == "AWAIT_G2_SOURCE_PREFLIGHT_HANDOFF"
    assert r["new_browser_sends"] == 0


@pytest.mark.parametrize("fault",["changed_plan","failed_worker","old_ledger"])
def test_daemon_bridge_rejects_forged_completed_receipt(owned,fault,monkeypatch):
    from selenium_pipeline.g2_owned_request_outcome_reconciliation_v1 import (
        auto_audit_completed_handoff)
    from selenium_pipeline import gemini_response_recovery
    monkeypatch.setattr(gemini_response_recovery,"default_quarantine_dir",
                        lambda:owned["quarantine_root"])
    name,plan_path,ledger,work=_prepared_completed_handoff(owned)
    if fault=="changed_plan":
        plan_path.write_text('{"tampered":true}')
    elif fault=="failed_worker":
        checkpoint=json.loads((work / "state.json").read_text())
        checkpoint["tasks"]["g2_original_source_preflight_003"]["status"]="failed"
        (work / "state.json").write_text(json.dumps(checkpoint))
    else:
        ledger["plans"][name]["sha256"]="0"*64
        (owned["state_root"] / "handoff_intake_v1.json").write_text(
            json.dumps(ledger))
    with pytest.raises(ValueError):
        auto_audit_completed_handoff(
            handoff_dir=owned["source_backlog"].parent,
            state_dir=owned["state_root"])
    assert not (owned["state_root"] /
                "g2_owned_no_replay_dispositions_v1").exists()
