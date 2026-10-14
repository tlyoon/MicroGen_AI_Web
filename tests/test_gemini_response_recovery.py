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

    def test_short_dom_placeholder_prefers_verified_vendor_copy(self):
        from selenium_pipeline.gemini_response_recovery import (
            response_snapshot_with_scoped_copy,
        )
        driver = FakeDriver(response="Thinking...")
        full = '{"reply":"' + ("verified response content " * 20) + '"}'
        calls = []
        def response_scoped_copy(d):
            calls.append(d.current_window_handle)
            return full
        result = response_snapshot_with_scoped_copy(
            driver, "owned_tab", copy_response=response_scoped_copy,
        )
        self.assertEqual(result["text"], full)
        self.assertEqual(result["capture_status"], "vendor_verified_response_copy")
        self.assertEqual(calls, ["owned_tab"])
        saved = quarantine_snapshot(result, directory=self.dir)
        self.assertEqual(read_quarantined_response(saved["raw_path"]), full)

    def test_vendor_copy_never_runs_on_other_tab_or_url(self):
        from selenium_pipeline.gemini_response_recovery import (
            response_snapshot_with_scoped_copy,
        )
        spy = []
        def copy(d):
            spy.append(1)
            return "long response " * 30
        driver = FakeDriver(handle="borrowed_tab", response="Thinking...")
        self.assertEqual(
            response_snapshot_with_scoped_copy(
                driver, "owned_tab", copy_response=copy
            )["text"], ""
        )
        driver.current_url = "https://mail.google.com/"
        self.assertEqual(
            response_snapshot_with_scoped_copy(
                driver, "borrowed_tab", copy_response=copy
            )["text"], ""
        )
        self.assertEqual(spy, [])

    def test_vendor_copy_cannot_replace_full_dom_with_shorter_text(self):
        from selenium_pipeline.gemini_response_recovery import (
            response_snapshot_with_scoped_copy,
        )
        full = "This is a full model answer. " * 7
        driver = FakeDriver(response=full)
        spy = []
        result = response_snapshot_with_scoped_copy(
            driver,"owned_tab",copy_response=lambda d: spy.append(1),
        )
        self.assertEqual(result["text"], full)
        self.assertEqual(spy, [])

    def test_live_transport_timeout_quarantines_before_owned_tab_shutdown(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from contextlib import nullcontext
        from selenium_pipeline import series_gemini
        from selenium_pipeline.series_bridge import SeriesBridgeError

        driver = FakeDriver(response="Thinking...")
        full = '{"test":"verified response recovery",' + (
            '"sentence":"The last model answer was preserved without reupload."'
        ) + "}"
        fake_client = SimpleNamespace(
            driver=driver,
            _automation_tab="owned_tab",
            start=lambda **kwargs: None,
            open_clean_gemini_chat=lambda: None,
            upload_files=lambda files: None,
            type_prompt_text=lambda prompt, **kw: True,
            click_send_with_fallbacks=lambda **kw: True,
        )
        order = []
        def shutdown():
            order.append("shutdown")
        fake_client.shutdown = shutdown
        def capture(*a, **kw):
            raise TimeoutError("Simulated Gemini timeout")
        def copy(*a, **kw):
            order.append("copy")
            return full
        vendor = SimpleNamespace(
            Config=lambda **kw: SimpleNamespace(**kw),
            GeminiSeleniumClient=lambda cfg: fake_client,
            capture_gemini_response_like_manual_copy=capture,
            _copy_via_toolbar_copy_button=copy,
        )
        with patch.object(series_gemini, "_vendor_module",return_value=vendor), \
             patch("selenium_pipeline.three_pc_worker.LocalInstanceLock",
                   side_effect=lambda *a, **kw: nullcontext()), \
             patch("selenium_pipeline.gemini_model.ensure_mode"), \
             patch.dict("os.environ",{"LOCALAPPDATA":str(self.dir)}):
            with self.assertRaisesRegex(
                SeriesBridgeError, "quarantined"
            ):
                series_gemini._browser_request(
                    "A synthetic prompt",[self.dir/"source.pdf"],
                    port=9222,wait_cap_s=90,
                )
        self.assertEqual(order,["copy","shutdown"])
        snapshots=list((self.dir/"Microvid"/"gemini_quarantine").glob("*.raw.txt"))
        self.assertEqual(len(snapshots),1)
        self.assertEqual(read_quarantined_response(snapshots[0]),full)


if __name__ == "__main__":
    unittest.main()
