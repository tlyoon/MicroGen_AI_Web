"""Offline scheduler / restart regression for on-flight historical captionless recovery."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

from selenium_pipeline.evidence_reuse_contract import file_sha256
from selenium_pipeline.windows_lecture_progression_coordinator import advance_one
from selenium_pipeline.windows_auto_captionless_recovery import (
    recover_failed_captionless_on_flight,
)
from selenium_pipeline.original_multisource_recovery_campaign import CampaignRecoveryBlocked, _new_atomic


class AutoCaptionlessRecoveryTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        env = patch.dict(os.environ, {"LOCALAPPDATA": str(self.root)})
        env.start()
        self.addCleanup(env.stop)
        self.source_root = self.root / "publisher"
        self.source = self.source_root / "47" / "47.2" / "source.pdf"
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(b"%PDF-1.7\n" + b"independent source bytes " * 30)
        self.sha = file_sha256(self.source)
        self.prior = self.root / "failed_historical_trial"
        self.prior.mkdir()
        _new_atomic(self.prior / "fresh_trial_contract.json", {
            "schema_version": 1,
            "status": "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL",
            "source_path": str(self.source),
            "source_sha256": self.sha,
            "staged_source_path": str(self.prior / "source_tree/47/47.2/source.pdf"),
            "stage_goal": "figures",
            "paid_tts_authorized": False,
            "student_publication_authorized": False,
        })
        _new_atomic(self.prior / "figures_attempt_result.json", {
            "schema_version": 1,
            "status": "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY",
            "figure_stage_exit_code": 1,
            "original_source_sha256": self.sha,
        })

    def recover(self):
        return recover_failed_captionless_on_flight(
            source_root=self.source_root, section="47.2",
            previous_trial=self.prior)

    def synthetic_salvage(self, *, previous_trial, new_trial):
        (new_trial / "figures_source_only_local_recovery.json").write_text(
            json.dumps({"new_provider_sends": 0}))
        return {"status": "FIGURES_SOURCE_ONLY_LOCAL_RECOVERY_STRUCTURALLY_VALID"}

    def test_new_successor_created_once_then_restart_reused(self):
        with patch("selenium_pipeline.windows_auto_captionless_recovery.recover",
                   side_effect=self.synthetic_salvage) as salvage, patch(
            "selenium_pipeline.windows_auto_captionless_recovery.verify_recovery_receipt",
            return_value=Path("verified")) as verify:
            first = self.recover()
            second = self.recover()
        self.assertEqual(first["status"], "AUTO_CAPTIONLESS_RECOVERY_COMPLETED")
        self.assertEqual(second["status"], "AUTO_CAPTIONLESS_RECOVERY_REUSED")
        self.assertEqual(first["recovery_trial"], second["recovery_trial"])
        self.assertEqual(first["new_model_sends"], 0)
        self.assertEqual(salvage.call_count, 1)
        self.assertEqual(verify.call_count, 2)
        self.assertEqual((self.prior / "figures_attempt_result.json").exists(), True)
        self.assertFalse((self.prior / "figures_source_only_local_recovery.json").exists())

    def test_crash_copy_only_repaired_on_restart_without_resending(self):
        def partial(*, previous_trial, new_trial):
            work = new_trial / "source_tree/47/47.2/.microgen_work"
            work.mkdir()
            (work / "stale-copied-only.txt").write_text("stale")
            raise RuntimeError("crash after source-only copy")
        with patch("selenium_pipeline.windows_auto_captionless_recovery.recover",
                   side_effect=partial):
            with self.assertRaises(RuntimeError):
                self.recover()
        def confirmed(*, previous_trial, new_trial):
            work = new_trial / "source_tree/47/47.2/.microgen_work"
            self.assertFalse(work.exists())
            return self.synthetic_salvage(previous_trial=previous_trial,
                                          new_trial=new_trial)
        with patch("selenium_pipeline.windows_auto_captionless_recovery.recover",
                   side_effect=confirmed), patch(
            "selenium_pipeline.windows_auto_captionless_recovery.verify_recovery_receipt"):
            result = self.recover()
        self.assertEqual(result["status"], "AUTO_CAPTIONLESS_RECOVERY_COMPLETED")
        self.assertEqual(result["new_model_sends"], 0)

    def test_orphan_send_or_tampered_marker_cannot_be_cleared(self):
        with patch("selenium_pipeline.windows_auto_captionless_recovery.recover",
                   side_effect=RuntimeError("interrupted")):
            with self.assertRaises(RuntimeError):
                self.recover()
        new = next(self.root.glob("auto_captionless_*"))
        (new / "stage_slides_started.json").write_text("{}")
        with self.assertRaises(CampaignRecoveryBlocked):
            self.recover()
        (new / "stage_slides_started.json").unlink()
        marker = new / "auto_captionless_recovery_intent.json"
        record = json.loads(marker.read_text())
        record["source_sha256"] = "a" * 64
        marker.write_text(json.dumps(record))
        with self.assertRaises(CampaignRecoveryBlocked):
            self.recover()

    def test_mismatched_original_source_refused_before_new_claim(self):
        self.source.write_bytes(self.source.read_bytes() + b"changed")
        with self.assertRaises(CampaignRecoveryBlocked):
            self.recover()
        self.assertEqual(list(self.root.glob("auto_captionless_*")), [])

    def test_normal_operator_schedules_and_dispatches_one_next_stage(self):
        failed = {"status": "HALTED_PREVIOUS_FIGURES_FAILED_NO_RESEND",
                  "source_sha256": self.sha, "section": "47.2"}
        ready = {"status": "NEXT_SOURCE_STAGE_READY_EXPLICIT_ONE_SHOT_ONLY",
                 "source_sha256": self.sha, "section": "47.2",
                 "next_stage": "slides"}
        fresh = self.root / "successor"
        with patch("selenium_pipeline.windows_lecture_progression_coordinator.inspect_progress",
                   side_effect=[failed, ready]) as inspect, patch(
            "selenium_pipeline.windows_auto_captionless_recovery.recover_failed_captionless_on_flight",
            return_value={"status": "AUTO_CAPTIONLESS_RECOVERY_COMPLETED",
                          "recovery_trial": str(fresh),
                          "source_sha256": self.sha, "new_model_sends": 0}) as salvage, patch(
            "selenium_pipeline.windows_original_stage_sequence.run_stage",
            return_value={"status": "GEMINI_SOURCE_ROUTE_UNVERIFIED_NO_SUBMISSION"}) as runner:
            out = advance_one(source_root=self.source_root, section="47.2",
                              trial_dir=self.prior, execute_next=True)
        self.assertEqual(out["status"], "EXACTLY_ONE_SOURCE_STAGE_ATTEMPT_FINISHED_NO_AUTO_CHAIN")
        self.assertEqual(out["attempted_stage"], "slides")
        self.assertEqual(out["active_trial_dir"], str(fresh))
        self.assertEqual(inspect.call_count, 2)
        salvage.assert_called_once()
        runner.assert_called_once()
        self.assertEqual(runner.call_args.kwargs["trial_dir"], fresh)

    def test_unsafe_failure_stays_blocked_without_stage_attempt(self):
        failed = {"status": "HALTED_PREVIOUS_FIGURES_FAILED_NO_RESEND",
                  "source_sha256": self.sha, "section": "47.2"}
        with patch("selenium_pipeline.windows_lecture_progression_coordinator.inspect_progress",
                   return_value=failed), patch(
            "selenium_pipeline.windows_auto_captionless_recovery.recover_failed_captionless_on_flight",
            side_effect=CampaignRecoveryBlocked("not unique")) as salvage, patch(
            "selenium_pipeline.windows_original_stage_sequence.run_stage") as stage:
            out = advance_one(source_root=self.source_root, section="47.2",
                              trial_dir=self.prior, execute_next=True)
        self.assertEqual(out["automatic_captionless_recovery"], "NOT_SOURCE_PROVEN_NO_RESEND")
        salvage.assert_called_once()
        stage.assert_not_called()

    def test_read_only_status_never_schedules_recovery(self):
        failed = {"status": "HALTED_PREVIOUS_FIGURES_FAILED_NO_RESEND"}
        with patch("selenium_pipeline.windows_lecture_progression_coordinator.inspect_progress",
                   return_value=failed), patch(
            "selenium_pipeline.windows_auto_captionless_recovery.recover_failed_captionless_on_flight") as salvage:
            out = advance_one(source_root=self.source_root, section="47.2",
                              trial_dir=self.prior, execute_next=False)
        self.assertIs(out, failed)
        salvage.assert_not_called()

    def test_on_flight_figure_failure_schedules_recovery_same_invocation(self):
        ready = {"status": "NEXT_SOURCE_STAGE_READY_EXPLICIT_ONE_SHOT_ONLY",
                 "source_sha256": self.sha, "section": "47.2",
                 "next_stage": "figures"}
        with patch("selenium_pipeline.windows_lecture_progression_coordinator.inspect_progress",
                   return_value=ready), patch(
            "selenium_pipeline.windows_fresh_source_trial.run_trial",
            return_value={"status": "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY"}) as stage, patch(
            "selenium_pipeline.windows_auto_captionless_recovery.recover_failed_captionless_on_flight",
            return_value={"status": "AUTO_CAPTIONLESS_RECOVERY_COMPLETED",
                          "new_model_sends": 0}) as salvage:
            out = advance_one(source_root=self.source_root, section="47.2",
                              trial_dir=self.prior, execute_next=True)
        stage.assert_called_once()
        salvage.assert_called_once()
        self.assertEqual(out["attempted_stage"], "figures")
        self.assertEqual(out["automatic_captionless_recovery"]["new_model_sends"], 0)
        self.assertTrue(out["next_invocation_requires_fresh_read_only_sha_review"])

    def test_kernel_lease_blocks_parallel_scheduling(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        started = Event()
        release = Event()

        def slow_recover(*, previous_trial, new_trial):
            started.set()
            self.assertTrue(release.wait(4))
            return self.synthetic_salvage(previous_trial=previous_trial, new_trial=new_trial)

        with patch("selenium_pipeline.windows_auto_captionless_recovery.recover",
                   side_effect=slow_recover) as salvage, patch(
            "selenium_pipeline.windows_auto_captionless_recovery.verify_recovery_receipt"):
            with ThreadPoolExecutor(max_workers=2) as pool:
                future = pool.submit(self.recover)
                self.assertTrue(started.wait(4))
                with self.assertRaises(CampaignRecoveryBlocked):
                    self.recover()
                release.set()
                done = future.result(timeout=5)
                reused = self.recover()
        self.assertEqual(done["status"], "AUTO_CAPTIONLESS_RECOVERY_COMPLETED")
        self.assertEqual(reused["status"], "AUTO_CAPTIONLESS_RECOVERY_REUSED")
        self.assertEqual(salvage.call_count, 1)


if __name__ == "__main__":
    unittest.main()
