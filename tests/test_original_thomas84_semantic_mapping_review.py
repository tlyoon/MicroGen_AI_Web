"""No invented audio timings or unreviewed math approvals in source-PDF ranking."""
from __future__ import annotations
import tempfile
from pathlib import Path
import unittest
from selenium_pipeline.original_thomas84_semantic_mapping_review import (
    ranked_pdf_candidates, build_real_pdf_mapping_worklist,
)

def target(i, text):
    return {"draft_element_id": i, "kind": "text_block",
            "visible_text": text, "rendered_rect_pt": [0, 0, 200, 70],
            "panel_identity_review_required": False}

class RealPDFWorklistTests(unittest.TestCase):
    def test_step_two_prefers_actual_numbered_step(self):
        hits = ranked_pdf_candidates(
            "Second, substitute into the integrand and simplify algebraically.",
            [target("step1", "1 Substitute: Write x in terms of u"),
             target("step2", "2 Transform: Insert x and dx and simplify algebraically")])
        self.assertTrue(hits)
        self.assertEqual(hits[0]["original_pdf_element_id"], "step2")
        self.assertFalse(hits[0]["safe_for_student_highlight"])

    def test_sine_cosine_mismatch_does_not_approve_wrong_formula(self):
        hits = ranked_pdf_candidates(
            "Use sine u to simplify the radical.",
            [target("wrong", "cos u is positive"),
             target("right", "sin u is positive")])
        self.assertTrue(hits)
        self.assertNotIn("wrong", [x["original_pdf_element_id"] for x in hits])
        self.assertEqual(hits[0]["original_pdf_element_id"], "right")
        self.assertFalse(hits[0]["math_semantics_verified"])

    def test_composite_figures_never_become_text_targets(self):
        figure = target("fig", "Tangent ratio")
        figure["kind"] = "image_whole"
        self.assertEqual(ranked_pdf_candidates("tangent ratio", [figure]), [])

    def test_invalid_pdf_rectangle_rejected(self):
        malformed = target("x", "3 Integrate: Evaluate the integral")
        malformed["rendered_rect_pt"] = [40, 40, 20, 20]
        with self.assertRaises(ValueError):
            ranked_pdf_candidates("Third, integrate the integral", [malformed])

    def test_absent_original_source_creates_no_approved_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            out = base / "worklist.json"
            with self.assertRaises((ValueError, FileNotFoundError)):
                build_real_pdf_mapping_worklist(
                    original=base / "missing",
                    timing_receipt=base / "nonexistent.json", output=out)
            self.assertFalse(out.exists())

if __name__ == "__main__":
    unittest.main()
