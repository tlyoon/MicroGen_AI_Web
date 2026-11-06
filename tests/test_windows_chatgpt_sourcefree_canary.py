"""Offline single-send ChatGPT diagnostic: no PDF, no duplicate model job."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.windows_chatgpt_sourcefree_canary import (
    _local_root, _prompt_for_marker, _current_ui_exact_canary,
    prior_owned_draft, reconcile_existing, expected_text, run, SEND_BUTTON_CSS,
    inspect_existing_no_send,
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

    def test_readonly_sha_bound_no_click_failure_is_never_generation_proof(self):
        def no_editor_input(prompt, expected, timeout):
            return {
                "outcome": "PROMPT_NOT_CONFIRMED_NO_SEND",
                "send_click_attempted": False,
                "user_turn_confirmed": False,
                "assistant_response_seen": False,
            }
        run(root=self.root, live=True, readiness=self.ready, browser=no_editor_input)
        before = (self.root / "chatgpt_canary_result.json").read_bytes()
        status = inspect_existing_no_send(root=self.root)
        self.assertEqual(status["status"],
                         "CHATGPT_OWNED_EDITOR_INPUT_NOT_VERIFIED_NO_SEND")
        self.assertTrue(status["pre_send_editor_failure_independently_verified"])
        self.assertFalse(status["browser_submission_proven_successful"])
        self.assertFalse(status["old_source_retry_authorized"])
        self.assertFalse(status["new_model_or_tts_calls"])
        self.assertEqual(before, (self.root / "chatgpt_canary_result.json").read_bytes())
        self.assertFalse((self.root / "chatgpt_send_click_intent.json").exists())
        result = self.root / "chatgpt_canary_result.json"
        data = json.loads(result.read_text(encoding="utf8"))
        data["prompt_sha256"] = "0" * 64
        result.write_text(json.dumps(data), encoding="utf8")
        with self.assertRaisesRegex(ValueError, "Unmatched or untrusted"):
            inspect_existing_no_send(root=self.root)

    def test_send_click_intent_can_never_be_labeled_editor_no_send(self):
        def uncertain(prompt, expected, timeout):
            return {
                "outcome": "NO_VERIFIED_RESPONSE",
                "send_click_attempted": True,
                "user_turn_confirmed": False,
            }
        run(root=self.root, live=True, readiness=self.ready, browser=uncertain)
        report = inspect_existing_no_send(root=self.root)
        self.assertFalse(report["pre_send_editor_failure_independently_verified"])
        self.assertEqual(report["status"],
                         "CHATGPT_PRIOR_CANARY_NOT_A_PROVEN_EDITOR_FAILURE")
        (self.root / "chatgpt_send_click_intent.json").write_text("{}")
        self.assertFalse(inspect_existing_no_send(
            root=self.root)["pre_send_editor_failure_independently_verified"])

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

    def test_canonical_local_temp_paths_and_parent_traversal_guard(self):
        expected = (Path(self.tmp.name) / "nested" / "new").resolve()
        self.assertEqual(_local_root(expected), expected)
        self.assertEqual(_local_root(Path(self.tmp.name) / "nested" / "new"),
                         expected)
        with self.assertRaises(ValueError):
            _local_root(Path(self.tmp.name) / ".." / "not_owned")

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

    def make_prior(self, *, clicked=False, tamper=False):
        previous = Path(self.tmp.name) / "prior_owned"
        previous.mkdir()
        marker = "MICROGEN_CHATGPT_CANARY_A1B2C3D4E5F6_OK"
        prompt = _prompt_for_marker(marker)
        claim = {
            "schema_version": 1, "provider": "chatgpt",
            "debug_port": 9223, "one_send_only": True,
            "source_files_attached": False,
            "expected_response_marker": marker,
            "prompt_sha256": (
                "wrong" if tamper else hashlib.sha256(prompt.encode()).hexdigest()),
        }
        result = {
            "status": "CANARY_TERMINAL",
            "outcome": "NO_VERIFIED_RESPONSE",
            "expected_response_marker": marker,
            "send_click_attempted": clicked,
            "student_publication_authorized": False,
        }
        (previous / "chatgpt_canary_claim.json").write_text(json.dumps(claim))
        (previous / "chatgpt_canary_result.json").write_text(json.dumps(result))
        return previous, prompt

    def test_exact_prior_owned_draft_replaces_only_owned_text(self):
        previous, prompt = self.make_prior()
        self.assertEqual(prior_owned_draft(previous), prompt)
        report = run(
            root=self.root, live=True, prior_owned_checkpoint=previous,
            readiness=self.ready,
            browser=lambda new, marker, wait: {
                "outcome": "VALID_ATTRIBUTED_RESPONSE",
                "send_click_attempted": True,
                "user_turn_confirmed": True,
                "assistant_response_seen": True,
            })
        self.assertTrue(report["known_owned_draft_replacement"])
        self.assertNotEqual(report["expected_response_marker"],
                            "MICROGEN_CHATGPT_CANARY_A1B2C3D4E5F6_OK")
        again = run(
            root=self.root, live=True, prior_owned_checkpoint=previous,
            readiness=self.ready, browser=lambda *a: self.fail("duplicate"))
        self.assertEqual(again["status"], "EXISTING_CLAIM_REUSED_NO_NEW_SEND")

    def test_tampered_or_previously_clicked_prior_never_qualifies(self):
        previous, _ = self.make_prior(tamper=True)
        with self.assertRaises(ValueError):
            prior_owned_draft(previous)
        claim = previous / "chatgpt_canary_claim.json"
        data = json.loads(claim.read_text())
        data["prompt_sha256"] = hashlib.sha256(
            _prompt_for_marker(data["expected_response_marker"]).encode()).hexdigest()
        claim.write_text(json.dumps(data))
        rfile = previous / "chatgpt_canary_result.json"
        result = json.loads(rfile.read_text())
        result["send_click_attempted"] = True
        rfile.write_text(json.dumps(result))
        with self.assertRaises(ValueError):
            prior_owned_draft(previous)

    def test_no_self_reconciliation_and_no_conflicting_allowlist(self):
        previous, _ = self.make_prior()
        with self.assertRaises(ValueError):
            run(root=previous, prior_owned_checkpoint=previous)
        with self.assertRaises(ValueError):
            run(root=self.root, prior_owned_checkpoint=previous,
                owned_draft_exact="MICROGEN_EDITOR_TYPING_DIAGNOSTIC_52E0")

    def test_visible_2026_chatgpt_said_parser_requires_exact_pair(self):
        marker = "MICROGEN_CHATGPT_CANARY_A1B2C3D4E5F6_OK"
        text = (_prompt_for_marker(marker) + "\nChatGPT said:\n\n"
                + marker + "\n\nChatGPT can make mistakes. Check important info.")
        self.assertTrue(_current_ui_exact_canary(text, marker))
        self.assertFalse(_current_ui_exact_canary(text.replace(
            "ChatGPT said:", "Unknown said:"), marker))
        self.assertFalse(_current_ui_exact_canary(text.replace(
            marker + "\n\nChatGPT can", "WRONG\n\nChatGPT can"), marker))
        self.assertFalse(_current_ui_exact_canary(text + "\n" + marker, marker))

    def test_existing_timeout_reconciled_with_no_new_send(self):
        prior, prompt = self.make_prior(clicked=True)
        result = prior / "chatgpt_canary_result.json"
        obj = json.loads(result.read_text())
        obj["outcome"] = "TIMEOUT_RECONCILE_NO_RESEND"
        result.write_text(json.dumps(obj))
        marker = obj["expected_response_marker"]
        (prior / "chatgpt_send_click_intent.json").write_text(json.dumps({
            "schema_version": 1,
            "status": "SEND_CLICK_INTENT_NOT_DELIVERY_PROOF",
            "expected_response_marker": marker, "one_click_only": True,
        }))
        main = prompt + "\nChatGPT said:\n\n" + marker + (
            "\n\nChatGPT can make mistakes. Check important info.")
        snapshot = {"url": "https://chatgpt.com/c/synthetic-owned",
                    "main_text": main, "stop_visible": False}
        first = reconcile_existing(root=prior, snapshots=[snapshot])
        self.assertEqual(first["status"],
                         "CHATGPT_CANARY_EXACT_RESPONSE_INDEPENDENTLY_VERIFIED")
        self.assertTrue(first["exact_marker_response_confirmed"])
        self.assertEqual(first["model_submissions_this_call"], 0)
        self.assertFalse(first["original_timeout_receipt_overwritten"])
        second = reconcile_existing(root=prior, snapshots=[])
        self.assertEqual(second["status"], "PRIOR_RECONCILIATION_REUSED_NO_SEND")

    def test_reconcile_missing_or_nonconforming_response_fails_closed(self):
        prior, prompt = self.make_prior(clicked=True)
        rpath = prior / "chatgpt_canary_result.json"
        r = json.loads(rpath.read_text())
        r["outcome"] = "TIMEOUT_RECONCILE_NO_RESEND"
        rpath.write_text(json.dumps(r))
        marker = r["expected_response_marker"]
        (prior / "chatgpt_send_click_intent.json").write_text(json.dumps({
            "status": "SEND_CLICK_INTENT_NOT_DELIVERY_PROOF",
            "expected_response_marker": marker, "one_click_only": True,
        }))
        snapshot = {"url": "https://chatgpt.com/c/owned",
                    "main_text": prompt + "\nChatGPT said:\n\nWRONG",
                    "stop_visible": False}
        rejected = reconcile_existing(root=prior, snapshots=[snapshot])
        self.assertEqual(rejected["status"],
                         "RESPONSE_NOT_INDEPENDENTLY_VERIFIED_NO_SEND")
        self.assertFalse((prior / "chatgpt_canary_independent_reconciliation.json").exists())

    def test_expected_marker_is_exact_single_line(self):
        self.assertEqual(expected_text("ABC012"),
                         "MICROGEN_CHATGPT_CANARY_ABC012_OK")


if __name__ == "__main__":
    unittest.main()
