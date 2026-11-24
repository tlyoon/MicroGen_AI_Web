"""A new uncertain science Send invalidates older source-free health."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from selenium_pipeline import g3_browser_post_send_health_gate_v1 as gate
from selenium_pipeline.recovery_registry import lookup_mechanism


S="a"*64


def _task(root:Path,section="Serway_8_3",sha=S,
          kind="g3_prepass_source_gap_repair_v2",
          model="new_scientific_source_review_job",scope="b"*64):
    target=root/kind/section
    target.mkdir(parents=True,exist_ok=True)
    (target/(scope+".json")).write_text(json.dumps({
        "scope_sha256":scope,
        model:{"source_sha256":sha},
        "status":"G3_REPAIRED_SOURCE_CLAIM_REQUIRES_TWO_PASS_SCIENCE_NO_SEND",
    }))
    return scope


def _claim(root:Path,scope:str,
           review="g3_prepass_source_science_reviews_v1",
           phase="initial_request",status="SUBMITTED_OR_UNCERTAIN",
           observed=False):
    home=root/review/scope/phase
    home.mkdir(parents=True,exist_ok=True)
    (home/"request_state.json").write_text(json.dumps({
        "schema_version":1,
        "status":status,
        "request_fingerprint":"f"*64,
    }))
    if observed:
        (home/"model_response_identity.json").write_text('{"saved":true}')
    return home


def test_executable_post_send_health_gate_registered():
    assert lookup_mechanism(gate.KIND,gate.SIGNATURE)==gate.MECHANISM


def test_uncertain_prepass_send_makes_prior_health_stale(tmp_path):
    scope=_task(tmp_path)
    claim=_claim(tmp_path,scope)
    incident=gate.latest_unresolved_incident(
        state_root=tmp_path,section="Serway_8_3",source_sha256=S)
    assert incident>=claim.stat().st_mtime-0.1
    valid={"status":"G3_SOURCE_FREE_NEON_HIGH_HEALTH_VERIFIED",
           "fresh_neon_high_source_free_health":True,
           "observed_unix":incident+1}
    assert gate.receipt_is_fresher(
        receipt=valid,incident_unix=incident) is True
    valid["observed_unix"]=incident-1
    assert gate.receipt_is_fresher(
        receipt=valid,incident_unix=incident) is False
    assert gate.receipt_is_fresher(
        receipt=None,incident_unix=incident) is False


def test_source_scopes_isolated_between_two_textbooks(tmp_path):
    scope=_task(tmp_path,section="Serway_8_3")
    _claim(tmp_path,scope)
    assert gate.latest_unresolved_incident(
        state_root=tmp_path,section="Serway_8_2",
        source_sha256=S)==0
    assert gate.latest_unresolved_incident(
        state_root=tmp_path,section="Serway_8_3",
        source_sha256=S)>0


@pytest.mark.parametrize("status",[
    "SUBMITTED_OR_UNCERTAIN",
    "NO_RESPONSE_UNRESOLVED",
    "LEGACY_SENT_NO_RESPONSE",
])
def test_source_science_unknown_send_status_needs_new_health(tmp_path,status):
    scope=_task(tmp_path)
    _claim(tmp_path,scope,status=status)
    assert gate.latest_unresolved_incident(
        state_root=tmp_path,section="Serway_8_3",
        source_sha256=S)>0


def test_existing_owned_model_response_can_be_reconciled_without_new_health(
        tmp_path):
    scope=_task(tmp_path)
    _claim(tmp_path,scope,observed=True)
    assert gate.latest_unresolved_incident(
        state_root=tmp_path,section="Serway_8_3",
        source_sha256=S)==0


def test_original_academic_evidence_without_send_is_not_outage(tmp_path):
    scope=_task(tmp_path)
    _claim(tmp_path,scope,status="SOURCE_VALIDATED_ONE_PASS_UNAPPROVED")
    assert gate.latest_unresolved_incident(
        state_root=tmp_path,section="Serway_8_3",
        source_sha256=S)==0


def test_damaged_g3_academic_claim_fail_closed(tmp_path):
    scope=_task(tmp_path)
    claim=tmp_path/"g3_prepass_source_science_reviews_v1"/scope/"initial_request"
    claim.mkdir(parents=True,exist_ok=True)
    assert gate.latest_unresolved_incident(
        state_root=tmp_path,section="Serway_8_3",
        source_sha256=S)>0


def test_changed_claim_source_sha_rejected(tmp_path):
    scope=_task(tmp_path,sha="b"*64)
    _claim(tmp_path,scope)
    with pytest.raises(ValueError,match="changed source identity"):
        gate.latest_unresolved_incident(
            state_root=tmp_path,section="Serway_8_3",
            source_sha256=S)


def test_receipt_not_authenticated_neon_high_fails(tmp_path):
    assert gate.receipt_is_fresher(
        receipt={"status":"CHANGED_MODEL","observed_unix":900,
                 "fresh_neon_high_source_free_health":True},
        incident_unix=100) is False
