"""Gemini 4 browser request entrypoint: never index a retired Pro/Flash map."""
from __future__ import annotations

from contextlib import nullcontext
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from selenium_pipeline.gemini_model import (
    browser_model_evidence,browser_requested_model_id,GeminiModelError)


class BrowserModelIdentityRouteTests(TestCase):
    def test_all_supported_browser_families_can_assert_ui_without_fake_api_id(self):
        for family in (
                "neon","carbon","hydrogen","hydrogen-thinking","argon",
                "flash","flash-lite","pro"):
            with self.subTest(family=family),patch.dict(
                    os.environ,{"MICROGEN_LLM_MODEL":""}):
                value=browser_requested_model_id(family)
                if family in ("neon","carbon","hydrogen",
                              "hydrogen-thinking","argon"):
                    self.assertEqual(value,"ui-only-"+family)
                proof=browser_model_evidence(
                    "Open mode picker, currently Gemini 4 "+family.title(),
                    requested_mode=family,requested_model_id=value)
                self.assertTrue(proof["selected_family_verified"])
                self.assertFalse(proof["exact_model_id_verified"])

    def test_new_model_from_env_must_match_owned_ui_not_default_pro(self):
        with patch.dict(os.environ,{"MICROGEN_LLM_MODEL":"ui-only-neon"}):
            chosen=browser_requested_model_id("neon")
            self.assertEqual(chosen,"ui-only-neon")
            evidence=browser_model_evidence(
                "Open mode picker, currently Neon High",
                requested_mode="neon",requested_model_id=chosen)
            self.assertEqual(evidence["verification_scope"],
                             "browser_ui_family_only")
        with patch.dict(os.environ,{"MICROGEN_LLM_MODEL":"gemini-3.1-pro"}):
            with self.assertRaisesRegex(GeminiModelError,"contradicts"):
                browser_model_evidence(
                    "Open mode picker, currently Neon High",
                    requested_mode="neon",
                    requested_model_id=browser_requested_model_id("neon"))
        with self.assertRaises(GeminiModelError):
            browser_requested_model_id("unknown-browser-model")

    def test_real_series_browser_prepare_reaches_presend_upload_without_index_error(self):
        """Proof directly through original series _browser_request prepare path.

        A synthetic source-free attachment triggers a controlled exception
        *before upload*, preventing any possibility of a model Send.
        """
        from selenium_pipeline.series_gemini import _browser_request
        tmp=TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        directory=Path(tmp.name)
        fake_pdf=directory/"SyntheticOnly.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4\n% synthetic test; never uploaded")
        reached=[]
        class Client:
            def __init__(self,*_args,**_kwargs):
                self.driver=SimpleNamespace()
                self._automation_tab="owned"
            def start(self,**kwargs):
                self_started=True
                reached.append("start")
            def open_clean_gemini_chat(self):
                os.environ["MICROGEN_GEMINI_UI_MODE"]="neon"
                os.environ["MICROGEN_LLM_MODEL"]="ui-only-neon"
                reached.append("fresh_chat_neon")
            def upload_files(self,attachments):
                reached.append("exact_model_evidence_passed")
                raise RuntimeError("SYNTHETIC_SOURCE_FREE_STOP_BEFORE_UPLOAD")
            def shutdown(self): reached.append("shutdown")
        vendor=SimpleNamespace(
            Config=lambda **kw:SimpleNamespace(**kw),
            GeminiSeleniumClient=Client)
        def one_prepare(*,make_client,prepare_without_send,dispose,**kwargs):
            owned=make_client()
            try:prepare_without_send(owned)
            finally:dispose(owned)
            raise AssertionError("Upload must fail closed before any Send")
        with patch.dict(os.environ,{
            "LOCALAPPDATA":str(directory),
            "MICROGEN_ACTIVE_GENERATION_STAGE":"narration",
            "MICROGEN_GEMINI_UI_MODE":"flash",
            "MICROGEN_GEMINI_THINKING_LEVEL":"medium",
            "MICROGEN_LLM_MODEL":"",
            "MICROGEN_DYNAMIC_ROUTE_PENDING":
                '{"schema_version":1,"stage":"narration","family":"neon",'
                '"catalog_sha256":"'+("b"*64)+'"}',
        }),patch(
            "selenium_pipeline.series_gemini._vendor_module",
            return_value=vendor),patch(
            "selenium_pipeline.three_pc_worker.LocalInstanceLock",
            return_value=nullcontext()),patch(
            "selenium_pipeline.gemini_selenium_only_policy.prepare_with_bounded_retries",
            side_effect=one_prepare),patch(
            "selenium_pipeline.gemini_thinking.select_owned_gemini_thinking_with_recovery",
            return_value="medium"),patch(
            "selenium_pipeline.gemini_model.assert_owned_gemini_mode",
            return_value="Open mode picker, currently Neon Medium") as proof:
            try:
                _browser_request("synthetic diagnostic only",[fake_pdf],
                                 port=9222,wait_cap_s=10)
            except (RuntimeError,ValueError,AssertionError):
                pass
        self.assertIn("exact_model_evidence_passed",reached)
        self.assertEqual(proof.call_count,1)
        self.assertNotIn("send",reached)
        self.assertNotIn("files_uploaded",reached)


if __name__=="__main__":
    import unittest
    unittest.main()
