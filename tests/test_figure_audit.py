import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.figure_audit import enforce_graphics

class FigureGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        (self.folder / "source.pdf").write_bytes(b"source")

    def test_guarded_missing_figure_fails(self):
        (self.folder / "slides.tex").write_text(
            r"\IfFileExists{Figure_12_4.png}{\includegraphics{Figure_12_4.png}}{}")
        with self.assertRaisesRegex(ValueError, "Figure_12_4.png"):
            enforce_graphics(self.folder)

    def test_exact_staged_recovery(self):
        (self.folder / "slides.tex").write_text(r"\includegraphics{Figure_12_4.png}")
        stage = self.folder / ".microgen_work"
        stage.mkdir()
        (stage / "Figure_12_4.png").write_bytes(b"valid-image-placeholder")
        result = enforce_graphics(self.folder)
        self.assertEqual(result["figures"][0]["status"], "verified_file")
        self.assertEqual((self.folder / "Figure_12_4.png").read_bytes(), b"valid-image-placeholder")

    def test_no_guessing_similar_name(self):
        (self.folder / "slides.tex").write_text(r"\includegraphics{Figure_12_4.png}")
        (self.folder / "Figure 12.4.png").write_bytes(b"other")
        with self.assertRaisesRegex(ValueError, "Figure_12_4.png"):
            enforce_graphics(self.folder)

if __name__ == "__main__":
    unittest.main()
