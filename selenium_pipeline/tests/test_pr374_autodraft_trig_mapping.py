"""No disjoint trigonometric cues in actual source focus draft ranking."""
import unittest
from selenium_pipeline.element_plan_autodraft import stable_recommendations

class TestOriginalMathFocusDraft(unittest.TestCase):
    def entry(self, text):
        return {"kind":"text_block", "visible_text":text,
                "draft_element_id":"element-1", "anchor":{"type":"text_block","index":0}}

    def test_multi_function_conflicts_excluded(self):
        for spoken, visible in (
            ("Integrate sine and cosine", "Integrate tangent"),
            ("Substitute tangent", "Substitute sine and cosine"),
        ):
            with self.subTest(spoken=spoken):
                self.assertEqual(stable_recommendations(spoken, [self.entry(visible)]), [])

    def test_matching_function_still_review_candidate(self):
        result = stable_recommendations("Integrate sine", [self.entry("Integrate sine")])
        self.assertEqual(len(result), 1)
        self.assertFalse(result[0]["possible_trig_mismatch_review"])

if __name__ == "__main__":
    unittest.main()
