"""Native-Windows offline tests of production ChatGPT single-submit transport."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.windows_chatgpt_once_transport import (
    ChatGPTPreSendBlocked, ChatGPTUncertainSubmission,
    extract_current_chatgpt_reply, find_exact_self_authored_draft,
    write_click_intent, submit_one_in_owned_tab, chatgpt_once,
)


PROMPT = '{"source":"vetted","action":"return exact JSON only"}'
REPLY = '{"associations":[],"slide":1}'
TRANSCRIPT = (
    "Share\nToday\nYou said:\n" + PROMPT
    + "\nChatGPT said:\n\n" + REPLY
    + "\n\nChatGPT can make mistakes. Check important info.\nLatest response\n"
)


class FakeEditable:
    def __init__(self, driver):
        self.driver = driver
    def is_displayed(self):
        return True
    def is_enabled(self):
        return True
    def click(self):
        return None


class FakeSend:
    def __init__(self, driver):
        self.driver = driver
    def is_displayed(self):
        return True
    def is_enabled(self):
        return True
    def click(self):
        self.driver.clicks += 1
        self.driver.current_url = "https://chatgpt.com/c/owned-transcript"
        if self.driver.raise_click:
            raise RuntimeError("unknown Chrome click delivery")


class FakeDriver:
    def __init__(self, *, draft="", transcript=TRANSCRIPT, raise_click=False):
        self.current_url = "https://chatgpt.com/"
        self.draft = draft
        self.transcript = transcript
        self.clicks = 0
        self.raise_click = raise_click
        self.editor = FakeEditable(self)
        self.send = FakeSend(self)
    def find_elements(self, how, css):
        if css == "button[data-testid='login-button']":
            return []
        if "contenteditable" in css or css == "#prompt-textarea" or "composer-text-input" in css:
            return [self.editor]
        if "send-button" in css:
            return [self.send]
        return []
    def execute_script(self, javascript, *args):
        if ".innerText || '').trim()" in javascript:
            return self.draft
        if "document.execCommand" in javascript:
            self.draft = args[0]
            return True
        if "document.querySelector('main')" in javascript:
            return self.transcript if self.clicks else ""
        return ""


class ProductionTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.click_file = Path(self.temp.name) / "once_click.json"

    def test_current_chatgpt_transcript_json_answer_exact_attribution(self):
        self.assertEqual(extract_current_chatgpt_reply(TRANSCRIPT, PROMPT), REPLY)
        self.assertIsNone(extract_current_chatgpt_reply(TRANSCRIPT, "DIFFERENT"))
        self.assertIsNone(extract_current_chatgpt_reply(TRANSCRIPT.replace(
            "ChatGPT said:", "Assistant:"), PROMPT))
        self.assertIsNone(extract_current_chatgpt_reply(TRANSCRIPT.replace(
            "ChatGPT can make mistakes.", "Message still loading."), PROMPT))
        self.assertIsNone(extract_current_chatgpt_reply(
            TRANSCRIPT + "\nYou said:\nsecond turn", PROMPT))
        self.assertIsNone(extract_current_chatgpt_reply(
            TRANSCRIPT + "\n" + PROMPT + "\n", PROMPT))

    def test_single_realistic_click_and_stable_full_json_capture(self):
        driver = FakeDriver()
        value = submit_one_in_owned_tab(
            driver, PROMPT, wait_cap_s=10, click_intent_path=self.click_file,
            sleeper=lambda _: None)
        self.assertEqual(value, REPLY)
        self.assertEqual(driver.clicks, 1)
        self.assertTrue(self.click_file.is_file())
        record = json.loads(self.click_file.read_text(encoding="utf8"))
        self.assertEqual(record["status"], "CHATGPT_CLICK_INTENT_NOT_DELIVERY_PROOF")
        self.assertNotIn(PROMPT, self.click_file.read_text(encoding="utf8"))
        with self.assertRaises(ChatGPTPreSendBlocked):
            write_click_intent(self.click_file, PROMPT)

    def test_unowned_draft_blocks_before_send_and_leaves_text(self):
        driver = FakeDriver(draft="User's unrelated unsent work")
        with self.assertRaisesRegex(ChatGPTPreSendBlocked, "UNOWNED_OR_UNCERTAIN"):
            submit_one_in_owned_tab(
                driver, PROMPT, wait_cap_s=10,
                click_intent_path=self.click_file)
        self.assertEqual(driver.clicks, 0)
        self.assertFalse(self.click_file.exists())
        self.assertEqual(driver.draft, "User's unrelated unsent work")

    def test_broken_response_after_click_never_attempts_second_send(self):
        driver = FakeDriver(transcript="You said:\n" + PROMPT)
        count = iter([0, 1, 11])
        with self.assertRaises(ChatGPTUncertainSubmission):
            submit_one_in_owned_tab(
                driver, PROMPT, wait_cap_s=10,
                click_intent_path=self.click_file,
                clock=lambda: next(count), sleeper=lambda _: None)
        self.assertEqual(driver.clicks, 1)
        self.assertTrue(self.click_file.exists())

    def test_uncertain_click_exception_has_durable_intent(self):
        driver = FakeDriver(raise_click=True)
        with self.assertRaises(ChatGPTUncertainSubmission):
            submit_one_in_owned_tab(
                driver, PROMPT, wait_cap_s=10,
                click_intent_path=self.click_file)
        self.assertEqual(driver.clicks, 1)
        self.assertTrue(self.click_file.is_file())

    def test_owned_draft_match_requires_prior_verified_local_receipt(self):
        root = Path(self.temp.name) / "checkpoints"
        owned = root / "owned"
        owned.mkdir(parents=True)
        (owned / "chatgpt_canary_claim.json").write_text("{}")
        with patch("selenium_pipeline.windows_chatgpt_once_transport.prior_owned_draft",
                   return_value="MicroGen test-only prompt"):
            self.assertTrue(find_exact_self_authored_draft(
                "MicroGen test-only prompt", root))
            self.assertFalse(find_exact_self_authored_draft("Other user text", root))
            (owned / "chatgpt_send_click_intent.json").write_text("{}")
            self.assertFalse(find_exact_self_authored_draft(
                "MicroGen test-only prompt", root))


    def test_owned_tab_closed_only_after_verified_capture(self):
        class Browser:
            def __init__(self):
                self.window_handles = ["user_tab"]
                self.current_window_handle = "user_tab"
                self.switch_to = self
                self.closed = []
            def new_window(self, kind):
                self.window_handles.append("microgen_owned_tab")
                self.current_window_handle = "microgen_owned_tab"
            def window(self, handle):
                self.current_window_handle = handle
            def get(self, url):
                assert url == "https://chatgpt.com/"
            def close(self):
                self.closed.append(self.current_window_handle)
                self.window_handles.remove(self.current_window_handle)
        obj = Browser()
        ready = {"status": "AUTHENTICATED_COMPOSER_READY"}
        with patch("selenium_pipeline.rich_mapping_provider_readiness.inspect_provider",
                   return_value=ready), patch(
                       "selenium_pipeline.windows_chatgpt_once_transport."
                       "submit_one_in_owned_tab", return_value=REPLY):
            response = chatgpt_once(
                PROMPT, port=9223, wait_cap_s=12,
                click_intent_path=self.click_file, driver_factory=lambda: obj)
        self.assertEqual(response, REPLY)
        self.assertEqual(obj.closed, ["microgen_owned_tab"])
        self.assertEqual(obj.window_handles, ["user_tab"])

    def test_uncertain_submission_keeps_owned_tab_for_readonly_reconciliation(self):
        class Browser:
            def __init__(self):
                self.window_handles = ["original"]
                self.current_window_handle = "original"
                self.switch_to = self
                self.closed = []
            def new_window(self, kind):
                self.window_handles.append("owned")
                self.current_window_handle = "owned"
            def window(self, handle):
                self.current_window_handle = handle
            def get(self, url):
                pass
            def close(self):
                self.closed.append(self.current_window_handle)
        obj = Browser()
        with patch("selenium_pipeline.rich_mapping_provider_readiness.inspect_provider",
                   return_value={"status": "AUTHENTICATED_COMPOSER_READY"}), patch(
                       "selenium_pipeline.windows_chatgpt_once_transport."
                       "submit_one_in_owned_tab",
                       side_effect=ChatGPTUncertainSubmission(
                           "RESPONSE_CAPTURE_PENDING_RECONCILE_NO_RESEND")):
            with self.assertRaises(ChatGPTUncertainSubmission):
                chatgpt_once(PROMPT,port=9223,wait_cap_s=12,
                             click_intent_path=self.click_file,
                             driver_factory=lambda:obj)
        self.assertEqual(obj.closed, [])
        self.assertIn("owned", obj.window_handles)

    def test_wrong_provider_port_rejected_before_any_browser_attach(self):
        with self.assertRaises(ChatGPTPreSendBlocked):
            chatgpt_once(PROMPT,port=9222,wait_cap_s=12,
                         click_intent_path=self.click_file,
                         driver_factory=lambda:self.fail("no browser attach"))

if __name__ == "__main__":
    unittest.main()
