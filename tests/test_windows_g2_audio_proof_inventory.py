"""Offline, actual WAV + source-hash G2 candidate proof inventory."""
from pathlib import Path
import json
import tempfile
import unittest
import wave

import pymupdf

from selenium_pipeline.evidence_reuse_contract import file_sha256
from selenium_pipeline.tts_candidate_integrity import (
    job_identity, record_one,
)
from selenium_pipeline.windows_g2_audio_proof_inventory import inventory


class G2AudioProofInventoryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.lecture = self.base / "lecture"
        self.job = self.base / "tts_job"
        self.candidate = self.job / ".tts_candidate"
        self.lecture.mkdir()
        self.candidate.mkdir(parents=True)
        (self.lecture / "source.pdf").write_bytes(b"source ground truth")
        (self.lecture / "script.txt").write_text("Slide 1 intro. Slide 2 outro.")
        doc = pymupdf.open()
        doc.new_page()
        doc.new_page()
        doc.save(self.lecture / "slides.pdf")
        doc.close()
        self.sha = file_sha256(self.lecture / "script.txt")
        self.identity = job_identity(
            [(1, "Intro."), (2, "Outro.")], provider="gemini",
            model="gemini-3.8-flash-lite-tts", voice="Kore",
            script_sha256=self.sha)
        (self.candidate / "candidate_job_identity.json").write_text(
            json.dumps(self.identity, sort_keys=True))
        (self.job / "source_audio_stage_manifest.json").write_text(json.dumps({
            "source_sha256": file_sha256(self.lecture / "source.pdf"),
            "slides_sha256": file_sha256(self.lecture / "slides.pdf"),
            "script_sha256": self.sha,
            "slide_count": 2,
            "model": "gemini-3.8-flash-lite-tts",
            "voice": "Kore"}))
        self.add_wave(1)

    def add_wave(self, number):
        path = self.candidate / f"slide{number}.wav"
        with wave.open(str(path), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(24000)
            out.writeframes(b"\0\0" * 2400)
        record_one(self.candidate, path.name, self.identity)

    def test_missing_wave_is_not_accepted(self):
        report = inventory(lecture_dir=self.lecture, audio_job=self.job)
        self.assertEqual(report["verified_wav_count"], 1)
        self.assertEqual(report["missing_proof_slides"], [2])
        self.assertFalse(report["per_element_audio_alignment_verified"])
        self.assertFalse(report["student_publication_authorized"])

    def test_complete_two_waves_technical_only(self):
        self.add_wave(2)
        report = inventory(lecture_dir=self.lecture, audio_job=self.job)
        self.assertEqual(report["status"],
                         "ALL_SLIDE_WAV_PROOF_PRESENT_TECHNICAL_ONLY")
        self.assertEqual(report["verified_wav_count"], 2)
        self.assertFalse(report["independent_acoustic_qa_verified"])

    def test_modified_wav_invalidates_verification(self):
        path = self.candidate / "slide1.wav"
        path.write_bytes(path.read_bytes() + b"modification")
        report = inventory(lecture_dir=self.lecture, audio_job=self.job)
        self.assertEqual(report["verified_wav_count"], 0)
        self.assertEqual(report["incomplete_proof_slides"], [1])

    def test_changed_script_rejects_source_binding(self):
        (self.lecture / "script.txt").write_text("Different speech.")
        with self.assertRaisesRegex(ValueError, "different source"):
            inventory(lecture_dir=self.lecture, audio_job=self.job)


if __name__ == "__main__":
    unittest.main()
