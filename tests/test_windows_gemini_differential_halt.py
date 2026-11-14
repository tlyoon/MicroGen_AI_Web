"""No-billing, no-send Gemini diagnostic and cross-job halt regression."""
from __future__ import annotations
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from selenium_pipeline.windows_gemini_differential_probe import classify, run_canary, _valid
from selenium_pipeline.windows_gemini_provider_halt import inspect_halt, record_stage, inspect_completed_trials
from selenium_pipeline.original_multisource_recovery_campaign import _new_atomic


class DifferentialCanaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"LOCALAPPDATA": str(self.root)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.place = self.root / "probe"
        self.valid = '{"microgen_transport_probe":"ok"}'

    @patch("selenium_pipeline.windows_gemini_differential_probe.sys.platform", "win32")
    def test_browser_canary_one_claim_and_no_retries(self):
        send = Mock(return_value=self.valid)
        okay = lambda: {"authenticated_ui_ready": True}
        first = run_canary(checkpoint_dir=self.place, backend="browser",
                           browser_transport=send, browser_ready=okay)
        second = run_canary(checkpoint_dir=self.place, backend="browser",
                            browser_transport=send, browser_ready=okay)
        self.assertEqual(first["outcome"], "VALID_CANARY_RESPONSE")
        self.assertEqual(second["status"], "PRIOR_CANARY_RECEIPT_REUSED")
        self.assertEqual(send.call_count, 1)
        self.assertTrue((self.place / "browser_probe_started.json").is_file())
        self.assertFalse(first["source_pdf_transmitted"])

    @patch("selenium_pipeline.windows_gemini_differential_probe.sys.platform", "win32")
    def test_api_requires_explicit_billing_consent_before_claim(self):
        send = Mock(return_value=self.valid)
        with self.assertRaisesRegex(ValueError, "confirm-api-diagnostic-cost"):
            run_canary(checkpoint_dir=self.place, backend="api", api_transport=send)
        self.assertFalse((self.place / "api_probe_started.json").exists())
        send.assert_not_called()
        first = run_canary(checkpoint_dir=self.place, backend="api",
                           confirm_api_diagnostic_cost=True, api_transport=send)
        again = run_canary(checkpoint_dir=self.place, backend="api",
                           confirm_api_diagnostic_cost=True, api_transport=send)
        self.assertEqual(first["outcome"], "VALID_CANARY_RESPONSE")
        self.assertEqual(again["status"], "PRIOR_CANARY_RECEIPT_REUSED")
        self.assertEqual(send.call_count, 1)

    @patch("selenium_pipeline.windows_gemini_differential_probe.sys.platform", "win32")
    def test_ambiguous_exception_never_resends_or_leaks_secret(self):
        send = Mock(side_effect=RuntimeError("PRIVATE_API_KEY_STRING"))
        first = run_canary(checkpoint_dir=self.place, backend="api",
                           confirm_api_diagnostic_cost=True, api_transport=send)
        self.assertEqual(first["outcome"], "NO_VERIFIED_RESPONSE")
        raw = (self.place / "api_probe_result.json").read_text(encoding="utf8")
        self.assertNotIn("PRIVATE_API_KEY_STRING", raw)
        again = run_canary(checkpoint_dir=self.place, backend="api",
                           confirm_api_diagnostic_cost=True, api_transport=send)
        self.assertEqual(again["status"], "PRIOR_CANARY_RECEIPT_REUSED")
        self.assertEqual(send.call_count, 1)

    @patch("selenium_pipeline.windows_gemini_differential_probe.sys.platform", "win32")
    def test_crashed_preclaim_cannot_be_resent(self):
        self.place.mkdir()
        (self.place / "browser_probe_started.json").write_text(
            '{"one_submission_only":true}', encoding="utf8")
        never = Mock(side_effect=AssertionError("Resent"))
        result = run_canary(checkpoint_dir=self.place, backend="browser",
                            browser_transport=never)
        self.assertEqual(result["outcome"], "UNRESOLVED_CLAIM")
        never.assert_not_called()

    @patch("selenium_pipeline.windows_gemini_differential_probe.sys.platform", "win32")
    def test_unauthed_browser_no_send(self):
        send = Mock(side_effect=AssertionError("should not send"))
        result = run_canary(checkpoint_dir=self.place, backend="browser",
                            browser_transport=send,
                            browser_ready=lambda: {"authenticated_ui_ready": False})
        self.assertEqual(result["outcome"], "NO_SUBMISSION_PRECHECK")
        self.assertFalse((self.place / "browser_probe_started.json").exists())
        send.assert_not_called()

    @patch("selenium_pipeline.windows_gemini_differential_probe.sys.platform", "win32")
    def test_source_sized_synthetic_browser_probe_one_send_and_sha_bound(self):
        send = Mock(return_value='{"probe":"microgen_source_transport_ok"}')
        ready = lambda: {"authenticated_ui_ready": True}
        first = run_canary(
            checkpoint_dir=self.place, backend="browser",
            browser_transport=send, browser_ready=ready, profile="source_sized")
        self.assertEqual(first["outcome"], "VALID_CANARY_RESPONSE")
        self.assertEqual(first["probe_profile"], "source_sized")
        self.assertGreaterEqual(first["prompt_characters"], 1200)
        self.assertLessEqual(first["prompt_characters"], 3000)
        self.assertEqual(send.call_count, 1)
        prompt = send.call_args.args[0]
        self.assertNotIn("source.pdf", prompt)
        self.assertIn("inert test data", prompt)
        again = run_canary(
            checkpoint_dir=self.place, backend="browser",
            browser_transport=send, browser_ready=ready, profile="source_sized")
        self.assertEqual(again["status"], "PRIOR_CANARY_RECEIPT_REUSED")
        self.assertEqual(send.call_count, 1)
        result = classify(browser=again, api=None)
        self.assertEqual(
            result["status"],
            "BROWSER_SOURCE_SIZED_INPUT_CANARY_OK_FULL_LESSON_NOT_CERTIFIED")
        self.assertTrue(result["source_sized_text_input_response_verified"])
        self.assertFalse(result["new_api_content_cost_authorized"])
        self.assertFalse(result["provider_server_outage_proven"])

    @patch("selenium_pipeline.windows_gemini_differential_probe.sys.platform", "win32")
    def test_source_sized_claim_cannot_be_reused_as_short_or_as_api(self):
        send = Mock(return_value='{"probe":"microgen_source_transport_ok"}')
        ready = lambda: {"authenticated_ui_ready": True}
        run_canary(checkpoint_dir=self.place, backend="browser",
                   browser_transport=send, browser_ready=ready,
                   profile="source_sized")
        with self.assertRaisesRegex(ValueError, "Different canary profiles"):
            run_canary(checkpoint_dir=self.place, backend="browser",
                       browser_transport=send, browser_ready=ready,
                       profile="short")
        with self.assertRaisesRegex(ValueError, "browser-only"):
            run_canary(checkpoint_dir=self.place, backend="api",
                       confirm_api_diagnostic_cost=True,
                       api_transport=send, profile="source_sized")
        self.assertEqual(send.call_count, 1)
        self.assertFalse((self.place / "api_probe_started.json").exists())

    @patch("selenium_pipeline.windows_gemini_differential_probe.sys.platform", "win32")
    def test_source_sized_wrong_reply_and_uncertain_claim_never_resend(self):
        send = Mock(return_value='{"microgen_transport_probe":"ok"}')
        ready = lambda: {"authenticated_ui_ready": True}
        first = run_canary(checkpoint_dir=self.place, backend="browser",
                           browser_transport=send, browser_ready=ready,
                           profile="source_sized")
        self.assertEqual(first["outcome"], "RESPONSE_RETURNED_BUT_NONCONFORMING")
        again = run_canary(checkpoint_dir=self.place, backend="browser",
                           browser_transport=send, browser_ready=ready,
                           profile="source_sized")
        self.assertEqual(again["status"], "PRIOR_CANARY_RECEIPT_REUSED")
        self.assertEqual(send.call_count, 1)
        failed = classify(browser=first, api=None)
        self.assertEqual(
            failed["status"],
            "INCONCLUSIVE_BROWSER_FAILURE_METADATA_NOT_GENERATION_PROOF")
        self.assertFalse(failed["source_sized_text_input_response_verified"])

    @patch("selenium_pipeline.windows_gemini_differential_probe.sys.platform", "win32")
    def test_source_sized_post_claim_crash_is_non_retryable(self):
        from selenium_pipeline.windows_gemini_differential_probe import _profile_spec
        import json
        self.place.mkdir()
        prompt, _, sha = _profile_spec("source_sized")
        (self.place / "browser_probe_started.json").write_text(
            json.dumps({
                "schema_version": 1, "backend": "browser",
                "content_model": "gemini-3.8-flash",
                "generic_prompt_sha256": sha,
                "probe_profile": "source_sized",
                "one_submission_only": True,
            }), encoding="utf8")
        send = Mock(side_effect=AssertionError("duplicate browser Send"))
        result = run_canary(checkpoint_dir=self.place, backend="browser",
                            browser_transport=send, profile="source_sized")
        self.assertEqual(result["status"], "PRIOR_CANARY_MAY_HAVE_SUBMITTED_NO_RESEND")
        send.assert_not_called()

    def test_differential_conclusions_do_not_overclaim(self):
        a = {"outcome": "VALID_CANARY_RESPONSE"}
        b = {"outcome": "NO_VERIFIED_RESPONSE"}
        self.assertEqual(classify(browser=b, api=a)["status"],
                         "BROWSER_AUTOMATION_OR_RESPONSE_CAPTURE_SUSPECTED")
        self.assertEqual(classify(browser=b, api=None,
                                  metadata_reachable=True)["status"],
                         "INCONCLUSIVE_BROWSER_FAILURE_METADATA_NOT_GENERATION_PROOF")
        self.assertEqual(classify(browser=b, api=b)["status"],
                         "SERVICE_OR_NETWORK_OR_BOTH_TRANSPORTS_SUSPECTED")
        self.assertFalse(classify(browser=b, api=b)["provider_server_outage_proven"])
        self.assertEqual(classify(browser=a, api=a)["status"],
                         "BOTH_GENERATION_TRANSPORTS_RESPOND_TO_SMALL_CANARY")

    def test_short_canary_rejects_placeholders_and_wrapped_output(self):
        self.assertTrue(_valid(self.valid))
        self.assertFalse(_valid("Flash"))
        self.assertFalse(_valid(chr(96)*3+"json\n"+self.valid+"\n"+chr(96)*3))
        self.assertFalse(_valid('{"microgen_transport_probe":"wrong"}'))


class CrossTaskGeminiHaltTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.health = self.root / "health"

    def receipt(self, section, stage, success, *, send=True):
        root = self.root / f"trial_{section}"
        root.mkdir()
        source = "a" * 62 + section
        _new_atomic(root / "fresh_trial_contract.json", {
            "schema_version": 1, "source_sha256": source})
        result_name = ("figures_attempt_result.json" if stage == "figures"
                       else f"stage_{stage}_result.json")
        if stage == "figures":
            item = {
                "status": ("FIGURES_STAGE_RETURNED_SUCCESS_NOT_FULL_LECTURE"
                           if success else "FIGURES_ATTEMPT_TIMEOUT_NO_AUTO_RETRY"),
                "original_source_sha256": source,
                "student_publication_authorized": False}
            log_name = "figures_stage_stdout.raw.log"
        else:
            item = {
                "status": ("STAGE_COMPLETED_AND_SOURCE_SHA_BOUND"
                           if success else "STAGE_FAILED_OR_OUTPUT_INCOMPLETE_NO_RETRY"),
                "source_sha256": source,
                "student_publication_authorized": False}
            log_name = f"stage_{stage}_stdout.raw.log"
        _new_atomic(root / result_name, item)
        claim_name = ("figures_attempt_started.json" if stage == "figures"
                      else f"stage_{stage}_started.json")
        _new_atomic(root / claim_name, {
            "schema_version": 1, "source_sha256": source, "stage": stage})
        (root / log_name).write_text(
            "[2026-11-04 15:32:05] [INFO] Gemini submission registered via "
            "new-user-turn+composer-cleared.\n" if send else
            "[INFO] No Gemini response received pre-submit\n", encoding="utf8")
        return root

    def test_real_vendor_timing_send_marker_drives_health_classification(self):
        trial = self.receipt("14", "figures", False, send=False)
        (trial / "figures_stage_stdout.raw.log").write_text(
            "[2026-11-10 13:33:14] [INFO] [TIMING] "
            "attempt 1 verified send: 0.052s | registered=True\n",
            encoding="utf8")
        event = record_stage(trial_dir=trial, stage="figures",
                             folder=self.health, now=1000)
        self.assertEqual(event["outcome"], "SENT_BUT_NOT_ACCEPTED")
        recorded = list((self.health / "events").glob("*.json"))
        self.assertEqual(len(recorded), 1)
        import json
        self.assertTrue(json.loads(recorded[0].read_text(
            encoding="utf8"))["owned_browser_send_registered"])

    def test_two_distinct_failed_browser_sends_pause_new_tasks(self):
        a = self.receipt("01", "figures", False)
        b = self.receipt("02", "slides", False)
        first = record_stage(trial_dir=a, stage="figures", folder=self.health, now=1000)
        self.assertEqual(first["outcome"], "SENT_BUT_NOT_ACCEPTED")
        record_stage(trial_dir=b, stage="slides", folder=self.health, now=1010)
        state = inspect_halt(folder=self.health, now=1100)
        self.assertEqual(state["status"], "HALT_NEW_GEMINI_TASKS")
        self.assertFalse(state["new_generation_dispatch_allowed_by_health_policy"])
        self.assertFalse(state["existing_ambiguous_source_resubmission_authorized"])
        self.assertEqual(inspect_halt(folder=self.health, now=3000)["status"],
                         "NO_PROVIDER_HALT")
        reused = record_stage(trial_dir=a, stage="figures", folder=self.health)
        self.assertEqual(reused["status"], "PRIOR_STAGE_HEALTH_REUSED")
        self.assertEqual(len(list((self.health / "events").glob("*.json"))), 2)
        self.assertEqual(inspect_halt(folder=self.health, backend="api",
                                      now=1100)["status"], "NO_PROVIDER_HALT")

    def test_accepted_stage_closes_after_previous_stalls(self):
        a = self.receipt("11", "figures", False)
        b = self.receipt("12", "slides", False)
        c = self.receipt("13", "figures", True)
        record_stage(trial_dir=a, stage="figures", folder=self.health, now=1000)
        record_stage(trial_dir=b, stage="slides", folder=self.health, now=1010)
        record_stage(trial_dir=c, stage="figures", folder=self.health, now=1020)
        self.assertEqual(inspect_halt(folder=self.health, now=1100)["status"],
                         "NO_PROVIDER_HALT")

    def test_timeout_without_verified_send_not_server_outage(self):
        a = self.receipt("21", "figures", False, send=False)
        b = self.receipt("22", "figures", False, send=False)
        first = record_stage(trial_dir=a, stage="figures", folder=self.health, now=1000)
        record_stage(trial_dir=b, stage="figures", folder=self.health, now=1010)
        self.assertEqual(first["outcome"], "UNKNOWN_SUBMISSION")
        self.assertEqual(inspect_halt(folder=self.health, now=1100)["status"],
                         "NO_PROVIDER_HALT")

    def test_wrong_backend_cannot_poison_browser_or_api_health(self):
        a = self.receipt("41", "figures", False)
        with self.assertRaisesRegex(ValueError, "send intent"):
            record_stage(trial_dir=a, stage="figures",
                         backend="api", folder=self.health)
        self.assertFalse(self.health.exists())

    def test_readonly_log_evidence_does_not_dispatch(self):
        a = self.receipt("31", "figures", False)
        item = inspect_completed_trials(paths=[a])
        self.assertTrue(item[0]["browser_send_registered"])
        self.assertFalse(item[0]["gemini_outage_proven"])
        self.assertFalse(self.health.exists())


if __name__ == "__main__":
    unittest.main()
