"""One-use, forensic-bound academic review: never silently repeat a send."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from selenium_pipeline.original_slide4_reconciled_once import (
    APPROVAL, execute_one_reconciled_initial_review, _write_new,
)


class OneUseSourceReviewWindow(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.base=Path(self.temp.name)
        self.original=self.base/"original"
        self.original.mkdir()
        self.queue=self.base/"history"
        self.queue.mkdir()
        self.forensic=self.base/"forensic.json"
        self.intent=self.base/"intent.json"
        self.proof={"source_sha256":"f"*64,"original_utterance_count":5}
        self.job={
            "status":"SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED",
            "utterance_count":5,
            "slides":[{"slide":4,"utterances":[
                {"id":f"s004.utterance.{i:03d}","spoken_sha256":f"{i:064x}"}
                for i in range(1,6)]}]
        }
        self.calls=0

    def tearDown(self):
        self.temp.cleanup()

    def execute(self,handler=None,approval=APPROVAL):
        window=self.base/"one-time-window"
        def deliver(*,folder,job,mode,transport,response_observer):
            self.calls+=1
            if handler is not None:
                return handler(response_observer)
            response_observer('{"status":"answer"}')
            return {"status":"SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS",
                    "mode":"INITIAL_REVIEW","review_count":5,
                    "student_publication_authorized":False}
        with patch(
            "selenium_pipeline.original_slide4_reconciled_once.reconcile_original_slide4",
            side_effect=lambda **kwargs: dict(self.proof)
        ), patch(
            "selenium_pipeline.original_slide4_reconciled_once.build_review_job",
            return_value=self.job
        ), patch(
            "selenium_pipeline.original_slide4_reconciled_once.run_web_review",
            side_effect=deliver
        ), patch(
            "selenium_pipeline.original_slide4_reconciled_once._independently_check_saved_pass",
            return_value=[]
        ):
            return execute_one_reconciled_initial_review(
                folder=self.original,queue_root=self.queue,
                forensic_path=self.forensic,intent_path=self.intent,
                window_root=window,approval_reference=approval)

    def test_one_valid_first_pass_is_not_independent_agreement(self):
        result=self.execute()
        self.assertEqual(result["original_utterances_reviewed"],5)
        self.assertEqual(self.calls,1)
        self.assertFalse(result["mathematics_independently_approved"])
        self.assertTrue((self.base/"one-time-window"/"possible_submission_intent.json").is_file())
        self.assertTrue((self.base/"one-time-window"/"original_slide4_first_pass_candidate.json").is_file())

    def test_second_request_fails_before_provider_callback(self):
        self.execute()
        with self.assertRaises(ValueError):
            self.execute()
        self.assertEqual(self.calls,1)

    def test_wrong_owner_scope_fails_before_creating_window(self):
        with self.assertRaises(ValueError):
            self.execute(approval="other")
        self.assertEqual(self.calls,0)
        self.assertFalse((self.base/"one-time-window").exists())

    def test_after_possible_send_exception_quarantined_and_not_retryable(self):
        def ambiguous(witness):
            raise ConnectionError("Provider response unavailable after possible send")
        r=self.execute(handler=ambiguous)
        self.assertEqual(r["provider_submission_state"],
                         "UNKNOWN_AFTER_POSSIBLE_SUBMISSION")
        self.assertEqual(r["new_attempts_remaining_in_this_window"],0)
        self.assertTrue(r["requires_owner_reconciliation"])
        self.assertFalse((self.base/"one-time-window"/"original_slide4_first_pass_candidate.json").exists())
        with self.assertRaises(ValueError):
            self.execute()
        self.assertEqual(self.calls,1)

    def test_unusable_return_is_quarantined_without_auto_retry(self):
        def invalid(witness):
            witness("present but invalid JSON")
            raise RuntimeError("Invalid JSON")
        r=self.execute(handler=invalid)
        self.assertEqual(r["provider_submission_state"],"RETURNED_RESPONSE_INVALID")
        self.assertEqual(self.calls,1)
        self.assertTrue((self.base/"one-time-window"/"quarantined_outcome.json").is_file())

    def test_source_evidence_drift_aborts_no_success(self):
        def drifting(witness):
            witness("one response")
            self.proof["source_sha256"]="changed"
            return {"status":"SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS",
                    "review_count":5,"mode":"INITIAL_REVIEW"}
        r=self.execute(handler=drifting)
        self.assertEqual(r["status"],"NEW_SCOPED_INITIAL_REVIEW_FAILURE_QUARANTINED")
        self.assertEqual(self.calls,1)


if __name__=="__main__":
    unittest.main()
