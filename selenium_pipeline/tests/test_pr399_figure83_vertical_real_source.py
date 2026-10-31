"""Regression for the actual Figure 8.3 vertically stacked source curves."""
import unittest

from selenium_pipeline.figure83_vertical_original_panel_identity import (
    choose_original_slide_axis)
from selenium_pipeline.figure83_slide_inverse_glyph_correspondence import (
    validate_glyph_matrix)

class RealFigure83VerticalPanelTests(unittest.TestCase):
    def test_actual_slide_bitmap_measures_vertical_orientation(self):
        self.assertEqual(choose_original_slide_axis(
            image_width=232,image_height=480),"vertical")

    def test_historical_wrong_horizontal_assumption_is_detected(self):
        self.assertEqual(choose_original_slide_axis(
            image_width=480,image_height=232),"horizontal")
        self.assertEqual(choose_original_slide_axis(
            image_width=232,image_height=232),"undetermined")

    def test_actual_independently_matched_inverse_glyph_matrix(self):
        matrix=[[.78845,.58299,.5712],
                [.69433,.80213,.5599],
                [.56858,.56193,.78747]]
        proof=validate_glyph_matrix(matrix,min_score=.75,min_margin=.075)
        self.assertTrue(
            proof["all_three_source_inverse_operator_glyphs_in_slide_verified"])

    def test_swapped_source_operator_panel_is_rejected(self):
        matrix=[[.58299,.78845,.5712],
                [.80213,.69433,.5599],
                [.56858,.56193,.78747]]
        self.assertFalse(validate_glyph_matrix(matrix)[
            "all_three_source_inverse_operator_glyphs_in_slide_verified"])

    def test_competing_nonunique_label_is_rejected(self):
        matrix=[[.79,.78,.56],[.69,.81,.55],[.55,.52,.82]]
        self.assertFalse(validate_glyph_matrix(matrix)[
            "all_three_source_inverse_operator_glyphs_in_slide_verified"])

    def test_missing_operator_fails_closed(self):
        matrix=[[.79,.58,.56],[.69,.48,.55],[.55,.52,.82]]
        self.assertFalse(validate_glyph_matrix(matrix)[
            "all_three_source_inverse_operator_glyphs_in_slide_verified"])

if __name__=="__main__":
    unittest.main()
