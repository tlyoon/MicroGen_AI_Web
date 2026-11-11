"""Figure page-to-crop caption locator uses Flash-Lite, no Thinking submenu.

The heavy lecture-writing stages still require individually verified
Flash + Thinking. Every test is source-free and makes zero provider requests.
"""
from __future__ import annotations
import os
import unittest
from unittest.mock import patch

from selenium_pipeline.gemini_model import (
    _matches_mode, _eligible_mode_menu_text, browser_model_evidence,
    select_owned_gemini_mode, assert_owned_gemini_mode, GeminiModelError)
from selenium_pipeline.gemini_stage_policy import (
    stage_ui_contract, browser_stage_needs_thinking, GeminiStagePolicyError,
    FIGURE_MODEL_ID)
from selenium_pipeline.windows_gemini_stage_transport_triage import (
    audit_original_stage_model_family)
from tests.test_gemini_adaptive_ui_thinking import AdaptiveBrowser


class FigureCaptionPolicyTests(unittest.TestCase):
    def test_exact_lite_not_mistaken_for_full_flash_or_pro(self):
        lite = "Open mode picker, currently Flash-Lite"
        self.assertTrue(_matches_mode(lite,"flash-lite"))
        self.assertFalse(_matches_mode(lite,"flash"))
        self.assertFalse(_matches_mode("Open mode picker, currently Flash Medium","flash-lite"))
        self.assertFalse(_matches_mode("Open mode picker, currently Flash-Lite / Pro","flash-lite"))
        self.assertTrue(_eligible_mode_menu_text("Quick answers\n3.5 Flash-Lite","flash-lite"))
        self.assertFalse(_eligible_mode_menu_text("All-around help\n3.8 Flash","flash-lite"))
        self.assertFalse(_eligible_mode_menu_text("3.5 Flash-Lite\n3.8 Flash","flash-lite"))
        self.assertFalse(_eligible_mode_menu_text("Flash-Lite\nPro","flash-lite"))
        evidence = browser_model_evidence(lite,requested_mode="flash-lite",
                                          requested_model_id=FIGURE_MODEL_ID)
        self.assertTrue(evidence["selected_family_verified"])
        self.assertFalse(evidence["exact_model_id_verified"])
        with self.assertRaises(GeminiModelError):
            browser_model_evidence(lite,requested_mode="flash-lite",
                                   requested_model_id="gemini-3.8-flash")

    def test_stage_scoped_default_is_lite_without_thinking(self):
        fig=stage_ui_contract("figures")
        self.assertEqual(fig["ui_mode"],"flash-lite")
        self.assertEqual(fig["thinking_level"],"not_required")
        self.assertFalse(fig["thinking_required"])
        self.assertEqual(fig["requested_model_id"],FIGURE_MODEL_ID)
        for stage in ("slides","narration"):
            policy=stage_ui_contract(stage)
            self.assertEqual(policy["ui_mode"],"flash")
            self.assertTrue(policy["thinking_required"])
            self.assertEqual(policy["thinking_level"],"medium")
        with self.assertRaises(GeminiStagePolicyError):
            stage_ui_contract("tts")

    def test_only_figures_may_skip_thinking(self):
        with patch.dict(os.environ,{
                "MICROGEN_ACTIVE_GENERATION_STAGE":"figures",
                "MICROGEN_GEMINI_UI_MODE":"flash-lite",
                "MICROGEN_GEMINI_THINKING_LEVEL":"medium"}):
            self.assertFalse(browser_stage_needs_thinking())
        for stage in ("","slides","narration"):
            with self.subTest(stage=stage):
                with patch.dict(os.environ,{
                        "MICROGEN_ACTIVE_GENERATION_STAGE":stage,
                        "MICROGEN_GEMINI_UI_MODE":"flash-lite"}):
                    with self.assertRaises(GeminiStagePolicyError):
                        browser_stage_needs_thinking()
        with self.assertRaises(GeminiStagePolicyError):
            browser_stage_needs_thinking(mode="flash",stage="figures")

    def test_figure_selector_accepts_lite_after_new_chat_and_no_medium(self):
        browser=AdaptiveBrowser(mode="flash",level="low")
        selected=select_owned_gemini_mode(browser,"owned",mode="flash-lite",timeout=1)
        self.assertTrue(_matches_mode(selected,"flash-lite"))
        self.assertEqual(browser.mode,"flash-lite")
        self.assertEqual(browser.level,"low")
        self.assertFalse(any(e.startswith("click:thinking") for e in browser.events))

    def test_real_vendor_one_send_boundary_no_thinking_opened(self):
        from selenium_pipeline.series_gemini import _vendor_module
        from selenium_pipeline import gemini_selenium_only_policy as policy
        vendor=_vendor_module()
        browser=AdaptiveBrowser(mode="flash-lite",level="low")
        client=vendor.GeminiSeleniumClient.__new__(vendor.GeminiSeleniumClient)
        client.driver=browser
        client._automation_tab="owned"
        sent=[]
        with patch.dict(os.environ,{
            "MICROGEN_SINGLE_PROVIDER_SEND":"1",
            "MICROGEN_ACTIVE_GENERATION_STAGE":"figures",
            "MICROGEN_GEMINI_UI_MODE":"flash-lite",
            "MICROGEN_GEMINI_THINKING_LEVEL":"medium"}), \
             patch.object(policy,"click_one_owned_gemini_send",
                          side_effect=lambda *a:sent.append("SEND") or True), \
             patch.object(policy,"owned_gemini_send_baseline",
                          return_value={"ok":True}), \
             patch.object(policy,"observe_gemini_send_registration",
                          return_value={"registered":True,
                           "status":"NEW_USER_TURN_AND_COMPOSER_CLEARED"}):
            self.assertTrue(client.click_send_with_fallbacks(retries=1))
        self.assertEqual(sent,["SEND"])
        self.assertEqual(browser.mode,"flash-lite")
        self.assertEqual(browser.level,"low")
        self.assertFalse(any(e.startswith("click:thinking") for e in browser.events))

    def test_lite_figures_log_requires_exact_pre_send_no_thinking_proof(self):
        before=(
            "[microgen] stage: figures\n"
            "[microgen] browser UI model: flash-lite\n"
            "[microgen] browser thinking level: not_required\n"
            "[2026-11-11 21:00:00] [INFO] Selected Gemini tab via mode picker: "
            "Open mode picker, currently Flash-Lite (phase=development)\n"
            "[2026-11-11 21:00:01] [INFO] [GEMINI-MODE] "
            "PRE_SEND_OWNED_FAMILY_VERIFIED Open mode picker, currently Flash-Lite\n")
        positive=before+(
            "[2026-11-11 21:00:01] [INFO] [GEMINI-THINKING] "
            "PRE_SEND_FIGURES_FLASH_LITE_NOT_REQUIRED\n")
        positive_audit=audit_original_stage_model_family(positive,registered_send=True)
        self.assertFalse(positive_audit["owned_worker_wrong_ui_family_observed"])
        self.assertFalse(positive_audit["owned_worker_thinking_contract_breach_observed"])
        self.assertTrue(positive_audit["owned_worker_requested_thinking_verified_before_send"])
        negative=audit_original_stage_model_family(before,registered_send=True)
        self.assertTrue(negative["owned_worker_thinking_contract_breach_observed"])
        self.assertFalse(negative["owned_worker_requested_thinking_verified_before_send"])

    def test_production_paths_contain_stage_separation_not_only_documentation(self):
        from selenium_pipeline import runner
        from pathlib import Path
        root=Path(runner.__file__).parent
        vendor=(root/"vendor_template_v2"/"selenium.py").read_text(encoding="utf8")
        direct=(root/"series_gemini.py").read_text(encoding="utf8")
        runner_src=(root/"runner.py").read_text(encoding="utf8")
        self.assertIn("MICROGEN_ACTIVE_GENERATION_STAGE",runner_src)
        self.assertIn('stage_policy["ui_mode"]',runner_src)
        self.assertIn("browser_stage_needs_thinking",vendor)
        self.assertIn("PRE_SEND_FIGURES_FLASH_LITE_NOT_REQUIRED",vendor)
        self.assertIn("browser_stage_needs_thinking",direct)


if __name__=="__main__":
    unittest.main()
