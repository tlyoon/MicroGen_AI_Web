"""Selenium provider port isolation and manual ChatGPT login: no prompts."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.launch_gemini import (
    ALT_PORT, DEFAULT_PORT, CHATGPT_RESERVED_PORT, launch,
)
from selenium_pipeline.runner import Settings, execute
from selenium_pipeline.rich_mapping_provider_readiness import DEFAULT_PORTS
from selenium_pipeline.windows_chatgpt_login_recovery import (
    inspect_login, focus_existing_login_tab,
)


class FakeDriver:
    def __init__(self):
        self.window_handles = ["unrelated", "chatgpt_tab"]
        self.switch_to = self
        self.current_url = ""
        self.focus_calls = 0
        self.navigations = []

    def window(self, handle):
        self.current_url = (
            "https://gemini.google.com/app"
            if handle == "unrelated" else "https://chatgpt.com/"
        )

    def execute_cdp_cmd(self, cmd, params):
        assert cmd == "Page.bringToFront"
        self.focus_calls += 1

    def get(self, url):
        self.navigations.append(url)


class ProviderPortIsolationTests(unittest.TestCase):
    @patch("selenium_pipeline.windows_chatgpt_login_recovery.sys.platform", "win32")
    def test_readonly_login_status_distinguishes_auth_and_guest(self):
        def guest(provider, port):
            return {
                "provider": provider, "debug_port": port,
                "status": "LOGIN_REQUIRED",
                "authenticated_ui_ready": False,
                "model_submission_performed": False,
            }
        r = inspect_login(browser_check=guest)
        self.assertEqual(r["status"],
                         "CHATGPT_MANUAL_LOGIN_REQUIRED_IN_EXISTING_PROFILE")
        self.assertTrue(r["manual_login_required"])
        self.assertFalse(r["authenticated_chatgpt_session"])
        self.assertFalse(r["browser_prompt_submitted"])
        self.assertFalse(r["password_or_cookies_read_or_transferred"])
        self.assertFalse(r["automatic_existing_source_resubmission_authorized"])
        self.assertFalse(r["student_publication_authorized"])

        def authenticated(provider, port):
            return dict(guest(provider, port),
                        status="AUTHENTICATED_COMPOSER_READY",
                        authenticated_ui_ready=True)
        good = inspect_login(browser_check=authenticated)
        self.assertTrue(good["authenticated_chatgpt_session"])
        self.assertFalse(good["manual_login_required"])
        self.assertFalse(good["new_model_or_tts_calls"])

    @patch("selenium_pipeline.windows_chatgpt_login_recovery.sys.platform", "win32")
    def test_guest_composer_cannot_masquerade_as_login(self):
        r = inspect_login(browser_check=lambda provider, port: {
            "provider": provider, "debug_port": port,
            "status": "LOGIN_REQUIRED",
            "authenticated_ui_ready": True,
            "model_submission_performed": False,
        })
        self.assertFalse(r["authenticated_chatgpt_session"])

    @patch("selenium_pipeline.windows_chatgpt_login_recovery.sys.platform", "win32")
    def test_focus_only_existing_chatgpt_tab_no_navigate_or_send(self):
        fake = FakeDriver()
        focused = focus_existing_login_tab(browser_factory=lambda port: fake)
        self.assertTrue(focused)
        self.assertEqual(fake.focus_calls, 1)
        self.assertEqual(fake.navigations, [])
        self.assertEqual(len(fake.window_handles), 2)

    @patch("selenium_pipeline.windows_chatgpt_login_recovery.sys.platform", "win32")
    def test_explicit_wrong_port_rejected_before_browser(self):
        for port in (9222, 9225, 9224):
            with self.subTest(port=port):
                with self.assertRaises(ValueError):
                    inspect_login(port=port, browser_check=lambda *a:
                                  self.fail("wrong port should not connect"))
                with self.assertRaises(ValueError):
                    focus_existing_login_tab(port=port,
                                             browser_factory=lambda *a:
                                             self.fail("wrong port should not connect"))

    def test_port_contract_never_overlaps(self):
        self.assertEqual(DEFAULT_PORT, 9222)
        self.assertEqual(ALT_PORT, 9225)
        self.assertEqual(CHATGPT_RESERVED_PORT, 9223)
        self.assertEqual(DEFAULT_PORTS["chatgpt"], 9223)
        self.assertEqual(len({DEFAULT_PORT, ALT_PORT,
                              DEFAULT_PORTS["chatgpt"]}), 3)

    def test_explicit_gemini_chatgpt_port_rejected_before_any_browser(self):
        with patch("selenium_pipeline.launch_gemini.ready",
                   side_effect=AssertionError("should not contact Chrome")):
            with self.assertRaisesRegex(ValueError, "ChatGPT"):
                launch(alternate_user="other", port=9223)

    def test_primary_and_alternate_gemini_profiles_cannot_swap_ports(self):
        with patch("selenium_pipeline.launch_gemini.ready",
                   side_effect=AssertionError("should not contact Chrome")):
            with self.assertRaisesRegex(ValueError, "primary and alternate"):
                launch(alternate_user="teaching", port=9222)
            with self.assertRaisesRegex(ValueError, "primary and alternate"):
                launch(alternate_user=None, port=9225)

    def test_alternate_gemini_runner_locks_dedicated_9225_not_chatgpt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            s = Settings(source_root=root, work_root=None, subchapter="8.1",
                         from_stage="figures", through_stage="slides",
                         alternate_gemini_user="teaching")
            with patch("selenium_pipeline.runner._execute_unlocked",
                       return_value=root), patch(
                "selenium_pipeline.three_pc_worker.LocalInstanceLock",
            ) as lock:
                execute(s)
            self.assertEqual(lock.call_args.args[0], "gemini_port_9225")

    def test_legacy_launcher_rejects_guest_even_if_composer_is_visible(self):
        from unittest.mock import Mock
        from selenium_pipeline.vendor_template_v2 import launch_chatgpt_chrome
        login_button = Mock()
        login_button.is_displayed.return_value = True
        guest = Mock()
        guest.find_elements.side_effect = lambda _kind, selector: (
            [login_button] if selector == 'button[data-testid="login-button"]'
            else []
        )
        by = Mock(CSS_SELECTOR="css selector")
        self.assertFalse(
            launch_chatgpt_chrome.authenticated_chatgpt_composer_only(
                guest, by))
        with patch.object(launch_chatgpt_chrome, "launch_chrome_debug"), patch.object(
            launch_chatgpt_chrome, "import_real_selenium",
            return_value=(Mock(), Mock(By=by), Mock(), Mock(), Mock()),
        ), patch.object(
            launch_chatgpt_chrome, "list_debug_targets", return_value=[],
        ), patch.object(
            launch_chatgpt_chrome, "attach_driver", return_value=guest,
        ), patch.object(
            launch_chatgpt_chrome, "find_interactable_composer",
            return_value=Mock(),
        ), patch.object(
            launch_chatgpt_chrome, "send_keepalive_to_composer",
            side_effect=AssertionError("Guest must never be prompted"),
        ):
            launch_chatgpt_chrome.main()
        guest.service.stop.assert_called_once_with()
        guest.quit.assert_not_called()

    def test_legacy_chatgpt_launcher_detaches_without_closing_user_chrome(self):
        from unittest.mock import Mock
        from selenium_pipeline.vendor_template_v2 import launch_chatgpt_chrome
        fake = Mock()
        with patch.object(launch_chatgpt_chrome, "launch_chrome_debug"), patch.object(
            launch_chatgpt_chrome, "import_real_selenium",
            return_value=tuple(Mock() for _ in range(5)),
        ), patch.object(
            launch_chatgpt_chrome, "list_debug_targets", return_value=[],
        ), patch.object(
            launch_chatgpt_chrome, "attach_driver", return_value=fake,
        ), patch.object(
            launch_chatgpt_chrome, "find_interactable_composer", return_value=None,
        ):
            launch_chatgpt_chrome.main()
        fake.service.stop.assert_called_once_with()
        fake.quit.assert_not_called()

    def test_launcher_rejects_reserved_chatgpt_port_without_gemini_send(self):
        from selenium_pipeline.vendor_template_v2 import launch_chatgpt_chrome
        with patch.object(launch_chatgpt_chrome, "DEBUG_PORT", 9222):
            with self.assertRaisesRegex(RuntimeError, "reserved"):
                launch_chatgpt_chrome.launch_chrome_debug()
        with patch.object(launch_chatgpt_chrome, "DEBUG_PORT", 9225):
            with self.assertRaisesRegex(RuntimeError, "reserved"):
                launch_chatgpt_chrome.launch_chrome_debug()


if __name__ == "__main__":
    unittest.main()
