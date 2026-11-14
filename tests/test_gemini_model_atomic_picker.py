"""Long-composer Gemini picker drift: atomic DOM read before one claimed Send.

Source-free fake DOM and browser only. No Gemini requests, images, paid API,
Send click, automatic retries of a source, or production tab mutations.
"""
import unittest

from selenium_pipeline.gemini_model import (
    GeminiModelError, _owned_picker, assert_owned_gemini_mode,
)


class Element:
    def __init__(self, ident="flash", label="Open mode picker, currently Flash Medium"):
        self.id = ident
        self.label = label
        self.text = "Flash"

    def get_attribute(self, name):
        return {"aria-label": self.label,
                "data-test-id": "bard-mode-menu-button"}.get(name)

    def is_displayed(self):
        return True


class SnapshotBrowser:
    def __init__(self, batches, *, owner="owned", url="https://gemini.google.com/app"):
        self.current_window_handle = owner
        self.current_url = url
        self.batches = list(batches)
        self.snapshots = 0
        self.sequential_css_calls = 0
        self.sent = 0

    def execute_script(self, script):
        # Real Chrome's JS command returns deduplicated DOM nodes from ONE
        # synchronous evaluation while Angular updates the long editor.
        assert "document.querySelectorAll" in script
        assert "new Set()" in script
        assert "getComputedStyle" in script
        self.snapshots += 1
        return self.batches.pop(0) if self.batches else []

    def find_elements(self, by, selector):
        self.sequential_css_calls += 1
        raise AssertionError("Unstable multi-query DOM is not authoritative")


class AtomicPickerTests(unittest.TestCase):
    def test_single_logical_control_under_multiple_css_selectors(self):
        browser = SnapshotBrowser([[Element()]])
        selected = assert_owned_gemini_mode(
            browser, "owned", "flash", wait_seconds=0)
        self.assertIn("Flash Medium", selected)
        self.assertEqual(browser.snapshots, 1)
        self.assertEqual(browser.sequential_css_calls, 0)
        self.assertEqual(browser.sent, 0)

    def test_transient_empty_dom_is_only_polled_before_send(self):
        browser = SnapshotBrowser([[], [], [Element()]])
        from unittest.mock import patch
        with patch("selenium_pipeline.gemini_model.time.sleep"):
            selected = assert_owned_gemini_mode(
                browser, "owned", "flash", wait_seconds=1)
        self.assertIn("Flash Medium", selected)
        self.assertEqual(browser.snapshots, 3)
        self.assertEqual(browser.sent, 0)

    def test_two_simultaneous_distinct_pickers_are_never_guessed(self):
        browser = SnapshotBrowser([[Element("a"), Element("b")]])
        with self.assertRaisesRegex(GeminiModelError, "NOT_UNIQUE_OR_MISSING"):
            assert_owned_gemini_mode(browser, "owned", wait_seconds=0)
        self.assertEqual(browser.sent, 0)

    def test_flash_lite_is_rejected_without_sending_or_retrying(self):
        browser = SnapshotBrowser([[Element(label="Open mode picker, currently Flash-Lite")]])
        with self.assertRaisesRegex(GeminiModelError, "FAMILY_MISMATCH"):
            assert_owned_gemini_mode(browser, "owned", "flash", wait_seconds=4)
        self.assertEqual(browser.snapshots, 1)
        self.assertEqual(browser.sent, 0)

    def test_foreign_tab_and_foreign_origin_rejected_before_inspecting_dom(self):
        for kw in ({"owner":"foreign"}, {"url":"https://unrelated.example/" }):
            browser = SnapshotBrowser([[Element()]], **kw)
            with self.assertRaises(GeminiModelError):
                assert_owned_gemini_mode(browser, "owned", wait_seconds=4)
            self.assertEqual(browser.snapshots, 0)

    def test_real_vendor_send_entrypoint_verifies_atomic_control_twice(self):
        import os
        from unittest.mock import patch
        from selenium_pipeline.series_gemini import _vendor_module
        from selenium_pipeline import gemini_selenium_only_policy as policy
        vendor = _vendor_module()
        client = vendor.GeminiSeleniumClient.__new__(vendor.GeminiSeleniumClient)
        browser = SnapshotBrowser([[Element()], [Element()]])
        client.driver = browser
        client._automation_tab = "owned"
        clicks = []
        with patch.dict(os.environ, {
                "MICROGEN_SINGLE_PROVIDER_SEND": "1",
                "MICROGEN_GEMINI_UI_MODE": "flash",
                "MICROGEN_GEMINI_THINKING_LEVEL": "medium"}), \
             patch("selenium_pipeline.gemini_thinking.assert_owned_gemini_thinking_level",
                   return_value="medium"), \
             patch.object(policy, "click_one_owned_gemini_send",
                          side_effect=lambda *a: clicks.append("ONE") or True), \
             patch.object(policy, "owned_gemini_send_baseline",
                          return_value={"safe":True}), \
             patch.object(policy, "observe_gemini_send_registration",
                          return_value={"registered":True,
                                        "status":"NEW_USER_TURN_AND_COMPOSER_CLEARED"}):
            self.assertTrue(client.click_send_with_fallbacks(retries=1))
        self.assertEqual(browser.snapshots, 2)
        self.assertEqual(browser.sequential_css_calls, 0)
        self.assertEqual(clicks, ["ONE"])

    def test_real_vendor_boundary_refuses_two_atomic_controls_no_send(self):
        import os
        from unittest.mock import patch
        from selenium_pipeline.series_gemini import _vendor_module
        from selenium_pipeline import gemini_selenium_only_policy as policy
        vendor = _vendor_module()
        client = vendor.GeminiSeleniumClient.__new__(vendor.GeminiSeleniumClient)
        client.driver = SnapshotBrowser([[Element("first"), Element("second")]])
        client._automation_tab = "owned"
        with patch.dict(os.environ, {"MICROGEN_SINGLE_PROVIDER_SEND":"1"}), \
             patch.object(policy, "click_one_owned_gemini_send",
                          side_effect=AssertionError("NEVER_SEND")):
            # The only allowed recovery is to STOP safely before a click.
            from unittest.mock import patch as mock_patch
            with mock_patch("selenium_pipeline.gemini_model.time.sleep"):
                # Real pre-Send path waits briefly, then fails closed.
                with self.assertRaisesRegex(GeminiModelError, "NOT_UNIQUE_OR_MISSING"):
                    client.click_send_with_fallbacks(retries=1)


if __name__ == "__main__":
    unittest.main()
