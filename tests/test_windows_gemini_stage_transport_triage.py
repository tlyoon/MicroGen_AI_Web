"""Windows Gemini transport triage: synthetic immutable offline evidence."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline.original_multisource_recovery_campaign import _new_atomic
from selenium_pipeline.windows_gemini_stage_transport_triage import diagnose


class GeminiStageTransportTriageTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.local = Path(tmp.name)
        self.env = patch.dict(os.environ, {"LOCALAPPDATA": str(self.local)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.trial = self.local / "trial"
        self.trial.mkdir()
        self.sha = "a" * 64
        _new_atomic(self.trial / "fresh_trial_contract.json", {
            "schema_version": 1,
            "status": "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL",
            "source_sha256": self.sha,
            "student_publication_authorized": False,
        })

    def begun(self, stage="figures"):
        prefix = "figures_attempt" if stage == "figures" else "stage_" + stage
        _new_atomic(self.trial / f"{prefix}_started.json", {
            "schema_version": 1, "stage": stage, "source_sha256": self.sha,
            "single_provider_attempt_only": True,
        })
        return prefix

    def finish(self, prefix, status, stage="figures"):
        value = {
            "schema_version": 1, "status": status,
            "source_sha256": self.sha,
            "student_publication_authorized": False,
        }
        if stage == "figures":
            value["original_source_sha256"] = self.sha
        _new_atomic(self.trial / f"{prefix}_result.json", value)

    def log(self, text, stage="figures"):
        file = ("figures_stage_stdout.raw.log" if stage == "figures"
                else f"stage_{stage}_stdout.raw.log")
        (self.trial / file).write_text(text, encoding="utf8")

    def test_realistic_local_extraction_and_browser_attach_timeout(self):
        p = self.begun()
        self.finish(p, "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY")
        self.log("[gemini] reusing active debug session on port 9222\n"
                 "Figure extraction completed successfully.\n"
                 "processing folder private; KEY_NOT_TO_REPORT")
        before = sorted(self.trial.iterdir())
        r = diagnose(trial_dir=self.trial)
        self.assertEqual(r["status"],
                         "LOCAL_EXTRACTION_DONE_BROWSER_SESSION_SEEN_SEND_UNVERIFIED")
        self.assertTrue(r["local_figure_extraction_finished_in_log"])
        self.assertTrue(r["browser_debug_session_seen_in_log"])
        self.assertFalse(r["owned_browser_send_registered"])
        self.assertFalse(r["provider_outage_proven"])
        self.assertFalse(r["browser_automation_or_capture_failure_proven"])
        self.assertFalse(r["original_submission_resend_authorized"])
        self.assertNotIn("KEY_NOT_TO_REPORT", str(r))
        self.assertEqual(before, sorted(self.trial.iterdir()))

    def test_owned_browser_send_registered_without_accepted_output(self):
        p = self.begun()
        self.finish(p, "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY")
        self.log("[INFO] Gemini submission registered via new-user-turn+composer-cleared.")
        r = diagnose(trial_dir=self.trial)
        self.assertEqual(r["status"], "REGISTERED_BROWSER_SEND_BUT_NO_ACCEPTED_STAGE")
        self.assertTrue(r["owned_browser_send_registered"])
        self.assertFalse(r["original_submission_resend_authorized"])

    def test_suspicious_prompt_text_does_not_fake_send_proof(self):
        p = self.begun()
        self.finish(p, "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY")
        self.log("user payload: Gemini submission registered via new-user-turn+composer-cleared.")
        r = diagnose(trial_dir=self.trial)
        self.assertFalse(r["owned_browser_send_registered"])

    def test_started_but_no_result_is_no_resend(self):
        self.begun()
        r = diagnose(trial_dir=self.trial)
        self.assertEqual(r["status"],
                         "PRE_SEND_INTENT_WITH_NO_FINAL_RESULT_REVIEW_REQUIRED")
        self.assertFalse(r["original_submission_resend_authorized"])

    def test_no_started_receipt_is_not_a_success(self):
        r = diagnose(trial_dir=self.trial)
        self.assertEqual(r["status"], "NO_STORED_STAGE_SEND_INTENT")
        self.assertFalse(r["provider_outage_proven"])

    def test_successful_stage_receipt_is_not_full_lecture(self):
        p = self.begun()
        self.finish(p, "FIGURES_STAGE_RETURNED_SUCCESS_NOT_FULL_LECTURE")
        r = diagnose(trial_dir=self.trial)
        self.assertEqual(r["status"], "TECHNICAL_STAGE_RECEIPT_SUCCESS_NOT_FULL_LECTURE")
        self.assertTrue(r["stage_accepted_receipt_present"])
        self.assertFalse(r["student_publication_authorized"])

    def test_mismatched_original_sha_cannot_be_triaged_as_valid(self):
        p = self.begun()
        value = {
            "schema_version": 1, "status": "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY",
            "original_source_sha256": "b" * 64, "student_publication_authorized": False,
        }
        _new_atomic(self.trial / f"{p}_result.json", value)
        with self.assertRaisesRegex(ValueError, "original SHA"):
            diagnose(trial_dir=self.trial)

    def test_result_without_pre_send_ledger_refused(self):
        _new_atomic(self.trial / "figures_attempt_result.json", {
            "schema_version": 1, "status": "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY",
        })
        with self.assertRaisesRegex(ValueError, "Result without pre-send"):
            diagnose(trial_dir=self.trial)

    def test_slides_is_supported_without_figures_specific_assumptions(self):
        p = self.begun("slides")
        self.finish(p, "STAGE_TIMEOUT_UNKNOWN_PROVIDER_SEND_NO_RETRY", "slides")
        self.log("Selenium attached successfully.", "slides")
        r = diagnose(trial_dir=self.trial, stage="slides")
        self.assertEqual(r["stage"], "slides")
        self.assertEqual(r["status"], "BROWSER_SESSION_SEEN_SEND_UNVERIFIED")

    def test_api_does_not_infer_browser_send(self):
        p = "stage_narration"
        _new_atomic(self.trial / f"{p}_started.json", {
            "schema_version": 1, "stage": "narration",
            "source_sha256": self.sha, "communication_mode": "api",
            "paid_content_api_explicitly_authorized": True,
        })
        self.finish(p, "STAGE_PROCESS_ERROR_NO_RETRY", "narration")
        r = diagnose(trial_dir=self.trial, stage="narration")
        self.assertEqual(r["status"], "API_STAGE_TERMINAL_WITHOUT_VERIFIED_RESPONSE")
        self.assertFalse(r["owned_browser_send_registered"])
        self.assertFalse(r["original_submission_resend_authorized"])


if __name__ == "__main__":
    unittest.main()
