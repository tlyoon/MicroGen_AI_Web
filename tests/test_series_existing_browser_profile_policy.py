"""Source-stage Gemini requests must never spawn an unverified Chrome profile."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from selenium_pipeline.series_gemini import _browser_request


class DeliberateNoBrowser(Exception):
    pass


class ExistingProfilePolicyTests(unittest.TestCase):
    def test_normal_source_stage_requires_existing_authenticated_debug_port(self):
        recorded = {}
        def stop_at_config(**kwargs):
            recorded.update(kwargs)
            raise DeliberateNoBrowser()
        vendor = SimpleNamespace(Config=stop_at_config)
        with patch("selenium_pipeline.series_gemini._vendor_module",
                   return_value=vendor):
            with self.assertRaises(DeliberateNoBrowser):
                _browser_request("synthetic test only", [], port=9222, wait_cap_s=1)
        self.assertEqual(recorded["debug_port"], 9222)
        self.assertTrue(recorded["use_persistent_chrome"])
        self.assertTrue(recorded["existing_session_only"])
        self.assertFalse(recorded["force_kill_chrome_to_free_port"])

    def test_vendor_isolated_run_compatibility_remains_opt_in(self):
        from selenium_pipeline.vendor_template_v2.selenium import Config
        self.assertFalse(Config(root=Path(".")).existing_session_only)
