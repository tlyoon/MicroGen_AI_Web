"""G2 Pro/Medium genuine nested UI delayed hydration, no-Send regression."""
import time
import unittest
from unittest.mock import patch

from selenium_pipeline import gemini_thinking as th


class DummyOwnedDriver:
    current_window_handle = "owned-gemini-tab"
    current_url = "https://gemini.google.com/app"


class CheckedOption:
    def __init__(self, checked=True):
        self.checked = checked

    def get_attribute(self, name):
        if name == "aria-checked":
            return "true" if self.checked else "false"
        if name == "aria-disabled":
            return "false"
        return None


class NestedThinkingHydrationTests(unittest.TestCase):
    def setUp(self):
        self.driver = DummyOwnedDriver()
        self.radio = CheckedOption()

    def test_delayed_checked_medium_reuses_same_owned_menu(self):
        with patch.object(th, "_thinking_options",
                          side_effect=[[], [], [self.radio]]) as observed:
            with patch.object(th.time, "sleep", return_value=None) as sleeps:
                choices = th._await_owned_nested_thinking_options(
                    self.driver, "owned-gemini-tab", "medium",
                    deadline=time.monotonic()+2)
        self.assertEqual(choices, [self.radio])
        self.assertEqual(observed.call_count, 3)
        self.assertEqual(sleeps.call_count, 2)

    def test_unregistered_recovery_rejects_before_any_dom_read(self):
        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value=None):
            with patch.object(th, "_thinking_options") as observed:
                with self.assertRaisesRegex(th.GeminiThinkingError,
                                            "NOT_REGISTERED"):
                    th._await_owned_nested_thinking_options(
                        self.driver, "owned-gemini-tab", "medium",
                        deadline=time.monotonic()+2)
                observed.assert_not_called()

    def test_foreign_tab_never_reuses_proof_or_retries(self):
        with patch.object(th, "_thinking_options") as observed:
            with self.assertRaisesRegex(th.GeminiThinkingError, "FOREIGN"):
                th._await_owned_nested_thinking_options(
                    self.driver, "foreign-tab", "medium",
                    deadline=time.monotonic()+2)
            observed.assert_not_called()

    def test_ambiguous_delayed_medium_fails_closed(self):
        with patch.object(th, "_thinking_options",
                          side_effect=[[], [self.radio, CheckedOption()]]) as seen:
            with patch.object(th.time, "sleep", return_value=None):
                with self.assertRaisesRegex(th.GeminiThinkingError,
                                            "AMBIGUOUS"):
                    th._await_owned_nested_thinking_options(
                        self.driver, "owned-gemini-tab", "medium",
                        deadline=time.monotonic()+2)
        self.assertEqual(seen.call_count, 2)

    def test_missing_nested_medium_remains_unqualified(self):
        with patch.object(th, "_thinking_options", return_value=[]) as find:
            with patch.object(th.time, "sleep", return_value=None):
                result = th._await_owned_nested_thinking_options(
                    self.driver, "owned-gemini-tab", "medium",
                    deadline=time.monotonic()+1)
        self.assertEqual(result, [])
        self.assertEqual(find.call_count, 5)

    def test_full_presend_select_waits_after_expander_without_resend(self):
        picker = object()
        with patch.object(th, "_expand_for_thinking", return_value=picker) as opened:
            with patch.object(th, "_thinking_options",
                              side_effect=[[], [], [self.radio]]) as found:
                with patch.object(th, "_remember_level_verified_by_radio") as remembered:
                    with patch.object(th, "_close_picker") as closed:
                        with patch.object(th.time, "sleep", return_value=None):
                            self.assertEqual(th.select_owned_gemini_thinking_level(
                                self.driver, "owned-gemini-tab", level="medium",
                                timeout=2), "medium")
        opened.assert_called_once()
        self.assertEqual(found.call_count, 3)
        remembered.assert_called_once_with(
            self.driver, "owned-gemini-tab", "medium")
        closed.assert_called_once_with(
            self.driver, "owned-gemini-tab", picker)

    def test_independent_exact_radio_assert_waits_after_expander(self):
        picker = object()
        with patch.object(th, "_read_only_reuse_verified_level",
                          return_value=False):
            with patch.object(th, "_expand_for_thinking", return_value=picker):
                with patch.object(th, "_thinking_options",
                                  side_effect=[[], [], [self.radio]]):
                    with patch.object(th, "_remember_level_verified_by_radio") as remember:
                        with patch.object(th, "_close_picker") as close:
                            with patch.object(th.time, "sleep", return_value=None):
                                self.assertEqual(
                                    th.assert_owned_gemini_thinking_level(
                                        self.driver, "owned-gemini-tab",
                                        level="medium"), "medium")
        remember.assert_called_once()
        close.assert_called_once_with(self.driver, "owned-gemini-tab", picker)

    def test_visible_but_unchecked_medium_is_not_accepted(self):
        picker = object()
        with patch.object(th, "_read_only_reuse_verified_level",
                          return_value=False):
            with patch.object(th, "_expand_for_thinking", return_value=picker):
                with patch.object(th, "_thinking_options",
                                  side_effect=[[], [CheckedOption(False)]]):
                    with patch.object(th, "_close_picker"):
                        with patch.object(th.time, "sleep", return_value=None):
                            with self.assertRaisesRegex(
                                th.GeminiThinkingError, "NOT_VERIFIED"):
                                th.assert_owned_gemini_thinking_level(
                                    self.driver, "owned-gemini-tab",
                                    level="medium")


if __name__ == "__main__":
    unittest.main()
