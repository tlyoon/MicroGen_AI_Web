"""No-WAV pre-TTS science reviews: real PDF anchors, no fake approval/send."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.ai_academic_web_review import build_review_job
from selenium_pipeline.ai_academic_review_queue import prepare_resumable_review
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.incremental_lecture_sync_queue import inspect_pre_tts_folder
from test_original_packet_evidence_audit import fixture


class PreTTSReviewWithoutAudio(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.folder = self.root / "original"
        fixture(self.folder)
        (self.folder / "script.txt").write_text(
            "**Slide 1 [1 sec]:\nA visible equation**\n", encoding="utf-8")

    def test_review_job_from_original_pdf_and_script_with_zero_wavs(self):
        before = {p.name: p.read_bytes() for p in self.folder.iterdir()
                  if p.is_file()}
        record = inspect_pre_tts_folder(self.folder)
        self.assertEqual(record["status"],
                         "PRE_TTS_SOURCE_ONLY_ELEMENT_QUEUE_REVIEW_ONLY")
        self.assertFalse(record["audio_inventory_verified"])
        self.assertFalse(record["ready_for_paid_element_tts"])
        self.assertFalse(record["student_publication_authorized"])
        job = build_review_job(folder=self.folder, slide_numbers=[1])
        self.assertTrue(job["source_only_pre_tts_review"])
        self.assertEqual(job["utterance_count"], 1)
        self.assertEqual(job["slides"][0]["slide"], 1)
        self.assertTrue(job["slides"][0]["visual_targets"])
        self.assertEqual(job["slides"][0]["utterances"][0]["id"],
                         "s001.utterance.001")
        self.assertFalse(job["academic_approval"])
        self.assertFalse(job["student_publication_authorized"])
        queue = self.root / "independent_review_queue"
        planned = prepare_resumable_review(
            folder=self.folder, output_root=queue, slide_numbers=[1])
        self.assertEqual(planned["expected_utterances"], 1)
        self.assertEqual(planned["provider_requests_performed"], 0)
        self.assertFalse(planned["student_publication_authorized"])
        self.assertEqual(before, {p.name: p.read_bytes()
                                  for p in self.folder.iterdir()
                                  if p.is_file()})

    def test_stale_or_missing_script_fails_closed(self):
        (self.folder / "script.txt").write_text(
            "**Slide 2 [1 sec]:\nOut of order**\n", encoding="utf-8")
        with self.assertRaises((FigureIdentityReviewRequired, ValueError)):
            build_review_job(folder=self.folder, slide_numbers=[1])
        (self.folder / "script.txt").unlink()
        with self.assertRaises((FigureIdentityReviewRequired, ValueError)):
            build_review_job(folder=self.folder, slide_numbers=[1])

    def test_partial_or_corrupt_wav_never_uses_no_audio_fallback(self):
        (self.folder / "slide1.wav").write_bytes(b"broken")
        with self.assertRaises(FigureIdentityReviewRequired):
            build_review_job(folder=self.folder, slide_numbers=[1])
        with self.assertRaises(FigureIdentityReviewRequired):
            inspect_pre_tts_folder(self.folder)


if __name__ == "__main__":
    unittest.main()
