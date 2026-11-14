"""Simulated registered Gemini Send followed by an indefinitely blank reply.

No real browser, Gemini request, API, TTS, or original academic source.
"""
from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
import unittest
import json
from selenium_pipeline import series_gemini
from selenium_pipeline.series_bridge import SeriesBridgeError
from test_gemini_response_recovery import FakeDriver


class GeminiG1GenerationStallTests(unittest.TestCase):
    def setUp(self):
        # Generation-stall tests model transport only; thinking-level
        # selection has separate stateful regression coverage.
        for name in (
            "select_owned_gemini_thinking_level",
            "select_owned_gemini_thinking_with_recovery",
            "assert_owned_gemini_thinking_level",
        ):
            fake = patch("selenium_pipeline.gemini_thinking." + name,
                         return_value="medium")
            fake.start()
            self.addCleanup(fake.stop)

    def test_direct_owned_g1_send_refuses_flash_lite_before_any_click(self):
        from selenium_pipeline.gemini_model import GeminiModelError
        with tempfile.TemporaryDirectory() as folder:
            driver=FakeDriver(response="",generating=False)
            clicks=[]
            closed=[]
            client=SimpleNamespace(
                driver=driver,_automation_tab="owned_tab",
                start=lambda **kw:None,open_clean_gemini_chat=lambda:None,
                upload_files=lambda files:None,
                type_prompt_text=lambda *a,**kw:True,
                shutdown=lambda:closed.append("closed"))
            vendor=SimpleNamespace(
                Config=lambda **kw:SimpleNamespace(**kw),
                GeminiSeleniumClient=lambda cfg:client)
            with (patch.object(series_gemini,"_vendor_module",return_value=vendor),
                  patch("selenium_pipeline.three_pc_worker.LocalInstanceLock",
                        side_effect=lambda *a,**kw:nullcontext()),
                  patch("selenium_pipeline.gemini_model.ensure_mode",
                        return_value="Open mode picker, currently Flash"),
                  patch("selenium_pipeline.gemini_model.assert_owned_gemini_mode",
                        side_effect=GeminiModelError(
                            "PRE_SEND_GEMINI_MODEL_FAMILY_MISMATCH_NO_SEND: Flash-Lite")),
                  patch("selenium_pipeline.gemini_response_recovery.await_owned_gemini_send_visible",
                        return_value=True),
                  patch("selenium_pipeline.gemini_selenium_only_policy.click_one_owned_gemini_send",
                        side_effect=lambda *a,**kw:clicks.append("UNSAFE_SEND")),
                  patch.dict("os.environ",{"LOCALAPPDATA":folder})):
                # Normal direct G1 path applies bounded PRE-SEND recovery
                # and intentionally wraps the selector error in its typed
                # no-Send halt; an old raw GeminiModelError is not its API.
                from selenium_pipeline.gemini_selenium_only_policy import (
                    GeminiSeleniumTemporaryFailure)
                with self.assertRaises(GeminiSeleniumTemporaryFailure) as caught:
                    series_gemini._browser_request(
                        "source-free synthetic request",[],port=9222,
                        wait_cap_s=20,min_chars=8)
            self.assertEqual(clicks,[])
            self.assertTrue(1 <= len(closed) <= 3)
            self.assertTrue(all(x=="closed" for x in closed))
            self.assertIsInstance(caught.exception.__cause__,GeminiModelError)
            self.assertFalse(caught.exception.gemini_send_boundary_entered)
            self.assertEqual(caught.exception.gemini_failure_phase,
                             "GEMINI_MODEL_PICKER_NOT_READY")

    def test_registered_send_zero_text_stalled_generation_is_exactly_classified(self):
        with tempfile.TemporaryDirectory() as d:
            driver=FakeDriver(response="",generating=True)
            calls={"send":0,"shutdown":0}
            client=SimpleNamespace(
                driver=driver,_automation_tab="owned_tab",
                start=lambda **_:None,
                open_clean_gemini_chat=lambda:None,
                upload_files=lambda _:None,
                type_prompt_text=lambda *a,**kw:True,
                shutdown=lambda:calls.__setitem__(
                    "shutdown",calls["shutdown"]+1))
            def one_send(*a,**kw):
                calls["send"]+=1
                return True
            vendor=SimpleNamespace(
                Config=lambda **kw:SimpleNamespace(**kw),
                GeminiSeleniumClient=lambda cfg:client,
                capture_gemini_response_like_manual_copy=lambda *a,**kw:
                    (_ for _ in ()).throw(TimeoutError("bounded model reply timeout")),
                _copy_via_toolbar_copy_button=lambda *_:"")
            stalled={
                "text":"","generating":True,
                "capture_status":"empty_model_response"}
            with (patch.object(series_gemini,"_vendor_module",return_value=vendor),
                  patch("selenium_pipeline.three_pc_worker.LocalInstanceLock",
                        side_effect=lambda *a,**kw:nullcontext()),
                  patch("selenium_pipeline.gemini_model.ensure_mode",
                        return_value="Open mode picker, currently Gemini Flash"),
                  patch("selenium_pipeline.gemini_model.assert_owned_gemini_mode",
                        return_value="Open mode picker, currently Flash"),
                  patch("selenium_pipeline.gemini_response_recovery.await_owned_gemini_send_visible",
                        return_value=True),
                  patch("selenium_pipeline.gemini_selenium_only_policy.owned_gemini_send_baseline",
                        return_value={"users":0,"models":0,
                                      "editor_length":80,"route":"/app"}),
                  patch("selenium_pipeline.gemini_selenium_only_policy.click_one_owned_gemini_send",
                        side_effect=one_send),
                  patch("selenium_pipeline.gemini_selenium_only_policy.observe_gemini_send_registration",
                        return_value={
                            "status":"NEW_USER_TURN_AND_COMPOSER_CLEARED",
                            "registered":True}),
                  patch("selenium_pipeline.gemini_response_recovery.poll_existing_owned_response",
                        return_value=(None,stalled)),
                  patch.dict("os.environ",{"LOCALAPPDATA":d})):
                with self.assertRaises(SeriesBridgeError) as caught:
                    series_gemini._browser_request(
                        "A fresh source-free diagnostic",[],
                        port=9222,wait_cap_s=20,min_chars=8)
            self.assertIn("ZERO model response characters",str(caught.exception))
            self.assertEqual(caught.exception.gemini_failure_phase,
                             "REGISTERED_SEND_GENERATION_STALLED_ZERO_MODEL_TEXT")
            self.assertTrue(caught.exception.gemini_new_user_turn_verified)
            self.assertTrue(caught.exception.gemini_generation_active_at_stop)
            self.assertEqual(caught.exception.gemini_visible_model_chars_at_stop,0)
            self.assertEqual(calls["send"],1)
            self.assertEqual(calls["shutdown"],1)
            receipts=list((Path(d)/"Microvid"/"gemini_quarantine").glob("*.meta.json"))
            self.assertEqual(len(receipts),1)
            meta=json.loads(receipts[0].read_text(encoding="utf8"))
            self.assertEqual(meta["reason"],
                             "verified_new_turn_generation_active_no_model_text")
            self.assertEqual(meta["model_response_chars"],0)
            self.assertTrue(meta["generation_active_at_capture"])


if __name__=="__main__":
    unittest.main()
