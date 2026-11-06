"""Provider UI error classification: protect old evidence and no-resend rule."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.gemini_provider_ui_terminal_error import (
    classify_visible_reply, inspect_quarantine,
)
from selenium_pipeline.gemini_response_recovery import quarantine_snapshot
from selenium_pipeline.gemini_bridge_failure_triage import (
    classify_owned_gemini_failure,
)
from selenium_pipeline.series_bridge import SeriesBridgeError

UI_ERROR = (
    "Gemini said\n\nI seem to be encountering an error. "
    "Can I try something else for you?"
)


class GeminiProviderVisibleUIErrorTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "quarantine"
        self.root.mkdir()

    def test_exact_owned_visible_terminal_error_separated_from_capture_failure(self):
        r = classify_visible_reply(
            text=UI_ERROR, capture_status="visible_model_response")
        self.assertEqual(r["status"],
                         "GEMINI_OWNED_MODEL_VISIBLE_UI_ERROR_NOT_API_OUTAGE_PROOF")
        self.assertTrue(r["known_gemini_ui_error_text_observed"])
        self.assertTrue(r["owned_visible_model_response_text_observed"])
        self.assertFalse(r["provider_server_outage_proven"])
        self.assertFalse(r["browser_capture_total_failure_proven"])
        self.assertFalse(r["original_source_retry_authorized"])
        self.assertNotIn(UI_ERROR, str(r))

    def test_exact_new_model_ui_error_without_claiming_api_outage(self):
        error = "Sorry, something went wrong. Please try your request again."
        result = classify_visible_reply(
            text=error, capture_status="visible_model_response")
        self.assertTrue(result["known_gemini_ui_error_text_observed"])
        self.assertEqual(result["known_gemini_ui_error_code"],
                         "GEMINI_MODEL_REQUEST_ERROR")
        self.assertFalse(result["provider_server_outage_proven"])
        self.assertFalse(result["original_source_retry_authorized"])
        self.assertNotIn(error, str(result))
        for text, capture, generating in (
            ("User said: " + error, "visible_model_response", False),
            (error + " Additional text", "visible_model_response", False),
            (error, "unavailable", False),
            (error, "visible_model_response", True),
        ):
            with self.subTest(capture=capture, generating=generating, text=text[:15]):
                rejected = classify_visible_reply(
                    text=text, capture_status=capture, generating=generating)
                self.assertFalse(rejected["known_gemini_ui_error_text_observed"])

    def test_owned_gemini_terminal_guard_fails_closed_on_other_tab(self):
        from selenium_pipeline.gemini_provider_ui_terminal_error import (
            GeminiOwnedVisibleTerminalError, require_no_owned_terminal_error)
        class FakeDriver:
            def __init__(self):
                self.current_window_handle = "microgen_owned"
                self.current_url = "https://gemini.google.com/app"
                self.text = "Sorry, something went wrong. Please try your request again."
                self.generating = False
                self.calls = 0
            def execute_script(self, script):
                self.calls += 1
                assert "model-response" in script
                return {"text": self.text, "generating": self.generating}
        driver = FakeDriver()
        with self.assertRaisesRegex(GeminiOwnedVisibleTerminalError,
                                    "NO_RESEND"):
            require_no_owned_terminal_error(driver, "microgen_owned")
        self.assertEqual(driver.calls, 1)
        require_no_owned_terminal_error(driver, "other_user_tab")
        self.assertEqual(driver.calls, 1)
        driver.generating = True
        require_no_owned_terminal_error(driver, "microgen_owned")
        driver.generating = False
        driver.text = "The word sorry, something went wrong appears in a textbook."
        require_no_owned_terminal_error(driver, "microgen_owned")

    def test_figure_watcher_exits_on_same_owned_model_error_without_waiting(self):
        # Execute the actual figure-mapper watcher without importing its
        # command-line module or contacting any browser/model service.
        import ast
        import os
        import time
        from types import SimpleNamespace
        from selenium_pipeline.gemini_provider_ui_terminal_error import (
            GeminiOwnedVisibleTerminalError,
        )
        source = Path(__file__).resolve().parents[1] / (
            "selenium_pipeline/vendor_template_v2/map_and_rename_selenium_v8.py"
        )
        tree = ast.parse(source.read_text(encoding="utf8"))
        func = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == "wait_for_mapping_response_ready")
        error = "Sorry, something went wrong. Please try your request again."

        class FakeDriver:
            current_window_handle = "microgen_owned"
            current_url = "https://gemini.google.com/app"
            def find_elements(self, *_):
                return []
            def execute_script(self, script):
                assert "model-response" in script
                return {"text": error, "generating": False}
        emitted = []
        ns = {
            "os": os, "time": time, "log": lambda *v: emitted.append(v),
            "clean_model_text": lambda text: text,
            "get_latest_response_text": lambda driver: error,
            "_looks_like_gemini_failure_text":
                lambda text: "something went wrong" in text.lower(),
            "parse_mapping_lines": lambda text: [],
            "GeminiGenerationStalled": RuntimeError,
        }
        exec(compile(ast.fix_missing_locations(
            ast.Module(body=[func], type_ignores=[])), str(source), "exec"), ns)
        client = SimpleNamespace(driver=FakeDriver(),
                                 _automation_tab="microgen_owned")
        start = time.monotonic()
        with self.assertRaisesRegex(
            GeminiOwnedVisibleTerminalError, "NO_RESEND"
        ):
            ns["wait_for_mapping_response_ready"](
                client, timeout=60, poll=0.1,
            )
        self.assertLess(time.monotonic() - start, 2.0)
        self.assertTrue(any("OWNED_VISIBLE_UI_TERMINAL_ERROR_NO_RESEND"
                            in str(msg) for msg in emitted))

    def test_copy_accepted_only_if_exact_model_reply_not_quasi_error(self):
        for raw, capture, generating in (
            (UI_ERROR, "unavailable", False),
            (UI_ERROR, "visible_model_response", True),
            (UI_ERROR + "\nAdditional commentary", "visible_model_response", False),
            ("User said: " + UI_ERROR, "visible_model_response", False),
            ("Gemini said\n\nGemini is typing", "visible_model_response", False),
            ("", "empty_model_response", False),
        ):
            with self.subTest(capture=capture, generating=generating, length=len(raw)):
                result = classify_visible_reply(
                    text=raw, capture_status=capture, generating=generating)
                self.assertFalse(result["known_gemini_ui_error_text_observed"])

    def test_prior_immutable_quarantine_reclassified_read_only(self):
        saved = quarantine_snapshot({
            "text": UI_ERROR, "generating": False,
            "capture_status": "visible_model_response",
        }, directory=self.root, reason="strict_json_capture_timeout")
        before = saved["raw_path"].read_bytes()
        r = inspect_quarantine(
            metadata_path=saved["meta_path"], allowed_root=self.root)
        self.assertEqual(r["quarantined_model_response_chars"], len(UI_ERROR))
        self.assertTrue(r["quarantine_payload_sha256_verified"])
        self.assertTrue(r["known_gemini_ui_error_text_observed"])
        self.assertFalse(r["provider_server_outage_proven"])
        self.assertFalse(r["original_source_retry_authorized"])
        self.assertFalse(r["new_model_or_tts_calls"])
        self.assertNotIn(UI_ERROR, str(r))
        self.assertEqual(before, saved["raw_path"].read_bytes())
        meta = json.loads(saved["meta_path"].read_text(encoding="utf8"))
        self.assertTrue(meta["known_gemini_ui_error_text_observed"])
        self.assertFalse(meta["provider_server_outage_proven"])

    def test_canonical_windows_quarantine_root_alias_from_temp(self):
        # GitHub Actions' Windows temp can be a reparse-path alias.
        # snapshot() resolves its root but .absolute() retains '..'.
        saved = quarantine_snapshot({
            "text": UI_ERROR, "generating": False,
            "capture_status": "visible_model_response",
        }, directory=self.root)
        alias = self.root / ".." / self.root.name
        self.assertNotEqual(alias.absolute(), self.root.absolute())
        self.assertEqual(alias.resolve(), self.root.resolve())
        result = inspect_quarantine(
            metadata_path=saved["meta_path"], allowed_root=alias)
        self.assertTrue(result["known_gemini_ui_error_text_observed"])
        self.assertTrue(result["quarantine_payload_sha256_verified"])

    def test_tamper_prevents_reclassification(self):
        saved = quarantine_snapshot({
            "text": UI_ERROR, "generating": False,
            "capture_status": "visible_model_response",
        }, directory=self.root)
        saved["raw_path"].write_text("tampered", encoding="utf8")
        with self.assertRaisesRegex(ValueError, "changed"):
            inspect_quarantine(metadata_path=saved["meta_path"],
                               allowed_root=self.root)

    def test_other_quarantine_root_denied(self):
        saved = quarantine_snapshot({
            "text": UI_ERROR, "generating": False,
            "capture_status": "visible_model_response",
        }, directory=self.root)
        with self.assertRaisesRegex(ValueError, "trusted local root"):
            inspect_quarantine(metadata_path=saved["meta_path"],
                               allowed_root=self.root.parent)

    def test_owned_vendor_error_is_not_reported_as_api_outage(self):
        err = SeriesBridgeError(
            "Gemini browser returned a visible owned-model UI error "
            "without the requested JSON answer; captured and quarantined.")
        r = classify_owned_gemini_failure(err)
        self.assertEqual(r["stage"],
                         "OWNED_GEMINI_UI_TERMINAL_ERROR_TEXT_NOT_API_PROOF")
        self.assertFalse(r["gemini_provider_overload_proven"])
        self.assertFalse(r["retry_or_scientific_approval_authorized"])


if __name__ == "__main__":
    unittest.main()
