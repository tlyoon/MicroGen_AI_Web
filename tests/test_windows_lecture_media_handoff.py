"""Source-bound reviewed WAV -> real FFmpeg handoff, no model invocation."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from selenium_pipeline.evidence_reuse_contract import file_sha256
from selenium_pipeline.original_multisource_recovery_campaign import CampaignRecoveryBlocked
from selenium_pipeline.windows_lecture_media_handoff import handoff_media
from tests.test_windows_lecture_progression_coordinator import (
    WindowsSourceProgressionTests,
)


class WindowsReviewedMediaHandoffTests(unittest.TestCase):
    def setUp(self):
        self.seed = WindowsSourceProgressionTests(
            "test_no_receipts_read_only_plan_is_first_figures")
        self.seed.setUp()
        self.addCleanup(self.seed.doCleanups)
        self.seed.figures_ready()
        for name in ("slides", "narration", "script_qa"):
            self.seed.stage_pass(name)
        self.audio = self.seed.root / "reviewed_existing_wav"
        self.audio.mkdir()
        for i in range(1, 3):
            (self.audio / f"s01_e0{i}.wav").write_bytes(bytes([i]) * 2048)
            (self.audio / f"s01_e0{i}.wav.verified.json").write_text(
                '{"synthetic_verified_wav_receipt":"offline mock"}',
                encoding="utf8")
        self.draft = self.seed.root / "source_matched_review_draft.json"
        self.selection = self.seed.root / "reviewed_author_selection.json"
        self.request = self.seed.root / "approved_tts_request.json"
        for p in (self.draft, self.selection, self.request):
            p.write_text('{"synthetic_test_only":true}', encoding="utf8")
        self.out = self.seed.root / "new_external_media_review"
        self.args = {
            "source_root": self.seed.source_root,
            "section": "77.9",
            "trial_dir": self.seed.trial,
            "draft": self.draft,
            "selection": self.selection,
            "tts_request": self.request,
            "audio": self.audio,
            "outdir": self.out,
            "technical_check": self.seed.check,
        }
        self.renderer = Mock(side_effect=self.fake_decode)

    def fake_decode(self, **kwargs):
        self.assertEqual(kwargs["source"], self.seed.lecture / "source.pdf")
        self.assertEqual(kwargs["slides"], self.seed.lecture / "slides.pdf")
        self.assertEqual(kwargs["script"], self.seed.lecture / "script.txt")
        target = kwargs["outdir"]
        target.mkdir()
        part = target / "encoded_review" / "rendered" / "part_01"
        part.mkdir(parents=True)
        video = part / "part_01_review.mp4"
        video.write_bytes(b"mp4_synthetic_genuine_bytes" * 100)
        receipt = {
            "schema_version": 1,
            "status": "SOURCEBOUND_ELEMENT_REVIEW_MP4_ENCODED_AND_DECODED",
            "source_sha256": self.seed.sha,
            "slides_sha256": file_sha256(self.seed.lecture / "slides.pdf"),
            "script_sha256": file_sha256(self.seed.lecture / "script.txt"),
            "part_sha256": {video.name: file_sha256(video)},
            "covered_slides": 1,
            "covered_elements": 2,
            "decoded_pixel_checks_passed": True,
            "new_tts_or_model_calls": False,
            "production_media_approved": False,
            "student_publication_authorized": False,
        }
        (target / "review_only_receipt.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf8")
        return receipt

    def test_read_only_media_preview_does_not_encode_or_send(self):
        report = handoff_media(**self.args, media_renderer=self.renderer)
        self.assertEqual(report["status"],
                         "REVIEWED_MEDIA_INPUTS_READY_EXPLICIT_FFMPEG_ONLY")
        self.assertFalse(report["new_model_or_tts_calls"])
        self.assertFalse(report["student_publication_authorized"])
        self.assertFalse(self.out.exists())
        self.renderer.assert_not_called()

    def test_one_explicit_encode_is_reusable_without_rerender(self):
        first = handoff_media(**self.args, execute_encode=True,
                              media_renderer=self.renderer)
        self.assertEqual(first["status"],
                         "SOURCEBOUND_REVIEWED_MEDIA_NEW_MP4_TECHNICAL_PASS_ONLY")
        self.assertTrue(first["new_video_rendered"])
        self.assertFalse(first["formal_academic_release_approved"])
        self.assertEqual(self.renderer.call_count, 1)
        again = handoff_media(**self.args, execute_encode=True,
                              media_renderer=self.renderer)
        self.assertEqual(again["status"],
                         "SOURCEBOUND_REVIEWED_MEDIA_REUSED_SHA_VERIFIED")
        self.assertFalse(again["new_video_rendered"])
        self.assertEqual(self.renderer.call_count, 1)

    def test_edited_wav_proof_after_encoding_cannot_reuse_or_rerender(self):
        handoff_media(**self.args, execute_encode=True,
                      media_renderer=self.renderer)
        proof = self.audio / "s01_e01.wav.verified.json"
        proof.write_text('{"tampered":true}', encoding="utf8")
        with self.assertRaisesRegex(CampaignRecoveryBlocked,
                                    "reviewed WAV evidence"):
            handoff_media(**self.args, execute_encode=True,
                          media_renderer=self.renderer)
        self.assertEqual(self.renderer.call_count, 1)

    def test_changed_encoded_video_bytes_refuse_reuse(self):
        handoff_media(**self.args, execute_encode=True,
                      media_renderer=self.renderer)
        video = next(self.out.glob("encoded_review/rendered/*/*.mp4"))
        video.write_bytes(video.read_bytes() + b"tamper")
        with self.assertRaisesRegex(CampaignRecoveryBlocked,
                                    "actual encoded video bytes changed"):
            handoff_media(**self.args, execute_encode=True,
                          media_renderer=self.renderer)
        self.assertEqual(self.renderer.call_count, 1)

    def test_partial_output_preserved_no_second_ffmpeg(self):
        self.out.mkdir()
        (self.out / "partial.mp4").write_bytes(b"some bytes")
        report = handoff_media(**self.args, execute_encode=True,
                               media_renderer=self.renderer)
        self.assertEqual(report["status"],
                         "HALTED_PARTIAL_MEDIA_OUTPUT_NO_REENCODE")
        self.assertEqual(self.renderer.call_count, 0)
        self.assertTrue((self.out / "partial.mp4").exists())

    def test_no_accepted_stage_no_reviewed_video(self):
        (self.seed.trial / "stage_script_qa_result.json").unlink()
        report = handoff_media(**self.args, execute_encode=True,
                               media_renderer=self.renderer)
        self.assertEqual(report["status"],
                         "MEDIA_PREREQUISITES_NOT_ACCEPTED_NO_ENCODING")
        self.renderer.assert_not_called()
        self.assertFalse(self.out.exists())

    def test_missing_reviewed_wav_proof_blocks_before_any_output(self):
        (self.audio / "s01_e02.wav.verified.json").unlink()
        with self.assertRaisesRegex(CampaignRecoveryBlocked, "PCM WAV"):
            handoff_media(**self.args, execute_encode=True,
                          media_renderer=self.renderer)
        self.renderer.assert_not_called()
        self.assertFalse(self.out.exists())

    def test_wrong_original_source_blocks_even_valid_audio(self):
        self.seed.original.write_bytes(self.seed.original.read_bytes() + b"changed")
        with self.assertRaises(CampaignRecoveryBlocked):
            handoff_media(**self.args, execute_encode=True,
                          media_renderer=self.renderer)
        self.renderer.assert_not_called()
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
