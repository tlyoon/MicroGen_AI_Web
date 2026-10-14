"""Doctor must fail before a real Gemini/Docling/TTS stage is launched."""
from __future__ import annotations
from unittest import TestCase
from unittest.mock import patch
from types import SimpleNamespace
from io import StringIO
from contextlib import redirect_stdout

from selenium_pipeline import runner


class DoctorGateTests(TestCase):
    def _probe(self, missing=(), pipeline=True, tts=True):
        output=StringIO()
        def spec(name):
            return None if name in missing else object()
        with patch("importlib.util.find_spec",side_effect=spec), \
             patch("importlib.import_module",return_value=SimpleNamespace()), \
             patch.object(runner,"pipeline_python_executable",
                          side_effect=None if pipeline else RuntimeError("docling missing"),
                          return_value="C:\\pipeline\\python.exe"), \
             patch.object(runner,"tts_python_executable",
                          side_effect=None if tts else RuntimeError("google.genai missing"),
                          return_value="C:\\tts\\python.exe"), \
             patch.object(runner.shutil,"which",return_value="C:\\bin\\tool.exe"), \
             patch.object(runner,"VENDOR",SimpleNamespace(exists=lambda:True)), \
             redirect_stdout(output):
            ready=runner.doctor()
        return ready,output.getvalue()

    def test_real_import_spec_none_is_reported_missing(self):
        ready,text=self._probe(missing=("selenium.webdriver",))
        self.assertFalse(ready)
        self.assertIn("selenium.webdriver: missing",text)
        self.assertIn("full-pipeline readiness: FAIL",text)

    def test_missing_docling_stage_interpreter_blocks_readiness(self):
        ready,text=self._probe(pipeline=False)
        self.assertFalse(ready)
        self.assertIn("pipeline Python (docling + selenium + pypdf): missing",text)

    def test_missing_tts_interpreter_blocks_readiness(self):
        ready,text=self._probe(tts=False)
        self.assertFalse(ready)
        self.assertIn("Gemini TTS Python (google.genai): missing",text)

    def test_complete_dependency_matrix_returns_pass(self):
        ready,text=self._probe()
        self.assertTrue(ready)
        self.assertIn("full-pipeline readiness: PASS",text)

    def test_main_returns_nonzero_for_failed_doctor(self):
        with patch.object(runner,"load_microvid_env"), \
             patch("selenium_pipeline.communication_policy.resolve_mode") as mode, \
             patch.object(runner,"doctor",return_value=False):
            mode.return_value=SimpleNamespace(value="selenium")
            self.assertEqual(runner.main(["--doctor"]),2)


if __name__=="__main__":
    import unittest
    unittest.main()
