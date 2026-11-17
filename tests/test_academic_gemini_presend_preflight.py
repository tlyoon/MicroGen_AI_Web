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
            patch("selenium_pipeline.launch_gemini.ready",return_value=True),
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

    def test_missing_owned_thinking_control_tries_only_existing_alt_no_send(self):
        from selenium_pipeline.academic_gemini_presend_preflight import (
            select_ready_existing_session)
        seen=[]
        def probe(*,port):
            seen.append(port)
            if port==9222:
                raise AcademicGeminiPreSendBlocked(
                    "GEMINI_THINKING_CONTROL_UNAVAILABLE_OR_AMBIGUOUS")
            return {"status":"EXACT_OWNED_GEMINI_MODEL_AND_THINKING_READY_NO_SEND",
                    "model_family":"pro","thinking_level":"high",
                    "gemini_requests_submitted":0}
        with patch("selenium_pipeline.academic_gemini_presend_preflight.inspect",
                   side_effect=probe),\
             patch("selenium_pipeline.launch_gemini.ready",
                   return_value=True):
            result=select_ready_existing_session(primary_port=9222)
        self.assertEqual(seen,[9222,9225])
        self.assertEqual(result["verified_port"],9225)
        self.assertTrue(result["existing_profile_only"])
        self.assertEqual(result["thinking_level"],"high")
        self.assertEqual(result["gemini_requests_submitted"],0)

    def test_retired_thinking_profile_recovery_never_reaches_second_account(self):
        from selenium_pipeline.academic_gemini_presend_preflight import (
            select_ready_existing_session)
        seen=[]
        def probe(*,port):
            seen.append(port)
            raise AcademicGeminiPreSendBlocked(
                "GEMINI_THINKING_CONTROL_UNAVAILABLE_OR_AMBIGUOUS")
        with patch("selenium_pipeline.academic_gemini_presend_preflight.inspect",
                   side_effect=probe),\
             patch("selenium_pipeline.launch_gemini.ready",
                   return_value=True),\
             patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value=None):
            with self.assertRaises(AcademicGeminiPreSendBlocked):
                select_ready_existing_session(primary_port=9222)
        self.assertEqual(seen,[9222])

    def test_missing_thinking_control_never_invents_level_when_alt_is_blocked(self):
        from selenium_pipeline.academic_gemini_presend_preflight import (
            select_ready_existing_session)
        seen=[]
        def probe(*,port):
            seen.append(port)
            raise AcademicGeminiPreSendBlocked(
                "GEMINI_THINKING_CONTROL_UNAVAILABLE_OR_AMBIGUOUS")
        with patch("selenium_pipeline.academic_gemini_presend_preflight.inspect",
                   side_effect=probe),\
             patch("selenium_pipeline.launch_gemini.ready",
                   return_value=True):
            with self.assertRaises(AcademicGeminiPreSendBlocked) as found:
                select_ready_existing_session(primary_port=9222)
        self.assertEqual(seen,[9222,9225])
        self.assertEqual(found.exception.failure_phase,
                         "GEMINI_THINKING_CONTROL_UNAVAILABLE_OR_AMBIGUOUS")

    def test_distinct_thinking_failure_codes_are_not_mislabelled_model_picker(self):
        from selenium_pipeline.gemini_selenium_only_policy import presend_failure_code
        cases={
            "PRE_SEND_THINKING_EXPANDER_NOT_UNIQUE_OR_MISSING":
                "GEMINI_THINKING_CONTROL_UNAVAILABLE_OR_AMBIGUOUS",
            "PRE_SEND_REQUESTED_THINKING_LEVEL_UNAVAILABLE_NO_SEND":
                "GEMINI_THINKING_LEVEL_UNAVAILABLE_NO_SEND",
            "PRE_SEND_THINKING_SELECTION_NOT_CONFIRMED_NO_SEND":
                "GEMINI_THINKING_SELECTION_UNVERIFIED_NO_SEND",
            "PRE_SEND_REQUESTED_GEMINI_MODEL_NOT_AVAILABLE_NO_SEND":
                "GEMINI_REQUESTED_MODEL_FAMILY_UNAVAILABLE",
        }
        for cause,expected in cases.items():
            with self.subTest(cause=cause):
                self.assertEqual(presend_failure_code(RuntimeError(cause)),
                                 expected)

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

    def test_absent_debug_session_never_launches_disposable_chrome(self):
        from selenium_pipeline.academic_gemini_presend_preflight import inspect
        with patch("selenium_pipeline.launch_gemini.ready",
                   return_value=False):
            with self.assertRaises(AcademicGeminiPreSendBlocked) as found:
                inspect(port=9222)
        self.assertEqual(found.exception.failure_phase,
                         "GEMINI_EXISTING_DEBUG_SESSION_UNAVAILABLE_NO_SEND")
        self.provider.start.assert_not_called()
        self.provider.open_clean_gemini_chat.assert_not_called()
        self.provider.shutdown.assert_not_called()
        self.assertFalse(list(self.root.rglob("dispatch_attempted.claim")))

    def test_disappeared_primary_checks_running_alt_under_registry_only(self):
        from selenium_pipeline.academic_gemini_presend_preflight import (
            select_ready_existing_session)
        attempted=[]
        def fake_inspect(*,port):
            attempted.append(port)
            if port==9222:
                raise AcademicGeminiPreSendBlocked(
                    "GEMINI_EXISTING_DEBUG_SESSION_UNAVAILABLE_NO_SEND")
            return {"status":"EXACT_OWNED_GEMINI_MODEL_AND_THINKING_READY_NO_SEND",
                    "model_family":"pro","thinking_level":"medium",
                    "gemini_requests_submitted":0,"files_uploaded":0}
        with patch("selenium_pipeline.academic_gemini_presend_preflight.inspect",
                   side_effect=fake_inspect):
            result=select_ready_existing_session(primary_port=9222)
        self.assertEqual(attempted,[9222,9225])
        self.assertEqual(result["verified_port"],9225)
        self.assertTrue(result["alternate_account_used"])
        self.assertTrue(result["existing_profile_only"])
        self.assertEqual(result["gemini_requests_submitted"],0)
        self.provider.start.assert_not_called()

    def test_disappeared_primary_without_running_alt_stops_no_send(self):
        from selenium_pipeline.academic_gemini_presend_preflight import (
            select_ready_existing_session)
        with patch("selenium_pipeline.launch_gemini.ready",
                   return_value=False):
            with self.assertRaises(AcademicGeminiPreSendBlocked) as found:
                select_ready_existing_session(primary_port=9222)
        self.assertEqual(found.exception.failure_phase,
                         "GEMINI_EXISTING_DEBUG_SESSION_UNAVAILABLE_NO_SEND")
        self.provider.start.assert_not_called()

    def test_disabled_primary_port_repair_never_inspects_alt(self):
        from selenium_pipeline.academic_gemini_presend_preflight import (
            select_ready_existing_session)
        attempted=[]
        def fake_inspect(*,port):
            attempted.append(port)
            raise AcademicGeminiPreSendBlocked(
                "GEMINI_EXISTING_DEBUG_SESSION_UNAVAILABLE_NO_SEND")
        with patch("selenium_pipeline.academic_gemini_presend_preflight.inspect",
                   side_effect=fake_inspect),patch(
                   "selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value=None):
            with self.assertRaises(AcademicGeminiPreSendBlocked):
                select_ready_existing_session(primary_port=9222)
        self.assertEqual(attempted,[9222])

    def test_vendor_lost_debug_port_race_cannot_launch_new_chrome(self):
        from selenium_pipeline.vendor_template_v2.selenium import (
            Config, GeminiSeleniumClient)
        cfg=Config(root=self.root,debug_port=9222,
                   existing_session_only=True,use_persistent_chrome=True,
                   force_kill_chrome_to_free_port=False)
        with patch("selenium_pipeline.vendor_template_v2.selenium._is_port_in_use",
                   return_value=False),patch(
                   "selenium_pipeline.vendor_template_v2.selenium.subprocess.Popen",
                   side_effect=AssertionError("No new browser launch")) as spawned:
            with self.assertRaisesRegex(
                    RuntimeError,
                    "EXISTING_GEMINI_DEBUG_SESSION_UNAVAILABLE_NO_SEND"):
                GeminiSeleniumClient(cfg).start()
        spawned.assert_not_called()

    def test_existing_port_vanishes_after_preflight_fails_precisely(self):
        self.provider.start.side_effect=RuntimeError(
            "EXISTING_GEMINI_DEBUG_SESSION_UNAVAILABLE_NO_SEND")
        with self.assertRaises(AcademicGeminiPreSendBlocked) as found:
            inspect(port=9222)
        self.assertEqual(found.exception.failure_phase,
                         "GEMINI_EXISTING_DEBUG_SESSION_UNAVAILABLE_NO_SEND")
        self.provider.open_clean_gemini_chat.assert_not_called()

    def test_port_disappearing_is_not_retried_as_generic_browser_error(self):
        from selenium_pipeline.gemini_selenium_only_policy import (
            prepare_with_bounded_retries,GeminiSeleniumTemporaryFailure)
        calls=[]
        def failed_attach(_):
            calls.append(1)
            raise RuntimeError(
                "EXISTING_GEMINI_DEBUG_SESSION_UNAVAILABLE_NO_SEND")
        with self.assertRaises(GeminiSeleniumTemporaryFailure) as found:
            prepare_with_bounded_retries(
                make_client=lambda:object(),prepare_without_send=failed_attach,
                dispose=lambda _:None,attempts=3,sleeper=lambda _:None)
        self.assertEqual(len(calls),1)
        self.assertEqual(found.exception.gemini_failure_phase,
                         "GEMINI_EXISTING_DEBUG_SESSION_UNAVAILABLE_NO_SEND")

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
