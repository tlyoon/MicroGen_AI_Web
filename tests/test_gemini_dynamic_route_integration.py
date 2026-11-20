"""Normal Selenium model-recovery integration and SHA-bound persistence."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from selenium_pipeline.gemini_model import (
    GeminiModelError,select_owned_gemini_with_recovery)
from selenium_pipeline.gemini_dynamic_task_router import (
    commit_verified_pending_route,read_task_default,DynamicGeminiRouteError)

CATALOG={"source_state":"FRESH_OFFICIAL_HELP","help_sha256":"a"*64,
         "verified_app_families":["flash","flash-lite","pro","hydrogen","argon"]}

class RealEntrypointRouteTests(TestCase):
    def setUp(self):
        self.t=TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.driver=SimpleNamespace()
        self.env=patch.dict(os.environ,{
            "LOCALAPPDATA":self.t.name,
            "MICROGEN_GEMINI_UI_MODE":"flash",
            "MICROGEN_GEMINI_CHROME_PORT":"9222",
            "MICROGEN_ACTIVE_GENERATION_STAGE":"slides",
            "MICROGEN_DYNAMIC_ROUTE_PENDING":"",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def _fallback(self,stage="slides",offered=("hydrogen","pro")):
        from selenium_pipeline.gemini_ui_semantic_controls import Option
        elements={name:SimpleNamespace() for name in offered}
        labels={"hydrogen":"Everyday help\n4 Hydrogen",
                "pro":"Detailed research\n3.1 Pro",
                "argon":"Long-horizon reasoning\n4 Argon"}
        choices=[(family,Option(elements[family],labels[family],False,False))
                 for family in offered]
        return patch.multiple("selenium_pipeline.gemini_model",
            select_owned_gemini_mode=__import__("unittest").mock.DEFAULT,
            _visible_model_options=__import__("unittest").mock.DEFAULT,
            visible_offered_gemini_families=__import__("unittest").mock.DEFAULT),choices

    def test_removed_flash_selects_official_visible_hydrogen_then_requires_radio(self):
        from selenium_pipeline.gemini_ui_semantic_controls import Option
        target=SimpleNamespace()
        rows=[("hydrogen",Option(target,"Everyday help\n4 Hydrogen",False,False)),
              ("pro",Option(SimpleNamespace(),
                            "Detailed research\n3.1 Pro",False,False))]
        with patch("selenium_pipeline.gemini_model.select_owned_gemini_mode",
                   side_effect=[
                      GeminiModelError(
                        "PRE_SEND_REQUESTED_GEMINI_MODEL_NOT_AVAILABLE_NO_SEND"),
                      "Open mode picker, currently 4 Hydrogen"]) as select,patch(
                "selenium_pipeline.gemini_model._visible_model_options",
                return_value=rows),patch(
                "selenium_pipeline.gemini_model.visible_offered_gemini_families",
                return_value=["hydrogen","pro"]),patch(
                "selenium_pipeline.gemini_dynamic_task_router.official_ui_catalog",
                return_value=CATALOG):
            selected=select_owned_gemini_with_recovery(
                self.driver,"owned",mode="flash",stage="slides",
                timeout=2,allow_fallback=True)
        self.assertIn("Hydrogen",selected)
        self.assertEqual(select.call_args_list[-1].kwargs["mode"],"hydrogen")
        self.assertEqual(os.getenv("MICROGEN_GEMINI_UI_MODE"),"hydrogen")
        self.assertEqual(os.getenv("MICROGEN_LLM_MODEL"),"ui-only-hydrogen")
        self.assertFalse(read_task_default("slides"))
        with self.assertRaises(DynamicGeminiRouteError):
            commit_verified_pending_route(
                stage="slides",owned_selected_label=selected,
                thinking_level="medium",model_ui_checked=True,
                thinking_radio_checked=False)
        self.assertFalse(read_task_default("slides"))
        final=commit_verified_pending_route(
            stage="slides",owned_selected_label=selected,
            thinking_level="medium",model_ui_checked=True,
            thinking_radio_checked=True)
        self.assertEqual(final["family"],"hydrogen")
        self.assertEqual(final["thinking_level"],"medium")
        self.assertFalse(final["provider_send"])
        self.assertFalse(final["source_approval"])
        self.assertEqual(read_task_default("slides")["family"],"hydrogen")
        self.assertFalse(os.getenv("MICROGEN_DYNAMIC_ROUTE_PENDING"))

    def test_restarted_worker_uses_verified_persisted_default(self):
        from selenium_pipeline.gemini_dynamic_task_router import (
            save_verified_task_default)
        save_verified_task_default(
            stage="slides",family="hydrogen",
            visible_label="Open mode picker, currently 4 Hydrogen",
            thinking_level="medium",catalog_sha="a"*64,
            ui_model_verified=True,thinking_verified=True,
            reason="TEST_PREVIOUS_VERIFIED")
        with patch("selenium_pipeline.gemini_model.select_owned_gemini_mode",
                   return_value="Open mode picker, currently 4 Hydrogen") as selector,patch(
                "selenium_pipeline.gemini_dynamic_task_router.official_ui_catalog",
                side_effect=AssertionError(
                    "No web needed when old verified default remains visible")):
            selected=select_owned_gemini_with_recovery(
                self.driver,"owned",mode="flash",stage="slides",
                timeout=2,allow_fallback=True)
        self.assertIn("Hydrogen",selected)
        self.assertEqual(selector.call_count,1)
        self.assertEqual(selector.call_args.kwargs["mode"],"hydrogen")
        self.assertEqual(os.getenv("MICROGEN_GEMINI_UI_MODE"),"hydrogen")

    def test_retired_dynamic_registry_blocks_new_model_click_and_send(self):
        from selenium_pipeline.gemini_ui_semantic_controls import Option
        rows=[("hydrogen",Option(SimpleNamespace(),"4 Hydrogen",False,False))]
        with patch("selenium_pipeline.gemini_model.select_owned_gemini_mode",
                   side_effect=GeminiModelError(
                      "PRE_SEND_REQUESTED_GEMINI_MODEL_NOT_AVAILABLE_NO_SEND")) as selector,patch(
                "selenium_pipeline.gemini_model._visible_model_options",
                return_value=rows),patch(
                "selenium_pipeline.gemini_model.visible_offered_gemini_families",
                return_value=["hydrogen"]),patch(
                "selenium_pipeline.recovery_registry.lookup_mechanism",
                return_value=None),patch(
                "selenium_pipeline.gemini_dynamic_task_router.official_ui_catalog",
                side_effect=AssertionError("No catalog fetch when registry retired")):
            with self.assertRaisesRegex(GeminiModelError,"DYNAMIC_TASK_MODEL_NOT_VERIFIABLE"):
                select_owned_gemini_with_recovery(
                    self.driver,"owned",mode="flash",stage="slides",
                    timeout=2,allow_fallback=True)
        self.assertEqual(selector.call_count,1)
        self.assertFalse(os.getenv("MICROGEN_DYNAMIC_ROUTE_PENDING"))

    def test_academic_can_select_argon_only_as_unqualified_presend_ui(self):
        from selenium_pipeline.gemini_ui_semantic_controls import Option
        rows=[("argon",Option(SimpleNamespace(),"4 Argon",False,False))]
        with patch("selenium_pipeline.gemini_model.select_owned_gemini_mode",
                   side_effect=[
                      GeminiModelError(
                        "PRE_SEND_REQUESTED_GEMINI_MODEL_NOT_AVAILABLE_NO_SEND"),
                      "Open mode picker, currently 4 Argon"]) as sel,patch(
                "selenium_pipeline.gemini_model._visible_model_options",
                return_value=rows),patch(
                "selenium_pipeline.gemini_model.visible_offered_gemini_families",
                return_value=["argon"]),patch(
                "selenium_pipeline.gemini_dynamic_task_router.official_ui_catalog",
                return_value=CATALOG):
            selected=select_owned_gemini_with_recovery(
                self.driver,"owned",mode="pro",stage="academic_review",
                timeout=2,allow_fallback=True)
        self.assertIn("Argon",selected)
        self.assertEqual(sel.call_count,2)
        self.assertEqual(os.getenv("MICROGEN_GEMINI_UI_MODE"),"argon")
        self.assertEqual(os.getenv("MICROGEN_ACADEMIC_SOURCE_MODEL_REQUALIFICATION_PENDING"),"1")
        self.assertEqual(os.getenv("MICROGEN_MODEL_ROUTE_REASON"),
                         "ACADEMIC_ALTERNATE_UI_ONLY_INDEPENDENT_PDF_REQUALIFICATION_REQUIRED")
        self.assertFalse(read_task_default("academic_review"))
        self.assertTrue(os.getenv("MICROGEN_DYNAMIC_ROUTE_PENDING"))

if __name__=="__main__":
    import unittest
    unittest.main()
