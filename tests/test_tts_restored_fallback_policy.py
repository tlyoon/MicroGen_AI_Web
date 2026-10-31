"""Fully offline contract regression: approved TTS fallback cannot mix voices or erase originals."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.tts import (
    _fallback_specs, _whole_batch_fallback, TTSFallbackModelExhausted,
)
from selenium_pipeline.tts_billing_guard import (
    require_tts_cost_authorization, TTSCostAuthorizationError,
)
from selenium_pipeline.tts_attempt_evidence import AttemptEvidence


def wav_data():
    out=io.BytesIO()
    with wave.open(out, "wb") as wavefile:
        wavefile.setnchannels(1)
        wavefile.setsampwidth(2)
        wavefile.setframerate(24000)
        wavefile.writeframes(b"\x00\x01" * 24000)
    return out.getvalue()


class RestoredFallbackTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder=Path(temp.name)
        (self.folder/"script.txt").write_text(
            "**Slide 1 [1 sec]:\nFirst university lesson.\n\n"
            "**Slide 2 [1 sec]:\nSecond university lesson.",encoding="utf-8")
        self.items=[(1,"First university lesson."),(2,"Second university lesson.")]
        self.requested={"provider":"gemini","model":"gemini-3.8-flash-lite-tts",
                        "voice":"Kore"}
        self.flash={"provider":"gemini","model":"gemini-3.8-flash-tts",
                    "voice":"Kore"}
        self.cloud={"provider":"chirp3","model":"chirp3-hd",
                    "voice":"en-US-Chirp3-HD-Kore"}
        self.evidence=AttemptEvidence(self.folder,self.items)

    def seed_failures(self, *, flash=False):
        for model in (["gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts"]
                      if flash else ["gemini-3.8-flash-lite-tts"]):
            for round_number in (1,2,3):
                self.evidence.record(provider="gemini",model=model,slide=1,
                    round_number=round_number, outcome="transient_failure",
                    error_type="RuntimeError")

    def simulate_full_batch(self, location, provider, model, voice, *,
                            allow_fallback=False, attempt_evidence=None):
        self.assertFalse(allow_fallback)
        self.assertIs(attempt_evidence,self.evidence)
        self.assertEqual(sorted([1,2]),sorted(n for n,_ in self.items))
        for number,text in self.items:
            (location/f"slide{number}.wav").write_bytes(wav_data())
            attempt_evidence.record(
                provider=provider,model=model,slide=number,
                round_number=1,outcome="success")
        manifest={"version":2,"primary":{"provider":provider,"model":model,"voice":voice},
                  "slides":[
                     {"slide":number,"source_text":text,"tts_text":text,
                      "provider":provider,"model":model,"voice":voice,
                      "fallback_used":False} for number,text in self.items]}
        (location/"tts_input_manifest.json").write_text(json.dumps(manifest))

    def test_flash_full_batch_leaves_old_primary_candidates_intact(self):
        self.seed_failures()
        primary=self.folder/".tts_candidate"
        primary.mkdir()
        (primary/"slide1.wav").write_bytes(b"historical PRIMARY partial")
        with patch("selenium_pipeline.tts._synthesize_folder_unlocked",
                   side_effect=self.simulate_full_batch) as mocked:
            rows=_whole_batch_fallback(
                self.folder,self.items,self.flash,
                requested=self.requested,
                completed_gemini_models=("gemini-3.8-flash-lite-tts",),
                    attempt_evidence=self.evidence)
        mocked.assert_called_once()
        self.assertEqual((primary/"slide1.wav").read_bytes(),
                         b"historical PRIMARY partial")
        self.assertEqual(rows[1]["model"],"gemini-3.8-flash-tts")
        manifest=json.loads((self.folder/"tts_input_manifest.json").read_text())
        self.assertEqual(manifest["primary"],self.flash)
        self.assertEqual(manifest["fallback_chain"],
                         ["gemini-3.8-flash-lite-tts"])
        self.assertTrue(manifest["all_slides_one_effective_voice"])
        self.assertTrue(all(row["fallback_used"] for row in manifest["slides"]))
        self.assertTrue(all(row["voice"]=="Kore" for row in manifest["slides"]))
        self.assertTrue(all(not row["voice_consistency"][
            "cross_model_voice_equivalence_verified"] for row in manifest["slides"]))

    def test_cloud_requires_both_failed_gemini_models(self):
        self.seed_failures()
        for prior in (
            (),
            ("gemini-3.8-flash-lite-tts",),
            ("gemini-3.8-flash-tts",),
        ):
            with self.subTest(prior=prior):
                with patch("selenium_pipeline.tts._synthesize_folder_unlocked") as synth:
                    with self.assertRaisesRegex(RuntimeError,"No verified 3-attempt exhausted|both Gemini models"):
                        _whole_batch_fallback(
                            self.folder,self.items,self.cloud,
                            requested=self.requested,
                            completed_gemini_models=prior,
                            attempt_evidence=self.evidence)
                    synth.assert_not_called()
        self.assertFalse((self.folder/"tts_input_manifest.json").exists())

    def test_cloud_after_both_failures_produces_one_corey_narrator(self):
        self.seed_failures(flash=True)
        with patch("selenium_pipeline.tts._synthesize_folder_unlocked",
                   side_effect=self.simulate_full_batch):
            _whole_batch_fallback(self.folder,self.items,self.cloud,
                requested=self.requested,
                completed_gemini_models=(
                    "gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts"),
                attempt_evidence=self.evidence)
        data=json.loads((self.folder/"tts_input_manifest.json").read_text())
        self.assertEqual(data["primary"],self.cloud)
        self.assertEqual(len(data["fallback_chain"]),2)
        self.assertTrue(all(r["voice"]=="en-US-Chirp3-HD-Kore"
                            for r in data["slides"]))
        self.assertTrue(all(r["primary_voice"]=="Kore" for r in data["slides"]))
        self.assertFalse(any(r["voice"]=="Kore" for r in data["slides"]))

    def test_failed_flash_batch_preserves_existing_candidates_and_publishes_nothing(self):
        self.seed_failures()
        candidate=self.folder/".tts_candidate"
        candidate.mkdir()
        (candidate/"slide1.wav").write_bytes(b"do not delete original")
        with patch("selenium_pipeline.tts._synthesize_folder_unlocked",
                   side_effect=RuntimeError("queue exhausted with 1 slide")):
            with self.assertRaises(TTSFallbackModelExhausted):
                _whole_batch_fallback(self.folder,self.items,self.flash,
                    requested=self.requested,
                    completed_gemini_models=("gemini-3.8-flash-lite-tts",),
                    attempt_evidence=self.evidence)
        self.assertEqual((candidate/"slide1.wav").read_bytes(),b"do not delete original")
        self.assertFalse((self.folder/"slide1.wav").exists())
        self.assertFalse((self.folder/"tts_input_manifest.json").exists())

    def test_existing_final_wav_blocks_new_billable_fallback_before_synth(self):
        self.seed_failures()
        (self.folder/"slide1.wav").write_bytes(b"ORIGINAL WAV REMAINS")
        with patch("selenium_pipeline.tts._synthesize_folder_unlocked") as synth:
            with self.assertRaisesRegex(RuntimeError,"Existing final TTS outputs"):
                _whole_batch_fallback(self.folder,self.items,self.flash,
                    requested=self.requested,
                    completed_gemini_models=("gemini-3.8-flash-lite-tts",),
                    attempt_evidence=self.evidence)
            synth.assert_not_called()
        self.assertEqual((self.folder/"slide1.wav").read_bytes(),b"ORIGINAL WAV REMAINS")

    def test_standing_consent_is_specific_to_routine_gemini_and_conditional_cloud(self):
        require_tts_cost_authorization("gemini",routine_gemini=True)
        require_tts_cost_authorization("chirp3",conditional_cloud_fallback=True)
        with self.assertRaises(TTSCostAuthorizationError):
            require_tts_cost_authorization("chirp3",routine_gemini=True)
        with self.assertRaises(TTSCostAuthorizationError):
            require_tts_cost_authorization("gemini")
        with self.assertRaises(TTSCostAuthorizationError):
            require_tts_cost_authorization("chirp3")


if __name__=="__main__":
    unittest.main()
