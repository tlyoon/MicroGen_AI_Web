"""Regression: repeated owned Gemini Thinking inspection after uploads has no menu click."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from tests.test_gemini_adaptive_ui_thinking import AdaptiveBrowser
from selenium_pipeline import gemini_thinking as logic


class AfterUploadBrowser(AdaptiveBrowser):
    def __init__(self):
        super().__init__(mode="flash", level="medium")
        self.block_overlay = False
        self.picker.name = "owned thinking"
        self.session_id = "sandbox-session"

    def picker_label(self):
        family = {"flash": "Flash", "flash-lite": "Flash-Lite", "pro": "Pro"}[self.mode]
        return "Open mode picker, currently " + family + " " + self.level.title()


class ThinkingPreSendReuseTests(unittest.TestCase):
    def setUp(self):
        logic._VERIFIED_THINKING_BY_TAB.clear()

    def tearDown(self):
        logic._VERIFIED_THINKING_BY_TAB.clear()

    def test_pre_send_reuses_verified_radio_without_overlay_click(self):
        browser = AfterUploadBrowser()
        self.assertEqual(logic.assert_owned_gemini_thinking_level(
            browser, "owned", "medium"), "medium")
        before = len(browser.events)
        with patch.object(browser.picker, "click",
                          side_effect=RuntimeError("element not interactable")):
            self.assertEqual(logic.assert_owned_gemini_thinking_level(
                browser, "owned", "medium"), "medium")
        self.assertEqual(len(browser.events), before)

    def test_already_selected_medium_is_cached_before_upload(self):
        browser = AfterUploadBrowser()
        self.assertEqual(logic.select_owned_gemini_thinking_level(
            browser, "owned", level="medium", timeout=1), "medium")
        before = len(browser.events)
        with patch.object(browser.picker, "click",
                          side_effect=RuntimeError("element not interactable")):
            self.assertEqual(logic.assert_owned_gemini_thinking_level(
                browser, "owned", "medium"), "medium")
        self.assertEqual(len(browser.events), before)

    def test_changed_label_and_tab_cannot_reuse_old_radio(self):
        browser = AfterUploadBrowser()
        logic.assert_owned_gemini_thinking_level(browser, "owned", "medium")
        browser.mode = "pro"
        self.assertFalse(logic._read_only_reuse_verified_level(
            browser, "owned", "medium"))
        browser.mode = "flash"
        browser.current_window_handle = "other-tab"
        with self.assertRaises(logic.GeminiThinkingError):
            logic._read_only_reuse_verified_level(browser, "owned", "medium")

    def test_stale_level_and_unproved_level_cannot_reuse(self):
        browser = AfterUploadBrowser()
        self.assertFalse(logic._read_only_reuse_verified_level(
            browser, "owned", "medium"))
        logic.assert_owned_gemini_thinking_level(browser, "owned", "medium")
        self.assertFalse(logic._read_only_reuse_verified_level(
            browser, "owned", "high"))
        key = logic._tab_key(browser, "owned")
        level, label, observed = logic._VERIFIED_THINKING_BY_TAB[key]
        logic._VERIFIED_THINKING_BY_TAB[key] = (
            level, label, observed-logic._PROOF_TTL_SECONDS-1)
        self.assertFalse(logic._read_only_reuse_verified_level(
            browser, "owned", "medium"))


if __name__ == "__main__":
    unittest.main()
