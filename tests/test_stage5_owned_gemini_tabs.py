"""Ownership regression: Gemini automation must never reset the user's tab.

The vendored Selenium UI module is loaded explicitly so that its filename
'selenium.py' cannot shadow the installed upstream selenium package.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

SOURCE = Path(__file__).resolve().parents[1] / "selenium_pipeline" / "vendor_template_v2" / "selenium.py"


def load_client():
    spec = importlib.util.spec_from_file_location("_microgen_test_gemini_vendor", SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakePicker:
    def is_displayed(self):
        return True

    def get_attribute(self, key):
        return "Open mode picker, currently Flash High" if key == "aria-label" else None


class FakeSwitch:
    def __init__(self, driver):
        self.driver = driver

    def window(self, handle):
        if handle not in self.driver.window_handles:
            raise ValueError(f"unknown handle: {handle}")
        self.driver.current_window_handle = handle
        self.driver.visited.append(handle)

    def new_window(self, kind):
        assert kind == "tab"
        name = f"owned-{self.driver.new_count}"
        self.driver.new_count += 1
        self.driver.window_handles.append(name)
        self.driver.current_window_handle = name
        self.driver.created.append(name)


class FakeDriver:
    def __init__(self, *, mode_picker=True):
        self.window_handles = ["borrowed-user-chat"]
        self.current_window_handle = self.window_handles[0]
        self.switch_to = FakeSwitch(self)
        self.created = []
        self.closed = []
        self.visited = []
        self.navigated = []
        self.new_count = 0
        self.mode_picker = mode_picker
        self.did_quit = False

    @property
    def current_url(self):
        return "https://gemini.google.com/app"

    def get(self, url):
        self.navigated.append((self.current_window_handle, url))

    def execute_script(self, script, *args):
        # The real client now verifies the lifecycle state of its owned
        # tab before model selection; an already-visible fake page needs
        # no CDP focus emulation or browser-global effects.
        if script == "return document.visibilityState":
            if not self.current_window_handle.startswith("owned-"):
                raise AssertionError("Visibility queried on borrowed browser tab")
            return "visible"
        raise AssertionError("Unexpected Selenium script")

    def find_elements(self, by, selector):
        if 'Open mode picker' in selector:
            return [FakePicker()] if self.mode_picker else []
        if 'Send' in selector and "button" in selector:
            return [SimpleNamespace(is_enabled=lambda: True)]
        if '[contenteditable="true"][role="textbox"]' in selector:
            return [object()]
        return []

    def close(self):
        self.closed.append(self.current_window_handle)
        self.window_handles.remove(self.current_window_handle)
        self.current_window_handle = self.window_handles[0] if self.window_handles else None

    def quit(self):
        self.did_quit = True


class OwnedGeminiTabTests(unittest.TestCase):
    def setUp(self):
        self.module = load_client()
        self.client = self.module.GeminiSeleniumClient(self.module.Config(root=Path.cwd()))
        self.client.driver = FakeDriver()
        self.client.ensure_driver_is_alive = lambda: None
        self.client._clear_prompt_safely = lambda: None

    def test_new_request_uses_fresh_owned_tab_and_never_borrows_user_chat(self):
        self.client.open_clean_gemini_chat()
        first = self.client._automation_tab
        self.assertIn(first, self.client.driver.created)
        self.assertEqual(self.client.driver.closed, [])
        self.assertNotIn("borrowed-user-chat", self.client.driver.visited)
        self.client.open_clean_gemini_chat()
        second = self.client._automation_tab
        self.assertNotEqual(first, second)
        self.assertEqual(self.client.driver.closed, [first])
        self.assertIn("borrowed-user-chat", self.client.driver.window_handles)
        self.assertTrue(all(h.startswith("owned-") for h, url in self.client.driver.navigated))

    def test_shutdown_closes_only_owned_tab(self):
        self.client.open_clean_gemini_chat()
        owned = self.client._automation_tab
        driver = self.client.driver
        self.client.shutdown()
        self.assertIsNone(self.client.driver)
        self.assertIsNone(self.client._automation_tab)
        self.assertEqual(driver.closed, [owned])
        self.assertEqual(driver.window_handles, ["borrowed-user-chat"])

    def test_reconnect_discards_stale_owned_handle_without_closing_borrowed(self):
        self.client._automation_tab = "already-disconnected"
        self.client.open_clean_gemini_chat()
        self.assertEqual(self.client.driver.closed, [])
        self.assertIn("borrowed-user-chat", self.client.driver.window_handles)


if __name__ == "__main__":
    unittest.main()
