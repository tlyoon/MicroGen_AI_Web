"""Real production gate regression with synthetic Gemini transport, never API Sends."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import json
import os

from selenium_pipeline.series_gemini import OwnedGeminiResponse
from selenium_pipeline.academic_incident_response_health import (
    ROOT, incident_identity, latest_incident_success, probe_incident_once,
    verify_result, AcademicProbeError, MIN_PROBE_SPACING_SECONDS,
)
from selenium_pipeline.academic_queue_fresh_send_health import check

SOURCE = "a" * 64
FAMILY = "pro"
T = 1800000000.0


def reply(prompt, port):
    assert port == 9222
    assert "contains no lecture" in prompt
    expected = prompt[prompt.index('{"microgen_health":"ok"'):]
    return OwnedGeminiResponse(
        expected,
        registration_status="NEW_USER_TURN_AND_COMPOSER_CLEARED",
        new_turn_verified=True,
    )


class IncidentResponseHealthTests(TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.queue = self.root / "queue"
        self.queue.mkdir()
        env = patch.dict(os.environ, {
            "MICROGEN_ACTIVE_GENERATION_STAGE": "academic_review",
            "MICROGEN_GEMINI_UI_MODE": "pro",
            "MICROGEN_GEMINI_THINKING_LEVEL": "medium",
        })
        env.start()
        self.addCleanup(env.stop)
        self.claim = {
            "checkpoint_name": "slide_003_initial_review_attempt_01_request",
            "request_fingerprint": "b" * 64,
        }
        self.incident = incident_identity(
            self.claim, source_sha=SOURCE, family=FAMILY)

    def probe(self, when=T + 500, transport=reply, incident=None, after=T):
        return probe_incident_once(
            checkpoint_parent=self.root, source_sha=SOURCE,
            family=FAMILY, incident=incident or self.incident,
            after_unix=after, now=when, browser_request=transport)

    def history(self, incident=None, now=T + 4000, after=T):
        return latest_incident_success(
            checkpoint_parent=self.root, source_sha=SOURCE,
            family=FAMILY, incident=incident or self.incident,
            after_unix=after, now=now)

    def original(self, slide=3, when=T, fingerprint=None):
        name = f"slide_{slide:03d}_initial_review_attempt_01_request"
        path = self.queue / name
        path.mkdir()
        fp = fingerprint or (("b" if slide == 3 else "c") * 64)
        (path / "request_state.json").write_text(json.dumps({
            "source_sha256": SOURCE,
            "request_fingerprint": fp,
            "status": "SUBMITTED_OR_UNCERTAIN",
            "submission_may_have_occurred": True,
            "can_auto_retry": False,
            "student_publication_authorized": False,
        }))
        (path / "dispatch_attempted.claim").write_text(fp)
        os.utime(path / "request_state.json", (when, when))
        return path

    def test_real_owned_reply_persists_and_reuses_without_second_send(self):
        calls = []
        def transport(prompt, port):
            calls.append(prompt)
            return reply(prompt, port)
        first = self.probe(transport=transport)
        self.assertEqual(first["status"],
                         "SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED")
        self.assertEqual(len(calls), 1)
        saved = self.history()
        self.assertEqual(saved["claim_sha256"], first["claim_sha256"])
        second = self.probe(when=T + 600, transport=transport)
        self.assertEqual(second["new_provider_requests"], 0)
        self.assertEqual(second["status"], "SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED")
        self.assertTrue(second["reused_immutable_probe"])
        self.assertEqual(len(calls), 1)

    def test_failed_reply_is_not_reinterpreted_as_good_health(self):
        seen = []
        def failure(prompt, port):
            seen.append(prompt)
            raise TimeoutError("Gemini response capture unknown")
        self.assertEqual(self.probe(transport=failure)["status"],
                         "NO_VERIFIED_SOURCE_FREE_RESPONSE")
        self.assertIsNone(self.history())
        same = self.probe(when=T + 550, transport=failure)
        self.assertEqual(same["new_provider_requests"], 0)
        self.assertEqual(len(seen), 1)
        later = self.probe(
            when=T + 500 + MIN_PROBE_SPACING_SECONDS + 1,
            transport=reply)
        self.assertEqual(later["status"],
                         "SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED")
        self.assertIsNotNone(self.history())
        self.assertEqual(self.probe(when=T + 4000)["new_provider_requests"], 0)
        self.assertEqual(len(list((self.root / ROOT).rglob("claim.json"))), 2)

    def test_cross_incident_daily_budget_preserves_old_source_claim(self):
        old = self.original(slide=3, when=T)
        before = (old / "request_state.json").read_bytes()
        self.assertEqual(self.probe()["status"],
                         "SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED")
        new = self.original(slide=5, when=T + 1000)
        incident2 = incident_identity({
            "checkpoint_name": new.name,
            "request_fingerprint": "c" * 64,
        }, source_sha=SOURCE, family=FAMILY)
        second = self.probe(incident=incident2, after=T + 1000,
                            when=T + 1600)
        self.assertEqual(second["status"],
                         "SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED")
        incident3 = incident_identity({
            "checkpoint_name": "slide_007_initial_review_attempt_01_request",
            "request_fingerprint": "d" * 64,
        }, source_sha=SOURCE, family=FAMILY)
        third = self.probe(incident=incident3, after=T + 2000,
                           when=T + 3000)
        self.assertEqual(third["status"],
                         "INCIDENT_DAILY_DIAGNOSTIC_BUDGET_EXHAUSTED")
        self.assertEqual(third["new_provider_requests"], 0)
        self.assertEqual((old / "request_state.json").read_bytes(), before)
        self.assertEqual((old / "dispatch_attempted.claim").read_text(), "b"*64)

    def test_invalid_model_or_thinking_fails_before_claim(self):
        with patch.dict(os.environ, {"MICROGEN_GEMINI_UI_MODE": "flash"}):
            with self.assertRaises(AcademicProbeError):
                self.probe()
        with patch.dict(os.environ, {"MICROGEN_GEMINI_THINKING_LEVEL": "high"}):
            with self.assertRaises(AcademicProbeError):
                self.probe()
        self.assertEqual(list((self.root / ROOT).rglob("claim.json"))
                         if (self.root / ROOT).exists() else [], [])

    def test_tampered_persisted_response_fails_closed(self):
        self.probe()
        path = next((self.root / ROOT).rglob("result.json"))
        record = json.loads(path.read_text())
        record["response_text"] = '{"microgen_health":"ok","nonce":"forged"}'
        path.write_text(json.dumps(record))
        with self.assertRaises(AcademicProbeError):
            self.history()

    def test_missing_result_claim_is_never_replayed(self):
        self.probe()
        slot = next((self.root / ROOT).rglob("result.json"))
        slot.unlink()  # emulate loss/crash after a genuine browser submission
        self.assertIsNone(self.history())
        again = self.probe(when=T + 550)
        self.assertEqual(again["new_provider_requests"], 0)
        next_attempt = self.probe(when=T + 1700)
        self.assertEqual(next_attempt["status"],
                         "SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED")
        self.assertEqual(len(list((self.root / ROOT).rglob("claim.json"))), 2)

    def test_later_claim_never_uses_prior_incident_health_proof(self):
        self.original(slide=3, when=T)
        self.probe(when=T + 500)
        self.original(slide=5, when=T + 700)
        # Read-only G2 check must refuse the existing proof, which predates
        # the newest distinct academic Send.
        result = check(
            queue_root=self.queue, checkpoint_parent=self.root,
            source_sha=SOURCE, family="pro",
            execute_source_free_probe=False, clock=lambda: T + 1000,
            latest_success_fn=lambda **k: None)
        self.assertFalse(result["new_source_review_send_allowed"])
        self.assertEqual(result["original_unattributed_requests"], 2)

    def test_normal_g2_check_requalifies_only_new_incident_and_resumes(self):
        original = self.original(slide=3, when=T)
        prior_bytes = (original / "request_state.json").read_bytes()
        # An immutable legacy daily diagnostic now predates this later
        # uncertain source request. Mock only the legacy lookup/reuse.
        from selenium_pipeline import academic_provider_requalification as legacy
        with patch.object(legacy, "probe_once", return_value={
            "status": "SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED",
            "reused_immutable_probe": True, "source_sha256": SOURCE,
            "model_family": "pro", "observed_unix": T - 30,
            "no_original_source_uploaded": True,
            "gemini_new_user_turn_verified": True,
            "new_provider_requests": 0,
        }), patch(
            "selenium_pipeline.academic_incident_response_health."
            "probe_incident_once",
            side_effect=lambda **k: probe_incident_once(
                **k, browser_request=reply)):
            approved = check(
                queue_root=self.queue, checkpoint_parent=self.root,
                source_sha=SOURCE, family="pro",
                execute_source_free_probe=True, clock=lambda: T + 500,
                latest_success_fn=lambda **k: None)
        self.assertTrue(approved["new_source_review_send_allowed"])
        self.assertEqual(approved["health_proof_scope"],
                         "LATEST_UNCERTAIN_SOURCE_INCIDENT")
        self.assertEqual(approved["source_free_new_requests"], 1)
        self.assertEqual((original / "request_state.json").read_bytes(), prior_bytes)
        restarted = check(
            queue_root=self.queue, checkpoint_parent=self.root,
            source_sha=SOURCE, family="pro",
            execute_source_free_probe=False, clock=lambda: T + 600,
            latest_success_fn=lambda **k: None)
        self.assertTrue(restarted["new_source_review_send_allowed"])
        self.assertEqual(restarted["source_free_new_requests"], 0)
        self.assertEqual(restarted["status"],
                         "NEW_INCIDENT_SOURCE_FREE_RESPONSE_REVERIFIED")


if __name__ == "__main__":
    import unittest
    unittest.main()
