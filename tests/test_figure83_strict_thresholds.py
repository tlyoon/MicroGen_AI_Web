import unittest
from selenium_pipeline.figure83_slide_inverse_glyph_correspondence import validate_glyph_matrix
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

VALID=[[.79,.55,.55],[.55,.82,.55],[.55,.55,.80]]
class GlyphStrictThresholdTests(unittest.TestCase):
    def test_real_good_matrix(self):
        self.assertTrue(validate_glyph_matrix(VALID)["all_three_source_inverse_operator_glyphs_in_slide_verified"])
    def test_malicious_disabled_thresholds(self):
        for score,margin in [(0,.075),(-1,-1),(.75,0),(.75,-.1),
                (float("nan"),.075),(.75,float("inf")),(float("inf"),.075),
                (.75,float("nan")),(1.01,.075),(.75,1.01),(True,.075)]:
            with self.subTest(score=score,margin=margin),self.assertRaises(FigureIdentityReviewRequired):
                validate_glyph_matrix(VALID,min_score=score,min_margin=margin)
    def test_bool_score_rejected(self):
        bad=[[True,.4,.4],[.4,.8,.4],[.4,.4,.8]]
        with self.assertRaises(FigureIdentityReviewRequired):
            validate_glyph_matrix(bad)
