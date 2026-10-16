"""Deterministic offline tests for three-layer, fail-closed TTS review screening."""
import hashlib
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest
import wave

from selenium_pipeline.element_series_audit import check_tts_quality
from selenium_pipeline.tts_quality_gate import (
    acoustic_check, math_marks, math_token_order, screen, word_error_rate,
)


def save_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TtsQualityGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.plan = self.root / "plan.json"
        self.audio = self.root / "audio"
        self.audio.mkdir()
        self.asr = self.root / "asr"
        self.asr.mkdir()
        self.output = self.root / "quality.json"
        self.script = "The sine of theta equals one plus two in our equation."
        save_json(self.plan, {
            "status": "author_specified_unapproved_element_narration",
            "parts": [{"slides": [{"elements": [
                {"wav": "s01_e01.wav", "spoken_text": self.script}
            ]}]}],
        })
        self.wav = self.audio / "s01_e01.wav"
        self.make_wav()
        save_json(self.asr / "asr_job.json", {
            "plan_sha256": sha(self.plan),
            "model": "gemini-3.1-flash-lite",
            "source_model": "gemini-3.8-flash-lite-tts",
            "clips": [self.wav.name],
        })

    def make_wav(self, duration=4.0, amplitude=5000, silence=False):
        n = round(24000 * duration)
        with wave.open(str(self.wav), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(24000)
            output.writeframes(b"".join(
                struct.pack("<h", 0 if silence else round(amplitude *
                            math.sin(2 * math.pi * 440 * i / 24000)))
                for i in range(n)
            ))

    def receipt(self, transcript=None):
        words = self.script if transcript is None else transcript
        save_json(self.asr / (self.wav.name + ".asr.json"), {
            "wav": self.wav.name,
            "wav_sha256": sha(self.wav),
            "reference_sha256": hashlib.sha256(self.script.encode()).hexdigest(),
            "transcript": words,
            "transcript_sha256": hashlib.sha256(words.encode()).hexdigest(),
            "asr_model": "gemini-3.1-flash-lite",
            "metrics": {"machine_asr_consistent": True, "wer": 0},
        })

    def run_screen(self, use_asr=True):
        return screen(plan=self.plan, audio=self.audio, output=self.output,
                      asr_dir=self.asr if use_asr else None)

    def test_independent_asr_missing_never_approves(self):
        result = self.run_screen()
        self.assertEqual(result["pending_asr"], 1)
        self.assertEqual(result["manual_review_required"], 1)
        self.assertFalse(result["production_approved"])

    def test_no_asr_directory_never_approves(self):
        result = self.run_screen(False)
        self.assertEqual(result["pending_asr"], 1)
        self.assertFalse(result["all_machine_checks_passed"])

    def test_screen_match_remains_review_only(self):
        self.receipt()
        result = self.run_screen()
        self.assertTrue(result["all_machine_checks_passed"])
        self.assertEqual(result["machine_screen_passed"], 1)
        self.assertFalse(result["human_listening_complete"])
        self.assertFalse(result["production_approved"])

    def test_math_mismatch_cannot_be_hidden_by_passing_asr_receipt(self):
        self.receipt("The sine of theta equals one plus three in our equation.")
        result = self.run_screen()
        self.assertEqual(result["manual_review_required"], 1)
        self.assertIn("mathematical_spoken_token_discrepancy",
                      result["clips"][0]["review_flags"])

    def test_standard_word_edit_distance(self):
        self.assertEqual(word_error_rate("one two three", "one three"), .3333)
        self.assertEqual(word_error_rate("one two three", "one two three"), 0)
        self.assertEqual(math_marks("pi over two"),
                         math_marks("π/2"))

    def test_mathematical_section_number_digit_notation(self):
        self.assertEqual(math_marks("Section eight point four"),
                         math_marks("Section 8.4"))
        self.assertNotEqual(math_marks("negative pi over two"),
                            math_marks("positive pi over two"))

    def test_noncommutative_math_order_never_auto_passes(self):
        self.assertEqual(math_marks("two minus three"),
                         math_marks("three minus two"))
        self.assertNotEqual(math_token_order("two minus three"),
                            math_token_order("three minus two"))
        self.assertNotEqual(math_token_order("negative pi over two"),
                            math_token_order("positive pi over two"))
        self.assertEqual(math_token_order("Section 8.4"),
                         math_token_order("Section eight point four"))

    def test_swapped_mathematical_operands_are_flagged(self):
        self.script = "We calculate two minus three in this expression."
        self.plan.write_text(json.dumps({
            "status": "author_specified_unapproved_element_narration",
            "parts": [{"slides": [{"elements": [
                {"wav": self.wav.name, "spoken_text": self.script}
            ]}]}]}),encoding="utf-8")
        job=json.loads((self.asr/"asr_job.json").read_text())
        job["plan_sha256"]=sha(self.plan)
        save_json(self.asr/"asr_job.json",job)
        self.receipt("We calculate three minus two in this expression.")
        result=self.run_screen()
        self.assertIn("mathematical_spoken_token_discrepancy",
                      result["clips"][0]["review_flags"])
        self.assertTrue(result["clips"][0]["math_token_discrepancy"]["order_changed"])

    def test_clipping_is_technical_rejection(self):
        self.make_wav(amplitude=32767)
        result = self.run_screen(False)
        self.assertEqual(result["technical_rejected"], 1)
        self.assertIn("excessive_clipping",
                      result["clips"][0]["acoustics"]["technical_flags"])

    def test_silence_is_technical_rejection(self):
        self.make_wav(silence=True)
        result = self.run_screen(False)
        self.assertEqual(result["technical_rejected"], 1)

    def test_tampered_asr_transcript_hash_refused(self):
        self.receipt()
        receipt = self.asr / (self.wav.name + ".asr.json")
        data = json.loads(receipt.read_text())
        data["transcript"] = "altered transcript"
        save_json(receipt, data)
        with self.assertRaisesRegex(ValueError, "Tampered"):
            self.run_screen()
        self.assertFalse(self.output.exists())

    def test_stale_wav_refused(self):
        self.receipt()
        self.make_wav(amplitude=7000)
        with self.assertRaisesRegex(ValueError, "Tampered"):
            self.run_screen()

    def test_reject_edited_machine_pass_labels_in_audit(self):
        result = self.run_screen()
        result["clips"][0]["quality_state"] = "machine_screen_consistent_not_certified"
        result["clips"][0]["review_flags"] = []
        result["machine_screen_passed"] = 1
        result["manual_review_required"] = 0
        result["pending_asr"] = 0
        result["all_machine_checks_passed"] = True
        save_json(self.output, result)
        with self.assertRaisesRegex(ValueError, "recomputation"):
            check_tts_quality(json.loads(self.plan.read_text()), self.audio,
                              self.output, required=True,
                              authored_sha256=sha(self.plan),
                              authored_path=self.plan, asr_dir=self.asr)

    def test_refuses_report_overwrite(self):
        self.receipt()
        self.run_screen()
        with self.assertRaises(ValueError):
            self.run_screen()

    def test_integrated_strict_gate_refuses_missing_asr(self):
        self.run_screen()
        plan = json.loads(self.plan.read_text(encoding="utf-8"))
        report = check_tts_quality(plan, self.audio, self.output,
                                   authored_sha256=sha(self.plan), authored_path=self.plan, asr_dir=self.asr)
        self.assertFalse(report["machine_complete"])
        with self.assertRaisesRegex(ValueError, "incomplete/flagged"):
            check_tts_quality(plan, self.audio, self.output, required=True,
                              authored_sha256=sha(self.plan), authored_path=self.plan, asr_dir=self.asr)

    def test_integrated_screen_gates_and_audio_digest(self):
        self.receipt()
        self.run_screen()
        plan = json.loads(self.plan.read_text(encoding="utf-8"))
        report = check_tts_quality(plan, self.audio, self.output, required=True,
                                   authored_sha256=sha(self.plan), authored_path=self.plan, asr_dir=self.asr)
        self.assertTrue(report["machine_complete"])
        self.assertFalse(report["human_certified"])
        self.make_wav(amplitude=6800)
        with self.assertRaisesRegex(ValueError, "mismatched audio|Tampered"):
            check_tts_quality(plan, self.audio, self.output,
                              authored_sha256=sha(self.plan), authored_path=self.plan, asr_dir=self.asr)



if __name__ == "__main__":
    unittest.main()
