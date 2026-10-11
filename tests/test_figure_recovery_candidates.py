"""Source-grounded figure candidate previews, never guessed published images."""
import tempfile
import unittest
from pathlib import Path
import pymupdf
from selenium_pipeline.figure_recovery_candidates import figure_number, stage_review


class FigureCandidateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name) / "12.1"
        self.folder.mkdir()
        self.review = Path(tmp.name) / "review"
        source = self.folder / "source.pdf"
        with pymupdf.open() as pdf:
            a = pdf.new_page()
            a.insert_text((72,72), "Introductory discussion")
            b = pdf.new_page()
            b.insert_text((72,72), "Figure 12.1: Torque diagram")
            pdf.save(source)

    def test_figure_number_variants(self):
        self.assertEqual(figure_number("Figure12_1.png"), (12,1))
        self.assertEqual(figure_number("Figure 10.7.png"), (10,7))
        self.assertEqual(figure_number("Figure10_4.png"), (10,4))
        self.assertIsNone(figure_number("logo.png"))

    def test_review_finds_correct_caption_page_without_publishing(self):
        (self.folder / "slides.tex").write_text(
            r"\includegraphics{Figure12_1.png}")
        result = stage_review(self.folder, self.review)
        self.assertEqual(result["records"][0]["matching_pdf_pages"], [2])
        self.assertTrue((self.review / "figure_1_page_2.png").is_file())
        self.assertTrue((self.review / "manifest.json").is_file())
        self.assertFalse((self.folder / "Figure12_1.png").exists())

    def test_unmapped_name_not_guessed(self):
        (self.folder / "slides.tex").write_text(
            r"\includegraphics{mystery_portrait.png}")
        result = stage_review(self.folder, self.review)
        self.assertEqual(result["records"][0]["matching_pdf_pages"], [])
        self.assertFalse(list(self.review.glob("*.png")))

    def test_failed_figure_gate_stages_source_page_review_automatically(self):
        from selenium_pipeline.figure_audit import enforce_graphics
        (self.folder / "slides.tex").write_text(
            r"\IfFileExists{Figure12_1.png}{\includegraphics{Figure12_1.png}}{}")
        with self.assertRaisesRegex(ValueError, "Figure12_1.png"):
            enforce_graphics(self.folder)
        review = self.folder / ".microgen_work" / "figure_review_candidates"
        self.assertTrue((review / "manifest.json").is_file())
        self.assertTrue((review / "figure_1_page_2.png").is_file())
        self.assertFalse((self.folder / "Figure12_1.png").exists())

    def test_repeat_cannot_replace_existing_review(self):
        (self.folder / "slides.tex").write_text(r"\includegraphics{Figure12_1.png}")
        stage_review(self.folder, self.review)
        with self.assertRaises(FileExistsError):
            stage_review(self.folder, self.review)
