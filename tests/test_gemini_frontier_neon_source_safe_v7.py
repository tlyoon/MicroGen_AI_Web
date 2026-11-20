"""Nov-20 Google Gemini 4 model-drift recovery and academic no-Send gates."""
from __future__ import annotations
from contextlib import nullcontext
import os
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from selenium_pipeline.gemini_dynamic_task_router import (
    choose_task_model,select_task_thinking,find_dynamic_replacement,
    DynamicGeminiRouteError,task_policy,read_task_default)
from selenium_pipeline.gemini_model import (
    GeminiModelError,select_owned_gemini_with_recovery,
    _matches_mode,MODEL_SPECS)
from selenium_pipeline.gemini_ui_adaptive_protocol import normalized_family
from selenium_pipeline.gemini_ui_semantic_controls import Option
from selenium_pipeline.academic_gemini_presend_preflight import (
    AcademicGeminiPreSendBlocked,inspect)
from selenium_pipeline.gemini_official_catalog import MODEL_TIERS

CATALOG={"source_state":"FRESH_OFFICIAL_HELP","help_sha256":"b"*64,
         "verified_app_families":["hydrogen","neon","carbon"]}
def row(name,label=None,disabled=False):
    return {"family":name,"label":label or "Gemini 4 "+name.title(),
            "disabled":disabled}

class FrontierRoutingTests(unittest.TestCase):
    def setUp(self):
        tmp=TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        env=patch.dict(os.environ,{"LOCALAPPDATA":str(self.root),
          "MICROGEN_GEMINI_UI_MODE":"pro",
          "MICROGEN_ACTIVE_GENERATION_STAGE":"academic_review",
          "MICROGEN_GEMINI_CHROME_PORT":"9222",
          "MICROGEN_DYNAMIC_ROUTE_PENDING":"",
          "MICROGEN_ACADEMIC_SOURCE_MODEL_REQUALIFICATION_PENDING":""})
        env.start()
        self.addCleanup(env.stop)

    def test_current_official_frontier_neon_is_named_independently(self):
        self.assertIn("neon",MODEL_TIERS)
        self.assertIn("neon",MODEL_SPECS)
        self.assertEqual(normalized_family("Neon Medium"),"neon")
        self.assertEqual(normalized_family("Gemini 4 Neon"),"neon")
        self.assertIsNone(normalized_family("Neon and Carbon"))
        self.assertTrue(_matches_mode(
            "Open mode picker, currently Neon High","neon"))
        self.assertFalse(_matches_mode(
            "Open mode picker, currently Neon High","pro"))

    def test_missing_pro_ranks_neon_presend_only_and_explicit_high(self):
        result=choose_task_model(stage="academic_review",
            requested_family="pro",
            visible_rows=[row("hydrogen"),row("carbon"),row("neon")],
            catalog=CATALOG)
        self.assertEqual(result.family,"neon")
        self.assertEqual(result.required_thinking,"high")
        self.assertTrue(result.academic_pdf_requalification_pending)
        self.assertIn("INDEPENDENT_PDF",result.reason)
        self.assertFalse(read_task_default("academic_review"))
        self.assertEqual(task_policy("academic_review")["minimum_thinking"],"high")

    def test_only_carbon_selects_high_but_never_science(self):
        r=choose_task_model(stage="academic_review",
            requested_family="pro",visible_rows=[row("hydrogen"),row("carbon")],
            catalog=CATALOG)
        self.assertEqual(r.family,"carbon")
        self.assertTrue(r.academic_pdf_requalification_pending)
        self.assertEqual(r.required_thinking,"high")

    def test_hydrogen_only_cannot_claim_equivalent_academic_science(self):
        with self.assertRaisesRegex(
                DynamicGeminiRouteError,
                "NO_ELIGIBLE|SOURCE_REVIEW_COMPATIBLE_FRONTIER_MODEL"):
            choose_task_model(stage="academic_review",requested_family="pro",
                visible_rows=[row("hydrogen")],catalog=CATALOG)

    def test_normal_configured_thinking_uses_actual_task_profile_default(self):
        from selenium_pipeline.gemini_thinking import (
            configured_thinking_level,GeminiThinkingError)
        with patch.dict(os.environ,{"MICROGEN_GEMINI_THINKING_LEVEL":""}):
            for stage,want in (
                ("figures","low"),("slides","medium"),
                ("narration","medium"),("rich_mapping","high"),
                ("academic_review","high"),("acoustic_qa","medium"),
                ("repair_analysis","high")):
                with self.subTest(stage=stage):
                    os.environ["MICROGEN_ACTIVE_GENERATION_STAGE"]=stage
                    self.assertEqual(configured_thinking_level(),want)
        with patch.dict(os.environ,{
                "MICROGEN_ACTIVE_GENERATION_STAGE":"academic_review",
                "MICROGEN_GEMINI_THINKING_LEVEL":"medium"}):
            with self.assertRaisesRegex(
                    GeminiThinkingError,"BELOW_REGISTERED_MINIMUM"):
                configured_thinking_level()
        with patch.dict(os.environ,{
                "MICROGEN_ACTIVE_GENERATION_STAGE":"slides",
                "MICROGEN_GEMINI_THINKING_LEVEL":"high"}):
            self.assertEqual(configured_thinking_level(),"high")

    def test_explicit_source_review_thinking_never_downgrades_high(self):
        self.assertEqual(select_task_thinking("academic_review",
            ["low","medium","high"],mode="neon"),"high")
        self.assertEqual(select_task_thinking("academic_review",
            ["high"],mode="carbon",requested="medium"),"high")
        with self.assertRaisesRegex(DynamicGeminiRouteError,"NON_DOWNGRADING"):
            select_task_thinking("academic_review",
                ["low","medium"],mode="neon")
        self.assertEqual(select_task_thinking("figures",
            ["low"],mode="hydrogen"),"low")
        self.assertEqual(select_task_thinking("slides",
            ["low","medium"],mode="hydrogen"),"medium")

    def test_retired_source_model_recovery_registry_fails_before_source_selection(self):
        from selenium_pipeline.recovery_registry import lookup_mechanism as original
        def registered(kind,signature):
            if signature=="ACADEMIC_DEFAULT_GEMINI_UI_FAMILY_ABSENT_NEW_FRONTIER_AVAILABLE":
                return None
            return original(kind,signature)
        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   side_effect=registered):
            with self.assertRaisesRegex(
                    DynamicGeminiRouteError,"REGISTRY_NOT_VERIFIED"):
                choose_task_model(stage="academic_review",
                    requested_family="pro",visible_rows=[row("neon")],
                    catalog=CATALOG)

    def test_old_fresh_cache_triggers_live_new_model_official_refetch(self):
        cached=dict(CATALOG,source_state="FRESH_VERIFIED_CACHE",
                    verified_app_families=["hydrogen","carbon"])
        with patch("selenium_pipeline.gemini_dynamic_task_router.official_ui_catalog",
                   side_effect=[cached,CATALOG]) as official:
            r=find_dynamic_replacement(stage="academic_review",
                requested_family="pro",
                visible_rows=[row("neon"),row("carbon")])
        self.assertEqual(official.call_count,2)
        self.assertEqual(official.call_args_list[-1].kwargs["force"],True)
        self.assertEqual(r.family,"neon")

    def test_owned_selected_neon_omitted_from_menu_is_exact_verified(self):
        # Real provider snapshot: picker says Neon Medium while model menu
        # lists only Carbon and Hydrogen. Re-selecting Carbon did not stick.
        driver=SimpleNamespace()
        opts=[("carbon",Option(SimpleNamespace(),"Gemini 4 Carbon",False,False)),
              ("hydrogen",Option(SimpleNamespace(),"Gemini 4 Hydrogen",False,False))]
        with patch("selenium_pipeline.gemini_model.select_owned_gemini_mode",
                   side_effect=GeminiModelError(
                       "PRE_SEND_REQUESTED_GEMINI_MODEL_NOT_AVAILABLE_NO_SEND")) as selector,patch(
                "selenium_pipeline.gemini_model._visible_model_options",
                return_value=opts),patch(
                "selenium_pipeline.gemini_model.visible_offered_gemini_families",
                return_value=["carbon","hydrogen"]),patch(
                "selenium_pipeline.gemini_model._owned_picker",
                return_value=SimpleNamespace()),patch(
                "selenium_pipeline.gemini_model._observed_picker_label",
                return_value="Open mode picker, currently Neon Medium"),patch(
                "selenium_pipeline.gemini_model.assert_owned_gemini_mode",
                return_value="Open mode picker, currently Neon Medium") as proof,patch(
                "selenium_pipeline.gemini_dynamic_task_router.official_ui_catalog",
                return_value=CATALOG):
            selected=select_owned_gemini_with_recovery(driver,"owned",
                 mode="pro",stage="academic_review",timeout=1)
        self.assertIn("Neon",selected)
        self.assertEqual(selector.call_count,1)
        self.assertEqual(proof.call_count,2)
        self.assertEqual(os.getenv("MICROGEN_GEMINI_UI_MODE"),"neon")
        self.assertEqual(os.getenv("MICROGEN_LLM_MODEL"),"ui-only-neon")
        self.assertEqual(os.getenv(
            "MICROGEN_ACADEMIC_SOURCE_MODEL_REQUALIFICATION_PENDING"),"1")
        self.assertFalse(read_task_default("academic_review"))

    def test_real_academic_inspect_never_approves_new_model_without_pdf(self):
        class FakeClient:
            def __init__(self,_):
                self.driver=SimpleNamespace()
                self._automation_tab="owned"
            def start(self,**_):pass
            def open_clean_gemini_chat(self):
                os.environ["MICROGEN_GEMINI_UI_MODE"]="neon"
                os.environ[
                   "MICROGEN_ACADEMIC_SOURCE_MODEL_REQUALIFICATION_PENDING"]="1"
                os.environ["MICROGEN_DYNAMIC_ROUTE_PENDING"]=json.dumps({
                    "schema_version":1,"stage":"academic_review",
                    "family":"neon","catalog_sha256":"b"*64})
            def shutdown(self):pass
        fake=SimpleNamespace(Config=lambda **kwargs:SimpleNamespace(**kwargs),
                             GeminiSeleniumClient=FakeClient)
        with patch.dict(os.environ,{
                "MICROGEN_GEMINI_THINKING_LEVEL":"high"}),patch(
                "selenium_pipeline.series_gemini._vendor_module",
                   return_value=fake),patch(
                "selenium_pipeline.launch_gemini.ready",return_value=True),patch(
                "selenium_pipeline.three_pc_worker.LocalInstanceLock",
                return_value=nullcontext()),patch(
                "selenium_pipeline.gemini_model.assert_owned_gemini_mode",
                return_value="Open mode picker, currently Neon High") as mode,patch(
                "selenium_pipeline.gemini_thinking.assert_owned_gemini_thinking_level",
                return_value="high") as effort:
            with self.assertRaisesRegex(
                    AcademicGeminiPreSendBlocked,
                    "AWAITS_NEW_TWO_PDF_PROOF_NO_SEND"):
                inspect(port=9222)
        self.assertEqual(mode.call_args.kwargs["mode"],"neon")
        self.assertEqual(effort.call_args.kwargs["level"],"high")

if __name__=="__main__":
    unittest.main()
