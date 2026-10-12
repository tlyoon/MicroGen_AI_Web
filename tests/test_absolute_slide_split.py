"""Ensure the slide splitter launches on a PC without PYTHONPATH."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline import runner


class PortableSplitterLaunchTests(unittest.TestCase):
    def test_absolute_script_runs_in_isolated_python_from_source_folder(self):
        try:
            from PyPDF2 import PdfWriter, PdfReader
        except ImportError:
            from pypdf import PdfWriter, PdfReader
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            document = PdfWriter()
            document.add_blank_page(width=640, height=360)
            with (folder / "slides.pdf").open("wb") as stream:
                document.write(stream)
            script = runner.REPO / "selenium_pipeline" / "slide_pdf_split.py"
            self.assertTrue(script.is_file())
            environment = os.environ.copy()
            environment.pop("PYTHONPATH", None)
            result = subprocess.run(
                [sys.executable, "-I", str(script), "--folder", str(folder)],
                cwd=str(folder), env=environment, capture_output=True,
                text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            with (folder / "slide1.pdf").open("rb") as stream:
                self.assertEqual(len(PdfReader(stream).pages), 1)


if __name__ == "__main__":
    unittest.main()
