"""Bounded independent textbook-to-authored figure artwork QA must fail closed."""
import unittest
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.original_three_figure_source_body_visual_provenance import (
    classify_source_body,TARGETS,STATUS
)

def scores(good_page,good=.84,other=.40):
    return [{"page":i,"normalized_correlation":good if i==good_page else other,
             "top_left_xy_px":[55,145]} for i in range(1,7)]

class ThreeOriginalSourceBodyMatches(unittest.TestCase):
    def test_requires_correct_source_page_and_large_margin(self):
        for figure,(page,slide) in TARGETS.items():
            with self.subTest(figure=figure):
                out=classify_source_body(
                    figure_id=figure,expected_page=page,scores=scores(page))
                self.assertTrue(out[
                    "original_author_png_to_textbook_source_body_visual_pattern_match"])
                self.assertFalse(out["publisher_axis_ticks_and_symbol_science_approved"])
        self.assertIn("NOT_FULL_SCIENCE",STATUS)

    def test_wrong_textbook_page_fails_even_with_high_visual_score(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            classify_source_body(
                figure_id="8.5",expected_page=4,scores=scores(3,.95,.20))

    def test_too_weak_correlation_or_nonunique_match_rejected(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            classify_source_body(
                figure_id="8.6",expected_page=4,scores=scores(4,.77,.20))
        x=scores(4,.84,.80)
        with self.assertRaises(FigureIdentityReviewRequired):
            classify_source_body(figure_id="8.6",expected_page=4,scores=x)

    def test_incomplete_or_impossible_visual_measurement_rejected(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            classify_source_body(figure_id="8.4",expected_page=3,
                                 scores=scores(3)[:5])
        rows=scores(3)
        rows[0]["top_left_xy_px"]=[-1,50]
        with self.assertRaises(FigureIdentityReviewRequired):
            classify_source_body(figure_id="8.4",expected_page=3,scores=rows)

if __name__=="__main__":
    unittest.main()
