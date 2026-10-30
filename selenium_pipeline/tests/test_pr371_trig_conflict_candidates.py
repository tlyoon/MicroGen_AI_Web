"""Regression: reject disjoint trigonometric cues before candidate ranking."""
import unittest
from selenium_pipeline.original_thomas84_semantic_mapping_review import ranked_pdf_candidates


class TestTrigConflict(unittest.TestCase):
    def target(self, visible):
        return [{"kind": "text_block", "visible_text": visible,
                 "rendered_rect_pt": [1., 1., 40., 20.],
                 "draft_element_id": "test-element"}]

    def test_two_spoken_trig_functions_vs_disjoint_visible_one(self):
        self.assertEqual(ranked_pdf_candidates(
            "Use sine and cosine to integrate", self.target(
                "Use tangent to integrate this expression")), [])

    def test_one_spoken_vs_two_disjoint_visible_functions(self):
        self.assertEqual(ranked_pdf_candidates(
            "Use tangent to integrate", self.target(
                "Use sine and cosine to integrate")), [])

    def test_matching_trig_remains_candidate(self):
        result = ranked_pdf_candidates(
            "Integrate sine using substitution", self.target(
                "Integrate sine using substitution"))
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
