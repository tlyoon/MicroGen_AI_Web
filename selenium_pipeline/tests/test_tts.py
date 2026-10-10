import sys
import tempfile
import os
import io
import json
import wave
import subprocess
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from selenium_pipeline.tts import (
    _gemini_say_with_watchdog, _merge_wav_payloads, _split_tts_text,
    _tts_timeout_seconds, _tts_workspace_lock, synthesize_folder,
)

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


def fake_gemini_keys_module(models=None, keys=None):
    module = types.ModuleType("gemini_keys")
    module.get_gemini_api_keys = lambda: list(["TEST_NOT_REAL"] if keys is None else keys)
    module.create_gemini_client = lambda api_key: SimpleNamespace(models=models)

    def call_with_client_failover(client_factory, operation, **_kwargs):
        client = client_factory("TEST_NOT_REAL")
        return operation(client)

    module.call_with_client_failover = call_with_client_failover
    return module


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
            fake = fake_gemini_keys_module(models=models)
            with patch.dict(sys.modules, {"gemini_keys": fake}):
                synthesize_folder(folder, "gemini", "gemini-3.8-flash-lite-tts", "Kore")
            self.assertEqual((folder / "slide1.wav").read_bytes(), WAV)
            self.assertEqual((folder / "slide2.wav").read_bytes(), WAV)
            self.assertFalse((folder / ".tts_candidate").exists())
            self.assertFalse((folder / ".tts.lock").exists())
            manifest = json.loads((folder / "tts_input_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["slides"][1]["tts_text"], "Electric flux is proportional to charge.")
            self.assertEqual(models.requests[0]["model"], "gemini-3.8-flash-lite-tts")

    def test_failure_does_not_destroy_previous_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.make_folder(tmp)
            (folder / "slide1.wav").write_bytes(b"RIFF" + b"A" * 60)
            models = FakeModels(fail_at=2)
            fake = fake_gemini_keys_module(models=models)
            with patch.dict(sys.modules, {"gemini_keys": fake}), patch.dict(
                os.environ,
                {"MICROGEN_TTS_QUEUE_ROUNDS": "1"},
            ):
                with self.assertRaisesRegex(RuntimeError, "temporary API error"):
                    synthesize_folder(folder, "gemini", "gemini-3.8-flash-tts", "Kore")
            self.assertEqual((folder / "slide1.wav").read_bytes(), b"RIFF" + b"A" * 60)
            self.assertFalse((folder / "slide2.wav").exists())
            self.assertFalse((folder / ".tts.lock").exists())

    def test_transient_failure_is_deferred_while_later_slide_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.make_folder(tmp)
            models = FakeModels(fail_at=1)
            fake = fake_gemini_keys_module(models=models)
            with patch.dict(sys.modules, {"gemini_keys": fake}), patch.dict(
                os.environ,
                {
                    "MICROGEN_TTS_QUEUE_ROUNDS": "2",
                    "MICROGEN_TTS_QUEUE_DELAY_SECONDS": "0",
                },
            ):
                synthesize_folder(folder, "gemini", "gemini-3.8-flash-lite-tts", "Kore")
            self.assertEqual(len(models.requests), 3)
            self.assertTrue((folder / "slide1.wav").is_file())
            self.assertTrue((folder / "slide2.wav").is_file())

    def test_queue_exhaustion_preserves_successful_candidates(self):
        class AlwaysFailModels:
            def generate_content(self, **_kwargs):
                raise RuntimeError("503 high demand")

        with tempfile.TemporaryDirectory() as tmp:
            folder = self.make_folder(tmp)
            fake = fake_gemini_keys_module(models=AlwaysFailModels())
            with patch.dict(sys.modules, {"gemini_keys": fake}), patch.dict(
                os.environ,
                {
                    "MICROGEN_TTS_QUEUE_ROUNDS": "2",
                    "MICROGEN_TTS_QUEUE_DELAY_SECONDS": "0",
                },
            ):
                with self.assertRaisesRegex(RuntimeError, "queue exhausted"):
                    synthesize_folder(folder, "gemini", "gemini-3.8-flash-lite-tts", "Kore")
            self.assertTrue((folder / ".tts_candidate").is_dir())
            self.assertFalse((folder / ".tts.lock").exists())

    def test_direct_tts_blocks_ambiguous_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "script.txt").write_text(
                "**Slide 1 [3 sec]:\nSafe title**\n\n"
                "**Slide 2 [10 sec]:\nWe use A torsion balance here.**",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "TTS-ambiguous"):
                synthesize_folder(
                    folder,
                    "gemini",
                    "gemini-3.8-flash-lite-tts",
                    "Kore",
                )
            self.assertFalse((folder / ".tts.lock").exists())

    def test_no_secret_blocks_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = self.make_folder(tmp)
            fake = fake_gemini_keys_module(models=FakeModels(), keys=[])
            with patch.dict(sys.modules, {"gemini_keys": fake}):
                with self.assertRaises(EnvironmentError):
                    synthesize_folder(folder, "gemini", "gemini-3.8-flash-lite-tts", "Kore")
            self.assertFalse((folder / ".tts.lock").exists())

    def test_second_live_writer_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            with _tts_workspace_lock(folder):
                with self.assertRaisesRegex(RuntimeError, "already active"):
                    with _tts_workspace_lock(folder):
                        pass
            self.assertFalse((folder / ".tts.lock").exists())



    def test_adaptive_timeout_scales_with_narration_length(self):
        with patch.dict(os.environ, {}, clear=False):
            for key in (
                "MICROGEN_TTS_HARD_TIMEOUT_SECONDS",
                "MICROGEN_TTS_TIMEOUT_BASE_SECONDS",
                "MICROGEN_TTS_TIMEOUT_PER_100_CHARS_SECONDS",
                "MICROGEN_TTS_TIMEOUT_MAX_SECONDS",
            ):
                os.environ.pop(key, None)
            self.assertEqual(_tts_timeout_seconds("x" * 900), 225.0)
            self.assertEqual(_tts_timeout_seconds("x" * 100), 105.0)

    def test_explicit_timeout_override_is_preserved(self):
        with patch.dict(os.environ, {"MICROGEN_TTS_HARD_TIMEOUT_SECONDS": "240"}):
            self.assertEqual(_tts_timeout_seconds("x" * 900), 240.0)

    def test_sentence_aware_chunking(self):
        text = (
            "First sentence is short. "
            "Second sentence is somewhat longer but should remain intact. "
            "Third sentence finishes the narration."
        )
        chunks = _split_tts_text(text, max_chars=70)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(" ".join(chunks), text)

    def test_merge_wav_payloads_concatenates_pcm_frames(self):
        def make_wav(frames):
            out = io.BytesIO()
            with wave.open(out, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(24000)
                wav.writeframes(frames)
            return out.getvalue()

        merged = _merge_wav_payloads([make_wav(b"\x01\x00" * 4), make_wav(b"\x02\x00" * 3)])
        with wave.open(io.BytesIO(merged), "rb") as wav:
            self.assertEqual(wav.getnframes(), 7)
            self.assertEqual(wav.getframerate(), 24000)

    def test_watchdog_retries_and_times_out(self):
        timeout = subprocess.TimeoutExpired(cmd=["python"], timeout=10)
        with patch.dict(os.environ, {
            "MICROGEN_TTS_HARD_TIMEOUT_SECONDS": "10",
            "MICROGEN_TTS_REQUEST_ATTEMPTS": "2",
        }):
            with patch("selenium_pipeline.tts.subprocess.run", side_effect=timeout) as run:
                with self.assertRaises(TimeoutError):
                    _gemini_say_with_watchdog("hello", 7, "gemini-3.8-flash-lite-tts", "Kore")
                self.assertEqual(run.call_count, 2)

    def test_stale_lock_is_recovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / ".tts.lock").write_text("999999999\n", encoding="utf-8")
            with _tts_workspace_lock(folder):
                self.assertTrue((folder / ".tts.lock").exists())
            self.assertFalse((folder / ".tts.lock").exists())


if __name__ == "__main__":
    unittest.main()
