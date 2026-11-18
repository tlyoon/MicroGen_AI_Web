"""Safe original academic provider requalification before new unclaimed Sends."""
from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile
import unittest

from selenium_pipeline.academic_queue_fresh_send_health import (
    check, unreconciled_source_send_claims,
)

SHA="a"*64
FINGERPRINT="b"*64

class AcademicFreshReviewHealthTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.queue=self.root/"review_queue"
        self.queue.mkdir()
        self.checkpoint=self.queue/"slide_003_initial_review_attempt_01_request"
        self.clock=500000.

    def fake_claim(self, *, tamper=False, response=False):
        self.checkpoint.mkdir()
        state={
            "source_sha256":SHA,
            "request_fingerprint":FINGERPRINT,
            "status":"SUBMITTED_OR_UNCERTAIN",
            "submission_may_have_occurred":True,
            "can_auto_retry":False,
            "student_publication_authorized":False,
        }
        (self.checkpoint/"request_state.json").write_text(json.dumps(state))
        (self.checkpoint/"dispatch_attempted.claim").write_text(
            "c"*64 if tamper else FINGERPRINT)
        if response:
            (self.checkpoint/"model_response_untrusted.txt").write_text(
                '{"captured":true}')
        os.utime(self.checkpoint/"request_state.json",(self.clock-300,self.clock-300))

    def inspect(self, **kwargs):
        return check(queue_root=self.queue, checkpoint_parent=self.root,
                     source_sha=SHA,family="pro",
                     clock=lambda:self.clock,**kwargs)

    def test_no_source_uncertainty_allows_new_independent_unit_without_probe(self):
        out=self.inspect(
            execute_source_free_probe=False,
            probe_fn=lambda **k: self.fail("No canary needed"),
            latest_success_fn=lambda **k: None)
        self.assertTrue(out["new_source_review_send_allowed"])
        self.assertEqual(out["source_free_new_requests"],0)

    def test_unattributed_source_send_stops_new_pdf_before_probe(self):
        self.fake_claim()
        out=self.inspect(execute_source_free_probe=False,
                         latest_success_fn=lambda **k:None)
        self.assertEqual(out["status"],
                         "G2_FRESH_REVIEW_DEFERRED_PENDING_SOURCE_FREE_PROBE")
        self.assertFalse(out["new_source_review_send_allowed"])
        self.assertFalse(out["existing_claims_resent"])

    def test_healthy_post_claim_canary_reused_with_zero_new_request(self):
        self.fake_claim()
        def previous(**k):
            self.assertEqual(k["source_sha"],SHA)
            self.assertEqual(k["family"],"pro")
            self.assertEqual(k["after_unix"],self.clock-300)
            return {
                "status":"SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED",
                "source_sha256":SHA,"model_family":"pro",
                "observed_unix":self.clock-30,
            }
        out=self.inspect(execute_source_free_probe=False,
                         latest_success_fn=previous,
                         probe_fn=lambda **k:self.fail("Do not repeat prior canary"))
        self.assertEqual(out["status"],
                         "NEW_INDEPENDENT_SOURCE_FREE_RESPONSE_REVERIFIED")
        self.assertEqual(out["source_free_new_requests"],0)
        self.assertTrue(out["new_source_review_send_allowed"])

    def test_one_new_inert_canary_can_requalify_but_never_retry_source(self):
        self.fake_claim()
        calls=[]
        def probe(**k):
            calls.append(k)
            self.assertEqual(os.environ["MICROGEN_ACTIVE_GENERATION_STAGE"],
                             "academic_review")
            self.assertEqual(os.environ["MICROGEN_GEMINI_UI_MODE"],"pro")
            self.assertEqual(os.environ["MICROGEN_GEMINI_THINKING_LEVEL"],"medium")
            return {
                "status":"SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED",
                "source_sha256":SHA,
                "model_family":"pro",
                "observed_unix":self.clock-10,
                "no_original_source_uploaded":True,
                "gemini_new_user_turn_verified":True,
                "new_provider_requests":1,
            }
        with __import__("unittest.mock").mock.patch.dict(os.environ,{
                "MICROGEN_ACTIVE_GENERATION_STAGE":"narration",
                "MICROGEN_GEMINI_UI_MODE":"flash",
                "MICROGEN_GEMINI_THINKING_LEVEL":"high"}):
            out=self.inspect(execute_source_free_probe=True,
                             latest_success_fn=lambda **k:None,probe_fn=probe)
            self.assertEqual(os.environ["MICROGEN_ACTIVE_GENERATION_STAGE"],
                             "narration")
            self.assertEqual(os.environ["MICROGEN_GEMINI_UI_MODE"],"flash")
            self.assertEqual(os.environ["MICROGEN_GEMINI_THINKING_LEVEL"],"high")
        self.assertEqual(len(calls),1)
        self.assertTrue(out["new_source_review_send_allowed"])
        self.assertEqual(out["source_free_new_requests"],1)
        self.assertFalse(out["existing_claims_resent"])

    def test_no_response_health_probe_does_not_authorize_source_send(self):
        self.fake_claim()
        out=self.inspect(execute_source_free_probe=True,
                         latest_success_fn=lambda **k:None,
                         probe_fn=lambda **k:{
                             "status":"NO_VERIFIED_SOURCE_FREE_RESPONSE",
                             "source_sha256":SHA,"model_family":"pro",
                             "observed_unix":self.clock,
                             "new_provider_requests":1,
                             "no_original_source_uploaded":True,
                             "gemini_new_user_turn_verified":False})
        self.assertFalse(out["new_source_review_send_allowed"])
        self.assertEqual(out["status"],
                         "G2_FRESH_REVIEW_DEFERRED_UNHEALTHY_OR_UNATTRIBUTED")

    def test_tamper_and_saved_reply_require_separate_validation(self):
        self.fake_claim(tamper=True)
        with self.assertRaises(ValueError):
            self.inspect(execute_source_free_probe=False,
                         latest_success_fn=lambda **k:None)
        (self.checkpoint/"dispatch_attempted.claim").write_text(FINGERPRINT)
        (self.checkpoint/"model_response_untrusted.txt").write_text("late reply")
        with self.assertRaises(ValueError):
            self.inspect(execute_source_free_probe=False,
                         latest_success_fn=lambda **k:None)

    def test_future_response_proof_not_accepted(self):
        self.fake_claim()
        with self.assertRaises(ValueError):
            self.inspect(execute_source_free_probe=False,
                         latest_success_fn=lambda **k:{
                             "status":"SOURCE_FREE_ATTRIBUTABLE_RESPONSE_VERIFIED",
                             "source_sha256":SHA,"model_family":"pro",
                             "observed_unix":self.clock+10})


if __name__=="__main__":
    unittest.main()
