"""October 2026 Gemini missing-mode-picker recovery (offline mocks)."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from selenium_pipeline.gemini_model import ensure_flash, GeminiModelError


class Picker:
    def is_displayed(self):
        return True

    def get_attribute(self, name):
        return "Open mode picker, currently Flash High"


class Browser:
    def __init__(self, *, url="https://gemini.google.com/app", recover=True):
        self.urls = {"old": url}
        self.active = "old"
        self.recover = recover
        self.draft = "an important saved draft"
        self.fresh_count = 0
        self.closed = []
        self.switched = SimpleNamespace()
        self.switch_to = SimpleNamespace(window=self.switch_window,
                                         new_window=self.new_window)

    @property
    def window_handles(self):
        return list(self.urls)

    @property
    def current_url(self):
        return self.urls[self.active]

    @property
    def current_window_handle(self):
        return self.active

    def switch_window(self, handle):
        self.active = handle

    def new_window(self, kind):
        assert kind == "tab"
        self.fresh_count += 1
        self.active = f"fresh_{self.fresh_count}"
        self.urls[self.active] = "about:blank"

    def get(self, url):
        self.urls[self.active] = url

    def find_elements(self, _by, _selector):
        if self.active.startswith("fresh_") and self.recover:
            return [Picker()]
        return []

    def close(self):
        self.closed.append(self.active)
        del self.urls[self.active]

    def quit(self):
        pass


class GeminiFreshTabRecoveryTests(unittest.TestCase):
    def test_missing_picker_recovered_using_new_tab_without_touching_draft(self):
        driver = Browser()
        with patch("selenium.webdriver.Chrome", return_value=driver):
            label = ensure_flash(timeout=0.01)
        self.assertIn("Flash High", label)
        self.assertEqual(driver.fresh_count, 1)
        self.assertEqual(driver.draft, "an important saved draft")
        self.assertFalse(driver.closed)

    def test_no_authenticated_gemini_tab_does_not_open_new_tab(self):
        driver = Browser(url="https://accounts.google.com/signin")
        with patch("selenium.webdriver.Chrome", return_value=driver):
            with self.assertRaises(GeminiModelError):
                ensure_flash(timeout=0.01)
        self.assertEqual(driver.fresh_count, 0)

    def test_failed_fresh_tab_closes_it_and_refuses_pro_fallback(self):
        driver = Browser(recover=False)
        with patch("selenium.webdriver.Chrome", return_value=driver):
            with self.assertRaises(GeminiModelError):
                ensure_flash(timeout=0.01)
        self.assertEqual(driver.fresh_count, 1)
        self.assertEqual(driver.closed, ["fresh_1"])
        self.assertEqual(driver.active, "old")


if __name__ == "__main__":
    unittest.main()
