"""No-network acceptance for source-sized Gemini Selenium-only G1 result.

Simulated browser callbacks, real immutable claims; no paid model or source.
"""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from selenium_pipeline.gemini_g1_single_route_cli import PROFILE, summarize
from selenium_pipeline.gemini_selenium_only_policy import (
    GeminiSeleniumTemporaryFailure, temporary_failure_message)
from selenium_pipeline.windows_gemini_differential_probe import (
    _profile_spec, run_canary, _read)


class G1SingleRouteTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        e=patch.dict(os.environ,{"LOCALAPPDATA":str(self.root)})
        e.start(); self.addCleanup(e.stop)
        self.folder=self.root/"fresh_single_g1"

    @patch("selenium_pipeline.windows_gemini_differential_probe.sys.platform","win32")
    def test_distinct_new_source_sized_profile_not_an_earlier_canary(self):
        prompt, expected, sha=_profile_spec(PROFILE)
        old_prompt, old_expected, old_sha=_profile_spec("source_sized")
        self.assertNotEqual(prompt,old_prompt)
        self.assertNotEqual(sha,old_sha)
        self.assertNotEqual(expected,old_expected)
        self.assertGreaterEqual(len(prompt),1200)
        self.assertLessEqual(len(prompt),3000)
        self.assertNotIn("source.pdf",prompt)
        self.assertIn("Selenium-only",prompt)

    @patch("selenium_pipeline.windows_gemini_differential_probe.sys.platform","win32")
    def test_verified_source_sized_gemini_response_is_not_academic_acceptance(self):
        _,expected,_=_profile_spec(PROFILE)
        mock=Mock(return_value=json.dumps(expected))
        first=run_canary(checkpoint_dir=self.folder,backend="browser",
            browser_transport=mock,profile=PROFILE,
            browser_ready=lambda:{"authenticated_ui_ready":True})
        report=summarize(first)
        self.assertEqual(report["exit_code"],0)
        self.assertEqual(report["g1_status"],
                         "G1_SOURCE_FREE_GEMINI_SELENIUM_SIZED_RESPONSE_VERIFIED")
        self.assertFalse(report["academic_original_lecture_accepted"])
        self.assertFalse(report["gemini_api_generation_fallback"])
        self.assertFalse(report["chatgpt_generation_fallback"])
        reused=run_canary(checkpoint_dir=self.folder,backend="browser",
            browser_transport=mock,profile=PROFILE,
            browser_ready=lambda:{"authenticated_ui_ready":True})
        self.assertEqual(reused["status"],"PRIOR_CANARY_RECEIPT_REUSED")
        self.assertTrue(summarize(reused)["prior_claim_reused_without_resend"])
        mock.assert_called_once()

    @patch("selenium_pipeline.windows_gemini_differential_probe.sys.platform","win32")
    def test_pre_send_exhaustion_records_zero_model_calls_and_clear_stop(self):
        def fail(_):
            raise GeminiSeleniumTemporaryFailure(
                "Gemini Selenium pre-Send temporary failure",attempts_used=3,
                failure_phase="GEMINI_MODEL_PICKER_NOT_READY")
        mock=Mock(side_effect=fail)
        result=run_canary(checkpoint_dir=self.folder,backend="browser",
            browser_transport=mock,profile=PROFILE,
            browser_ready=lambda:{"authenticated_ui_ready":True})
        self.assertEqual(result["request_may_have_been_submitted"],False)
        self.assertEqual(result["new_model_generation_calls"],0)
        self.assertEqual(result["gemini_browser_failure_phase"],
                         "PRE_SEND_NO_SUBMISSION")
        self.assertEqual(result["gemini_browser_presend_attempts_used"],3)
        self.assertEqual(result["browser_bridge_stage"],
                         "GEMINI_MODEL_PICKER_NOT_READY")
        report=summarize(result)
        self.assertEqual(report["exit_code"],2)
        self.assertIn("temporary failure",report["reason"])
        self.assertFalse(report["old_uncertain_job_auto_retry_allowed"])
        assert _read(self.folder/"browser_probe_result.json")==result
        run_canary(checkpoint_dir=self.folder,backend="browser",
            browser_transport=mock,profile=PROFILE,
            browser_ready=lambda:{"authenticated_ui_ready":True})
        mock.assert_called_once()

    @patch("selenium_pipeline.windows_gemini_differential_probe.sys.platform","win32")
    def test_uncertain_post_send_failure_never_claims_provider_outage(self):
        from selenium_pipeline.series_bridge import SeriesBridgeError
        def fail(_):
            error=SeriesBridgeError("No stable complete Gemini JSON")
            error.gemini_send_boundary_entered=True
            error.gemini_failure_phase="OWNED_RESPONSE_UNVERIFIED_QUARANTINED"
            error.gemini_prepare_attempts_used=2
            raise error
        mock=Mock(side_effect=fail)
        result=run_canary(checkpoint_dir=self.folder,backend="browser",
            browser_transport=mock,profile=PROFILE,
            browser_ready=lambda:{"authenticated_ui_ready":True})
        self.assertTrue(result["request_may_have_been_submitted"])
        self.assertEqual(result["new_model_generation_calls"],1)
        self.assertEqual(result["gemini_browser_failure_phase"],
                         "AFTER_POSSIBLE_SEND")
        report=summarize(result)
        self.assertIn("saved response quarantine",report["reason"])
        self.assertFalse(report["model_or_browser_error_is_api_outage_proof"])
        self.assertFalse(report["old_uncertain_job_auto_retry_allowed"])
        self.assertEqual(report["exit_code"],2)
        mock.assert_called_once()

    @patch("selenium_pipeline.windows_gemini_differential_probe.sys.platform","win32")
    def test_unattributed_legacy_error_is_not_labeled_pre_send(self):
        send=Mock(side_effect=RuntimeError("PRIVATE_SECRET_DO_NOT_PERSIST"))
        result=run_canary(checkpoint_dir=self.folder,backend="browser",
            browser_transport=send,profile=PROFILE,
            browser_ready=lambda:{"authenticated_ui_ready":True})
        self.assertEqual(result["gemini_browser_failure_phase"],
                         "UNKNOWN_SUBMISSION_OUTCOME")
        self.assertTrue(result["request_may_have_been_submitted"])
        record=(self.folder/"browser_probe_result.json").read_text()
        self.assertNotIn("PRIVATE_SECRET_DO_NOT_PERSIST",record)
        self.assertFalse(summarize(result)["model_or_browser_error_is_api_outage_proof"])

    @patch("selenium_pipeline.windows_gemini_differential_probe.sys.platform","win32")
    def test_not_authenticated_refuses_before_claim_and_fails_informatively(self):
        mock=Mock()
        result=run_canary(checkpoint_dir=self.folder,backend="browser",
            browser_transport=mock,profile=PROFILE,
            browser_ready=lambda:{"authenticated_ui_ready":False})
        report=summarize(result)
        self.assertEqual(report["g1_status"],
                         "G1_BLOCKED_GEMINI_BROWSER_NOT_READY_NO_SEND")
        self.assertEqual(report["exit_code"],2)
        self.assertFalse((self.folder/"browser_probe_started.json").exists())
        mock.assert_not_called()

    def test_unresolved_claim_never_retries(self):
        report=summarize({"status":"PRIOR_CANARY_MAY_HAVE_SUBMITTED_NO_RESEND",
                          "outcome":"UNRESOLVED_CLAIM"})
        self.assertEqual(report["exit_code"],2)
        self.assertEqual(report["g1_status"],
                         "G1_BLOCKED_PRIOR_UNKNOWN_SUBMISSION_NO_RESEND")
        self.assertIn("inspect the SHA-bound attempt claim",report["reason"])

    def test_cli_always_prints_terminal_failure_and_nonzero_exit(self):
        import io
        from contextlib import redirect_stdout, redirect_stderr
        from selenium_pipeline.gemini_g1_single_route_cli import main
        receipt={
            "status":"GENERIC_CANARY_TERMINAL",
            "outcome":"NO_VERIFIED_RESPONSE",
            "request_may_have_been_submitted":True,
            "gemini_browser_failure_phase":"AFTER_POSSIBLE_SEND",
            "browser_bridge_stage":
                "OWNED_GEMINI_UI_TERMINAL_ERROR_TEXT_NOT_API_PROOF"}
        stdout,stderr=io.StringIO(),io.StringIO()
        with patch(
                "selenium_pipeline.windows_gemini_differential_probe.run_canary",
                return_value=receipt) as owned, redirect_stdout(stdout),\
                redirect_stderr(stderr):
            code=main(["--canary-root",str(self.folder),
                       "--run-one-new-selenium-probe"])
        self.assertEqual(code,2)
        report=json.loads(stdout.getvalue())
        self.assertEqual(
            report["g1_status"],"G1_BLOCKED_GEMINI_SELENIUM_TEMPORARY_FAILURE")
        self.assertIn("STOPPED",stderr.getvalue())
        self.assertFalse(report["chatgpt_generation_fallback"])
        self.assertFalse(report["gemini_api_generation_fallback"])
        owned.assert_called_once_with(
            checkpoint_dir=self.folder,backend="browser",profile=PROFILE)

    def test_cli_local_receipt_error_stops_without_replaying_request(self):
        import io
        from contextlib import redirect_stdout, redirect_stderr
        from selenium_pipeline.gemini_g1_single_route_cli import main
        stdout,stderr=io.StringIO(),io.StringIO()
        with patch(
                "selenium_pipeline.windows_gemini_differential_probe.run_canary",
                side_effect=ValueError("PRIVATE_RAW_ERROR")) as invoked,\
                redirect_stdout(stdout),redirect_stderr(stderr):
            code=main(["--canary-root",str(self.folder),
                       "--run-one-new-selenium-probe"])
        self.assertEqual(code,2)
        report=json.loads(stdout.getvalue())
        self.assertEqual(report["g1_status"],
                         "G1_BLOCKED_DIAGNOSTIC_ERROR_NO_RESEND")
        self.assertNotIn("PRIVATE_RAW_ERROR",stdout.getvalue())
        self.assertNotIn("PRIVATE_RAW_ERROR",stderr.getvalue())
        self.assertIn("STOPPED",stderr.getvalue())
        invoked.assert_called_once()


if __name__=="__main__":
    unittest.main()
