"""Regressions for Dell-115 short-slide Gemini TTS timeout/recovery."""
from __future__ import annotations
import io
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from selenium_pipeline.tts import (
    _tts_child_request_env,
    _stream_batch_fallback_progress,
)


class TTSDeadlineTests(unittest.TestCase):
    def test_sdk_per_key_timeout_must_fit_under_outer_watchdog(self):
        with patch("gemini_keys.get_gemini_api_keys", return_value=["key-A", "key-B"]):
            with patch.dict(os.environ, {"MICROGEN_GEMINI_REQUEST_TIMEOUT_MS": "120000"}):
                env = _tts_child_request_env(105.0)
        self.assertLess(int(env["MICROGEN_GEMINI_REQUEST_TIMEOUT_MS"]) * 2, 105000)
        self.assertEqual(env["MICROGEN_GEMINI_MAX_RETRIES"], "0")
        self.assertEqual(env["MICROGEN_GEMINI_TRANSIENT_RETRIES_PER_KEY"], "1")
        self.assertEqual(env["MICROGEN_GEMINI_SDK_RETRY_ATTEMPTS"], "1")

    def test_stricter_user_http_timeout_is_respected(self):
        with patch("gemini_keys.get_gemini_api_keys", return_value=["key-A"]):
            with patch.dict(os.environ, {"MICROGEN_GEMINI_REQUEST_TIMEOUT_MS": "9000"}):
                env = _tts_child_request_env(105.0)
        self.assertEqual(env["MICROGEN_GEMINI_REQUEST_TIMEOUT_MS"], "9000")

    def test_batch_fallback_streams_progress_before_exit(self):
        child = subprocess.Popen(
            [sys.executable, "-u", "-c", "print('first-batch-slide-done',flush=True)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        stream = io.StringIO()
        with redirect_stdout(stream):
            tail = _stream_batch_fallback_progress(child, 8)
        self.assertEqual(child.returncode, 0)
        self.assertIn("first-batch-slide-done", tail)
        self.assertIn("[tts batch]", stream.getvalue())

    def test_batch_timeout_does_not_wait_for_all_children(self):
        child = subprocess.Popen(
            [sys.executable, "-u", "-c", "import time;time.sleep(10)"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            with self.assertRaises(subprocess.TimeoutExpired):
                _stream_batch_fallback_progress(child, 0.3)
        finally:
            child.kill()
            child.wait(timeout=5)
            if child.stdout is not None:
                child.stdout.close()


if __name__ == "__main__":
    unittest.main()
