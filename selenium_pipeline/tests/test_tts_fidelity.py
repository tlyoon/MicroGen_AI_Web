import io
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

from selenium_pipeline.speech import normalize_scientific_speech
from selenium_pipeline.tts_fidelity import (
    _qa_hard_timeout_seconds,
    _risk_checks_text,
    diff_spans,
    evaluate_slide,
    inspect_audio,
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

    def test_risk_hints_call_out_historical_failure_modes(self):
        hints = _risk_checks_text("The value c. is shown beside Y.")
        self.assertIn("c.", hints)
        self.assertIn("Y", hints)

    def test_critical_token_issue_forces_review_even_with_perfect_transcript(self):
        with tempfile.TemporaryDirectory() as td:
            wav_path = Path(td) / "slide1.wav"
            make_wav(wav_path)
            payload = {
                "transcript": "the y value is positive",
                "pronunciation_issues": [],
                "critical_token_issues": [
                    {
                        "script_text": "Y",
                        "heard_as": "wee",
                        "category": "variable",
                        "severity": "major",
                        "note": "Variable name was audibly wrong.",
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
                    "the y value is positive",
                    wav_path,
                    threshold=99.0,
                )
            self.assertEqual(result["fidelity_percent"], 100.0)
            self.assertEqual(result["status"], "review")
            self.assertEqual(len(result["critical_token_issues"]), 1)

    def test_qa_hard_timeout_scales_with_audio_duration(self):
        with tempfile.TemporaryDirectory() as td:
            short = Path(td) / "short.wav"
            long = Path(td) / "long.wav"
            make_wav(short, 1.0)
            make_wav(long, 60.0)
            with patch.dict("os.environ", {}, clear=False):
                self.assertGreater(
                    _qa_hard_timeout_seconds(long),
                    _qa_hard_timeout_seconds(short),
                )

    def test_inspect_audio_kills_and_retries_hung_worker(self):
        with tempfile.TemporaryDirectory() as td:
            wav_path = Path(td) / "slide1.wav"
            make_wav(wav_path)
            workers = []
            for pid in (101, 102):
                worker = MagicMock()
                worker.pid = pid
                worker.returncode = None
                worker.communicate.side_effect = [
                    subprocess.TimeoutExpired(cmd="worker", timeout=1),
                    ("", None),
                ]
                workers.append(worker)
            with patch(
                "selenium_pipeline.tts_fidelity._qa_hard_timeout_seconds",
                return_value=1,
            ), patch(
                "selenium_pipeline.tts_fidelity.subprocess.Popen",
                side_effect=workers,
            ) as popen, patch(
                "selenium_pipeline.tts_fidelity._terminate_process_tree",
            ) as terminate:
                with self.assertRaises(TimeoutError):
                    inspect_audio(wav_path, "safe narration")
            self.assertEqual(popen.call_count, 2)
            self.assertEqual(terminate.call_count, 2)

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
