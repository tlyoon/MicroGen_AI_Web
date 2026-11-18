"""Fault-injection for no-Gemini historical-stage acceptance and reuse."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline.evidence_reuse_contract import file_sha256
from selenium_pipeline.original_multisource_recovery_campaign import _new_atomic
from selenium_pipeline.windows_historical_stage_auto_reuse import (
    reuse_following, auto_reuse_accepted_stage)


class HistoricalStageAutoReuseTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        env = patch.dict(os.environ, {"LOCALAPPDATA": str(self.root)})
        env.start()
        self.addCleanup(env.stop)
        self.pdf = self.root / "publisher" / "8" / "8.4" / "source.pdf"
        self.pdf.parent.mkdir(parents=True)
        self.pdf.write_bytes(b"%PDF-1.7\n" + b"source " * 40)
        self.sha = file_sha256(self.pdf)
        self.old = self.make_trial("prior")
        self.new = self.make_trial("new")
        self.setup_old("narration")

    def make_trial(self, name):
        root = self.root / name
        work = root / "source_tree" / "8" / "8.4"
        hidden = work / ".microgen_work"
        hidden.mkdir(parents=True)
        (work / "source.pdf").write_bytes(self.pdf.read_bytes())
        (hidden / "source.pdf").write_bytes(self.pdf.read_bytes())
        _new_atomic(root / "fresh_trial_contract.json", {
            "schema_version": 1,
            "status": "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL",
            "source_path": str(self.pdf),
            "source_sha256": self.sha,
            "staged_source_path": str(work / "source.pdf"),
            "stage_goal": "figures",
            "paid_tts_authorized": False,
            "student_publication_authorized": False,
        })
        return root

    def receipt(self, trial, stage, output, previous=None):
        work = trial / "source_tree" / "8" / "8.4"
        from selenium_pipeline.windows_original_stage_sequence import _EXPECTED_OUTPUTS
        hashes = {}
        for name in _EXPECTED_OUTPUTS[stage]:
            data = output[name]
            (work / name).write_bytes(data)
            (work / ".microgen_work" / name).write_bytes(data)
            hashes[name] = file_sha256(work / name)
        body = {"schema_version": 1, "status": "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND",
                "stage": stage, "source_sha256": self.sha,
                "output_sha256": hashes, "exit_code": 0,
                "new_video_rendered": False,
                "student_publication_authorized": False}
        if previous:
            prevpath = trial / f"stage_{previous}_result.json"
            body["predecessor_receipt_sha256"] = file_sha256(prevpath)
        _new_atomic(trial / f"stage_{stage}_result.json", body)
        if previous:
            _new_atomic(trial / f"stage_{stage}_started.json", {
                "schema_version": 1, "stage": stage, "source_sha256": self.sha,
                "single_attempt_no_provider_resend": True,
                "predecessor_receipt_sha256": file_sha256(prevpath)})
        return body

    def setup_old(self, stage):
        slides = {"slides.pdf": b"real slide pixels synthetic fixture",
                  "slides.tex": b"source locked slide tex"}
        self.receipt(self.old, "slides", slides)
        self.receipt(self.new, "slides", slides)
        self.receipt(self.old, "narration",
                     {"script.txt": b"Original source-bound script."}, "slides")

    def test_reuse_narration_is_no_send_and_restart_not_repeated(self):
        with patch("selenium_pipeline.windows_historical_stage_auto_reuse.verify_recovery_receipt"), patch(
            "selenium_pipeline.windows_historical_stage_auto_reuse.check_valid",
            return_value=True), patch(
            "selenium_pipeline.windows_lecture_progression_coordinator._source_locked_ui_contract_breach",
            return_value=None):
            result = auto_reuse_accepted_stage(trial_dir=self.new, stage="narration")
            again = auto_reuse_accepted_stage(trial_dir=self.new, stage="narration")
        self.assertEqual(result["status"], "AUTO_REUSED_ACCEPTED_SOURCE_STAGE")
        self.assertEqual(result["new_model_sends"], 0)
        self.assertEqual(again["status"], "NO_VERIFIED_REUSABLE_HISTORICAL_STAGE")
        self.assertEqual(file_sha256(
            self.new / "source_tree/8/8.4/script.txt"), result["receipt"]["output_sha256"]["script.txt"])

    def test_changed_predecessor_rejected_without_output(self):
        path = self.new / "stage_slides_result.json"
        data = json.loads(path.read_text())
        data["output_sha256"]["slides.pdf"] = "0" * 64
        path.unlink()
        _new_atomic(path, data)
        with patch("selenium_pipeline.windows_historical_stage_auto_reuse.verify_recovery_receipt"), patch(
            "selenium_pipeline.windows_historical_stage_auto_reuse.check_valid",
            return_value=True):
            result = auto_reuse_accepted_stage(trial_dir=self.new, stage="narration")
        self.assertEqual(result["status"], "NO_VERIFIED_REUSABLE_HISTORICAL_STAGE")
        self.assertFalse((self.new / "stage_narration_started.json").exists())

    def test_accepted_script_qa_reuse_rebinds_exact_predecessor(self):
        self.receipt(self.old, "script_qa", {
            "script_risk_report.json": b'{"risks": []}',
            "math_semantic_report.json": b'{"status":"NO_KNOWN_DOMAIN_SIGN_HAZARDS_IN_LIMITED_RULESET"}',
        }, "narration")
        with patch("selenium_pipeline.windows_historical_stage_auto_reuse.verify_recovery_receipt"), patch(
            "selenium_pipeline.windows_historical_stage_auto_reuse.check_valid",
            return_value=True), patch(
            "selenium_pipeline.windows_lecture_progression_coordinator._source_locked_ui_contract_breach",
            return_value=None):
            reuse_following(prior_trial=self.old, new_trial=self.new, stage="narration")
            result = auto_reuse_accepted_stage(trial_dir=self.new, stage="script_qa")
        self.assertEqual(result["status"], "AUTO_REUSED_ACCEPTED_SOURCE_STAGE")
        self.assertEqual(result["new_model_sends"], 0)
        self.assertEqual(result["receipt"]["status"], "STAGE_COMPLETED_AND_SOURCE_SHA_BOUND")

    def test_different_original_never_reused(self):
        p = self.new / "fresh_trial_contract.json"
        d = json.loads(p.read_text())
        d["source_sha256"] = "f" * 64
        p.unlink()
        _new_atomic(p, d)
        with patch("selenium_pipeline.windows_historical_stage_auto_reuse.verify_recovery_receipt"), patch(
            "selenium_pipeline.windows_historical_stage_auto_reuse.check_valid",
            return_value=True):
            r = auto_reuse_accepted_stage(trial_dir=self.new, stage="narration")
        self.assertEqual(r["status"], "NO_VERIFIED_REUSABLE_HISTORICAL_STAGE")

    def test_normal_advance_chains_three_verified_reuses_without_model(self):
        from selenium_pipeline.windows_lecture_progression_coordinator import advance_one
        statuses = [
            {"status": "HALTED_PROVIDER_CAPACITY_NO_NEW_SUBMISSION",
             "source_sha256": self.sha, "section": "8.4", "next_stage": "slides"},
            {"status": "HALTED_PROVIDER_CAPACITY_NO_NEW_SUBMISSION",
             "source_sha256": self.sha, "section": "8.4", "next_stage": "narration"},
            {"status": "NEXT_SOURCE_STAGE_READY_EXPLICIT_ONE_SHOT_ONLY",
             "source_sha256": self.sha, "section": "8.4", "next_stage": "script_qa"},
            {"status": "REVIEWED_AUDIO_HANDOFF_REQUIRED_NO_AUTOMATIC_TTS",
             "source_sha256": self.sha, "section": "8.4", "next_stage": None},
        ]
        def adopted(*, trial_dir, stage):
            return {"status": "AUTO_REUSED_ACCEPTED_SOURCE_STAGE",
                    "stage": stage, "new_model_sends": 0}
        with patch("selenium_pipeline.windows_lecture_progression_coordinator.inspect_progress",
                   side_effect=statuses) as read, patch(
            "selenium_pipeline.windows_historical_stage_auto_reuse.auto_reuse_accepted_stage",
            side_effect=adopted) as reused, patch(
            "selenium_pipeline.windows_original_stage_sequence.run_stage") as provider:
            output = advance_one(source_root=self.root / "publisher",
                                 section="8.4", trial_dir=self.new,
                                 execute_next=True)
        self.assertEqual(output["status"], "REVIEWED_AUDIO_HANDOFF_REQUIRED_NO_AUTOMATIC_TTS")
        self.assertEqual(read.call_count, 4)
        self.assertEqual([c.kwargs["stage"] for c in reused.call_args_list],
                         ["slides", "narration", "script_qa"])
        self.assertEqual(len(output["historical_source_stages_reused"]), 3)
        self.assertFalse(output["new_model_or_tts_calls"])
        provider.assert_not_called()

    def test_unavailable_historical_stage_never_bypasses_provider_halt(self):
        from selenium_pipeline.windows_lecture_progression_coordinator import advance_one
        blocked = {"status": "HALTED_PROVIDER_CAPACITY_NO_NEW_SUBMISSION",
                   "source_sha256": self.sha, "section": "8.4",
                   "next_stage": "narration"}
        with patch("selenium_pipeline.windows_lecture_progression_coordinator.inspect_progress",
                   return_value=blocked), patch(
            "selenium_pipeline.windows_historical_stage_auto_reuse.auto_reuse_accepted_stage",
            return_value={"status": "NO_VERIFIED_REUSABLE_HISTORICAL_STAGE",
                          "new_model_sends": 0}), patch(
            "selenium_pipeline.windows_original_stage_sequence.run_stage") as provider:
            output = advance_one(source_root=self.root / "publisher",
                                 section="8.4", trial_dir=self.new,
                                 execute_next=True)
        self.assertEqual(output["status"], "HALTED_PROVIDER_CAPACITY_NO_NEW_SUBMISSION")
        provider.assert_not_called()


if __name__ == "__main__":
    unittest.main()
