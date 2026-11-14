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

    def test_g1_v3_size_controls_have_distinct_claim_identity(self):
        from selenium_pipeline.gemini_g1_single_route_cli import (
            SHORT_PROFILE, LONG_PROFILE, REGISTRATION_PROFILE)
        short, expected_short, sha_short = _profile_spec(SHORT_PROFILE)
        long, expected_long, sha_long = _profile_spec(LONG_PROFILE)
        old, old_expected, old_sha = _profile_spec(PROFILE)
        reg, expected_reg, sha_reg = _profile_spec(REGISTRATION_PROFILE)
        self.assertLess(len(reg), 400)
        self.assertLess(len(short), 400)
        self.assertGreaterEqual(len(long), 1200)
        self.assertLessEqual(len(long), 3000)
        self.assertEqual(len({sha_short, sha_long, old_sha, sha_reg}), 4)
        self.assertEqual(summarize({
            "outcome":"VALID_CANARY_RESPONSE",
            "probe_profile":REGISTRATION_PROFILE})["g1_status"],
            "G1_SHORT_GEMINI_RESPONSE_VERIFIED_LONG_FORM_UNTESTED")
        self.assertEqual(len({str(expected_short), str(expected_long),
                              str(old_expected)}), 3)
        self.assertEqual(
            summarize({"outcome":"VALID_CANARY_RESPONSE",
                       "probe_profile":SHORT_PROFILE})["g1_status"],
            "G1_SHORT_GEMINI_RESPONSE_VERIFIED_LONG_FORM_UNTESTED")
        self.assertFalse(summarize(
            {"outcome":"VALID_CANARY_RESPONSE","probe_profile":SHORT_PROFILE}
        )["academic_original_lecture_accepted"])

    def test_rich_route_v6_reuses_exact_production_picker_and_validator(self):
        from selenium_pipeline.gemini_g1_single_route_cli import (
            RICH_ROUTE_SOURCE_SIZED_PROFILE,APPROVED_PROFILES)
        from selenium_pipeline.windows_gemini_differential_probe import (
            _request_browser)
        profile=RICH_ROUTE_SOURCE_SIZED_PROFILE
        prompt,expected,digest=_profile_spec(profile)
        _,_,old_sha=_profile_spec("source_sized_g1_owned_turn_v5")
        self.assertIn(profile,APPROVED_PROFILES)
        self.assertNotEqual(digest,old_sha)
        self.assertTrue(1200<=len(prompt)<=3000)
        called=[]
        def production_route(provider,text,port,wait_cap,*,accept_fn):
            called.append((provider,text,port,wait_cap))
            good=json.dumps(expected)
            self.assertTrue(accept_fn(good))
            self.assertFalse(accept_fn('{"probe":"another_canary"}'))
            return good
        with patch("selenium_pipeline.rich_mapping_provider_dispatch."
                   "_real_transport",side_effect=production_route):
            result=_request_browser(prompt,profile=profile)
        self.assertEqual(result,json.dumps(expected))
        self.assertEqual(called,[("gemini",prompt,9222,150)])

    def test_new_owned_turn_v5_is_distinct_sha_bound_source_sized(self):
        from selenium_pipeline.gemini_g1_single_route_cli import (
            OWNED_SOURCE_SIZED_PROFILE, APPROVED_PROFILES)
        fresh,expected,digest=_profile_spec(OWNED_SOURCE_SIZED_PROFILE)
        old,_,old_digest=_profile_spec("source_sized_g1_selenium_only_v3")
        self.assertIn(OWNED_SOURCE_SIZED_PROFILE,APPROVED_PROFILES)
        self.assertNotEqual(digest,old_digest)
        self.assertNotEqual(fresh,old)
        self.assertTrue(1200<=len(fresh)<=3000)
        self.assertIn("source_sized_owned_v5_ok",str(expected))
        self.assertFalse(summarize({
            "probe_profile":OWNED_SOURCE_SIZED_PROFILE,
            "outcome":"NO_VERIFIED_RESPONSE",
        })["academic_original_lecture_accepted"])

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

    @patch("selenium_pipeline.windows_gemini_differential_probe.sys.platform", "win32")
    def test_success_receipt_persists_independent_owned_send_registration(self):
        from selenium_pipeline.series_gemini import OwnedGeminiResponse
        _, expected, _ = _profile_spec(PROFILE)
        text = OwnedGeminiResponse(
            json.dumps(expected),
            registration_status="NEW_USER_TURN_AND_COMPOSER_CLEARED",
            new_turn_verified=True, late_reconciled=True)
        result = run_canary(
            checkpoint_dir=self.folder, backend="browser",
            browser_transport=lambda _: text, profile=PROFILE,
            browser_ready=lambda: {"authenticated_ui_ready": True})
        self.assertEqual(result["outcome"], "VALID_CANARY_RESPONSE")
        self.assertTrue(result["gemini_new_user_turn_verified"])
        self.assertTrue(result["gemini_late_response_reconciled"])
        self.assertEqual(result["gemini_send_registration_status"],
                         "NEW_USER_TURN_AND_COMPOSER_CLEARED")
        self.assertEqual(_read(self.folder / "browser_probe_result.json"), result)

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
    def test_registered_blank_generating_reply_is_not_classed_as_selenium_send_error(self):
        from selenium_pipeline.series_bridge import SeriesBridgeError
        def fail(_):
            error=SeriesBridgeError(
                "Gemini new user turn was independently registered but "
                "generation stayed active with ZERO text")
            error.gemini_send_boundary_entered=True
            error.gemini_failure_phase="REGISTERED_SEND_GENERATION_STALLED_ZERO_MODEL_TEXT"
            error.gemini_prepare_attempts_used=1
            error.gemini_send_registration_status="NEW_USER_TURN_AND_COMPOSER_CLEARED"
            error.gemini_new_user_turn_verified=True
            error.gemini_visible_model_chars_at_stop=0
            error.gemini_generation_active_at_stop=True
            raise error
        result=run_canary(checkpoint_dir=self.folder,backend="browser",
            browser_transport=fail,profile=PROFILE,
            browser_ready=lambda:{"authenticated_ui_ready":True})
        self.assertEqual(result["browser_bridge_stage"],
                         "REGISTERED_SEND_GENERATION_STALLED_ZERO_MODEL_TEXT")
        self.assertTrue(result["gemini_new_user_turn_verified"])
        self.assertEqual(result["gemini_visible_model_chars_at_stop"],0)
        self.assertTrue(result["gemini_generation_active_at_stop"])
        self.assertIsNone(result["verified_api_http_status"])
        report=summarize(result)
        self.assertEqual(report["exit_code"],2)
        self.assertEqual(report["gemini_visible_model_chars_at_stop"],0)
        self.assertTrue(report["gemini_generation_active_at_stop"])
        self.assertFalse(report["model_or_browser_error_is_api_outage_proof"])

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

    def test_reused_historic_stop_message_gets_current_true_guidance(self):
        receipt={
            "status":"PRIOR_CANARY_RECEIPT_REUSED",
            "outcome":"NO_VERIFIED_RESPONSE",
            "request_may_have_been_submitted":True,
            "browser_bridge_stage":
                "OWNED_GEMINI_UI_TERMINAL_ERROR_TEXT_NOT_API_PROOF",
            "gemini_selenium_stop_message":
                "OLD: reconcile its owned tab later (already closed)"}
        report=summarize(receipt)
        self.assertTrue(report["prior_claim_reused_without_resend"])
        self.assertIn("saved response quarantine",report["reason"])
        self.assertNotIn("reconcile its owned tab",report["reason"])

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
