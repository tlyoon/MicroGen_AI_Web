"""Offline proof and preservation of Gemini TTS candidate cache across runs."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.tts_candidate_integrity import (
    CandidateIntegrityError, job_identity, prepare, record_one, verify_one,
)


class CandidateIdentityTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root = Path(d.name)
        self.c = self.root / ".tts_candidate"
        self.c.mkdir()
        self.items = [(1, "Exact narration for slide one."),
                      (2, "Exact narration for slide two.")]
        self.script = b"Slide one exact narration and slide two exact narration."
        self.i = job_identity(
            self.items, provider="gemini",
            model="gemini-3.8-flash-lite-tts", voice="Kore",
            script_sha256=hashlib.sha256(self.script).hexdigest())

    def seed(self):
        prepare(self.c, self.i)
        (self.c / "slide1.wav").write_bytes(b"RIFF" + b"W" * 80)
        record_one(self.c, "slide1.wav", self.i)

    def test_verified_original_cache_can_resume(self):
        self.seed()
        prepare(self.c, self.i)
        verify_one(self.c, "slide1.wav", self.i)
        self.assertEqual(len(list(self.c.glob("slide1.wav"))), 1)

    def test_legacy_unverified_wav_is_preserved_not_trusted(self):
        original=b"RIFF" + b"L" * 80
        (self.c / "slide1.wav").write_bytes(original)
        with self.assertRaisesRegex(CandidateIntegrityError, "Unverified legacy"):
            prepare(self.c, self.i)
        self.assertEqual((self.c / "slide1.wav").read_bytes(), original)
        self.assertFalse((self.c / "candidate_job_identity.json").exists())

    def test_alternative_model_cannot_reuse_flash_lite_cache(self):
        self.seed()
        different=dict(self.i, model="gemini-3.8-flash-tts")
        with self.assertRaisesRegex(CandidateIntegrityError, "model/voice/narration"):
            prepare(self.c, different)
        self.assertTrue((self.c / "slide1.wav").exists())

    def test_different_voice_cannot_reuse_kore_cache(self):
        self.seed()
        with self.assertRaises(CandidateIntegrityError):
            prepare(self.c, dict(self.i, voice="OtherVoice"))

    def test_script_and_spoken_text_changes_invalidate_cache(self):
        self.seed()
        with self.assertRaises(CandidateIntegrityError):
            prepare(self.c, dict(self.i, script_sha256="0"*64))
        altered = dict(self.i, narration_sha256_by_slide={
            **self.i["narration_sha256_by_slide"],
            "slide1.wav": "0"*64,
        })
        with self.assertRaises(CandidateIntegrityError):
            prepare(self.c, altered)

    def test_wav_bytes_and_receipt_tampering_block_resume(self):
        self.seed()
        source=self.c/"slide1.wav"
        source.write_bytes(source.read_bytes()+b"tampered")
        with self.assertRaisesRegex(CandidateIntegrityError, "hash mismatch"):
            prepare(self.c, self.i)
        self.assertTrue(source.is_file())

    def test_orphaned_partial_and_unlisted_wavs_cannot_be_deleted(self):
        self.seed()
        partial=self.c/"slide2.wav.partial"
        partial.write_bytes(b"keep")
        with self.assertRaisesRegex(CandidateIntegrityError, "interrupted"):
            prepare(self.c, self.i)
        self.assertEqual(partial.read_bytes(), b"keep")

    def test_stale_slide_number_not_silently_adopted(self):
        self.seed()
        wrong=self.c/"slide3.wav"
        wrong.write_bytes(b"RIFF"+b"Z"*80)
        with self.assertRaisesRegex(CandidateIntegrityError, "Stale candidate"):
            prepare(self.c, self.i)
        self.assertTrue(wrong.exists())

    def test_missing_wav_receipt_blocks_resume(self):
        self.seed()
        (self.c/"slide1.wav.verified.json").unlink()
        with self.assertRaisesRegex(CandidateIntegrityError, "Missing"):
            prepare(self.c, self.i)

    def test_orphaned_receipt_blocks_without_deletion(self):
        self.seed()
        extra=self.c/"slide2.wav.verified.json"
        extra.write_text(json.dumps({"not": "valid"}), encoding="utf-8")
        with self.assertRaisesRegex(CandidateIntegrityError, "Orphaned"):
            prepare(self.c, self.i)
        self.assertTrue(extra.exists())


if __name__=="__main__":
    unittest.main()
