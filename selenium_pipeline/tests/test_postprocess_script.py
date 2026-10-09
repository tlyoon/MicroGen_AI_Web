import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


POSTPROCESS = (
    Path(__file__).resolve().parents[1]
    / "vendor_template_v2"
    / "postprocess_script.py"
)


class PostprocessScriptTests(unittest.TestCase):
    def test_default_cleanup_does_not_rewrite_pronunciation(self):
        source = (
            "**Slide 1 [5 sec]:\nSafe title**\n\n"
            "**Slide 2 [20 sec]:\n"
            "We choose a Gaussian surface of radius r and area A. "
            "The ambiguous token c. must remain visible.**\n"
        )
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            (folder / "script.txt").write_text(source, encoding="utf-8")
            env = os.environ.copy()
            env.pop("MICROGEN_LEGACY_TTS_NORMALIZATION", None)
            completed = subprocess.run(
                [sys.executable, str(POSTPROCESS)],
                cwd=folder,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            output = (folder / "script.txt").read_text(encoding="utf-8")
            self.assertIn("a Gaussian surface", output)
            self.assertIn("radius r", output)
            self.assertIn("area A.", output)
            self.assertIn("c.", output)
            self.assertNotIn("We choose A Gaussian surface", output)

    def test_legacy_mode_is_explicit_opt_in(self):
        source = (
            "**Slide 1 [5 sec]:\nSafe title**\n\n"
            "**Slide 2 [20 sec]:\nWe choose a Gaussian surface.**\n"
        )
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            (folder / "script.txt").write_text(source, encoding="utf-8")
            env = os.environ.copy()
            env["MICROGEN_LEGACY_TTS_NORMALIZATION"] = "1"
            completed = subprocess.run(
                [sys.executable, str(POSTPROCESS)],
                cwd=folder,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            output = (folder / "script.txt").read_text(encoding="utf-8")
            self.assertIn("We choose A Gaussian surface", output)


if __name__ == "__main__":
    unittest.main()
