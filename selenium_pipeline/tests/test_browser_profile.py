import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.launch_gemini import profile_root


class BrowserProfileTests(unittest.TestCase):
    def test_default_reuses_template_v2_profile(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {"LOCALAPPDATA": td}):
            expected = Path(td) / f"gemini_automation_{socket.gethostname().replace(' ', '_')}"
            self.assertEqual(profile_root(None), expected)

    def test_alternate_user_is_isolated_and_sanitized(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {"LOCALAPPDATA": td}):
            alt = profile_root("teacher@example.com")
            self.assertEqual(alt, Path(td) / "MicroGen_AI_Web" / "gemini_alternate" / "teacher_example.com")
            self.assertNotEqual(alt, profile_root(None))


if __name__ == "__main__":
    unittest.main()
