"""Source- and retry-bound Gemini recovery controller fault injection."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from selenium_pipeline.gemini_failure_auto_recovery_v1 import (
    KIND, SIGNATURE, REPAIR, decide, persist, request_identity,
    handle_failed_request,
)
from selenium_pipeline.gemini_response_recovery import quarantine_snapshot
from selenium_pipeline.recovery_registry import lookup_mechanism


def test_controller_is_executable_registry_mechanism():
    assert lookup_mechanism(KIND, SIGNATURE) == REPAIR


def test_same_source_and_prompt_identity_reused_not_paths(tmp_path):
    pdf = tmp_path / "original_source.pdf"
    pdf.write_bytes(b"%PDF-1.4 Original textbook fixture A")
    first = request_identity("Review original proof", [pdf])
    assert first["source_identity_verified"]
    assert first == request_identity("Review original proof", [pdf])
    assert str(pdf) not in json.dumps(first)
    pdf.write_bytes(b"%PDF-1.4 Different textbook")
    changed = request_identity("Review original proof", [pdf])
    assert changed["request_sha256"] != first["request_sha256"]
    assert request_identity("Different review", [pdf])["request_sha256"] != changed["request_sha256"]


@pytest.mark.parametrize("possible_send,verified,phase,expected", [
    (False, False, "GEMINI_COMPOSER_OR_SEND_CONTROL_NOT_READY",
     "REQUALIFY_PRESEND_FOR_FUTURE_DISTINCT_WORK_ONLY"),
    (False, False, "AUTHENTICATION_OR_BROWSER_VERIFICATION_REQUIRED",
     "HOLD_FOR_AUTHENTICATED_OWNED_SESSION_NO_SEND"),
    (True, False, "OWNED_SEND_NOT_CONFIRMED",
     "QUARANTINE_UNKNOWN_SEND_ADVANCE_INDEPENDENT_WORK"),
    (True, True, "REGISTERED_SEND_GENERATION_STALLED_ZERO_MODEL_TEXT",
     "OBSERVE_ORIGINAL_OWNED_CONVERSATION_ONLY_NO_REPLAY"),
])
def test_no_automatic_provider_resend_in_any_transport_state(
        possible_send, verified, phase, expected):
    answer = decide(
        phase=phase, possible_send=possible_send,
        new_turn_verified=verified, attempts_used=3)
    assert answer["action"] == expected
    assert answer["new_provider_requests"] == 0
    assert answer["automatic_same_request_retry_authorized"] is False
    assert answer["paid_api_fallback_authorized"] is False
    assert answer["academic_scientific_acceptance"] is False
    assert answer["student_publication_authorized"] is False


def test_empty_valid_capture_is_not_provider_failure_proof(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    original = "Original source review request"
    raw_dir = tmp_path / "Microvid" / "gemini_quarantine"
    artifact = quarantine_snapshot(
        {"text": "", "capture_status": "empty_model_response",
         "generating": False},
        directory=raw_dir)
    result = handle_failed_request(
        instruction=original, attachments=[],
        phase="OWNED_RESPONSE_UNVERIFIED_QUARANTINED",
        possible_send=True, new_turn_verified=True,
        attempts_used=1, stage="academic_review", port=9222,
        quarantine_path=artifact["raw_path"],
        pre_send_request_sha256=request_identity(original, [])["request_sha256"])
    assert result["action"] == "PRESERVE_EMPTY_CAPTURE_ADVANCE_INDEPENDENT_WORK"
    assert result["retry_authorized"] is False
    record = json.loads(Path(result["receipt"]).read_text())
    assert record["quarantine_capture_status"] == (
        "EMPTY_ORIGINAL_CAPTURE_VERIFIED_NO_REPLAY")
    assert record["possible_provider_submission"] is True
    assert record["new_provider_requests"] == 0
    assert original not in json.dumps(record)
    repeated = handle_failed_request(
        instruction=original, attachments=[],
        phase="OWNED_RESPONSE_UNVERIFIED_QUARANTINED",
        possible_send=True, new_turn_verified=True, attempts_used=1,
        stage="academic_review", port=9222,
        quarantine_path=artifact["raw_path"],
        pre_send_request_sha256=request_identity(original, [])["request_sha256"])
    assert repeated["receipt"] == result["receipt"]


def test_source_absent_forces_hold_even_before_send(tmp_path):
    missing = tmp_path / "not-attached.pdf"
    got = handle_failed_request(
        instruction="Original", attachments=[missing],
        phase="GEMINI_BROWSER_OR_WEBDRIVER_NOT_READY",
        possible_send=False, new_turn_verified=False, attempts_used=2,
        stage="figures", port=9222, root=tmp_path / "checkpoint")
    record = json.loads(Path(got["receipt"]).read_text())
    assert record["source_identity_verified"] is False
    assert got["action"] == "HOLD_UNVERIFIED_SOURCE_IDENTITY_NO_REPLAY"
    assert got["new_provider_requests"] == 0


def test_untrusted_quarantine_from_another_root_does_not_authorize_send(
        tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "configured"))
    foreign = tmp_path / "elsewhere"
    raw = quarantine_snapshot(
        {"text": "bad JSON", "capture_status": "visible_model_response",
         "generating": False},
        directory=foreign)["raw_path"]
    got = handle_failed_request(
        instruction="Original", attachments=[],
        phase="OWNED_RESPONSE_UNVERIFIED_QUARANTINED",
        possible_send=True, new_turn_verified=False,
        attempts_used=1, stage="rich_mapping", port=9222,
        quarantine_path=raw,
        pre_send_request_sha256=request_identity("Original", [])["request_sha256"])
    record = json.loads(Path(got["receipt"]).read_text())
    assert record["quarantine_capture_status"] == "UNVERIFIED_QUARANTINE_NO_REPLAY"
    assert got["action"] == "QUARANTINE_UNKNOWN_SEND_ADVANCE_INDEPENDENT_WORK"


def test_tampered_recovery_decision_rejected(tmp_path):
    receipt = decide(phase="OWNED_SEND_NOT_CONFIRMED",
                     possible_send=True, new_turn_verified=False)
    receipt["automatic_same_request_retry_authorized"] = True
    with pytest.raises(ValueError, match="changed"):
        persist(decision=receipt, request_sha256="a" * 64,
                stage="academic_review", port=9222, root=tmp_path)


def test_crash_recovery_and_original_receipt_tamper(tmp_path):
    decision = decide(phase="OWNED_SEND_NOT_CONFIRMED",
                      possible_send=True, new_turn_verified=False)
    args = dict(decision=decision, request_sha256="a" * 64,
                stage="academic_review", port=9222, root=tmp_path)
    file = persist(**args)
    stage = file.with_suffix(".stage")
    file.rename(stage)
    assert persist(**args) == file
    assert file.exists() and not stage.exists()
    file.write_text('{"student_publication_authorized": true}')
    with pytest.raises(ValueError, match="mutated"):
        persist(**args)


@pytest.mark.parametrize("kwargs", [
    {"possible_send": "yes", "new_turn_verified": False},
    {"possible_send": True, "new_turn_verified": "false"},
    {"possible_send": True, "new_turn_verified": False, "attempts_used": 400},
])
def test_forged_state_never_creates_decision(kwargs):
    props = dict(phase="OWNED_SEND_NOT_CONFIRMED", possible_send=False,
                 new_turn_verified=False)
    props.update(kwargs)
    with pytest.raises(ValueError):
        decide(**props)


def test_normal_shared_selenium_error_path_creates_receipt(tmp_path, monkeypatch):
    """Actual _browser_request pre-Send failure, no browser and no Send."""
    from selenium_pipeline import series_gemini
    from selenium_pipeline.gemini_selenium_only_policy import (
        GeminiSeleniumTemporaryFailure)

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("MICROGEN_ACTIVE_GENERATION_STAGE", "academic_review")
    class Vendor:
        class Config:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
        class GeminiSeleniumClient:
            def __init__(self, config):
                self.config = config
            def start(self, **kwargs):
                raise ConnectionError("Original browser session not available")
            def shutdown(self):
                return None
    monkeypatch.setattr(series_gemini, "_vendor_module", lambda: Vendor)
    with pytest.raises(GeminiSeleniumTemporaryFailure) as captured:
        series_gemini._browser_request(
            "Academic source-grounded prompt", [], port=9222, wait_cap_s=5)
    error = captured.value
    assert error.gemini_send_boundary_entered is False
    assert error.gemini_recovery_action == (
        "REQUALIFY_PRESEND_FOR_FUTURE_DISTINCT_WORK_ONLY")
    saved = json.loads(Path(error.gemini_recovery_receipt).read_text())
    assert saved["possible_provider_submission"] is False
    assert saved["new_provider_requests"] == 0
    assert saved["student_publication_authorized"] is False


def test_shared_transport_ambiguous_click_records_hold_without_second_send(
        tmp_path, monkeypatch):
    """Fault-inject ambiguous click in the REAL _browser_request control flow."""
    from selenium_pipeline import series_gemini
    from selenium_pipeline import gemini_model
    from selenium_pipeline import gemini_stage_policy
    from selenium_pipeline import gemini_selenium_only_policy as policy
    from selenium_pipeline import gemini_owned_network_diagnostics as network
    from selenium_pipeline import gemini_request_cost as costs

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("MICROGEN_ACTIVE_GENERATION_STAGE", "rich_mapping")
    monkeypatch.setenv("MICROGEN_GEMINI_UI_MODE", "flash-lite")

    class Driver:
        current_window_handle = "owned"
        current_url = "https://gemini.google.com/app/abc"
    class Client:
        driver = Driver()
        _automation_tab = "owned"
        def shutdown(self):
            pass
    class Vendor:
        class Config:
            def __init__(self, **kwargs):
                pass
        GeminiSeleniumClient = Client
    client = Client()
    monkeypatch.setattr(series_gemini, "_vendor_module", lambda: Vendor)
    monkeypatch.setattr(policy, "prepare_with_bounded_retries",
                        lambda **kwargs: client)
    monkeypatch.setattr(policy, "owned_gemini_send_baseline",
                        lambda *args: {"status": "ready"})
    monkeypatch.setattr(gemini_model, "configured_ui_mode", lambda: "flash-lite")
    monkeypatch.setattr(gemini_model, "assert_owned_gemini_mode",
                        lambda *args, **kwargs: "flash-lite")
    monkeypatch.setattr(gemini_stage_policy, "browser_stage_needs_thinking",
                        lambda **kwargs: False)
    monkeypatch.setattr(network, "arm_owned_network_baseline",
                        lambda *args: {})
    monkeypatch.setattr(costs, "browser_begin",
                        lambda *args, **kwargs: None)
    clicks = []
    def ambiguous_click(*args):
        clicks.append(1)
        raise ConnectionError("Connection closed during original Send click")
    monkeypatch.setattr(policy, "click_one_owned_gemini_send",
                        ambiguous_click)
    with pytest.raises(ConnectionError) as caught:
        series_gemini._browser_request(
            "Original textbook-grounded mapping claim",
            [], port=9222, wait_cap_s=5)
    error = caught.value
    assert len(clicks) == 1
    assert error.gemini_send_boundary_entered is True
    assert error.gemini_recovery_action == (
        "QUARANTINE_UNKNOWN_SEND_ADVANCE_INDEPENDENT_WORK")
    record = json.loads(Path(error.gemini_recovery_receipt).read_text())
    assert record["possible_provider_submission"] is True
    assert record["original_new_user_turn_verified"] is False
    assert record["automatic_same_request_retry_authorized"] is False
    assert record["paid_api_fallback_authorized"] is False
    assert record["new_provider_requests"] == 0


def test_source_changed_during_possible_send_cannot_be_misattributed(tmp_path):
    """Original byte identity is witnessed before Send, then checked again."""
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-1.4 original A")
    prior = request_identity("Original request", [source])["request_sha256"]
    source.write_bytes(b"%PDF-1.4 replaced B")
    got = handle_failed_request(
        instruction="Original request", attachments=[source],
        phase="OWNED_RESPONSE_UNVERIFIED_QUARANTINED",
        possible_send=True, new_turn_verified=True, attempts_used=1,
        stage="academic_review", port=9222, root=tmp_path / "receipts",
        pre_send_request_sha256=prior)
    record = json.loads(Path(got["receipt"]).read_text())
    assert got["action"] == "HOLD_UNVERIFIED_SOURCE_IDENTITY_NO_REPLAY"
    assert record["source_identity_verified"] is False
    assert record["new_provider_requests"] == 0
    assert not record["automatic_same_request_retry_authorized"]


def test_uncertain_send_without_presend_input_witness_fails_closed(tmp_path):
    got = handle_failed_request(
        instruction="Original", attachments=[],
        phase="OWNED_SEND_NOT_CONFIRMED",
        possible_send=True, new_turn_verified=False, attempts_used=0,
        stage="rich_mapping", port=9222, root=tmp_path)
    record = json.loads(Path(got["receipt"]).read_text())
    assert record["source_identity_verified"] is False
    assert got["action"] == "HOLD_UNVERIFIED_SOURCE_IDENTITY_NO_REPLAY"
