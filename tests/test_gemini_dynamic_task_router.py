"""Official-web + exact UI task-default replacement, no model Send."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from selenium_pipeline.gemini_dynamic_task_router import (
    DynamicGeminiRouteError,choose_task_model,select_task_thinking,
    save_verified_task_default,read_task_default,find_dynamic_replacement,
)
from selenium_pipeline.gemini_official_catalog import (
    official_ui_catalog,HELP_URL,API_URL,CatalogUnavailable,
)
from selenium_pipeline.gemini_ui_adaptive_protocol import normalized_family
from selenium_pipeline.gemini_model import (
    _matches_mode,_eligible_mode_menu_text,MODEL_SPECS,
)

SHA="a"*64
CATALOG={"source_state":"FRESH_OFFICIAL_HELP","help_sha256":SHA,
         "verified_app_families":["flash-lite","flash","pro","hydrogen",
                                   "argon","carbon"]}
def row(family,label=None,disabled=False):
    return {"family":family,"label":label or family,"disabled":disabled}

class DynamicTaskRouteTests(unittest.TestCase):
    def setUp(self):
        tmp=TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.cache=self.root/"catalog.json"
        self.defaults=self.root/"defaults.json"

    def test_real_app_help_fetch_and_restart_cache(self):
        page=("Gemini Apps available models Gemini 4 Hydrogen, "
              "Gemini 4 Argon, Gemini 4 Carbon, Gemini 3.1 Pro, "
              "Gemini 3.8 Flash and Flash-Lite. "+"coverage "*70)
        seen=[]
        def network(url):
            seen.append(url)
            return (page if url==HELP_URL else "Gemini 3.8 Flash API "+("x"*300),
                    hashlib.sha256(url.encode()).hexdigest())
        first=official_ui_catalog(force=True,cache_path=self.cache,
                                  fetch=network)
        self.assertEqual(first["source_state"],"FRESH_OFFICIAL_HELP")
        self.assertIn("hydrogen",first["verified_app_families"])
        self.assertIn("argon",first["verified_app_families"])
        self.assertNotIn("hydrogen-thinking",first["verified_app_families"])
        self.assertEqual(seen,[HELP_URL,API_URL])
        second=official_ui_catalog(cache_path=self.cache,
                                   fetch=lambda _:self.fail("Cache missed"))
        self.assertEqual(second["source_state"],"FRESH_VERIFIED_CACHE")
        self.assertEqual(first["help_sha256"],second["help_sha256"])
        self.assertFalse(self.cache.is_symlink())

    def test_invalid_unavailable_internet_never_authorizes_new_unknown_ui(self):
        def broken(_):raise TimeoutError("offline")
        with self.assertRaises(CatalogUnavailable):
            official_ui_catalog(force=True,cache_path=self.cache,fetch=broken)

    def test_model_removed_routes_to_official_and_visible_hydrogen(self):
        rows=[row("hydrogen","Everyday help\n4 Hydrogen"),
              row("pro","Detailed research\n3.1 Pro")]
        result=choose_task_model(stage="slides",requested_family="flash",
                                 visible_rows=rows,catalog=CATALOG)
        self.assertEqual(result.family,"hydrogen")
        self.assertEqual(result.required_thinking,"medium")
        self.assertEqual(result.reason,
                         "PREFERRED_MODEL_MISSING_OFFICIAL_AND_LIVE_UI_FALLBACK")

    def test_representative_18_nov_real_accountB_menu_never_infers_medium(self):
        rows=[row("hydrogen","Everyday help\n4 Hydrogen"),
              row("hydrogen-thinking","Complex problems\n4 Hydrogen Thinking"),
              row("pro","Detailed research\n3.1 Pro")]
        route=choose_task_model(stage="slides",requested_family="flash",
                                visible_rows=rows,catalog=CATALOG)
        self.assertEqual(route.family,"hydrogen")
        self.assertNotIn("hydrogen-thinking",CATALOG["verified_app_families"])
        with self.assertRaisesRegex(DynamicGeminiRouteError,"THINKING"):
            select_task_thinking("slides",[],mode=route.family)
        with self.assertRaisesRegex(DynamicGeminiRouteError,"THINKING"):
            select_task_thinking("slides",["low"],mode=route.family)
        self.assertEqual(select_task_thinking("slides",["low","high"],
                                              mode=route.family),"high")
        self.assertEqual(select_task_thinking("figures",[],
                                              mode="flash-lite"),"not_required")

    def test_sources_cannot_force_unlisted_or_locked_model(self):
        rows=[row("argon","4 Argon",disabled=True),
              row("carbon","4 Carbon",disabled=True),
              row("hydrogen-thinking","4 Hydrogen Thinking")]
        with self.assertRaisesRegex(DynamicGeminiRouteError,"NO_ELIGIBLE"):
            choose_task_model(stage="academic_review",requested_family="pro",
                              visible_rows=rows,catalog=CATALOG)
        with self.assertRaisesRegex(DynamicGeminiRouteError,"NO_ELIGIBLE"):
            choose_task_model(stage="slides",requested_family="flash",
                              visible_rows=[row("hydrogen","4 Hydrogen")],
                              catalog=dict(CATALOG,
                                  verified_app_families=["flash","pro"]))

    def test_scientific_source_bound_route_does_not_change_without_requalification(self):
        rows=[row("argon","4 Argon")]
        with self.assertRaisesRegex(DynamicGeminiRouteError,"REQUALIFICATION"):
            choose_task_model(stage="academic_review",requested_family="pro",
                              visible_rows=rows,catalog=CATALOG)

    def test_exact_stored_default_wins_if_still_verified(self):
        saved={"family":"hydrogen"}
        rows=[row("hydrogen","4 Hydrogen"),row("pro","3.1 Pro")]
        result=choose_task_model(stage="slides",requested_family="flash",
                                 visible_rows=rows,catalog=CATALOG,
                                 saved=saved)
        self.assertEqual(result.family,"hydrogen")
        self.assertIn("PREVIOUS_VERIFIED",result.reason)

    def test_duplicate_family_options_cannot_be_arbitrarily_clicked(self):
        rows=[row("hydrogen","4 Hydrogen"),row("hydrogen","4 Hydrogen 2"),
              row("pro","3.1 Pro")]
        chosen=choose_task_model(stage="slides",requested_family="flash",
                                 visible_rows=rows,catalog=CATALOG)
        self.assertEqual(chosen.family,"pro")

    def test_thinking_fallback_never_downgrades_academic_review(self):
        self.assertEqual(select_task_thinking("academic_review",
                                              ["high"],mode="pro"),"high")
        with self.assertRaises(DynamicGeminiRouteError):
            select_task_thinking("academic_review",["low"],mode="pro")
        with self.assertRaises(DynamicGeminiRouteError):
            select_task_thinking("repair_analysis",[],mode="argon")

    def test_persist_only_after_actual_model_and_thinking_proof(self):
        with self.assertRaisesRegex(DynamicGeminiRouteError,"unverified"):
            save_verified_task_default(
                stage="slides",family="hydrogen",
                visible_label="Open mode picker, currently 4 Hydrogen",
                thinking_level="medium",path=self.defaults,
                ui_model_verified=True,thinking_verified=False,
                catalog_sha=SHA)
        self.assertFalse(self.defaults.exists())
        saved=save_verified_task_default(
            stage="slides",family="hydrogen",
            visible_label="Open mode picker, currently 4 Hydrogen",
            thinking_level="medium",path=self.defaults,
            ui_model_verified=True,thinking_verified=True,
            catalog_sha=SHA,reason="FRESH_OFFICIAL_AND_UI")
        self.assertFalse(saved["source_approval"])
        self.assertFalse(saved["model_id_verified"])
        restored=read_task_default("slides",path=self.defaults)
        self.assertEqual(restored["family"],"hydrogen")
        self.assertEqual(restored["thinking_level"],"medium")
        self.assertIsNone(read_task_default("narration",path=self.defaults))

    def test_atomic_persistence_does_not_authorize_unverified_lite_or_locked_tasks(self):
        with self.assertRaises(DynamicGeminiRouteError):
            save_verified_task_default(
                stage="figures",family="flash-lite",
                visible_label="Open mode picker, currently Flash-Lite",
                thinking_level="medium",path=self.defaults,
                ui_model_verified=True,thinking_verified=True,
                catalog_sha=SHA)
        with self.assertRaises(DynamicGeminiRouteError):
            save_verified_task_default(
                stage="academic_review",family="flash-lite",
                visible_label="Open mode picker, currently Flash-Lite",
                thinking_level="medium",path=self.defaults,
                ui_model_verified=True,thinking_verified=True,
                catalog_sha=SHA)

    def test_model_names_are_not_substring_equivalent(self):
        expected=[
            ("4 Hydrogen","hydrogen"),
            ("4 Hydrogen Thinking","hydrogen-thinking"),
            ("4 Argon","argon"),("4 Carbon","carbon"),
            ("3.1 Pro","pro"),("3.8 Flash","flash"),
            ("3.5 Flash-Lite","flash-lite"),
        ]
        for name,family in expected:
            with self.subTest(name=name):
                self.assertEqual(normalized_family(name),family)
                self.assertTrue(_matches_mode(
                    "Open mode picker, currently "+name,family))
                self.assertTrue(_eligible_mode_menu_text(
                    "Help for you\n"+name,family))
        self.assertIsNone(normalized_family("Flash / Pro"))
        self.assertNotEqual(normalized_family("4 Hydrogen Thinking"),
                            "hydrogen")
        self.assertFalse(_matches_mode(
            "Open mode picker, currently 4 Hydrogen Thinking","hydrogen"))
        self.assertIn("hydrogen",MODEL_SPECS)


if __name__=="__main__":
    unittest.main()
