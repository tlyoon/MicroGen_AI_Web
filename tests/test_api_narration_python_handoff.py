"""Selenium-only narration has no SDK Python handoff."""
import inspect
import unittest
from unittest.mock import patch
from selenium_pipeline import runner


class ContentPythonStageTests(unittest.TestCase):
    def test_narration_resume_does_not_request_sdk_python(self):
        with patch.dict("os.environ", {"MICROGEN_COMMUNICATION_MODE":"selenium"}):
            self.assertFalse(runner._needs_api_python_for_stages(["narration"]))
            self.assertFalse(runner._needs_api_python_for_stages(
                ["narration","script_qa","tts","tts_qa","video"]))
            self.assertFalse(runner._needs_api_python_for_stages(["figures","slides"]))

    def test_api_or_fallback_mode_denied_before_sdk_selection(self):
        for mode in ("api","fallback"):
            with patch.dict("os.environ",{"MICROGEN_COMMUNICATION_MODE":mode}):
                with self.assertRaisesRegex(ValueError,"SELENIUM_ONLY"):
                    runner._needs_api_python_for_stages(["narration"])

    def test_runner_does_not_resolve_api_python_for_content(self):
        source=inspect.getsource(runner._needs_api_python_for_stages)
        self.assertIn("return False",source)
        self.assertIn("resolve_mode()",source)
        launcher=inspect.getsource(runner._execute_unlocked)
        self.assertIn('"MICROGEN_FIGURE_MAPPING_BACKEND": "browser"',launcher)
        self.assertIn('"MICROGEN_NARRATION_BACKEND": "ui"',launcher)


if __name__=="__main__":
    unittest.main()
