"""Offline fault injection for Gemini response quarantine and recovery."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from selenium_pipeline.gemini_response_recovery import (
    MAX_CAPTURE_CHARS, latest_owned_response, quarantine_snapshot,
    read_quarantined_response,
)


class FakeDriver:
    def __init__(self, *, handle="owned_tab", url="https://gemini.google.com/app",
                 response="", generating=False, broken=False):
        self.current_window_handle = handle
        self.current_url = url
        self.response = response
        self.generating = generating
        self.broken = broken
        self.calls = 0

    def execute_script(self, script):
        self.calls += 1
        if self.broken:
            raise RuntimeError("Connection interrupted")
        assert "model-response" in script
        assert "user-query" not in script
        return {"text": self.response, "generating": self.generating}


class GeminiQuarantineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name) / "local_quarantine"

    def test_rejects_other_browser_tabs_or_unknown_owned_tab(self):
        driver = FakeDriver(response='{"confidential":"other chat"}')
        for owned in (None, "different_tab"):
            with self.subTest(owned=owned):
                result = latest_owned_response(driver, owned)
                self.assertFalse(result["text"])
        self.assertEqual(driver.calls, 0)
        driver.current_url = "https://gmail.com/inbox"
        self.assertEqual(latest_owned_response(driver, "owned_tab")["text"], "")
        self.assertEqual(driver.calls, 0)

    def test_snapshot_restricted_to_visible_model_response(self):
        driver = FakeDriver(response='{"status":"generating"}',
                            generating=True)
        snap = latest_owned_response(driver, "owned_tab")
        self.assertEqual(snap["text"], '{"status":"generating"}')
        self.assertTrue(snap["generating"])
        self.assertEqual(snap["capture_status"], "visible_model_response")

    def test_14kb_partial_json_is_preserved_not_approved(self):
        raw = '{"review":"'+("x" * 14000)
        snap = latest_owned_response(
            FakeDriver(response=raw, generating=True), "owned_tab"
        )
        saved = quarantine_snapshot(snap, directory=self.dir,
                                    reason="strict_json_capture_timeout")
        self.assertEqual(saved["status"], "incomplete_untrusted")
        self.assertEqual(saved["model_response_chars"], len(raw))
        self.assertTrue(saved["generation_active_at_capture"])
        self.assertTrue(saved["not_scientifically_reviewed"])
        self.assertEqual(read_quarantined_response(saved["raw_path"]), raw)
        metadata = json.loads(saved["meta_path"].read_text(encoding="utf-8"))
        self.assertNotIn("prompt", metadata)
        self.assertNotIn("source_pdf", metadata)
        self.assertNotIn("credentials", metadata)
        self.assertEqual(len(list(self.dir.glob("*.raw.txt"))), 1)

    def test_no_model_response_still_has_failure_receipt(self):
        snap = latest_owned_response(
            FakeDriver(response="", generating=False), "owned_tab"
        )
        saved = quarantine_snapshot(snap, directory=self.dir, reason="no_json")
        self.assertEqual(saved["model_response_chars"], 0)
        self.assertEqual(saved["capture_status"], "empty_model_response")
        self.assertEqual(read_quarantined_response(saved["raw_path"]), "")

    def test_connection_interruption_fails_safe(self):
        snap = latest_owned_response(FakeDriver(broken=True), "owned_tab")
        self.assertEqual(snap["capture_status"], "unavailable")
        self.assertEqual(snap["text"], "")

    def test_tampered_response_and_receipt_cannot_be_recovered(self):
        snap = {"text":'{"complete":true}',"generating":False,
                "capture_status":"visible_model_response"}
        saved = quarantine_snapshot(snap, directory=self.dir)
        saved["raw_path"].write_text("tampered", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed"):
            read_quarantined_response(saved["raw_path"])

    def test_unicode_and_upper_bound_enforced(self):
        raw = "⽂" * (MAX_CAPTURE_CHARS + 5)
        snap = latest_owned_response(
            FakeDriver(response=raw), "owned_tab"
        )
        self.assertEqual(len(snap["text"]), MAX_CAPTURE_CHARS)
        saved = quarantine_snapshot(snap, directory=self.dir)
        self.assertEqual(
            len(read_quarantined_response(saved["raw_path"])),
            MAX_CAPTURE_CHARS,
        )

    def test_two_attempts_never_overwrite_first_attempt(self):
        snap = {"text":'{"x":1}',"capture_status":"visible_model_response",
                "generating":False}
        a = quarantine_snapshot(snap, directory=self.dir)
        b = quarantine_snapshot(snap, directory=self.dir)
        self.assertNotEqual(a["raw_path"], b["raw_path"])
        self.assertEqual(read_quarantined_response(a["raw_path"]), '{"x":1}')
        self.assertEqual(len(list(self.dir.glob("*.raw.txt"))), 2)


if __name__ == "__main__":
    unittest.main()
