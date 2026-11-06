"""General offline Gemini response attribution and no-resend regressions.

No Chrome, credentials, textbook files, network access, or model sends.
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
import time
import unittest
from unittest.mock import patch

from selenium_pipeline.series_gemini import _vendor_module


class FakeClock:
    def __init__(self):
        self.now = 0.0
    def monotonic(self):
        return self.now
    def sleep(self, seconds):
        self.now += seconds


class FakeModel:
    def __init__(self, text):
        self.text = text
    def get_attribute(self, name):
        return self.text if name == "innerText" else None


class FakeWaitDriver:
    def __init__(self, clock, response_after=None):
        self.clock = clock
        self.response_after = response_after
    def find_elements(self, by, selector):
        if (selector == "model-response" and
                self.response_after is not None and
                self.clock.now >= self.response_after):
            return [FakeModel("Independent completed model answer")]
        return []
    def execute_script(self, script):
        assert "return [users.size, models, text]" in script
        if (self.response_after is not None and
                self.clock.now >= self.response_after):
            return [1, 1, ""]
        return [0, 0, ""]


class FakeOwnedDriver:
    def __init__(self, response, handle="owned"):
        self.response = response
        self.current_window_handle = handle
        self.current_url = "https://gemini.google.com/app"
    def execute_script(self, script):
        assert "model-response" in script and "user-query" not in script
        return {"text": self.response, "generating": False}


def load_slide_capture_functions(vendor):
    """Execute only the two production functions; importing full slide authoring
    has unrelated legacy module-level PDF/PATH dependencies and side effects."""
    root = Path(__file__).resolve().parents[1]
    path = (root / "selenium_pipeline" / "vendor_template_v2" /
            "gen_slides_selenium_v11.py")
    parsed = ast.parse(path.read_text(encoding="utf-8"))
    selected = [node for node in parsed.body
                if isinstance(node, ast.FunctionDef) and node.name in (
                    "_reconcile_existing_submitted_slides",
                    "send_prompt_and_capture_transport_block",
                )]
    if len(selected) != 2:
        raise AssertionError("Production slide transport functions missing")
    namespace = {
        "gemsel": vendor,
        "time": time,
        "log": lambda *args: None,
        "extract_fenced_latex_block": lambda raw: "",
        "capture_transport_block_via_copy_icon":
            lambda *args, **kw: (_ for _ in ()).throw(
                vendor.GeminiPostSubmitUnverified("simulated capture timeout")),
        "_wait_until_generation_finishes": lambda *args, **kw: None,
        "extract_longest_codeblock_from_latest_response": lambda *args: "",
        "extract_latest_response_text_from_dom": lambda *args: "",
    }
    exec(compile(ast.fix_missing_locations(
        ast.Module(body=selected, type_ignores=[])), str(path), "exec"),
        namespace)
    return namespace


BEAMER = (
    r"\documentclass{beamer}\begin{document}"
    r"\begin{frame}{Example}Independent physical explanation."
    r"\end{frame}\end{document}"
)


class GeminiPostSubmitNoResendTests(unittest.TestCase):
    def setUp(self):
        self.vendor = _vendor_module()

    def test_blank_conversation_raises_after_bounded_grace_never_returns_success(self):
        clock = FakeClock()
        driver = FakeWaitDriver(clock)
        with patch.object(self.vendor.time, "monotonic", clock.monotonic), \
             patch.object(self.vendor.time, "sleep", clock.sleep):
            with self.assertRaisesRegex(
                    self.vendor.GeminiPostSubmitUnverified,
                    "POST_SUBMIT_NO_ATTRIBUTED_RESPONSE_NO_RESEND"):
                self.vendor._wait_until_generation_finishes(
                    driver, timeout=40, poll=0.5)
        self.assertGreaterEqual(clock.now, 12.0)
        self.assertLess(clock.now, 16.0)

    def test_transient_blank_before_visible_reply_is_not_a_false_failure(self):
        clock = FakeClock()
        driver = FakeWaitDriver(clock, response_after=4.0)
        with patch.object(self.vendor.time, "monotonic", clock.monotonic), \
             patch.object(self.vendor.time, "sleep", clock.sleep):
            self.vendor._wait_until_generation_finishes(
                driver, timeout=40, poll=0.5)
        self.assertLess(clock.now, 12.0)

    def test_clipboard_without_attributed_latest_model_response_is_untrusted(self):
        with patch.object(self.vendor, "_latest_response_container",
                          return_value=None):
            self.assertFalse(
                self.vendor._copied_text_matches_latest_response(
                    object(), "arbitrary personal clipboard content"))
        with patch.object(self.vendor, "_latest_response_container",
                          return_value=object()), patch.object(
                          self.vendor, "_element_visible_text", return_value=""):
            self.assertFalse(
                self.vendor._copied_text_matches_latest_response(
                    object(), BEAMER))
        with patch.object(self.vendor, "_latest_response_container",
                          return_value=object()), patch.object(
                          self.vendor, "_element_visible_text",
                          return_value=BEAMER):
            self.assertTrue(
                self.vendor._copied_text_matches_latest_response(
                    object(), BEAMER))

    def client(self, *, response="Thinking...", handle="owned", registered=True):
        sent = []
        driver = FakeOwnedDriver(response, handle=handle)
        def submit(**kwargs):
            sent.append(kwargs)
            return registered
        return SimpleNamespace(
            driver=driver, _automation_tab="owned",
            type_prompt_text=lambda text, **kw: True,
            click_send_with_fallbacks=submit,
        ), sent

    def test_after_capture_timeout_recover_same_owned_tab_without_resend(self):
        namespace = load_slide_capture_functions(self.vendor)
        client, sends = self.client()
        copied = []
        with patch.object(
            self.vendor, "_copy_via_toolbar_copy_button",
            side_effect=lambda driver: copied.append(driver) or BEAMER,
        ):
            response = namespace["send_prompt_and_capture_transport_block"](
                client, "source-free synthetic Beamer request", wait_cap=15)
        self.assertEqual(response, BEAMER)
        self.assertEqual(sends, [{"retries": 1}])
        self.assertEqual(copied, [client.driver])

    def test_after_capture_timeout_unowned_tab_blocks_recovery_no_resend(self):
        namespace = load_slide_capture_functions(self.vendor)
        client, sends = self.client(handle="user_tab")
        with patch.object(
            self.vendor, "_copy_via_toolbar_copy_button",
            side_effect=AssertionError("Unowned tab must not copy")):
            with self.assertRaisesRegex(
                self.vendor.GeminiPostSubmitUnverified,
                "POST_SUBMIT_NO_ATTRIBUTED_RESPONSE_NO_RESEND"):
                namespace["send_prompt_and_capture_transport_block"](
                    client, "source-free synthetic Beamer request", wait_cap=15)
        self.assertEqual(sends, [{"retries": 1}])

    def test_send_outcome_unverified_not_a_reason_for_another_send(self):
        namespace = load_slide_capture_functions(self.vendor)
        client, sends = self.client(registered=False)
        with self.assertRaisesRegex(
            self.vendor.GeminiPostSubmitUnverified,
            "SEND_OUTCOME_UNVERIFIED_NO_RESEND"):
            namespace["send_prompt_and_capture_transport_block"](
                client, "source-free synthetic request", wait_cap=15)
        self.assertEqual(sends, [{"retries": 1}])

    def test_failure_cannot_be_swallowed_by_slide_attempt_loop(self):
        path = (Path(__file__).resolve().parents[1] / "selenium_pipeline"
                / "vendor_template_v2" / "gen_slides_selenium_v11.py")
        tree = ast.parse(path.read_text(encoding="utf8"))
        funcs = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef)
                 and node.name == "generate_slides_tex"]
        self.assertEqual(len(funcs), 1)
        src = ast.unparse(funcs[0])
        self.assertIn("gemsel.GeminiPostSubmitUnverified", src)
        self.assertIn("raise", src)


if __name__ == "__main__":
    unittest.main()
