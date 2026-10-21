import unittest
from pathlib import Path
from selenium_pipeline.figure83_full_expression_pixel_candidates import extract_real_equation_pixel_matrix
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

ROOT=Path(r'G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4')
class EquationPixelReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence=extract_real_equation_pixel_matrix(source=ROOT/'source.pdf',
                                                       slides=ROOT/'slides.pdf')
    def test_real_source_and_slide_report_three_by_three(self):
        result=self.evidence
        self.assertEqual(len(result["image_match_score_matrix"]),3)
        self.assertTrue(all(len(r)==3 for r in result["image_match_score_matrix"]))
        self.assertTrue(all(0<=x<=1 for row in result["image_match_score_matrix"] for x in row))
        # Real data: whole-expression cropped fonts are not a uniquely
        # matched matrix; passing operator glyphs do not prove equations.
        self.assertFalse(result["unambiguous_full_equation_pixel_matching_detected"])
    def test_no_premature_technical_or_paid_authorization(self):
        r=self.evidence
        self.assertFalse(r["source_equation_math_equivalence_to_slide_verified"])
        self.assertFalse(r["full_equation_mathematically_verified"])
        self.assertFalse(r["narration_word_alignment_verified"])
        self.assertFalse(r["paid_tts_authorized"])
        self.assertFalse(r["student_publication_authorized"])
    def test_invalid_pages_fail_closed(self):
        with self.assertRaises((IndexError,FigureIdentityReviewRequired,ValueError)):
            extract_real_equation_pixel_matrix(source=ROOT/'source.pdf',
                                               slides=ROOT/'slides.pdf',source_page=9999)
