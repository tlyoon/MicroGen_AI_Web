"""Local Gemini key setup must not hide accidental duplicate definitions."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.runner import load_microvid_env


class LocalEnvKeyTests(unittest.TestCase):
    def test_two_distinct_numbered_keys_are_valid(self):
        with tempfile.TemporaryDirectory() as name:
            config = Path(name)
            (config / ".env").write_text(
                "GEMINI_API_KEY_1=example_first\nGEMINI_API_KEY_2=example_second\n")
            with patch.dict(os.environ, {"MICROVID_CONFIG_DIR": name, "LOCALAPPDATA": ""}, clear=True):
                self.assertEqual(load_microvid_env(), config / ".env")
                self.assertEqual(os.environ["GEMINI_API_KEY_1"], "example_first")
                self.assertEqual(os.environ["GEMINI_API_KEY_2"], "example_second")

    def test_conflicting_duplicate_key_name_is_refused_without_secrets(self):
        with tempfile.TemporaryDirectory() as name:
            (Path(name) / ".env").write_text(
                "GEMINI_API_KEY_1=example_one\nGEMINI_API_KEY_1=example_two\n")
            with patch.dict(os.environ, {"MICROVID_CONFIG_DIR": name, "LOCALAPPDATA": ""}, clear=True):
                with self.assertRaisesRegex(ValueError, "Conflicting duplicate") as raised:
                    load_microvid_env()
            self.assertNotIn("example_one", str(raised.exception))
            self.assertNotIn("example_two", str(raised.exception))
