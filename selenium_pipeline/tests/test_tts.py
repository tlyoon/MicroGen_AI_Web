import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from selenium_pipeline.tts import synthesize_folder

WAV = b"RIFF" + b"X" * 80


def response(data):
    return SimpleNamespace(candidates=[SimpleNamespace(
        content=SimpleNamespace(parts=[SimpleNamespace(
            inline_data=SimpleNamespace(data=data))]))])


class FakeModels:
    def __init__(self, fail_at=0):
        self.requests = []
        self.fail_at = fail_at

    def generate_content(self, **kwargs):
        self.requests.append(kwargs)
        if len(self.requests) == self.fail_at:
            raise RuntimeError("temporary API error")
        return response(WAV)


class TTSTests(unittest.TestCase):
    def make_folder(self, root):
        folder = Path(root)
        (folder / "script.txt").write_text(
            "**Slide 1 [3 sec]:\nIntroduction**\n\n"
            "**Slide 2 [10 sec]:\nElectric flux is proportional to charge.**",
            encoding="utf-8")
        return folder

    def test_gemini_lite_publishes_complete_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.make_folder(tmp)
            models = FakeModels()
            with patch.dict(os.environ, {"GEMINI_API_KEY": "TEST_NOT_REAL"}):
                with patch("google.genai.Client", return_value=SimpleNamespace(models=models)):
                    synthesize_folder(folder, "gemini", "gemini-3.8-flash-lite-tts", "Kore")
            self.assertEqual((folder / "slide1.wav").read_bytes(), WAV)
            self.assertEqual((folder / "slide2.wav").read_bytes(), WAV)
            self.assertFalse((folder / ".tts_candidate").exists())
            self.assertEqual(models.requests[0]["model"], "gemini-3.8-flash-lite-tts")

    def test_failure_does_not_destroy_previous_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.make_folder(tmp)
            (folder / "slide1.wav").write_bytes(b"RIFF" + b"A" * 60)
            models = FakeModels(fail_at=2)
            with patch.dict(os.environ, {"GEMINI_API_KEY": "TEST_NOT_REAL"}):
                with patch("google.genai.Client", return_value=SimpleNamespace(models=models)):
                    with self.assertRaisesRegex(RuntimeError, "temporary API error"):
                        synthesize_folder(folder, "gemini", "gemini-3.8-flash-tts", "Kore")
            self.assertEqual((folder / "slide1.wav").read_bytes(), b"RIFF" + b"A" * 60)
            self.assertFalse((folder / "slide2.wav").exists())

    def test_no_secret_blocks_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.make_folder(tmp)
            with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}):
                with self.assertRaises(EnvironmentError):
                    synthesize_folder(folder, "gemini", "gemini-3.8-flash-lite-tts", "Kore")


if __name__ == "__main__":
    unittest.main()
