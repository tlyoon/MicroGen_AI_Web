"""Guard original review eligibility without authorizing provider dispatch."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.source_review_eligibility_preflight import (
    inspect_original_review_eligibility,
)
from selenium_pipeline.figure_source_identity import _sha
from test_review_retry_plan import ManualRetry


class OriginalReviewScope(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.queue = ManualRetry().make(self.temp.name)
        self.original = Path(self.temp.name) / "source"

    def run_preflight(self):
        job = {"utterance_count":1,
               "source_sha256":_sha(self.original/"source.pdf"),
               "slides_sha256":_sha(self.original/"slides.pdf"),
               "script_sha256":_sha(self.original/"script.txt")}
        with patch("selenium_pipeline.source_review_eligibility_preflight."
                   "build_review_job", return_value=job):
            return inspect_original_review_eligibility(
                folder=self.original, queue_root=self.queue, slide=1)

    def test_new_original_first_review_has_no_scope_authority(self):
        before={p.name:p.read_bytes() for p in self.queue.iterdir()}
        r=self.run_preflight()
        self.assertEqual(r["suggested_next_stage"],"INITIAL_REVIEW")
        self.assertEqual(r["planning_result"],
                         "NO_PENDING_RECEIPT_BUT_SCOPED_CONSENT_NOT_PROVEN")
        self.assertFalse(r["new_slide_specific_consent_verified"])
        self.assertFalse(r["review_model_request_sent"])
        self.assertFalse(r["automatic_retry_authorized"])
        self.assertFalse(r["student_publication_authorized"])
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.queue.iterdir()})

    def test_ambiguous_recorded_prior_failure_never_triggers_retry(self):
        self.receipt(1,"INITIAL_REVIEW","FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED")
        r=self.run_preflight()
        self.assertEqual(r["review_stages"]["INITIAL_REVIEW"]["observed_attempts"],1)
        self.assertEqual(r["planning_result"],
                         "RECONCILE_OLD_PROVIDER_ATTEMPTS_BEFORE_ANY_SEND")
        self.assertFalse(r["automatic_retry_authorized"])

    def test_unexpected_fourth_attempt_is_rejected(self):
        self.receipt(4,"INITIAL_REVIEW","FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED")
        with self.assertRaisesRegex(ValueError,"Unaccounted"):
            self.run_preflight()

    def test_three_original_failed_attempts_do_not_reset(self):
        for n in (1,2,3):
            self.receipt(n,"INITIAL_REVIEW","FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED")
        r=self.run_preflight()
        self.assertEqual(r["planning_result"],"EXHAUSTED_NO_MORE_REQUESTS")
        self.assertIsNone(r["review_stages"]["INITIAL_REVIEW"]["next_possible_attempt_number"])

    def test_unknown_legacy_attempt_blocks_instead_of_claiming_unsent(self):
        self.receipt(1,"INITIAL_REVIEW","CONFIRMED_SENT_IN_FLIGHT")
        r=self.run_preflight()
        self.assertEqual(r["planning_result"],
                         "RECONCILE_OLD_PROVIDER_ATTEMPTS_BEFORE_ANY_SEND")

    def test_wrong_source_identity_stops_preflight(self):
        (self.original/"source.pdf").write_text("changed")
        with self.assertRaises(ValueError):
            self.run_preflight()

    def test_challenge_only_after_first_saved_review(self):
        (self.queue/"slide_001_initial_review.json").write_text(
            json.dumps({"status":"SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS",
                        "mode":"INITIAL_REVIEW","review_count":1}))
        r=self.run_preflight()
        self.assertEqual(r["suggested_next_stage"],"INDEPENDENT_CHALLENGE")
        self.assertFalse(r["new_slide_specific_consent_verified"])
        self.assertFalse(r["historical_slide1_special_window_reusable"])

    def receipt(self,n,mode,status):
        (self.queue/f"slide_001_{mode.lower()}_attempt_{n:02d}.json").write_text(
            json.dumps({"slide":1,"mode":mode,"attempt":n,"status":status}))


if __name__=="__main__":
    unittest.main()
