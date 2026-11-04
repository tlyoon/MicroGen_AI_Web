"""Independent source-stage → reviewed MP4 → release gate, synthetic only."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from selenium_pipeline.original_multisource_recovery_campaign import (
    CampaignRecoveryBlocked,
)
from selenium_pipeline.windows_lecture_media_handoff import (
    handoff_media, inspect_reviewed_media_for_release,
)


class WindowsReleaseMediaProofIntegrationTests(unittest.TestCase):
    def setUp(self):
        # Reuse the exact unrelated section 77.9 synthetic source fixture
        # from the reviewed-audio bridge. Never use publisher PDFs/Gemini.
        from tests.test_windows_lecture_media_handoff import (
            WindowsReviewedMediaHandoffTests,
        )
        case = WindowsReviewedMediaHandoffTests(
            "test_read_only_media_preview_does_not_encode_or_send")
        case.setUp()
        self.case = case
        self.addCleanup(case.doCleanups)
        with patch("selenium_pipeline.runner.check_valid", return_value=True):
            handoff_media(**case.args, execute_encode=True,
                          media_renderer=case.renderer)
        self.media_dir = case.out
        self.trial_dir = case.seed.trial

    def verify(self):
        with patch("selenium_pipeline.runner.check_valid", return_value=True):
            return inspect_reviewed_media_for_release(
                trial_dir=self.trial_dir, media_dir=self.media_dir)

    def test_independent_release_receipt_reuses_existing_mp4_without_encoding(self):
        report = self.verify()
        self.assertEqual(report["status"],
                         "EXACT_SOURCEBOUND_MP4_TECHNICAL_EVIDENCE_VERIFIED_ONLY")
        self.assertTrue(report["technical_sourcebound_mp4_verified"])
        self.assertEqual(report["decoded_mp4_parts_verified"], 1)
        self.assertFalse(report["new_model_or_tts_calls"])
        self.assertFalse(report["new_video_rendered"])
        self.assertFalse(report["second_distinct_original_academic_acceptance_verified"])
        self.assertFalse(report["human_voice_and_figure_review_certified"])
        self.assertFalse(report["full_lecture_release_authorized"])
        self.assertFalse(report["student_publication_authorized"])
        self.case.renderer.assert_called_once()

    def test_full_release_board_reads_real_receipt_but_still_blocks_release(self):
        from selenium_pipeline.windows_release_readiness_board import (
            inspect_release,
        )
        repo = self.case.seed.root / "synthetic_git_repo"
        repo.mkdir()
        (repo / ".git").write_text("gitdir: isolated", encoding="utf8")
        workflow = repo / ".github" / "workflows"
        workflow.mkdir(parents=True)
        (workflow / "windows.yml").write_text(
            "jobs:\n  x:\n    runs-on: windows-latest\n", encoding="utf8")
        def _git(_repo, *cmd):
            key = " ".join(cmd)
            mapping = {
                "branch --show-current": "feature/pr507-fixture",
                "rev-parse HEAD": "a" * 40,
                "rev-parse main": "b" * 40,
                "rev-parse origin/main": "b" * 40,
                "rev-list --count origin/main..HEAD": "1",
                "rev-list --count HEAD..origin/main": "0",
                "status --porcelain": "",
            }
            return mapping[key]
        recovery = {
            "source_job_receipts_security_or_version_rejected": 0,
            "source_job_receipts_current_and_sha_verified": 1,
            "fresh_original_publisher_and_stage_sha_verified": True,
            "fresh_original_figure_attempt_state": "ACCEPTED",
            "automatic_provider_retry_authorized": False,
        }
        with patch("selenium_pipeline.windows_release_readiness_board._git",
                   side_effect=_git), patch(
            "selenium_pipeline.windows_release_readiness_board.audit",
            return_value=recovery,
        ), patch("selenium_pipeline.runner.check_valid", return_value=True):
            report = inspect_release(
                repo=repo, jobs_dir=self.case.seed.root / "synthetic_jobs",
                fresh_trial_dir=self.trial_dir,
                reviewed_media_dir=self.media_dir)
        self.assertTrue(report["required_release_gates"][
            "reviewed_sourcebound_mp4_technical_integrity_verified"])
        self.assertEqual(report["reviewed_sourcebound_mp4_evidence"][
            "decoded_mp4_parts_verified"], 1)
        self.assertFalse(report["required_release_gates"][
            "second_distinct_new_original_full_lecture_accepted"])
        self.assertFalse(report["release_candidate_ready"])
        self.assertFalse(report["student_publication_authorized"])
        self.case.renderer.assert_called_once()

    def test_separate_release_inspection_rejects_changed_actual_video(self):
        video = next(self.media_dir.glob("encoded_review/rendered/*/*.mp4"))
        video.write_bytes(video.read_bytes() + b"unsafe_modified")
        with self.assertRaisesRegex(CampaignRecoveryBlocked, "actual encoded video bytes"):
            self.verify()
        self.case.renderer.assert_called_once()

    def test_separate_release_inspection_rejects_changed_original_script(self):
        script = self.case.seed.lecture / "script.txt"
        script.write_bytes(script.read_bytes() + b"unsafe_modified")
        with self.assertRaises(CampaignRecoveryBlocked):
            self.verify()
        self.case.renderer.assert_called_once()

    def test_separate_release_inspection_rejects_altered_review_role(self):
        manifest = self.media_dir / "sourcebound_media_handoff_receipt.json"
        data = json.loads(manifest.read_text(encoding="utf8"))
        data["review_input_paths"]["draft"] = str(
            self.case.seed.root / "wrong_draft")
        manifest.write_text(json.dumps(data), encoding="utf8")
        with self.assertRaises(CampaignRecoveryBlocked):
            self.verify()
        self.case.renderer.assert_called_once()

    def test_separate_release_inspection_rejects_missing_wav_proof(self):
        proof = self.case.audio / "s01_e01.wav.verified.json"
        proof.unlink()
        with self.assertRaises(CampaignRecoveryBlocked):
            self.verify()
        self.case.renderer.assert_called_once()

    def test_separate_release_inspection_rejects_missing_immutable_media_receipt(self):
        (self.media_dir / "sourcebound_media_handoff_receipt.json").unlink()
        with self.assertRaises(CampaignRecoveryBlocked):
            self.verify()
        self.case.renderer.assert_called_once()


if __name__ == "__main__":
    unittest.main()
