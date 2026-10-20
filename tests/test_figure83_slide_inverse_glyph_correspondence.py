import unittest
from selenium_pipeline.figure83_slide_inverse_glyph_correspondence import validate_glyph_matrix
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

class SourceSlideEquationGlyphTests(unittest.TestCase):
    def test_realistic_unique_source_label_scores_pass(self):
        result=validate_glyph_matrix([
            [.7884,.5830,.5712],
            [.6943,.8021,.5599],
            [.5686,.5619,.7875],
        ])
        self.assertTrue(result["all_three_source_inverse_operator_glyphs_in_slide_verified"])
        self.assertTrue(all(row["uniqueness_margin"]>.075
                            for row in result["operator_glyph_matches"]))
    def test_swapped_slide_panel_glyphs_do_not_pass(self):
        result=validate_glyph_matrix([
            [.5830,.7884,.5712],
            [.8021,.6943,.5599],
            [.5619,.5686,.7875],
        ])
        self.assertFalse(result["all_three_source_inverse_operator_glyphs_in_slide_verified"])
    def test_deleted_or_incomplete_label_do_not_pass(self):
        result=validate_glyph_matrix([
            [.7884,.5830,.5712],
            [.6943,.3200,.5599],
            [.5686,.5619,.7875],
        ])
        self.assertFalse(result["all_three_source_inverse_operator_glyphs_in_slide_verified"])
    def test_ambiguous_same_label_repeated_rejected(self):
        result=validate_glyph_matrix([
            [.80,.79,.50],
            [.69,.81,.56],
            [.56,.56,.79],
        ])
        self.assertFalse(result["all_three_source_inverse_operator_glyphs_in_slide_verified"])
    def test_nan_missing_score_rejected(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            validate_glyph_matrix([[.8,.3,.3],[.3,float("nan"),.3],[.3,.3,.8]])
