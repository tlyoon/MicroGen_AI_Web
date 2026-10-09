import io
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.speech import normalize_scientific_speech
from selenium_pipeline.tts_fidelity import (
    diff_spans,
    evaluate_slide,
    normalize_for_comparison,
    wav_duration_seconds,
    word_error_stats,
)


def make_wav(path: Path, seconds: float = 1.0) -> None:
    frames = int(24000 * seconds)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        wav_file.writeframes(b"\x00\x00" * frames)


class TTSFidelityTests(unittest.TestCase):
    def test_identical_text_scores_100_percent(self):
        stats = word_error_stats(
            "Coulomb's law gives the electric force.",
            "Coulomb's law gives the electric force.",
        )
        self.assertEqual(stats["word_errors"], 0)
        self.assertEqual(stats["fidelity_percent"], 100.0)

    def test_punctuation_and_capitalization_are_ignored(self):
        stats = word_error_stats(
            "The Force, Is Positive.",
            "the force is positive",
        )
        self.assertEqual(stats["fidelity_percent"], 100.0)

    def test_inaudible_apostrophes_and_quotes_do_not_reduce_fidelity(self):
        stats = word_error_stats("Coulombs Law on 'A'", "Coulomb's Law on A")
        self.assertEqual(stats["fidelity_percent"], 100.0)

    def test_digit_and_spoken_number_forms_are_equivalent(self):
        stats = word_error_stats(
            "parts in ten to the sixteenth power",
            "parts in 10 to the 16th power",
        )
        self.assertEqual(stats["fidelity_percent"], 100.0)

    def test_word_omission_reduces_fidelity(self):
        stats = word_error_stats("one two three four", "one two four")
        self.assertEqual(stats["deletions"], 1)
        self.assertEqual(stats["fidelity_percent"], 75.0)

    def test_diff_spans_identifies_changed_phrase(self):
        findings = diff_spans(
            "electric force is attractive",
            "electric force is repulsive",
        )
        self.assertEqual(findings[0]["type"], "replace")
        self.assertEqual(findings[0]["expected"], "attractive")
        self.assertEqual(findings[0]["heard"], "repulsive")

    def test_scientific_speech_normalization_port(self):
        spoken = normalize_scientific_speech(
            r"Δx = 2 m/s^2 and π radians at 5%."
        )
        self.assertIn("delta", spoken)
        self.assertIn("metres per second squared", spoken)
        self.assertIn("pi", spoken)
        self.assertIn("percent", spoken)

    def test_evaluate_slide_uses_audio_findings_and_local_score(self):
        with tempfile.TemporaryDirectory() as td:
            wav_path = Path(td) / "slide1.wav"
            make_wav(wav_path, 2.0)
            payload = {
                "transcript": "electric force is attractive",
                "pronunciation_issues": [],
                "audio_defects": [],
                "notes": "",
            }
            with patch(
                "selenium_pipeline.tts_fidelity.inspect_audio",
                return_value=payload,
            ):
                result = evaluate_slide(
                    1,
                    "Electric force is attractive.",
                    wav_path,
                    threshold=99.0,
                )
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["fidelity_percent"], 100.0)
            self.assertAlmostEqual(result["duration_seconds"], 2.0, places=3)

    def test_major_pronunciation_issue_forces_review(self):
        with tempfile.TemporaryDirectory() as td:
            wav_path = Path(td) / "slide1.wav"
            make_wav(wav_path)
            payload = {
                "transcript": "a sphere",
                "pronunciation_issues": [
                    {
                        "script_text": "A sphere",
                        "heard_as": "ay sphere",
                        "severity": "major",
                        "note": "Article pronounced as letter name.",
                    }
                ],
                "audio_defects": [],
            }
            with patch(
                "selenium_pipeline.tts_fidelity.inspect_audio",
                return_value=payload,
            ):
                result = evaluate_slide(
                    1,
                    "A sphere",
                    wav_path,
                    threshold=99.0,
                )
            self.assertEqual(result["status"], "review")
            self.assertEqual(result["fidelity_percent"], 100.0)


if __name__ == "__main__":
    unittest.main()
