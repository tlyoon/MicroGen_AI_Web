"""Source-free regressions for the only approved generation route.

No real browser, model request, API, paid TTS, original PDF or publication.
"""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr

from selenium_pipeline.gemini_selenium_only_policy import (
    GeminiSeleniumTemporaryFailure, prepare_with_bounded_retries,
    click_one_owned_gemini_send, emit_temporary_failure,
)


class MockClient:
    def __init__(self, index):
        self.index = index
        self.shutdown_count = 0

    def shutdown(self):
        self.shutdown_count += 1


class MockButton:
    def __init__(self, error=False):
        self.calls = 0
        self.error = error

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def click(self):
        self.calls += 1
        if self.error:
            raise RuntimeError("click may have submitted")


class MockModePicker:
    """Actual read-only owned-tab model control, distinct from Send."""
    def is_displayed(self):
        return True

    def get_attribute(self, name):
        return ("Open mode picker, currently Flash"
                if name == "aria-label" else None)


class MockDriver:
    current_window_handle = "gemini-owned"
    current_url = "https://gemini.google.com/app"

    def __init__(self, buttons):
        self.buttons = buttons
        self.selectors = []
        self.mode_pickers = [MockModePicker()]

    def find_elements(self, by, selector):
        self.selectors.append((by, selector))
        if selector == 'button[aria-label^="Open mode picker"]':
            return self.mode_pickers
        return self.buttons


class GeminiSeleniumOnlyPolicyTests(unittest.TestCase):
    def test_two_proven_presend_failures_then_success_without_send(self):
        created, sleeps = [], []
        def create():
            obj = MockClient(len(created))
            created.append(obj)
            return obj
        def prepare(client):
            if client.index < 2:
                raise TimeoutError("browser mode selector not ready")
        accepted = prepare_with_bounded_retries(
            make_client=create, prepare_without_send=prepare,
            dispose=lambda c: c.shutdown(), sleeper=sleeps.append)
        self.assertIs(accepted, created[-1])
        self.assertEqual(len(created), 3)
        self.assertEqual([x.shutdown_count for x in created], [1, 1, 0])
        self.assertEqual(sleeps, [0.5, 1.0])

    def test_three_failed_presend_attempts_stop_with_no_fallback(self):
        clients = []
        def create():
            obj = MockClient(len(clients))
            clients.append(obj)
            return obj
        with self.assertRaisesRegex(
                GeminiSeleniumTemporaryFailure, "at most 3 attempts"):
            prepare_with_bounded_retries(
                make_client=create,
                prepare_without_send=lambda c: (_ for _ in ()).throw(
                    TimeoutError("model mode not ready")),
                dispose=lambda c: c.shutdown(),
                sleeper=lambda _: None)
        self.assertEqual(len(clients), 3)
        self.assertTrue(all(c.shutdown_count == 1 for c in clients))

    def test_authentication_or_challenge_stops_without_retries(self):
        tried = []
        with self.assertRaises(GeminiSeleniumTemporaryFailure):
            prepare_with_bounded_retries(
                make_client=lambda: tried.append(1) or MockClient(0),
                prepare_without_send=lambda c: (_ for _ in ()).throw(
                    PermissionError("browser verification challenge")),
                dispose=lambda c: c.shutdown(),
                sleeper=lambda _: self.fail("No security challenge retry"))
        self.assertEqual(len(tried), 1)

    def test_only_one_exact_visible_send_click(self):
        button = MockButton()
        driver = MockDriver([button])
        self.assertTrue(click_one_owned_gemini_send(driver, "gemini-owned"))
        self.assertEqual(button.calls, 1)
        self.assertEqual(len(driver.selectors), 1)
        self.assertIn('Send message', driver.selectors[0][1])

    def test_uncertain_click_never_falls_through_to_a_second_send(self):
        button = MockButton(error=True)
        driver = MockDriver([button])
        self.assertFalse(click_one_owned_gemini_send(driver, "gemini-owned"))
        self.assertEqual(button.calls, 1)

    def test_unowned_tab_and_ambiguous_buttons_cannot_send(self):
        button = MockButton()
        driver = MockDriver([button])
        with self.assertRaises(GeminiSeleniumTemporaryFailure):
            click_one_owned_gemini_send(driver, "different-tab")
        self.assertEqual(button.calls, 0)
        driver = MockDriver([button, MockButton()])
        with self.assertRaises(GeminiSeleniumTemporaryFailure):
            click_one_owned_gemini_send(driver, "gemini-owned")
        self.assertEqual(button.calls, 0)

    def test_vendored_production_gemini_adapter_never_clicks_twice(self):
        from unittest.mock import patch
        from selenium_pipeline.series_gemini import _vendor_module
        from selenium_pipeline import runner
        import os

        button = MockButton()
        driver = MockDriver([button])
        vendor = _vendor_module()
        client = vendor.GeminiSeleniumClient.__new__(
            vendor.GeminiSeleniumClient)
        client.driver = driver
        client._automation_tab = "gemini-owned"
        with patch.dict(os.environ, {"MICROGEN_SINGLE_PROVIDER_SEND": "1"}):
            self.assertTrue(client.click_send_with_fallbacks(retries=3))
        self.assertEqual(button.calls, 1)

    def test_vendored_shared_send_emits_actual_registration_proof(self):
        from contextlib import redirect_stdout
        from unittest.mock import patch
        from selenium_pipeline.series_gemini import _vendor_module
        import os

        vendor = _vendor_module()
        cases = (
            ("NEW_USER_TURN_AND_COMPOSER_CLEARED", "new-user-turn"),
            ("NEW_MODEL_RESPONSE_AND_COMPOSER_CLEARED", "new-model-response"),
            ("NEW_CONVERSATION_ROUTE_AND_COMPOSER_CLEARED", "new-conversation-route"),
        )
        for status, marker in cases:
            with self.subTest(status=status):
                button = MockButton()
                driver = MockDriver([button])
                client = vendor.GeminiSeleniumClient.__new__(
                    vendor.GeminiSeleniumClient)
                client.driver = driver
                client._automation_tab = "gemini-owned"
                output = io.StringIO()
                with (patch.dict(os.environ, {"MICROGEN_SINGLE_PROVIDER_SEND": "1"}),
                      patch("selenium_pipeline.gemini_selenium_only_policy.owned_gemini_send_baseline",
                            return_value={"users": 0, "models": 0, "editor_length": 70, "route": "/app"}) as baseline,
                      patch("selenium_pipeline.gemini_selenium_only_policy.observe_gemini_send_registration",
                            return_value={"status": status, "registered": True}) as observer,
                      redirect_stdout(output)):
                    self.assertTrue(client.click_send_with_fallbacks(retries=3))
                self.assertEqual(button.calls, 1)
                baseline.assert_called_once_with(driver, "gemini-owned")
                self.assertEqual(observer.call_count, 1)
                self.assertIn(
                    "Gemini submission registered via " + marker +
                    "+composer-cleared.", output.getvalue())

    def test_vendored_missing_registration_never_fakes_proof_or_resends(self):
        from contextlib import redirect_stdout
        from unittest.mock import patch
        from selenium_pipeline.series_gemini import _vendor_module
        import os
        button = MockButton()
        driver = MockDriver([button])
        vendor = _vendor_module()
        client = vendor.GeminiSeleniumClient.__new__(vendor.GeminiSeleniumClient)
        client.driver = driver
        client._automation_tab = "gemini-owned"
        output = io.StringIO()
        with (patch.dict(os.environ, {"MICROGEN_SINGLE_PROVIDER_SEND": "1"}),
              patch("selenium_pipeline.gemini_selenium_only_policy.owned_gemini_send_baseline",
                    return_value={"users": 0, "models": 0, "editor_length": 70, "route": "/app"}),
              patch("selenium_pipeline.gemini_selenium_only_policy.observe_gemini_send_registration",
                    return_value={"status": "NO_POSITIVE_NEW_USER_TURN_AFTER_CLICK",
                                  "registered": False}) as observer,
              redirect_stdout(output)):
            self.assertTrue(client.click_send_with_fallbacks(retries=3))
        self.assertEqual(button.calls, 1)
        observer.assert_called_once()
        self.assertNotIn("Gemini submission registered via ", output.getvalue())
        self.assertIn("possible Send remains uncertain", output.getvalue())

    def test_runner_refuses_explicit_non_selenium_generation_modes(self):
        from selenium_pipeline import runner
        import os
        from unittest.mock import patch
        with self.assertRaises(SystemExit) as result:
            runner.main(["--communication-mode", "api", "--dry-run",
                         "--subchapter", "22.1"])
        self.assertEqual(result.exception.code, 2)
        with patch.dict(os.environ, {"MICROGEN_COMMUNICATION_MODE":"fallback"}):
            with self.assertRaisesRegex(RuntimeError, "Selenium-only"):
                runner.execute(object())

    def test_new_user_turn_registration_requires_composer_clear(self):
        from selenium_pipeline.gemini_selenium_only_policy import (
            owned_gemini_send_baseline, observe_gemini_send_registration)
        import itertools
        class Owned:
            current_window_handle = "gemini-owned"
            current_url = "https://gemini.google.com/app"
            def __init__(self):
                self.reads = iter([
                    {"users":0,"models":0,"editor_length":85,
                     "route":"/app","origin":"https://gemini.google.com"},
                    {"users":0,"models":0,"editor_length":85,
                     "route":"/app","origin":"https://gemini.google.com"},
                    {"users":1,"models":0,"editor_length":0,
                     "route":"/app/unique","origin":"https://gemini.google.com"},
                ])
            def execute_script(self, _script):
                return next(self.reads)
        d=Owned()
        before=owned_gemini_send_baseline(d,"gemini-owned")
        ticks=iter([0.0,0.2,0.4,0.6])
        status=observe_gemini_send_registration(
            d,"gemini-owned",before,wait_s=0.5,poll_s=0.1,
            clock=lambda:next(ticks),sleep=lambda _:None)
        self.assertTrue(status["registered"])
        self.assertEqual(status["status"],
                         "NEW_USER_TURN_AND_COMPOSER_CLEARED")

    def test_no_new_turn_stays_unattributed_without_another_click(self):
        from selenium_pipeline.gemini_selenium_only_policy import (
            observe_gemini_send_registration)
        class Owned:
            current_window_handle = "gemini-owned"
            current_url = "https://gemini.google.com/app"
            def execute_script(self, _):
                return {"users":0,"models":0,"editor_length":0,
                        "route":"/app","origin":"https://gemini.google.com"}
        ticks=iter([0.0,0.2,0.4,0.6,0.8,1.0])
        status=observe_gemini_send_registration(
            Owned(),"gemini-owned",
            {"users":0,"models":0,"editor_length":90,"route":"/app"},
            wait_s=0.5,poll_s=0.1,clock=lambda:next(ticks),
            sleep=lambda _:None)
        self.assertFalse(status["registered"])
        self.assertEqual(status["status"],
                         "NO_POSITIVE_NEW_USER_TURN_AFTER_CLICK")

    def test_missing_pre_send_baseline_blocks_before_click(self):
        from selenium_pipeline.gemini_selenium_only_policy import (
            owned_gemini_send_baseline, GeminiSeleniumPreSendBlocked)
        class Owned:
            current_window_handle = "gemini-owned"
            current_url = "https://gemini.google.com/app"
            def execute_script(self, _):
                return {"users":0,"models":0,"editor_length":0,
                        "route":"/app","origin":"https://gemini.google.com"}
        with self.assertRaises(GeminiSeleniumPreSendBlocked):
            owned_gemini_send_baseline(Owned(),"gemini-owned")

    def test_stop_message_is_printed_in_stdout_free_form_and_no_provider_change(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            emit_temporary_failure("uncertain model response",
                                   may_have_submitted=True)
        text = stderr.getvalue()
        self.assertIn("Gemini Selenium temporary failure", text)
        self.assertIn("STOPPED", text)
        self.assertIn("No ChatGPT or Gemini API fallback", text)
        self.assertIn("saved response quarantine", text)


if __name__ == "__main__":
    unittest.main()
