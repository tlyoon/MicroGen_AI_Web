"""Regression tests for Gemini stale-draft handling (no browser/login needed)."""
import unittest

from selenium_pipeline.vendor_template_v2.selenium import GeminiSeleniumClient


class FakeEditor:
    tag_name = "div"

    def __init__(self, draft="", *, keyboard_clears=True):
        self.draft = draft
        self.keyboard_clears = keyboard_clears
        self.text = "Enter a prompt here"  # A placeholder must not count as a draft.

    def is_displayed(self):
        return True

    def get_attribute(self, name):
        return {"contenteditable": "true", "textContent": self.draft}.get(name)

    def click(self):
        pass

    def send_keys(self, *keys):
        if self.keyboard_clears and any(str(k).lower().endswith("backspace") or k == "\ue003" for k in keys):
            self.draft = ""


class FakeWrapper(FakeEditor):
    def get_attribute(self, name):
        if name == "contenteditable":
            return None
        return super().get_attribute(name)


class FakeDriver:
    def __init__(self, editor, *, wrapper=None, js_clears=False):
        self.editor = editor
        self.wrapper = wrapper
        self.js_clears = js_clears
        self.script_calls = 0

    def find_elements(self, _by, selector):
        if self.wrapper and selector.startswith("div[aria-label"):
            return [self.wrapper]
        return [self.editor]

    def execute_script(self, *args):
        self.script_calls += 1
        if self.js_clears:
            self.editor.draft = ""


def client_for(driver):
    client = GeminiSeleniumClient.__new__(GeminiSeleniumClient)
    client.driver = driver
    return client


class GeminiComposerGuardTests(unittest.TestCase):
    def test_empty_editable_does_not_mistake_placeholder_for_draft(self):
        editor = FakeEditor("")
        client = client_for(FakeDriver(editor))
        self.assertEqual(client._prompt_editable_text(editor), "")
        client._clear_prompt_safely()
        self.assertEqual(editor.draft, "")

    def test_refuses_noneditable_wrapper(self):
        editor = FakeEditor("")
        wrapper = FakeWrapper("Enter a prompt here")
        client = client_for(FakeDriver(editor, wrapper=wrapper))
        self.assertIs(client._get_prompt_editable(), editor)

    def test_keyboard_clear_must_be_verified(self):
        editor = FakeEditor("old unanswered prompt")
        client = client_for(FakeDriver(editor))
        client._clear_prompt_safely()
        self.assertEqual(editor.draft, "")

    def test_js_selection_clear_is_verified(self):
        editor = FakeEditor("old prompt", keyboard_clears=False)
        driver = FakeDriver(editor, js_clears=True)
        client = client_for(driver)
        client._clear_prompt_safely()
        self.assertGreater(driver.script_calls, 0)
        self.assertEqual(editor.draft, "")

    def test_uncleared_draft_fails_closed(self):
        editor = FakeEditor("old prompt", keyboard_clears=False)
        client = client_for(FakeDriver(editor))
        with self.assertRaisesRegex(RuntimeError, "stale draft"):
            client._clear_prompt_safely()
        self.assertEqual(editor.draft, "old prompt")


if __name__ == "__main__":
    unittest.main()
