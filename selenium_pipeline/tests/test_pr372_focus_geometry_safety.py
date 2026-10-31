"""Fail closed when mathematical focus target geometry is unsafe."""
import unittest
from selenium_pipeline.original_thomas84_semantic_mapping_review import ranked_pdf_candidates
from selenium_pipeline.production_video_contract import VideoContractError

class TestFocusGeometrySafety(unittest.TestCase):
    def target(self, rect):
        return [{"kind":"text_block", "visible_text":"Integrate sine using substitution",
                 "draft_element_id":"fixture", "rendered_rect_pt":rect}]

    def test_nonfinite_rejected(self):
        for value in (float('nan'), float('inf'), float('-inf')):
            with self.subTest(value=value), self.assertRaises(VideoContractError):
                ranked_pdf_candidates("Integrate sine using substitution", self.target([1, 2, value, 30]))

    def test_boolean_and_negative_rejected(self):
        for rect in ([True, 2, 20, 30], [-1, 2, 20, 30], [1, -2, 20, 30]):
            with self.subTest(rect=rect), self.assertRaises(VideoContractError):
                ranked_pdf_candidates("Integrate sine using substitution", self.target(rect))

    def test_valid_geometry_retained_review_only(self):
        candidates = ranked_pdf_candidates("Integrate sine using substitution", self.target([1, 2, 20, 30]))
        self.assertTrue(candidates)
        self.assertFalse(candidates[0]["safe_for_student_highlight"])
        self.assertFalse(candidates[0]["math_semantics_verified"])

if __name__ == '__main__':
    unittest.main()
