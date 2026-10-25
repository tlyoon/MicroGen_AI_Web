"""No new Gemini send on ambiguous original academic request receipts."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from selenium_pipeline.gemini_model import GeminiModelError

from selenium_pipeline.ai_academic_review_queue import execute_one_review
from selenium_pipeline.review_retry_plan import plan_manual_review_attempt
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_ai_academic_review_queue import ReviewQueue


class OriginalReviewAmbiguousSubmission(unittest.TestCase):
    def test_after_send_transport_uncertainty_blocks_next_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            source,queue=ReviewQueue().setup(d)
            calls=[]
            def interrupted(*args):
                calls.append("sent_or_unknown")
                raise RuntimeError("Connection lost after possible provider submission")
            fail=execute_one_review(
                queue_root=queue,folder=source,slide=1,
                mode="INITIAL_REVIEW",transport=interrupted)
            self.assertEqual(calls,["sent_or_unknown"])
            self.assertEqual(fail["provider_submission_state"],
                             "UNKNOWN_AFTER_POSSIBLE_SUBMISSION")
            self.assertTrue(fail["requires_owner_reconciliation"])
            self.assertFalse(fail["manual_retry_eligible"])
            planned=plan_manual_review_attempt(
                queue,slide=1,mode="INITIAL_REVIEW")
            self.assertEqual(planned["status"],
                             "BLOCKED_AMBIGUOUS_PROVIDER_REQUEST_NEEDS_RECONCILIATION")
            self.assertIsNone(planned["next_possible_attempt"])
            with self.assertRaises(FigureIdentityReviewRequired):
                execute_one_review(queue_root=queue,folder=source,slide=1,
                    mode="INITIAL_REVIEW",attempt=2,
                    transport=lambda *_:self.fail("DUPLICATE_PROVIDER_SEND"))
            self.assertFalse((queue/"slide_001_initial_review_attempt_02.json").exists())

    def test_returned_invalid_text_is_distinct_confirmed_terminal_failure(self):
        with tempfile.TemporaryDirectory() as d:
            source,queue=ReviewQueue().setup(d)
            got=execute_one_review(queue_root=queue,folder=source,slide=1,
                mode="INITIAL_REVIEW",
                transport=lambda *_:"Gemini said: completed unusable response")
            self.assertEqual(got["provider_submission_state"],
                             "RETURNED_RESPONSE_INVALID")
            self.assertTrue(got["manual_retry_eligible"])
            self.assertFalse(got["requires_owner_reconciliation"])
            planned=plan_manual_review_attempt(queue,slide=1,mode="INITIAL_REVIEW")
            self.assertEqual(planned["status"],
                             "EXPLICIT_MANUAL_RETRY_DECISION_REQUIRED")
            self.assertEqual(planned["next_possible_attempt"],2)
            self.assertFalse(planned["dispatch_authorized"])

    def test_confirmed_browser_model_error_before_send_allows_explicit_retry_only(self):
        with tempfile.TemporaryDirectory() as d:
            source,queue=ReviewQueue().setup(d)
            with patch(
                "selenium_pipeline.ai_academic_review_queue.run_web_review",
                side_effect=GeminiModelError(
                    "Model selection not confirmed for flash; UI reports Flash-Lite"),
            ):
                failure=execute_one_review(
                    queue_root=queue,folder=source,slide=1,mode="INITIAL_REVIEW")
            self.assertEqual(failure["provider_submission_state"],
                             "CONFIRMED_PRE_SUBMISSION_MODEL_SELECTION_FAILURE")
            self.assertTrue(failure["manual_retry_eligible"])
            self.assertFalse(failure["requires_owner_reconciliation"])
            planned=plan_manual_review_attempt(
                queue,slide=1,mode="INITIAL_REVIEW")
            self.assertEqual(planned["status"],
                             "EXPLICIT_MANUAL_RETRY_DECISION_REQUIRED")
            self.assertEqual(planned["next_possible_attempt"],2)
            self.assertFalse(planned["dispatch_authorized"])

    def test_injected_model_exception_is_not_proof_of_unsent_request(self):
        with tempfile.TemporaryDirectory() as d:
            source,queue=ReviewQueue().setup(d)
            fail=execute_one_review(
                queue_root=queue,folder=source,slide=1,mode="INITIAL_REVIEW",
                transport=lambda *_: (_ for _ in ()).throw(
                    GeminiModelError("Untrusted transport raised model error")))
            self.assertEqual(fail["provider_submission_state"],
                             "UNKNOWN_AFTER_POSSIBLE_SUBMISSION")
            self.assertFalse(fail["manual_retry_eligible"])

    def test_legacy_failure_receipt_is_not_evidence_of_unsent_request(self):
        with tempfile.TemporaryDirectory() as d:
            source,queue=ReviewQueue().setup(d)
            old=queue/"slide_001_initial_review_attempt_01.json"
            old.write_text(json.dumps({
                "status":"FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED",
                "slide":1,"mode":"INITIAL_REVIEW","attempt":1,
                "error_type":"RuntimeError","reason":"old generic timeout",
            }))
            report=plan_manual_review_attempt(queue,slide=1,mode="INITIAL_REVIEW")
            self.assertEqual(report["status"],
                             "BLOCKED_AMBIGUOUS_PROVIDER_REQUEST_NEEDS_RECONCILIATION")
            self.assertIsNone(report["next_possible_attempt"])
            with self.assertRaises(FigureIdentityReviewRequired):
                execute_one_review(queue_root=queue,folder=source,slide=1,
                    mode="INITIAL_REVIEW",attempt=2,
                    transport=lambda *_:self.fail("LEGACY_DUPLICATE_SEND"))


if __name__=="__main__":
    unittest.main()
