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
