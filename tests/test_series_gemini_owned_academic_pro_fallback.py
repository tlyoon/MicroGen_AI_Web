"""Reproduce removed-Flash Pro route failure in actual shared source transport.

Mocks stop at Gemini's pre-Send readiness check. No browser, prompt Send,
file uploads, paid APIs, runtime device or model response is used.
"""
from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
import os

from selenium_pipeline import series_gemini


class ReachedBeforeSend(BaseException):
    """Expected injected stop before any provider click."""


class OwnedClient:
    opens=0
    sends=0
    def __init__(self,*_):
        self.driver=object()
        self._automation_tab="sole-owned-tab"
    def start(self,*,ensure_gemini_on_launch):
        assert ensure_gemini_on_launch
    def open_clean_gemini_chat(self):
        type(self).opens+=1
    def type_prompt_text(self,prompt,*,retries):
        assert prompt=="test-only-prompt" and retries==3
        return True
    def shutdown(self):
        pass


def isolate_pre_send(browser_mode, model_id=None):
    OwnedClient.opens=0
    OwnedClient.sends=0
    fake_vendor=SimpleNamespace(
        Config=lambda **kw: SimpleNamespace(**kw),
        GeminiSeleniumClient=OwnedClient)
    environment={"MICROGEN_GEMINI_UI_MODE":browser_mode,
                 "MICROGEN_GEMINI_THINKING_LEVEL":"medium"}
    if model_id is not None:
        environment["MICROGEN_LLM_MODEL"]=model_id
    with patch.dict(os.environ,environment):
        if model_id is None:
            os.environ.pop("MICROGEN_LLM_MODEL",None)
        with patch("selenium_pipeline.series_gemini._vendor_module",
                   return_value=fake_vendor),\
             patch("selenium_pipeline.three_pc_worker.LocalInstanceLock",
                   side_effect=lambda *a,**k:nullcontext()),\
             patch("selenium_pipeline.gemini_model.ensure_mode",
                   side_effect=AssertionError(
                       "Foreign/parent tab mode selection MUST NOT occur")),\
             patch("selenium_pipeline.gemini_model.assert_owned_gemini_mode",
                   return_value="Open mode picker, currently "+(
                       "Pro Medium" if browser_mode=="pro" else
                       "Flash Medium")) as actual_owned,\
             patch("selenium_pipeline.gemini_thinking.select_owned_gemini_thinking_level",
                   return_value="medium"),\
             patch("selenium_pipeline.gemini_response_recovery.await_owned_gemini_send_visible",
                   side_effect=ReachedBeforeSend),\
             patch("selenium_pipeline.gemini_selenium_only_policy.prepare_with_bounded_retries",
                   side_effect=lambda *,make_client,prepare_without_send,
                   dispose: prepare_without_send(make_client())):
            with TestCase().assertRaises(ReachedBeforeSend):
                series_gemini._browser_request(
                    "test-only-prompt",[],port=9222,wait_cap_s=60,
                    min_chars=80)
            return actual_owned.call_args_list,OwnedClient.opens,OwnedClient.sends


class SourceBoundAcademicProPreSendTests(TestCase):
    def test_pro_medium_uses_own_model_id_and_never_touches_foreign_tab(self):
        checks,opens,sends=isolate_pre_send("pro")
        self.assertEqual(opens,1)
        self.assertEqual(sends,0)
        self.assertEqual(len(checks),1)
        self.assertEqual(checks[0].args[1],"sole-owned-tab")
        self.assertEqual(checks[0].kwargs["mode"],"pro")

    def test_normal_flash_preserves_existing_mode_and_own_tab(self):
        checks,opens,sends=isolate_pre_send("flash")
        self.assertEqual((opens,sends),(1,0))
        self.assertEqual(checks[0].kwargs["mode"],"flash")

    def test_immutable_explicit_model_id_contradiction_refused(self):
        from selenium_pipeline.gemini_model import (
            GeminiModelError,browser_model_evidence)
        with self.assertRaisesRegex(GeminiModelError,"contradicts"):
            browser_model_evidence(
                "Open mode picker, currently Pro Medium",
                requested_mode="pro",
                requested_model_id="gemini-3.8-flash")
