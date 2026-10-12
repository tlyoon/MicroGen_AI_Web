"""Regression for Stage 6 narration-only resume SDK Python handoff."""
import inspect
import unittest
from unittest.mock import patch
from selenium_pipeline import runner


class ApiPythonStageTests(unittest.TestCase):
    def test_narration_only_resume_requires_sdk_python(self):
        with patch.dict("os.environ", {"MICROGEN_COMMUNICATION_MODE":"api"}, clear=False):
            self.assertTrue(runner._needs_api_python_for_stages(["narration"]))
            self.assertTrue(runner._needs_api_python_for_stages(
                ["narration","script_qa","tts","tts_qa","video"]))
    def test_figures_only_api_requires_sdk_python(self):
        with patch.dict("os.environ", {"MICROGEN_COMMUNICATION_MODE":"api"}, clear=False):
            self.assertTrue(runner._needs_api_python_for_stages(["figures"]))
    def test_ui_stages_do_not_use_sdk_python(self):
        with patch.dict("os.environ", {"MICROGEN_NARRATION_BACKEND":"ui",
                                       "MICROGEN_COMMUNICATION_MODE":"selenium"}, clear=False):
            self.assertFalse(runner._needs_api_python_for_stages(["figures","narration"]))
            self.assertFalse(runner._needs_api_python_for_stages(["slides"]))
    def test_runner_applies_helper_to_child_env(self):
        source=inspect.getsource(runner._execute_unlocked)
        self.assertIn('if _needs_api_python_for_stages(planned):',source)
        self.assertIn('env["MICROGEN_TTS_PYTHON"] = tts_python_executable()',source)


if __name__=="__main__": unittest.main()
