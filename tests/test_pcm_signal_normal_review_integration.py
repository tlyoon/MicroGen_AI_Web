"""Cross-entrypoint regression: normal source-bound WAV review rejects gross audio damage.

Only upstream lesson/TTS provenance checks are fixture-stubbed here; the
original PCM verifier and actual signal health gate run without mocks.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline.evidence_reuse_contract import file_sha256
from selenium_pipeline.pcm_signal_integrity import PCMIntegrityBlocked
from selenium_pipeline.windows_slide_audio_timing_review import inspect
from tests.test_pcm_signal_integrity import RATE, tone, wav


class NormalReviewSignalGateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.original = root / "source"
        self.candidate = root / "audio_candidate"
        self.original.mkdir()
        self.candidate.mkdir()
        required = ("source.pdf", "slides.pdf", "slides.tex", "script.txt",
                    "script_risk_report.json", "script_risk_report.md",
                    "math_semantic_report.json",
                    "math_semantic_repair_prompt.json")
        for name in required:
            value = (b"**Slide 1 [10 sec]:\nAn example sentence.**\n"
                     if name == "script.txt" else (name + " unchanged").encode())
            (self.original/name).write_bytes(value)
            (self.candidate/name).write_bytes(value)
        (self.candidate/"source_audio_stage_manifest.json").write_text(
            json.dumps({
                "status": "SOURCE_SHA_BOUND_ROUTINE_GEMINI_TTS_CANDIDATE_STAGED",
                "student_publication_authorized": False,
                "element_highlight_semantics_verified": False,
                "model": "gemini-3.8-flash-lite-tts",
                "voice": "Kore",
                "source_trial": str(self.original),
                "source_sha256": file_sha256(self.original/"source.pdf"),
                "slides_sha256": file_sha256(self.original/"slides.pdf"),
                "script_sha256": file_sha256(self.original/"script.txt"),
                "slide_count": 1,
            }),encoding="utf8")
        (self.candidate/"tts_input_manifest.json").write_text(
            '{"verified_upstream_TTS_provider_fixture":false}',encoding="utf8")

    def review(self):
        # The test isolates the audio signal gate from the unrelated
        # full upstream production manifest. No resulting test QA is release.
        with patch("selenium_pipeline.windows_slide_audio_timing_review.check_valid",
                   return_value=True), patch(
            "selenium_pipeline.windows_slide_audio_timing_review.verify_effective_identity",
            return_value={"fallback_used": False}):
            return inspect(audio_folder=self.candidate,
                           original_source=self.original)

    def test_real_stage_receives_objective_signal_proof_only(self):
        original = wav(tone(2) + [0] * (RATE // 3) + tone(2))
        (self.candidate/"slide1.wav").write_bytes(original)
        result=self.review()
        self.assertTrue(result["objective_pcm_signal_integrity_verified"])
        self.assertFalse(result["audio_pronunciation_independently_verified"])
        self.assertFalse(result["per_element_sync_verified"])
        self.assertFalse(result["student_publication_authorized"])
        self.assertEqual(len(result["segments"]),1)
        proof=result["segments"][0]["pcm_signal_integrity"]
        self.assertTrue(proof["objective_pcm_signal_integrity_passed"])
        self.assertFalse(proof["acoustic_listening_qa_verified"])
        self.assertEqual((self.candidate/"slide1.wav").read_bytes(),original)

    def test_silent_recording_stops_normal_review_before_video_staging(self):
        original=wav([0] * (RATE * 2))
        (self.candidate/"slide1.wav").write_bytes(original)
        with self.assertRaises(PCMIntegrityBlocked):
            self.review()
        self.assertEqual((self.candidate/"slide1.wav").read_bytes(),original)
        self.assertFalse(any(self.candidate.glob("*.mp4")))


if __name__ == "__main__":
    unittest.main()
