"""Recovery port: fail-closed monitor registration and real task-state honesty."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.project_status_recovery_registry import lookup_mechanism
from selenium_pipeline.project_development_status import evaluate

NOW=1795170000.0

def task(state):
    return {"state":state,"last_result":0,"run_level":"Limited",
            "logon":"Interactive","last_run":"2026-11-20T08:00:00+00:00"}

class ProjectStatusConsolidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"registry.json"
        self.doc={
          "schema_version":1,"status":"SOURCE_BOUND_PROJECT_STATUS_RECOVERY_V1",
          "entries":[{
            "match_type":"development_status_watchdog",
            "signature":"V71_PROJECT_TASK_DISABLED_STALE_OR_HEARTBEAT_MISSING",
            "mechanism":"INSPECT_NATIVE_TASK_AND_REPORT_VERIFIED_STALL_WITHOUT_UNSAFE_REPLAY",
            "handler":"NORMAL_WINDOWS_PROJECT_STATUS_MONITOR",
            "enabled":True,"retry_limit":0,
          }]
        }
    def save(self):
        self.path.write_text(json.dumps(self.doc),encoding="utf8")
    def test_real_mechanism_is_allowlisted(self):
        self.save()
        self.assertEqual(lookup_mechanism("development_status_watchdog",
                         "V71_PROJECT_TASK_DISABLED_STALE_OR_HEARTBEAT_MISSING",path=self.path),
                         "INSPECT_NATIVE_TASK_AND_REPORT_VERIFIED_STALL_WITHOUT_UNSAFE_REPLAY")
    def test_disabled_registry_fails_closed(self):
        self.doc["entries"][0]["enabled"]=False
        self.save()
        with self.assertRaises(ValueError):lookup_mechanism(
          "development_status_watchdog",
          "V71_PROJECT_TASK_DISABLED_STALE_OR_HEARTBEAT_MISSING",path=self.path)
    def test_added_arbitrary_handler_rejected(self):
        self.doc["entries"][0]["handler"]="SEND_NEW_GEMINI_REQUESTS"
        self.save()
        with self.assertRaises(ValueError):lookup_mechanism(
          "development_status_watchdog",
          "V71_PROJECT_TASK_DISABLED_STALE_OR_HEARTBEAT_MISSING",path=self.path)
    def test_duplicate_or_unregistered_handlers_rejected(self):
        self.doc["entries"].append(self.doc["entries"][0].copy())
        self.save()
        with self.assertRaises(ValueError):lookup_mechanism(
          "development_status_watchdog",
          "V71_PROJECT_TASK_DISABLED_STALE_OR_HEARTBEAT_MISSING",path=self.path)
    def test_monitor_and_source_disabled_both_visible(self):
        s=evaluate(now=NOW,tasks={"source":task("Disabled"),
            "monitor":task("Disabled")},cycle={"status":"NO_CYCLE_RECEIPT"},
            g2={"status":"G2_EVIDENCE_UNVERIFIABLE","accepted":None,"total":None},
            heartbeat=None)
        self.assertEqual(s["status"],"BLOCKED")
        self.assertIn("SOURCE_ONLY_SCHEDULE_NOT_ENABLED",s["blockers"])
        self.assertIn("STATUS_WATCHDOG_TASK_NOT_ENABLED",s["blockers"])
        self.assertFalse(s["project_complete"])
        self.assertFalse(s["development_worker_attested"])
    def test_historical_g2_not_converted_to_claim(self):
        s=evaluate(now=NOW,tasks={"source":task("Disabled"),
            "monitor":task("Disabled")},cycle={"status":"NO_CYCLE_RECEIPT"},
            g2={"status":"G2_EVIDENCE_UNVERIFIABLE","accepted":None,"total":None},
            heartbeat=None)
        self.assertIsNone(s["g2"]["accepted"])
        self.assertFalse(s["project_completion_verified"])

if __name__=="__main__":unittest.main()
