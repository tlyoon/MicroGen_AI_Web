"""Academic Gemini capability preflight is source-free and zero Send.

No actual browser, user account, model request, media, API or source-file
operations. Real Dell-115 preflight has separate immutable evidence.
"""
from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import os
import tempfile
import unittest

from selenium_pipeline.academic_gemini_presend_preflight import (
    inspect, AcademicGeminiPreSendBlocked)
from selenium_pipeline.gemini_model import GeminiModelError


class ExactAcademicGeminiCapabilities(unittest.TestCase):
    def setUp(self):
        root=tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        self.root=Path(root.name)
        self.provider=SimpleNamespace()
        self.provider.driver=object()
        self.provider._automation_tab="owned"
        self.provider.start=Mock()
        self.provider.shutdown=Mock()
        self.provider.open_clean_gemini_chat=Mock()
        self.vendor=SimpleNamespace(
            Config=lambda **kw:SimpleNamespace(**kw),
            GeminiSeleniumClient=lambda _:self.provider)
        self.items=[
            patch.dict(os.environ,{
                "LOCALAPPDATA":str(self.root),
                "MICROGEN_GEMINI_UI_MODE":"flash",
                "MICROGEN_GEMINI_THINKING_LEVEL":"medium"}),
            patch("selenium_pipeline.series_gemini._vendor_module",
                  return_value=self.vendor),
            patch("selenium_pipeline.three_pc_worker.LocalInstanceLock",
                  side_effect=lambda *a,**k:nullcontext()),
        ]
        for item in self.items:
            item.start()
            self.addCleanup(item.stop)

    def test_provider_removed_contracted_flash_no_source_claim_or_send(self):
        self.provider.open_clean_gemini_chat.side_effect=GeminiModelError(
            "PRE_SEND_REQUESTED_GEMINI_MODEL_NOT_AVAILABLE_NO_SEND; "
            "requested=flash; offered=hydrogen,flash-lite,pro,argon,carbon")
        with patch("selenium_pipeline.gemini_model.assert_owned_gemini_mode",
                   side_effect=AssertionError("Wrong family must stop preflight")):
            with self.assertRaises(AcademicGeminiPreSendBlocked) as found:
                inspect(port=9222)
        self.assertEqual(
            found.exception.failure_phase,
            "GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE")
        self.provider.start.assert_called_once_with(
            ensure_gemini_on_launch=True)
        self.provider.open_clean_gemini_chat.assert_called_once()
        self.provider.shutdown.assert_called_once()
        self.assertFalse(list(self.root.rglob("dispatch_attempted.claim")))
        self.assertFalse(list(self.root.rglob("job_*_result.json")))

    def test_already_running_authorized_alt_reuses_exact_flash_without_switch(self):
        from selenium_pipeline.academic_gemini_presend_preflight import (
            select_ready_existing_session)
        seen=[]
        def probe(*,port):
            seen.append(port)
            if port==9222:
                raise AcademicGeminiPreSendBlocked(
                    "GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE")
            self.assertEqual(port,9225)
            return {"status":"EXACT_OWNED_GEMINI_MODEL_AND_THINKING_READY_NO_SEND",
                    "model_family":"flash","thinking_level":"medium",
                    "gemini_requests_submitted":0}
        with patch("selenium_pipeline.academic_gemini_presend_preflight.inspect",
                   side_effect=probe),\
             patch("selenium_pipeline.launch_gemini.ready",
                   return_value=True):
            result=select_ready_existing_session(primary_port=9222)
        self.assertEqual(seen,[9222,9225])
        self.assertEqual(result["verified_port"],9225)
        self.assertTrue(result["alternate_account_used"])
        self.assertEqual(result["model_family"],"flash")
        self.assertEqual(result["thinking_level"],"medium")
        self.assertEqual(result["gemini_requests_submitted"],0)

    def test_no_running_alternate_never_launches_or_switches_model(self):
        from selenium_pipeline.academic_gemini_presend_preflight import (
            select_ready_existing_session)
        ports=[]
        def probe(*,port):
            ports.append(port)
            raise AcademicGeminiPreSendBlocked(
                "GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE")
        with patch("selenium_pipeline.academic_gemini_presend_preflight.inspect",
                   side_effect=probe),\
             patch("selenium_pipeline.launch_gemini.ready",
                   return_value=False),\
             patch("selenium_pipeline.launch_gemini.launch",
                   side_effect=AssertionError("Do not open alternate profile")):
            with self.assertRaises(AcademicGeminiPreSendBlocked):
                select_ready_existing_session(primary_port=9222)
        self.assertEqual(ports,[9222])

    def test_only_true_owned_flash_medium_passes_before_any_send(self):
        with patch("selenium_pipeline.gemini_model.assert_owned_gemini_mode",
                   return_value="Open mode picker, currently Flash") as family:
            with patch("selenium_pipeline.gemini_thinking."
                       "assert_owned_gemini_thinking_level",
                       return_value="medium") as thinking:
                result=inspect(port=9222)
        family.assert_called_once_with(
            self.provider.driver,"owned",mode="flash",wait_seconds=4)
        thinking.assert_called_once_with(
            self.provider.driver,"owned",level="medium")
        self.assertEqual(result["status"],
            "EXACT_OWNED_GEMINI_MODEL_AND_THINKING_READY_NO_SEND")
        self.assertEqual(result["gemini_requests_submitted"],0)
        self.assertEqual(result["files_uploaded"],0)
        self.assertFalse(result["G2_approved"])
        self.provider.shutdown.assert_called_once()


if __name__=="__main__":
    unittest.main()
