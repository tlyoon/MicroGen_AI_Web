"""Academic browser worker uses proven Flash-first dynamic Pro/Medium fallback."""
from __future__ import annotations
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from selenium_pipeline.ai_academic_web_review import _academic_browser_request
from selenium_pipeline.gemini_ui_adaptive_protocol import (
    choose_family, GeminiAdaptivePolicyError)


class AcademicReviewAdaptiveModelRouteTests(unittest.TestCase):
    def test_academic_fallback_pro_only_when_flash_absent(self):
        route = choose_family(requested="flash",
                              offered=("flash-lite", "pro"),
                              stage="academic_review")
        self.assertEqual(route.chosen, "pro")
        self.assertTrue(route.thinking_required)
        self.assertEqual(route.reason,
                         "EXACT_PREFERRED_ABSENT_STAGE_COMPATIBLE_FALLBACK")
        self.assertEqual(choose_family(requested="flash",
                        offered=("flash", "pro"),
                        stage="academic_review").chosen, "flash")
        with self.assertRaises(GeminiAdaptivePolicyError):
            choose_family(requested="flash",
                          offered=("flash-lite",),
                          stage="academic_review")

    def test_real_worker_scopes_stage_and_restores_fallback(self):
        with patch.dict(os.environ, {
            "MICROGEN_ACTIVE_GENERATION_STAGE": "narration",
            "MICROGEN_GEMINI_UI_MODE": "flash",
            "MICROGEN_LLM_MODEL": "gemini-3.8-flash"}, clear=False):
            def fake_request(prompt, files, **kwargs):
                self.assertEqual(os.environ["MICROGEN_ACTIVE_GENERATION_STAGE"],
                                 "academic_review")
                self.assertEqual(os.environ["MICROGEN_GEMINI_UI_MODE"], "flash")
                self.assertEqual(os.environ["MICROGEN_LLM_MODEL"], "gemini-3.8-flash")
                self.assertEqual(kwargs["port"], 9222)
                # Mimic real Pro fallback selected from visibly offered menu.
                os.environ["MICROGEN_GEMINI_UI_MODE"] = "pro"
                os.environ["MICROGEN_LLM_MODEL"] = "gemini-3.1-pro"
                os.environ["MICROGEN_MODEL_ROUTE_REASON"] = "verified"
                return "source-bound response"
            os.environ.pop("MICROGEN_MODEL_ROUTE_REASON", None)
            with patch("selenium_pipeline.ai_academic_web_review._browser_request",
                       side_effect=fake_request) as provider:
                result = _academic_browser_request(
                    "review source", [Path("source.pdf")],
                    chrome_port=9222, wait_cap_s=120)
            self.assertEqual(result, "source-bound response")
            provider.assert_called_once()
            self.assertEqual(os.environ["MICROGEN_ACTIVE_GENERATION_STAGE"],
                             "narration")
            self.assertEqual(os.environ["MICROGEN_GEMINI_UI_MODE"], "flash")
            self.assertEqual(os.environ["MICROGEN_LLM_MODEL"], "gemini-3.8-flash")
            self.assertNotIn("MICROGEN_MODEL_ROUTE_REASON", os.environ)

    def test_legacy_flash_lite_does_not_bypass_thinking(self):
        with patch.dict(os.environ, {
            "MICROGEN_GEMINI_UI_MODE": "flash-lite",
            "MICROGEN_LLM_MODEL": "gemini-3.5-flash-lite"}, clear=False):
            def inspect(*args, **kwargs):
                self.assertEqual(os.environ["MICROGEN_ACTIVE_GENERATION_STAGE"],
                                 "academic_review")
                self.assertEqual(os.environ["MICROGEN_GEMINI_UI_MODE"], "flash")
                self.assertEqual(os.environ["MICROGEN_LLM_MODEL"], "gemini-3.8-flash")
                raise RuntimeError("no provider send")
            with patch("selenium_pipeline.ai_academic_web_review._browser_request",
                       side_effect=inspect):
                with self.assertRaisesRegex(RuntimeError, "no provider send"):
                    _academic_browser_request(
                        "review", [], chrome_port=9222, wait_cap_s=120)
            self.assertEqual(os.environ["MICROGEN_GEMINI_UI_MODE"],
                             "flash-lite")
            self.assertEqual(os.environ["MICROGEN_LLM_MODEL"],
                             "gemini-3.5-flash-lite")

    def test_vendor_adaptive_gate_includes_only_known_stage(self):
        path = (Path(__file__).resolve().parents[1] / "selenium_pipeline"
                / "vendor_template_v2" / "selenium.py")
        text = path.read_text(encoding="utf8")
        self.assertIn('"rich_mapping","academic_review"', text)
        self.assertIn("select_owned_gemini_with_recovery(", text)
        self.assertIn("allow_fallback=adaptive_allowed", text)


if __name__ == "__main__":
    unittest.main()
