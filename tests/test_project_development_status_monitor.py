"""PR564 watchdog, false-completion, scheduler-stall and alert regressions."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline.project_development_status import (
    MAX_AGE_SECONDS, _safe_json, evaluate, publish,
    record_sourceonly_heartbeat, _report_md,
)
from selenium_pipeline.windows_project_status_monitor_task import _wrap, _verify_task


NOW = 1795170000.0


def task(state="Ready", last_result=0, ago=1800):
    from datetime import datetime, timezone
    return {"state": state, "last_result": last_result,
            "run_level": "Limited", "logon": "Interactive",
            "last_run": datetime.fromtimestamp(NOW-ago,timezone.utc).isoformat(),
            "next_run": datetime.fromtimestamp(NOW+600,timezone.utc).isoformat()}


def sample(*, source=None, monitor=None, cycle=None, heartbeat=None,
           worker=False, g2=None):
    return evaluate(
        now=NOW,
        tasks={"source": source or task(),
               "monitor": monitor or task()},
        cycle=cycle or {"status": "PERSISTENT_SOURCE_ONLY_CHECKPOINT_CYCLE_RECONCILED",
                        "verified_stage_receipts": 6},
        g2=g2 or {"status": "SOURCE_REVIEW_UNFINISHED",
                  "accepted": 23, "total": 85, "pending": 62,
                  "complete": False},
        heartbeat=heartbeat, development_worker_attested=worker)


class ProjectStatusMonitorTests(unittest.TestCase):
    def test_sourceonly_ready_is_not_project_running(self):
        x=sample()
        self.assertEqual(x["status"], "PENDING")
        self.assertFalse(x["project_complete"])
        self.assertIn("AUTONOMOUS_DEVELOPMENT_EXECUTOR_NOT_VERIFIED", x["blockers"])

    def test_six_of_six_not_release(self):
        self.assertFalse(sample()["project_completion_verified"])
        self.assertFalse(sample()["student_release_authorized"])

    def test_malformed_source_evidence_blocks(self):
        x=sample(g2={"status":"G2_EVIDENCE_UNVERIFIABLE",
                     "accepted":None,"total":None,"complete":False})
        self.assertEqual(x["status"], "BLOCKED")

    def test_task_disabled_blocks_even_after_prior_success(self):
        x=sample(source=task(state="Disabled"))
        self.assertEqual(x["status"], "BLOCKED")
        self.assertIn("SOURCE_ONLY_SCHEDULE_NOT_ENABLED", x["blockers"])

    def test_monitor_disabled_blocks(self):
        x=sample(monitor=task(state="Disabled"))
        self.assertEqual(x["status"], "BLOCKED")
        self.assertIn("STATUS_WATCHDOG_TASK_NOT_ENABLED", x["blockers"])

    def test_missed_two_scheduled_intervals_stalls(self):
        x=sample(source=task(ago=MAX_AGE_SECONDS+30))
        self.assertEqual(x["status"], "STALLED")

    def test_no_false_stall_just_inside_threshold(self):
        self.assertEqual(sample(source=task(ago=MAX_AGE_SECONDS-30))["status"],
                         "PENDING")

    def test_heartbeat_stale_detected(self):
        beat={"schema_version":1, "worker_kind":"source_only",
              "phase":"RUNNING","updated_unix":NOW-MAX_AGE_SECONDS-10}
        self.assertEqual(sample(heartbeat=beat)["status"],"STALLED")

    def test_heartbeat_idle_not_autonomous_dev(self):
        beat={"schema_version":1,"worker_kind":"source_only",
              "phase":"IDLE","updated_unix":NOW-15}
        self.assertEqual(sample(heartbeat=beat)["status"],"PENDING")

    def test_heartbeat_wrong_worker_rejected(self):
        beat={"schema_version":1,"worker_kind":"full_autonomous_dev",
              "phase":"RUNNING","updated_unix":NOW}
        with self.assertRaises(RuntimeError):
            sample(heartbeat=beat)

    def test_failed_last_task_result_blocks(self):
        x=sample(source=task(last_result=3))
        self.assertEqual(x["status"], "BLOCKED")

    def test_forged_final_status_not_accepted(self):
        g2={"status":"ALL_ACCEPTED","accepted":85,
            "total":85,"pending":0,"complete":True}
        x=sample(g2=g2,worker=True)
        self.assertFalse(x["project_complete"])
        self.assertFalse(x["g3_acoustic_video_verified"])

    def test_status_report_atomic_and_redacted(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            checkpoint=root/"MicroGen_AI_Web_Checkpoints"
            checkpoint.mkdir()
            drive=root/"My Drive"
            drive.mkdir()
            state=sample(source=task(state="Disabled"))
            out=publish(checkpoint,state,drive_root=drive)
            self.assertTrue(out["drive_mirror_written_locally"])
            self.assertFalse(out["drive_sync_to_cloud_independently_verified"])
            got=json.loads((checkpoint/"development_status_v1"/"STATUS.json").read_text())
            self.assertEqual(got["status"],"BLOCKED")
            self.assertEqual((drive/"MicroGen_AI_Web_Development_Status"/"STATUS.md").read_text(encoding="utf8"),
                             _report_md(state))
            self.assertNotIn("student original textbook",_report_md(state))

    def test_transition_creates_single_durable_local_alert(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"MicroGen_AI_Web_Checkpoints"
            root.mkdir()
            publish(root,sample(),drive_root=None)
            self.assertFalse((root/"development_status_v1"/"ALERT_STATUS_CHANGE.json").exists())
            publish(root,sample(source=task(state="Disabled")),drive_root=None)
            path=root/"development_status_v1"/"ALERT_STATUS_CHANGE.json"
            self.assertTrue(path.is_file())
            note=json.loads(path.read_text())
            self.assertFalse(note["notification_delivered"])
            self.assertEqual(note["old"],"PENDING")
            self.assertEqual(note["new"],"BLOCKED")

    def test_symlink_status_input_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            f=root/"real.json";f.write_text("{}")
            try:
                (root/"link.json").symlink_to(f)
            except (NotImplementedError, OSError):
                self.skipTest("Symlinks not enabled")
            with self.assertRaises(RuntimeError):
                _safe_json(root/"link.json")

    def test_source_heartbeat_can_be_persisted_without_qa(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            record_sourceonly_heartbeat(checkpoint=root,head="a"*40,
                                        phase="IDLE",stage="source_only")
            f=root/"development_status_v1"/"sourceonly_supervisor_heartbeat.json"
            got=json.loads(f.read_text())
            self.assertEqual(got["worker_kind"],"source_only")
            self.assertFalse(got["project_complete"])

    def test_status_task_launcher_bound_to_source(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)/"repo";repo.mkdir()
            exe=Path(td)/"python.exe";exe.write_bytes(b"test")
            raw=_wrap(repo.absolute(),exe.absolute())
            self.assertIn(b"project_development_status",raw)
            self.assertNotIn(b"g2_forward_recovery",raw)

    def test_monitor_wrong_principal_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            w=Path(td)/"test.cmd";w.write_text("test")
            snapshot={"name":"MicroGen_AI_Web_v71_StatusMonitor",
                      "state":"Ready","run_level":"Highest",
                      "logon":"Interactive","action":str(w),"user":"user"}
            with self.assertRaises(RuntimeError):
                _verify_task(snapshot,w)


if __name__=="__main__":
    unittest.main()
