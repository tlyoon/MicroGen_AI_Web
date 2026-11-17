"""Passive Gemini network evidence: same tab, counts only, no provider requests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.gemini_owned_network_diagnostics import (
    _RESOURCE_TIMING_JS,arm_owned_network_baseline,
    observe_owned_network_timing,sanitize_network_diagnostic,
)
from selenium_pipeline.gemini_response_recovery import quarantine_snapshot


class FakeDriver:
    current_window_handle="owned"
    current_url="https://gemini.google.com/app/claim123"
    def __init__(self):
        self.calls=[]
        self.epoch=1794900000000
        self.live={
            "document_epoch_ms":self.epoch,"latest_start_ms":102,
            "resource_entry_count":4,"all_new_resources":3,
            "same_origin_new_resources":1,"gemini_api_new_resources":0,
            "other_google_new_resources":2,"fetch_xhr_new_resources":2,
            "http_4xx_new_resources":1,"http_5xx_new_resources":0,
            "unknown_http_status_new_resources":2}
    def execute_script(self,script,*args):
        self.calls.append((script,args))
        if args[0]>1e15:
            return {**self.live,"latest_start_ms":100.0}
        return dict(self.live)


class OwnedNetworkDiagnosticsTests(unittest.TestCase):
    def test_no_raw_urls_or_other_tab_and_no_mutating_js(self):
        for item in (".click(", "fetch(", "XMLHttpRequest(", "send(", "navigator.clipboard",
                     "window.open(", "dispatchEvent("):
            self.assertNotIn(item,_RESOURCE_TIMING_JS)
        d=FakeDriver()
        prior=arm_owned_network_baseline(d,"owned")
        result=observe_owned_network_timing(d,"owned",baseline=prior,
                expected_url="https://gemini.google.com/app/claim123")
        self.assertEqual(result["status"],
                         "OWNED_NETWORK_RESOURCE_TIMING_OBSERVED")
        self.assertEqual(result["all_new_resources"],3)
        self.assertEqual(result["http_4xx_new_resources"],1)
        self.assertFalse(result["provider_outage_proven"])
        self.assertFalse(result["retry_authorized"])
        self.assertNotIn("url",json.dumps(result))
        self.assertNotIn("request",json.dumps(result))
        self.assertNotIn("https",json.dumps(result))
        self.assertEqual(len(d.calls),2)

    def test_changed_owner_route_or_origin_fails_without_cross_tab_read(self):
        for handle,url,expected in (
            ("foreign","https://gemini.google.com/app/claim123",
             "OWNED_NETWORK_UNAVAILABLE"),
            ("owned","https://mail.google.com/inbox",
             "OWNED_NETWORK_NOT_GEMINI"),
            ("owned","https://gemini.google.com/app/different",
             "OWNED_NETWORK_ROUTE_MISMATCH")):
            d=FakeDriver()
            d.current_window_handle=handle
            d.current_url=url
            result=observe_owned_network_timing(
                d,"owned",baseline={"document_epoch_ms":d.epoch,
                                    "latest_start_ms":100.0},
                expected_url="https://gemini.google.com/app/claim123")
            self.assertEqual(result["status"],expected)
            self.assertEqual(d.calls,[])
        d=FakeDriver()
        baseline=arm_owned_network_baseline(d,"owned")
        d.epoch+=1000
        d.live["document_epoch_ms"]=d.epoch
        self.assertEqual(observe_owned_network_timing(
            d,"owned",baseline=baseline)["status"],
            "OWNED_NETWORK_DOCUMENT_REPLACED")

    def test_forged_metadata_cannot_authorize_retry_or_store_browser_fields(self):
        d=FakeDriver()
        prior=arm_owned_network_baseline(d,"owned")
        safe=observe_owned_network_timing(d,"owned",baseline=prior)
        malicious={**safe,"prompt":"PRIVATE_TEXT","url":"https://private/",
                   "cookie":"SECRET","provider_outage_proven":True,
                   "retry_authorized":True,
                   "model_response_verified":True}
        with tempfile.TemporaryDirectory() as root:
            item=quarantine_snapshot(
                {"text":"","generating":False,
                 "capture_status":"empty_model_response"},
                directory=Path(root),reason="strict_json_capture_exception",
                owned_network_diagnostic=malicious)
            meta=json.loads(item["meta_path"].read_text())
            saved=meta["owned_tab_network_timing"]
            self.assertEqual(saved["all_new_resources"],3)
            self.assertFalse(saved["provider_outage_proven"])
            self.assertFalse(saved["retry_authorized"])
            self.assertFalse(saved["model_response_verified"])
            for forbidden in ("SECRET","PRIVATE_TEXT","https://private/"):
                self.assertNotIn(forbidden,json.dumps(meta))

    def test_unknown_no_baseline_empty_and_registry_disabled(self):
        d=FakeDriver()
        self.assertEqual(observe_owned_network_timing(
            d,"owned",baseline=None)["status"],"OWNED_NETWORK_NO_BASELINE")
        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value=None):
            self.assertIsNone(arm_owned_network_baseline(d,"owned"))
            self.assertEqual(observe_owned_network_timing(
                d,"owned",baseline={"document_epoch_ms":d.epoch,
                                    "latest_start_ms":100.0})["status"],
                             "OWNED_NETWORK_UNAVAILABLE")
        self.assertEqual(sanitize_network_diagnostic({
            "status":"OWNED_NETWORK_RESOURCE_TIMING_OBSERVED",
            "schema_version":1,
            "all_new_resources":True})["status"],
            "OWNED_NETWORK_UNAVAILABLE")
        d.live["all_new_resources"]=0
        base={"document_epoch_ms":d.epoch,"latest_start_ms":100.0}
        self.assertEqual(observe_owned_network_timing(
            d,"owned",baseline=base)["status"],
            "OWNED_NETWORK_NO_NEW_RESOURCE_TIMING")
