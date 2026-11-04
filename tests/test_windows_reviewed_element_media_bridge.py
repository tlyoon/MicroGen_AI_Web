"""Genuine encoded synthetic MP4 acceptance using existing reviewed TTS path.

All model audio comes from a TEST WAV in memory, never Gemini network.
Actual FFmpeg encodes and independent decoded pixel QA run on Dell Windows.
"""
from __future__ import annotations
import io
import json
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from tests.test_element_plan_autodraft import CandidateAuthoringTests
from selenium_pipeline.element_plan_review_bridge import (
    promoted, PlanPromotionError,
)
from selenium_pipeline.element_narration_gemini import main as synth_main
from selenium_pipeline.windows_reviewed_element_media_bridge import (
    render_review, ReviewedMediaBridgeBlocked,
)
from selenium_pipeline.evidence_reuse_contract import file_sha256


def synthetic_test_wav() -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x01\x10" * 24000)
    return out.getvalue()


class ExistingReviewedSourceMediaIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.seed = CandidateAuthoringTests("test_no_words_are_generated_or_removed")
        self.seed.setUp()
        self.addCleanup(self.seed.doCleanups)
        self.root = self.seed.root
        self.request = self.root / "independently_reviewed_tts_request.json"
        prior = promoted(source=self.seed.source, slides=self.seed.slides,
                         script=self.seed.script,
                         draft_path=self.seed.draft_path,
                         selection=self.seed.selection, prepare_tts=True)
        self.request.write_text(json.dumps(prior), encoding="utf8")
        self.audio = self.root / "mock_only_recorded_wavs"
        self.dest = self.root / "new_external_review"
        self.args = dict(source=self.seed.source, slides=self.seed.slides,
                         script=self.seed.script,
                         draft=self.seed.draft_path,
                         selection=self.seed.selection,
                         tts_request=self.request, audio=self.audio,
                         outdir=self.dest)

    def synth_mock_only(self):
        with patch("selenium_pipeline.runner.load_microvid_env"), patch(
            "gemini_keys.get_gemini_api_keys", return_value=["TEST_ONLY_NEVER_REAL"]
        ), patch(
            "selenium_pipeline.tts._gemini_say_with_watchdog",
            return_value=synthetic_test_wav()
        ) as calls:
            rc = synth_main([
                "--authored-plan", str(self.request),
                "--output-folder", str(self.audio),
                "--voice", "Kore",
                "--model", "gemini-3.8-flash-lite-tts",
                "--confirm-live", "--confirm-reviewed-tts-request",
                "--confirm-gemini-api-cost",
            ])
        self.assertEqual(rc, 0)
        self.assertEqual(calls.call_count, 3)

    def test_real_encoded_review_from_existing_source_and_mock_recordings(self):
        self.synth_mock_only()
        hashes = [file_sha256(p) for p in (
            self.seed.source, self.seed.slides, self.seed.script)]
        receipt = render_review(**self.args)
        self.assertEqual(receipt["status"],
                         "SOURCEBOUND_ELEMENT_REVIEW_MP4_ENCODED_AND_DECODED")
        self.assertEqual(receipt["covered_slides"], 3)
        self.assertEqual(receipt["covered_elements"], 3)
        self.assertEqual(len(receipt["part_sha256"]), 2)
        self.assertTrue(all(len(x) == 64 for x in
                            receipt["part_sha256"].values()))
        self.assertFalse(receipt["production_media_approved"])
        self.assertFalse(receipt["student_publication_authorized"])
        self.assertFalse(receipt["new_tts_or_model_calls"])
        self.assertEqual(hashes, [file_sha256(p) for p in (
            self.seed.source, self.seed.slides, self.seed.script)])
        self.assertTrue((self.dest / "review_only_receipt.json").is_file())
        with self.assertRaises(ReviewedMediaBridgeBlocked):
            render_review(**self.args)

    def test_tampered_wav_proof_blocks_before_any_output_or_video(self):
        self.synth_mock_only()
        proof = self.audio / "s01_e01.wav.verified.json"
        data = json.loads(proof.read_text("utf8"))
        data["wav_sha256"] = "0" * 64
        proof.write_text(json.dumps(data), encoding="utf8")
        with self.assertRaises(PlanPromotionError):
            render_review(**self.args)
        self.assertFalse(self.dest.exists())

    def test_mutated_publisher_source_rejected_before_video(self):
        self.synth_mock_only()
        with self.seed.source.open("ab") as f:
            f.write(b"publisher source was changed")
        with self.assertRaises(PlanPromotionError):
            render_review(**self.args)
        self.assertFalse(self.dest.exists())

    def test_review_cannot_write_into_original_author_folder(self):
        self.synth_mock_only()
        args = dict(self.args, outdir=self.seed.source.parent / "bad_review")
        with self.assertRaises(ReviewedMediaBridgeBlocked):
            render_review(**args)
        self.assertFalse(args["outdir"].exists())


if __name__ == "__main__":
    unittest.main()
