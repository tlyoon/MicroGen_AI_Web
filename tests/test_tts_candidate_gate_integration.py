"""Offline end-to-end TTS cache contract: no model switch, adoption or overwrite."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.runner import blocks
from selenium_pipeline.tts import synthesize_folder
from selenium_pipeline.tts_candidate_integrity import (
    job_identity, prepare, record_one, CandidateIntegrityError,
)


WAV_A = b"RIFF" + b"A" * 80
WAV_B = b"RIFF" + b"B" * 80


def fake_gemini_module(payload=WAV_A):
    module = types.ModuleType("gemini_keys")
    module.get_gemini_api_keys = lambda: ["DUMMY_TEST_ONLY"]
    module.create_gemini_client = lambda _key: object()
    module.requests = []
    def failover(_factory, operation, **_kwargs):
        module.requests.append("called")
        return payload
    module.call_with_client_failover = failover
    return module


class PipelineCandidateSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        (self.folder / "script.txt").write_text(
            "**Slide 1 [3 sec]:\nFirst narration line.**\n\n"
            "**Slide 2 [3 sec]:\nSecond narration line.**",
            encoding="utf-8",
        )
        self.candidate = self.folder / ".tts_candidate"

    def seed(self, *, model="gemini-3.8-flash-lite-tts"):
        self.candidate.mkdir()
        script = (self.folder / "script.txt").read_bytes()
        identity = job_identity(
            blocks(script.decode("utf-8")), provider="gemini",
            model=model, voice="Kore",
            script_sha256=hashlib.sha256(script).hexdigest())
        prepare(self.candidate, identity)
        for number in (1, 2):
            name = f"slide{number}.wav"
            (self.candidate / name).write_bytes(WAV_A)
            record_one(self.candidate, name, identity)

    def test_unverified_legacy_wav_blocks_without_any_api_or_deletion(self):
        self.candidate.mkdir()
        (self.candidate / "slide1.wav").write_bytes(WAV_A)
        fake = fake_gemini_module()
        with patch.dict(sys.modules, {"gemini_keys": fake}):
            with self.assertRaisesRegex(CandidateIntegrityError,
                                        "Unverified legacy"):
                synthesize_folder(self.folder, "gemini",
                    "gemini-3.8-flash-lite-tts", "Kore")
        self.assertEqual(fake.requests, [])
        self.assertEqual((self.candidate / "slide1.wav").read_bytes(), WAV_A)
        self.assertFalse((self.folder / "slide1.wav").exists())

    def test_previous_flash_model_cache_never_passes_as_flash_lite(self):
        self.seed(model="gemini-3.8-flash-tts")
        fake = fake_gemini_module()
        with patch.dict(sys.modules, {"gemini_keys": fake}):
            with self.assertRaisesRegex(CandidateIntegrityError, "model/voice"):
                synthesize_folder(self.folder, "gemini",
                    "gemini-3.8-flash-lite-tts", "Kore")
        self.assertEqual(fake.requests, [])
        self.assertTrue((self.candidate / "slide1.wav").is_file())
        self.assertFalse((self.folder / "tts_input_manifest.json").exists())

    def test_existing_different_final_wav_remains_immutable(self):
        self.candidate.mkdir()
        self.candidate.rmdir()
        previous = self.folder / "slide1.wav"
        previous.write_bytes(WAV_B)
        fake = fake_gemini_module()
        with patch.dict(sys.modules, {"gemini_keys": fake}):
            with self.assertRaisesRegex(RuntimeError,"Existing final TTS outputs require reviewed reconciliation"):
                synthesize_folder(self.folder, "gemini",
                    "gemini-3.8-flash-lite-tts", "Kore")
        self.assertEqual(previous.read_bytes(), WAV_B)
        self.assertEqual(len(fake.requests), 0)
        self.assertFalse(self.candidate.exists())
        self.assertFalse((self.folder / "tts_input_manifest.json").exists())

    def test_identical_existing_final_file_blocks_before_api_even_with_no_manifest(self):
        existing=self.folder / "slide1.wav"
        existing.write_bytes(WAV_A)
        fake=fake_gemini_module()
        with patch.dict(sys.modules, {"gemini_keys": fake}):
            with self.assertRaisesRegex(CandidateIntegrityError,
                                        "Existing final TTS outputs"):
                synthesize_folder(self.folder, "gemini",
                                  "gemini-3.8-flash-lite-tts", "Kore")
        self.assertEqual(existing.read_bytes(), WAV_A)
        self.assertEqual(fake.requests, [])
        self.assertFalse(self.candidate.exists())

    def test_manifest_only_blocks_before_api_without_any_wav(self):
        manifest=self.folder / "tts_input_manifest.json"
        manifest.write_text('{"historical":true}', encoding="utf-8")
        fake=fake_gemini_module()
        with patch.dict(sys.modules, {"gemini_keys": fake}):
            with self.assertRaisesRegex(CandidateIntegrityError,
                                        "Existing final TTS outputs"):
                synthesize_folder(self.folder, "gemini",
                                  "gemini-3.8-flash-lite-tts", "Kore")
        self.assertEqual(fake.requests, [])
        self.assertEqual(manifest.read_text(encoding="utf-8"), '{"historical":true}')
        self.assertFalse(self.candidate.exists())

    def test_old_case_variant_final_wav_blocks_before_api(self):
        previous=self.folder / "Slide2.WAV"
        previous.write_bytes(WAV_B)
        fake=fake_gemini_module()
        with patch.dict(sys.modules, {"gemini_keys": fake}):
            with self.assertRaisesRegex(CandidateIntegrityError,
                                        "Existing final TTS outputs"):
                synthesize_folder(self.folder, "gemini",
                                  "gemini-3.8-flash-lite-tts", "Kore")
        self.assertEqual(previous.read_bytes(), WAV_B)
        self.assertEqual(fake.requests, [])

    def test_blocked_final_publication_does_not_touch_reviewable_candidate(self):
        self.seed()
        preexisting=self.folder / "slide2.wav"
        preexisting.write_bytes(WAV_B)
        proof_before=(self.candidate / "candidate_job_identity.json").read_bytes()
        wav_before=(self.candidate / "slide1.wav").read_bytes()
        fake=fake_gemini_module()
        with patch.dict(sys.modules, {"gemini_keys": fake}):
            with self.assertRaisesRegex(CandidateIntegrityError,
                                        "Existing final TTS outputs"):
                synthesize_folder(self.folder, "gemini",
                                  "gemini-3.8-flash-lite-tts", "Kore")
        self.assertEqual(fake.requests, [])
        self.assertEqual(proof_before,
                         (self.candidate / "candidate_job_identity.json").read_bytes())
        self.assertEqual(wav_before, (self.candidate / "slide1.wav").read_bytes())
        self.assertEqual(preexisting.read_bytes(), WAV_B)

    def test_exact_cached_wavs_publish_without_resynthesis_and_keep_proof(self):
        self.seed()
        fake = fake_gemini_module()
        with patch.dict(sys.modules, {"gemini_keys": fake}):
            synthesize_folder(self.folder, "gemini",
                              "gemini-3.8-flash-lite-tts", "Kore")
        self.assertEqual(fake.requests, [])
        self.assertEqual((self.folder / "slide1.wav").read_bytes(), WAV_A)
        self.assertEqual((self.folder / "slide2.wav").read_bytes(), WAV_A)
        self.assertFalse(self.candidate.exists())
        audit = self.folder / ".tts_candidate_receipts"
        snapshots = list(audit.iterdir())
        self.assertEqual(len(snapshots), 1)
        self.assertTrue((snapshots[0] / "candidate_job_identity.json").is_file())
        self.assertTrue((snapshots[0] / "slide1.wav.verified.json").is_file())
        manifest = json.loads((self.folder / "tts_input_manifest.json").read_text())
        self.assertTrue(all(row["model"] == "gemini-3.8-flash-lite-tts"
                            for row in manifest["slides"]))


if __name__=="__main__":
    unittest.main()
