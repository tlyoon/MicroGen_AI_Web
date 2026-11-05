"""Offline single-send ChatGPT diagnostic: no PDF, no duplicate model job."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.windows_chatgpt_sourcefree_canary import (
    _local_root, expected_text, run, SEND_BUTTON_CSS,
)


class OneSendChatGPTCanaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "new_trial"
        self.env = patch.dict("os.environ", {"LOCALAPPDATA": self.tmp.name})
        self.platform = patch(
            "selenium_pipeline.windows_chatgpt_sourcefree_canary.sys.platform", "win32")
        self.env.start()
        self.platform.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(self.platform.stop)
        self.ready = lambda: {
            "provider": "chatgpt", "debug_port": 9223,
            "status": "AUTHENTICATED_COMPOSER_READY",
            "authenticated_ui_ready": True,
        }

    def test_no_live_no_send_or_claim(self):
        result = run(root=self.root, readiness=self.ready)
        self.assertEqual(result["status"], "DRY_RUN_NO_SUBMISSION")
        self.assertFalse(self.root.exists())

    def test_authenticated_once_verified_and_duplicate_never_resends(self):
        calls = []
        def fake(prompt, expected, timeout):
            calls.append((prompt, expected, timeout))
            self.assertIn(expected, prompt)
            return {
                "outcome": "VALID_ATTRIBUTED_RESPONSE",
                "send_click_attempted": True, "user_turn_confirmed": True,
                "assistant_response_seen": True, "response_character_count": len(expected),
            }
        first = run(root=self.root, live=True, readiness=self.ready, browser=fake)
        self.assertEqual(first["outcome"], "VALID_ATTRIBUTED_RESPONSE")
        self.assertEqual(len(calls), 1)
        second = run(root=self.root, live=True, readiness=self.ready, browser=fake)
        self.assertEqual(len(calls), 1)
        self.assertEqual(second["status"], "EXISTING_CLAIM_REUSED_NO_NEW_SEND")

    def test_may_have_submitted_then_error_cannot_retry(self):
        received = []
        def fail(*args):
            received.append(1)
            raise TimeoutError("SECRET_NOT_FOR_REPORT")
        first = run(root=self.root, live=True, readiness=self.ready, browser=fail)
        self.assertEqual(first["outcome"], "NO_VERIFIED_RESPONSE")
        self.assertEqual(first["error_type"], "TimeoutError")
        self.assertNotIn("SECRET_NOT_FOR_REPORT", str(first))
        second = run(root=self.root, live=True, readiness=self.ready, browser=fail)
        self.assertEqual(len(received), 1)
        self.assertEqual(second["status"], "EXISTING_CLAIM_REUSED_NO_NEW_SEND")

    def test_verified_no_send_records_zero_model_submissions(self):
        def no_send(prompt, expected, timeout):
            return {"outcome": "PROMPT_NOT_CONFIRMED_NO_SEND",
                    "send_click_attempted": False,
                    "user_turn_confirmed": False}
        first = run(root=self.root, live=True, readiness=self.ready,
                    browser=no_send)
        self.assertEqual(first["model_submissions_this_call"], 0)
        self.assertFalse(first["send_click_attempted"])
        again = run(root=self.root, live=True, readiness=self.ready,
                    browser=lambda *a: self.fail("No retry permitted"))
        self.assertEqual(again["status"], "EXISTING_CLAIM_REUSED_NO_NEW_SEND")

    def test_orphan_claim_is_reconciliation_only(self):
        self.root.mkdir()
        (self.root / "chatgpt_canary_claim.json").write_text("{}")
        report = run(root=self.root, live=True, readiness=self.ready,
                     browser=lambda *a: self.fail("Must not send"))
        self.assertEqual(report["status"], "PRIOR_CLAIM_UNRESOLVED_NO_RESEND")

    def test_guest_never_writes_claim_or_sends(self):
        result = run(root=self.root, live=True,
                     readiness=lambda: {**self.ready(), "authenticated_ui_ready": False},
                     browser=lambda *a: self.fail("Guest send forbidden"))
        self.assertEqual(result["status"], "CHATGPT_NOT_AUTHENTICATED_NO_SEND")
        self.assertFalse(self.root.exists())

    def test_out_of_localappdata_rejected(self):
        with self.assertRaises(ValueError):
            _local_root(Path(self.tmp.name).parent / "not_localappdata")

    def test_only_exact_self_authored_draft_marker_is_eligible(self):
        with self.assertRaises(ValueError):
            run(root=self.root, live=True,
                owned_draft_exact="PERSONAL_DRAFT_MUST_NOT_BE_REMOVED",
                readiness=self.ready)
        self.assertFalse(self.root.exists())
        original = "MICROGEN_EDITOR_TYPING_DIAGNOSTIC_52E0"
        r = run(root=self.root, live=True, readiness=self.ready,
                owned_draft_exact=original,
                browser=lambda p,e,t: {
                    "outcome": "VALID_ATTRIBUTED_RESPONSE",
                    "send_click_attempted": True, "user_turn_confirmed": True,
                    "assistant_response_seen": True})
        self.assertTrue(r["known_owned_draft_replacement"])

    def test_current_chatgpt_send_button_selector_is_supported(self):
        self.assertIn("button[aria-label='Send']", SEND_BUTTON_CSS)
        self.assertIn("button[data-testid='send-button']", SEND_BUTTON_CSS)

    def test_exception_before_preclick_record_is_definitely_no_send(self):
        with patch(
            "selenium_pipeline.windows_chatgpt_sourcefree_canary._real_browser_once",
            side_effect=TimeoutError("not sent")):
            report = run(root=self.root, live=True, readiness=self.ready)
        self.assertEqual(report["outcome"], "PRE_CLICK_FAILURE_CONFIRMED_NO_SEND")
        self.assertFalse(report["send_click_attempted"])
        self.assertEqual(report["model_submissions_this_call"], 0)
        self.assertFalse((self.root / "chatgpt_send_click_intent.json").exists())

    def test_uncertain_click_retains_separate_intent_receipt(self):
        def error_after_intent(*args, **kwargs):
            kwargs["on_send_intent"]()
            raise TimeoutError("could be in-flight")
        with patch(
            "selenium_pipeline.windows_chatgpt_sourcefree_canary._real_browser_once",
            side_effect=error_after_intent):
            report = run(root=self.root, live=True, readiness=self.ready)
        self.assertEqual(report["model_submissions_this_call"], 1)
        self.assertTrue((self.root / "chatgpt_send_click_intent.json").is_file())
        self.assertEqual(report["outcome"], "NO_VERIFIED_RESPONSE")

    def test_expected_marker_is_exact_single_line(self):
        self.assertEqual(expected_text("ABC012"),
                         "MICROGEN_CHATGPT_CANARY_ABC012_OK")


if __name__ == "__main__":
    unittest.main()
