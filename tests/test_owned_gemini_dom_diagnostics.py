"""V6 same-owned-tab Gemini post-Send failure diagnostics, no source replay."""
import json
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.owned_gemini_dom_diagnostics import (
    _OWNED_RESPONSE_METADATA_JS,
    observe_owned_dom_metadata,
    sanitize_dom_diagnostic,
)
from selenium_pipeline.gemini_response_recovery import (
    quarantine_snapshot, read_quarantined_response,
)


class FakeOwnedDriver:
    def __init__(self, *, handle="owned", url="https://gemini.google.com/app/claim123",
                 result=None, fail=False):
        self.current_window_handle = handle
        self.current_url = url
        self.fail = fail
        self.calls = []
        self.result = result if result is not None else {
            "model_response_nodes": 1,
            "visible_model_response_nodes": 1,
            "visible_model_markdown_nodes": 1,
            "visible_assistant_semantic_nodes": 0,
            "model_answer_text_length": 32,
            "visible_stop_controls": 0,
        }

    def execute_script(self, script):
        self.calls.append(script)
        if self.fail:
            raise RuntimeError("Disconnected")
        return self.result


class SameTabDomDiagnosticsTests(unittest.TestCase):
    def test_read_only_owned_response_counts_not_text_or_html(self):
        self.assertNotIn(".click(", _OWNED_RESPONSE_METADATA_JS)
        self.assertNotIn("dispatchEvent(", _OWNED_RESPONSE_METADATA_JS)
        self.assertNotIn("navigator.clipboard", _OWNED_RESPONSE_METADATA_JS)
        self.assertNotIn("window.open(", _OWNED_RESPONSE_METADATA_JS)
        driver = FakeOwnedDriver()
        result = observe_owned_dom_metadata(
            driver, "owned", expected_url="https://gemini.google.com/app/claim123")
        self.assertEqual(result["status"], "OWNED_DOM_MODEL_TEXT_PRESENT")
        self.assertEqual(result["model_answer_text_length"], 32)
        self.assertEqual(len(driver.calls), 1)
        self.assertFalse(result["provider_outage_proven"])
        self.assertFalse(result["selector_defect_proven"])
        self.assertFalse(result["academic_approval"])
        self.assertFalse(result["retry_authorized"])
        self.assertNotIn("url", result)
        self.assertNotIn("text", result)

    def test_different_tab_or_conversation_never_executed(self):
        cases = [
            ("foreign", "https://gemini.google.com/app/claim123", "OWNED_DOM_UNAVAILABLE"),
            ("owned", "https://gemini.google.com/app/changed", "OWNED_DOM_ROUTE_MISMATCH"),
            ("owned", "https://mail.google.com/inbox", "OWNED_DOM_NOT_GEMINI"),
        ]
        for handle, url, expected in cases:
            with self.subTest(expected=expected):
                driver = FakeOwnedDriver(handle=handle,url=url)
                got = observe_owned_dom_metadata(
                    driver,"owned",expected_url="https://gemini.google.com/app/claim123")
                self.assertEqual(got["status"],expected)
                self.assertFalse(got["retry_authorized"])
                self.assertEqual(driver.calls, [])

    def test_dom_state_classification_does_not_infer_provider_outage(self):
        states = [
            (0,0,0,0,"OWNED_DOM_MODEL_ELEMENTS_ABSENT"),
            (0,0,2,0,"OWNED_DOM_ALTERNATE_ASSISTANT_PRESENT"),
            (1,1,0,0,"OWNED_DOM_MODEL_ELEMENTS_EMPTY"),
            (1,1,0,32,"OWNED_DOM_MODEL_TEXT_PRESENT"),
        ]
        for total,visible,semantic,chars,expected in states:
            with self.subTest(expected=expected):
                driver = FakeOwnedDriver(result={
                    "model_response_nodes":total,
                    "visible_model_response_nodes":visible,
                    "visible_model_markdown_nodes":0,
                    "visible_assistant_semantic_nodes":semantic,
                    "model_answer_text_length":chars,
                    "visible_stop_controls":1,
                })
                got=observe_owned_dom_metadata(
                    driver,"owned",expected_url="https://gemini.google.com/app/claim123")
                self.assertEqual(got["status"],expected)
                self.assertFalse(got["provider_outage_proven"])
                self.assertFalse(got["selector_defect_proven"])

    def test_disabled_or_changed_registry_blocks_only_diagnostic(self):
        from unittest.mock import patch
        for replacement in (None, "UNREVIEWED_BROWSER_RECOVERY"):
            driver=FakeOwnedDriver()
            with patch(
                "selenium_pipeline.recovery_registry.lookup_mechanism",
                return_value=replacement):
                got=observe_owned_dom_metadata(driver,"owned")
            self.assertEqual(got["status"],"OWNED_DOM_UNAVAILABLE")
            self.assertEqual(driver.calls,[])
            self.assertFalse(got["retry_authorized"])

    def test_browser_exception_or_bad_shape_fails_closed(self):
        driver=FakeOwnedDriver(fail=True)
        got=observe_owned_dom_metadata(driver,"owned")
        self.assertEqual(got["status"],"OWNED_DOM_UNAVAILABLE")
        self.assertFalse(got["retry_authorized"])
        for malformed in (
            {"model_response_nodes":99999},
            {"model_response_nodes":True},
            {"model_response_nodes":"3"},
            "this is raw browser DOM text",
        ):
            driver=FakeOwnedDriver(result=malformed)
            self.assertEqual(
                observe_owned_dom_metadata(driver,"owned")["status"],
                "OWNED_DOM_UNAVAILABLE")

    def test_quarantine_allowlist_drops_secrets_and_keeps_original_sha(self):
        driver=FakeOwnedDriver()
        diagnostic=observe_owned_dom_metadata(driver,"owned")
        malicious=dict(diagnostic)
        malicious.update({
            "url":"https://gemini.google.com/app/foreign",
            "prompt":"PRIVATE_SOURCE_TEXT",
            "password":"not-a-secret",
            "retry_authorized":True,
            "provider_outage_proven":True,
            "academic_approval":True,
        })
        with tempfile.TemporaryDirectory() as temp:
            saved=quarantine_snapshot(
                {"text":"","generating":False,"capture_status":"empty_model_response"},
                directory=Path(temp),reason="strict_json_capture_timeout",
                owned_dom_diagnostic=malicious)
            receipt=json.loads(saved["meta_path"].read_text(encoding="utf8"))
            dom=receipt["owned_tab_response_dom"]
            self.assertEqual(dom["status"],"OWNED_DOM_MODEL_TEXT_PRESENT")
            self.assertEqual(dom["model_answer_text_length"],32)
            for forbidden in ("url","prompt","password"):
                self.assertNotIn(forbidden,json.dumps(receipt))
            self.assertFalse(dom["retry_authorized"])
            self.assertFalse(dom["academic_approval"])
            self.assertFalse(dom["provider_outage_proven"])
            self.assertEqual(read_quarantined_response(saved["raw_path"]),"")

    def test_real_transport_failure_quarantines_metadata_before_shutdown(self):
        from contextlib import nullcontext
        from types import SimpleNamespace
        from unittest.mock import patch
        from selenium_pipeline import series_gemini
        from selenium_pipeline.series_bridge import SeriesBridgeError

        class LiveOwnedDriver(FakeOwnedDriver):
            def execute_script(self, script):
                self.calls.append(script)
                if "model_response_nodes:" in script:
                    return self.result
                return {"text":"","generating":False}

        driver=LiveOwnedDriver(result={
            "model_response_nodes":0,
            "visible_model_response_nodes":0,
            "visible_model_markdown_nodes":0,
            "visible_assistant_semantic_nodes":0,
            "model_answer_text_length":0,
            "visible_stop_controls":0,
        })
        events=[]
        client=SimpleNamespace(
            driver=driver,_automation_tab="owned",
            start=lambda **kw:None,
            open_clean_gemini_chat=lambda:None,
            upload_files=lambda files:None,
            type_prompt_text=lambda *a,**kw:True,
            shutdown=lambda:events.append("shutdown"))
        vendor=SimpleNamespace(
            Config=lambda **kw:SimpleNamespace(**kw),
            GeminiSeleniumClient=lambda cfg:client,
            capture_gemini_response_like_manual_copy=lambda *a,**kw:(
                (_ for _ in ()).throw(TimeoutError("stalled model"))),
            _copy_via_toolbar_copy_button=lambda *a,**kw:"",
        )
        with (tempfile.TemporaryDirectory() as temp,
              patch.object(series_gemini,"_vendor_module",return_value=vendor),
              patch("selenium_pipeline.three_pc_worker.LocalInstanceLock",
                    side_effect=lambda *args,**kw:nullcontext()),
              patch("selenium_pipeline.gemini_model.assert_owned_gemini_mode",
                    return_value="Open mode picker, currently Gemini Flash"),
              patch("selenium_pipeline.gemini_thinking.select_owned_gemini_thinking_with_recovery",
                    return_value="medium"),
              patch("selenium_pipeline.gemini_thinking.assert_owned_gemini_thinking_level",
                    return_value="medium"),
              patch("selenium_pipeline.gemini_response_recovery.await_owned_gemini_send_visible",
                    return_value=True),
              patch("selenium_pipeline.gemini_selenium_only_policy.owned_gemini_send_baseline",
                    return_value={"users":0,"models":0,"editor_length":30,"route":"/app"}),
              patch("selenium_pipeline.gemini_selenium_only_policy.click_one_owned_gemini_send",
                    return_value=True),
              patch("selenium_pipeline.gemini_selenium_only_policy.observe_gemini_send_registration",
                    return_value={"status":"NEW_USER_TURN_AND_COMPOSER_CLEARED",
                                  "registered":True}),
              patch("selenium_pipeline.gemini_response_recovery.poll_existing_owned_response",
                    return_value=(None,{
                        "text":"","generating":False,
                        "capture_status":"empty_model_response"})),
              patch.dict("os.environ",{"LOCALAPPDATA":temp})):
            with self.assertRaises(SeriesBridgeError):
                series_gemini._browser_request(
                    "Non-sensitive test",[],port=9222,wait_cap_s=30,
                    min_chars=20,accept_fn=lambda _:False)
            metadata=list(
                (Path(temp)/"Microvid"/"gemini_quarantine").glob("*.meta.json"))
            self.assertEqual(len(metadata),1)
            audit=json.loads(metadata[0].read_text(encoding="utf8"))
            self.assertEqual(audit["owned_tab_response_dom"]["status"],
                             "OWNED_DOM_MODEL_ELEMENTS_ABSENT")
            self.assertFalse(audit["original_source_retry_authorized"])
            self.assertFalse(audit["owned_tab_response_dom"]["retry_authorized"])
        self.assertEqual(events,["shutdown"])

    def test_poisoned_diagnostic_is_downgraded_not_persisted(self):
        got=sanitize_dom_diagnostic({
            "schema_version":1,
            "status":"OWNED_DOM_MODEL_TEXT_PRESENT",
            "model_answer_text_length":"very long prompt here",
            "secret":"private",
        })
        self.assertEqual(got["status"],"OWNED_DOM_UNAVAILABLE")
        self.assertNotIn("secret",got)
        self.assertFalse(got["retry_authorized"])


if __name__=="__main__":
    unittest.main()
