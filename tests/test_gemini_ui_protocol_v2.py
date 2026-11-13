"""Stage-aware, drift-tolerant Gemini UI protocol, all pre-Send and offline.

Each case reuses a source-free fake authenticated owned tab; no browser
network, model API, prompt, upload, LLM Send, or author files.
"""
import os
import unittest
from unittest.mock import patch
from selenium_pipeline.gemini_ui_adaptive_protocol import (
    normalized_family,choose_family,choose_thinking,GeminiAdaptivePolicyError)
from selenium_pipeline.gemini_model import (
    select_owned_gemini_with_recovery,GeminiModelError)
from selenium_pipeline.gemini_thinking import (
    select_owned_gemini_thinking_with_recovery,GeminiThinkingError)
from selenium_pipeline.gemini_stage_policy import browser_stage_needs_thinking
from tests.test_gemini_adaptive_ui_thinking import AdaptiveBrowser


class GeminiModelAndEffortProtocolV2(unittest.TestCase):
    def test_flash_by_default_without_conflating_flash_lite(self):
        self.assertEqual(normalized_family("Quick help\nGemini 4.8 Flash"),"flash")
        self.assertEqual(normalized_family("Fast\n3.5 Flash-Lite"),"flash-lite")
        self.assertEqual(normalized_family("3.1 Pro\nThorough research"),"pro")
        self.assertIsNone(normalized_family("Flash\nFlash-Lite"))
        self.assertIsNone(normalized_family("4 Hydrogen"))
        self.assertEqual(choose_family(
            requested="flash",offered=["pro","flash","flash-lite"],
            stage="slides").chosen,"flash")
        self.assertEqual(choose_family(
            requested="flash-lite",offered=["flash","flash-lite"],
            stage="figures").chosen,"flash-lite")

    def test_stage_safe_ranked_fallback_without_unknown_equivalence(self):
        self.assertEqual(choose_family(
            requested="flash",offered=["flash-lite","pro"],
            stage="narration").chosen,"pro")
        self.assertEqual(choose_family(
            requested="flash-lite",offered=["flash","pro"],
            stage="figures").chosen,"flash")
        self.assertTrue(choose_family(
            requested="flash-lite",offered=["flash","pro"],
            stage="figures").thinking_required)
        for offered in ([],["hydrogen"],["flash-lite"]):
            with self.subTest(offered=offered):
                with self.assertRaises(GeminiAdaptivePolicyError):
                    choose_family(requested="flash",offered=offered,
                                  stage="academic_review")

    def test_explicit_pro_benchmark_is_not_substituted(self):
        with self.assertRaisesRegex(
            GeminiAdaptivePolicyError,"EXPLICIT_PRO_BENCHMARK"):
            choose_family(requested="pro",offered=["flash"],
                          stage="slides")

    def test_missing_flash_is_recovered_in_owned_browser_with_pro(self):
        browser=AdaptiveBrowser(mode="flash-lite",level="low")
        browser.mode_rows=[x for x in browser.mode_rows
                           if x.id!="model-flash"]
        with patch.dict(os.environ,{
                "MICROGEN_GEMINI_UI_MODE":"flash",
                "MICROGEN_ACTIVE_GENERATION_STAGE":"slides"},clear=False):
            selected=select_owned_gemini_with_recovery(
                browser,"owned",mode="flash",stage="slides",timeout=1)
            self.assertEqual(browser.mode,"pro")
            self.assertIn("Pro",selected)
            self.assertEqual(os.environ["MICROGEN_GEMINI_UI_MODE"],"pro")
            self.assertEqual(os.environ["MICROGEN_LLM_MODEL"],"gemini-3.1-pro")
            self.assertTrue(browser_stage_needs_thinking(mode="pro"))
        self.assertFalse(any("send" in e for e in browser.events))

    def test_figure_lite_missing_can_use_flash_with_checked_thinking(self):
        browser=AdaptiveBrowser(mode="pro",level="low")
        browser.mode_rows=[x for x in browser.mode_rows
                           if x.id!="model-flash-lite"]
        with patch.dict(os.environ,{
                "MICROGEN_GEMINI_UI_MODE":"flash-lite",
                "MICROGEN_ACTIVE_GENERATION_STAGE":"figures",
                "MICROGEN_GEMINI_THINKING_LEVEL":"medium"}):
            selected=select_owned_gemini_with_recovery(
                browser,"owned",mode="flash-lite",stage="figures",
                timeout=1)
            self.assertIn("Flash",selected)
            self.assertEqual(os.environ["MICROGEN_GEMINI_UI_MODE"],"flash")
            self.assertTrue(browser_stage_needs_thinking(mode="flash",
                                                         stage="figures"))
            self.assertEqual(select_owned_gemini_thinking_with_recovery(
                browser,"owned",level="medium",stage="figures",
                timeout=1),"medium")
        self.assertEqual(browser.mode,"flash")
        self.assertEqual(browser.level,"medium")

    def test_fallback_is_disabled_in_strict_source_preflight(self):
        browser=AdaptiveBrowser(mode="flash-lite")
        browser.mode_rows=[x for x in browser.mode_rows
                           if x.id!="model-flash"]
        with patch.dict(os.environ,{"MICROGEN_GEMINI_UI_MODE":"flash"}):
            with self.assertRaisesRegex(GeminiModelError,
                                        "NOT_AVAILABLE_NO_SEND"):
                select_owned_gemini_with_recovery(
                    browser,"owned",mode="flash",stage="academic_review",
                    timeout=1,allow_fallback=False)
            self.assertEqual(os.environ["MICROGEN_GEMINI_UI_MODE"],"flash")
        self.assertEqual(browser.mode,"flash-lite")

    def test_missing_medium_can_non_downgrade_to_selected_high(self):
        browser=AdaptiveBrowser(mode="flash",level="low",
                                missing_medium=True)
        with patch.dict(os.environ,{
                "MICROGEN_GEMINI_THINKING_LEVEL":"medium",
                "MICROGEN_ACTIVE_GENERATION_STAGE":"slides"}):
            self.assertEqual(select_owned_gemini_thinking_with_recovery(
                browser,"owned",level="medium",stage="slides",
                timeout=1),"high")
            self.assertEqual(os.environ["MICROGEN_GEMINI_THINKING_LEVEL"],
                             "high")
        self.assertEqual(browser.level,"high")
        self.assertFalse(any("send" in e for e in browser.events))

    def test_explicit_high_never_downgrades_to_medium(self):
        browser=AdaptiveBrowser(mode="flash",level="low")
        browser.level_rows=[x for x in browser.level_rows
                            if x.id!="thinking-high"]
        with self.assertRaisesRegex(
                GeminiThinkingError,"NO_VERIFIABLE_NON_DOWNGRADING"):
            select_owned_gemini_thinking_with_recovery(
                browser,"owned",level="high",stage="narration",timeout=1)

    def test_unknown_language_or_missing_controls_never_guessed(self):
        browser=AdaptiveBrowser(mode="flash-lite")
        browser.mode_rows=[]
        with self.assertRaises(GeminiModelError):
            select_owned_gemini_with_recovery(
                browser,"owned",mode="flash",stage="slides",timeout=1)
        self.assertEqual(browser.mode,"flash-lite")

    def test_wrong_owner_rejected_without_any_control_action(self):
        browser=AdaptiveBrowser(mode="flash-lite")
        browser.current_window_handle="borrowed"
        with self.assertRaises(GeminiModelError):
            select_owned_gemini_with_recovery(
                browser,"owned",mode="flash",stage="slides",timeout=1)
        self.assertFalse(browser.events)

    def test_thinking_recommendations_are_strictly_not_weaker(self):
        self.assertEqual(choose_thinking(
            requested="medium",offered=["low","high"],
            stage="academic_review"),"high")
        with self.assertRaises(GeminiAdaptivePolicyError):
            choose_thinking(requested="medium",offered=["low"],
                            stage="academic_review")
        with self.assertRaises(GeminiAdaptivePolicyError):
            choose_thinking(requested="medium",offered=["auto","high"],
                            stage="slides")


if __name__=="__main__":
    unittest.main()
