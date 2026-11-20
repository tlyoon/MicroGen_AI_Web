"""Actual shared browser request cannot upload or Send on wrong diagnostic model."""
from __future__ import annotations
from contextlib import nullcontext
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from selenium_pipeline.series_gemini import _browser_request, OwnedGeminiResponse


class BrowserExactDiagnosticContractTests(TestCase):
    def test_response_can_carry_exact_owned_model_and_effort_evidence(self):
        result=OwnedGeminiResponse(
            '{"probe":"x"}',registration_status="NEW_USER_TURN_AND_COMPOSER_CLEARED",
            new_turn_verified=True,verified_model_family="neon",
            verified_thinking_level="high")
        self.assertEqual(result.gemini_verified_model_family,"neon")
        self.assertEqual(result.gemini_verified_thinking_level,"high")
        self.assertTrue(result.gemini_new_user_turn_verified)

    def test_wrong_model_fails_before_upload_or_send_even_with_source_free_pdfs(self):
        calls=[]
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            pdf=root/"SyntheticA.pdf";pdf.write_bytes(b"%PDF-1.4 small offline")
            class FakeClient:
                def __init__(self,*a,**kw):
                    self._automation_tab="owned";self.driver=SimpleNamespace()
                def start(self,**kw):calls.append("start")
                def open_clean_gemini_chat(self):
                    os.environ["MICROGEN_GEMINI_UI_MODE"]="pro"
                    calls.append("new_chat_pro")
                def upload_files(self,*a):calls.append("upload")
                def type_prompt_text(self,*a,**kw):calls.append("prompt")
                def shutdown(self):calls.append("shutdown")
            vendor=SimpleNamespace(Config=lambda **kw:SimpleNamespace(**kw),
                                   GeminiSeleniumClient=FakeClient)
            def prepare(*,make_client,prepare_without_send,dispose,**kw):
                client=make_client()
                try:prepare_without_send(client)
                finally:dispose(client)
            with patch.dict(os.environ,{"LOCALAPPDATA":tmp,
                "MICROGEN_ACTIVE_GENERATION_STAGE":"academic_review",
                "MICROGEN_GEMINI_UI_MODE":"pro",
                "MICROGEN_GEMINI_THINKING_LEVEL":"high"}):
                with patch("selenium_pipeline.series_gemini._vendor_module",
                           return_value=vendor),patch(
                    "selenium_pipeline.three_pc_worker.LocalInstanceLock",
                    return_value=nullcontext()),patch(
                    "selenium_pipeline.gemini_selenium_only_policy.prepare_with_bounded_retries",
                    side_effect=prepare),patch(
                    "selenium_pipeline.gemini_selenium_only_policy.click_one_owned_gemini_send"
                    ) as send:
                    try:
                        _browser_request("ONLY SYNTHETIC", [pdf], port=9222,
                                         wait_cap_s=8, expected_runtime_family="neon",
                                         expected_thinking_level="high")
                    except Exception: pass
                    send.assert_not_called()
            self.assertIn("new_chat_pro",calls)
            self.assertNotIn("upload",calls)
            self.assertNotIn("prompt",calls)
            self.assertNotIn("send",calls)

    def test_wrong_diag_parameters_rejected_without_browser(self):
        with patch("selenium_pipeline.series_gemini._vendor_module",
                   side_effect=AssertionError("Should never need actual vendor")):
            with self.assertRaises(Exception):
                _browser_request("text",[],port=9222,wait_cap_s=8,
                                  expected_runtime_family="flash-lite",
                                  expected_thinking_level="low")


if __name__=="__main__":
    import unittest
    unittest.main()
