"""Fail-closed auto-triage; no false academic or publication approval."""
from pathlib import Path
from unittest.mock import patch
import unittest

from selenium_pipeline.figure_layout_recovery_dispatch import (
    classify_layout_evidence, discover_source_slide_reflow,
)
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired


def evidence():
    return {
        "status":"THREE_GRAPH_COLORED_CURVES_REFLOW_CORROBORATED_REVIEW_REQUIRED",
        "original_vertical_graph_run_count":3,
        "slide_horizontal_graph_run_count":3,
        "three_graph_curve_shape_sequence_coherent":True,
        "graph_correspondence_evidence":[
            {"blue_red_curve_shapes_coherent":True,
             "original_math_axis_and_labels_verified":False}
            for _ in range(3)],
        "full_source_figure_equivalence_certified":False,
        "video_or_publication_authorized":False,
        "original_pdf_sha256":"source_hash",
        "existing_slides_pdf_sha256":"slide_hash",
    }


class LayoutAutoTriageTests(unittest.TestCase):
    def test_color_match_only_clears_false_whole_crop_aspect(self):
        r=classify_layout_evidence(evidence())
        self.assertTrue(r["layout_reflow_detected"])
        self.assertTrue(r["previous_whole_source_crop_aspect_mismatch_resolved_as_layout_only"])
        for key in ("complete_author_figure_certified",
                    "actual_math_label_semantics_certified",
                    "publication_authorized",
                    "auto_replacement_or_source_mutation"):
            self.assertFalse(r[key])

    def test_swapped_missing_or_forged_evidence_stays_blocked(self):
        for wrong in (
            {"original_vertical_graph_run_count":2},
            {"three_graph_curve_shape_sequence_coherent":False},
            {"graph_correspondence_evidence":[]},
            {"video_or_publication_authorized":True},
            {"full_source_figure_equivalence_certified":True},
        ):
            with self.subTest(wrong=wrong):
                report={**evidence(),**wrong}
                self.assertFalse(classify_layout_evidence(report)["layout_reflow_detected"])

    def test_optional_cv_dependency_failure_never_promotes_figure(self):
        with patch("selenium_pipeline.figure_three_graph_color_reflow."
                   "audit_real_three_graph_reflow",
                   side_effect=FigureIdentityReviewRequired("OpenCV unavailable")):
            r=discover_source_slide_reflow(
                source=Path("source.pdf"),slides=Path("slides.pdf"),
                source_page=1,slide_page=1,figure_id="8.3")
        self.assertEqual(r["status"],
            "AUTOMATIC_LAYOUT_DIAGNOSTIC_UNAVAILABLE_REVIEW_REQUIRED")
        self.assertFalse(r["publication_authorized"])
