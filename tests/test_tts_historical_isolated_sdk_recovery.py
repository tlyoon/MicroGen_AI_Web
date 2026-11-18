"""Previously installed SDK reuse in normal TTS child preflight.

No audio generation, provider request, credentials or pip install.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
import os
import sys

from selenium_pipeline.tts import _modern_tts_worker_python
from selenium_pipeline.gemini38_tts_interactions import InteractionsTTSCompatError

_MODEL="gemini-3.8-flash-lite-tts"

class HistoricalIsolatedSDKRecoveryTests(TestCase):
    def setUp(self):
        self.root=TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.altdir=Path(self.root.name)
        self.executable=(self.altdir/"MicroGen_AI_Web_Checkpoints"/
          "20261027_GEMINI38_SDK_ISOLATED_VENV"/"Scripts"/"python.exe")
        self.executable.parent.mkdir(parents=True)
        self.executable.write_bytes(b"offline-sdk-fixture")
        self.env=patch.dict(os.environ,{
            "LOCALAPPDATA":str(self.altdir),
            "MICROGEN_TTS_WORKER_PYTHON":""})
        self.env.start()
        self.addCleanup(self.env.stop)

    def _old_sdk(self):
        return patch("selenium_pipeline.gemini38_tts_interactions.require_modern_tts_sdk",
                     side_effect=InteractionsTTSCompatError("old google-genai SDK"))

    def test_registered_existing_isolated_python_selected_once_without_provider(self):
        with self._old_sdk(),patch(
                "selenium_pipeline.tts.subprocess.run",
                return_value=SimpleNamespace(returncode=0)) as local:
            result=_modern_tts_worker_python(_MODEL)
        self.assertEqual(Path(result),self.executable)
        local.assert_called_once()
        args=local.call_args.args[0]
        self.assertEqual(args[0],str(self.executable))
        self.assertEqual(args[1],"-c")
        self.assertNotIn("tts_worker",repr(args))
        self.assertFalse(any("pip" in str(x) for x in args))

    def test_missing_old_venv_stops_before_subprocess(self):
        self.executable.unlink()
        with self._old_sdk(),patch("selenium_pipeline.tts.subprocess.run",
                        side_effect=AssertionError("No executable should run")):
            with self.assertRaisesRegex(RuntimeError,"Historical isolated"):
                _modern_tts_worker_python(_MODEL)

    def test_retired_registry_stops_before_subprocess(self):
        with self._old_sdk(),patch(
                "selenium_pipeline.recovery_registry.lookup_mechanism",
                return_value=None),patch(
                "selenium_pipeline.tts.subprocess.run",
                side_effect=AssertionError("No executable should run")):
            with self.assertRaisesRegex(RuntimeError,"No registered isolated"):
                _modern_tts_worker_python(_MODEL)

    def test_incompatible_isolated_sdk_denied_without_api_send(self):
        with self._old_sdk(),patch(
                "selenium_pipeline.tts.subprocess.run",
                return_value=SimpleNamespace(returncode=1)) as local:
            with self.assertRaisesRegex(RuntimeError,"lacks google-genai"):
                _modern_tts_worker_python(_MODEL)
        self.assertEqual(local.call_count,1)

    def test_explicit_invalid_worker_is_not_overridden_by_historical_fallback(self):
        with patch.dict(os.environ,{"MICROGEN_TTS_WORKER_PYTHON":
                                    str(self.altdir/"missing"/"python.exe")}):
            with patch("selenium_pipeline.tts.subprocess.run",
                       side_effect=AssertionError("Must fail before spawn")):
                with self.assertRaisesRegex(RuntimeError,
                                            "not a real isolated"):
                    _modern_tts_worker_python(_MODEL)

    def test_non_interactions_model_does_not_select_a_worker_or_hit_registry(self):
        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   side_effect=AssertionError("No SDK recovery required")):
            self.assertEqual(_modern_tts_worker_python("other-tts"),sys.executable)

if __name__=="__main__":
    import unittest
    unittest.main()
