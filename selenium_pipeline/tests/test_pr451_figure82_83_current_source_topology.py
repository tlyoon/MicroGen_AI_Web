"""Original §8.4 Figure8.2/8.3 current-lecture routing is source-specific."""
import unittest
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.original_figure82_83_current_snapshot_routing import (
    triage_layout,STATUS
)

def source_layout(slide_bands=1):
    return {
        "source_page":2,"slide_page":6,
        "detected_graph_count":3,
        "original_vertical_graph_run_count":3,
        "slide_horizontal_graph_run_count":slide_bands,
        "three_graph_curve_shape_sequence_coherent":False,
        "three_graph_black_ink_geometry_plausible":False,
        "graph_correspondence_evidence":[{"order_index":i} for i in range(slide_bands)],
    }

class Figure82_83CurrentPinnedLecture(unittest.TestCase):
    def test_real_original_source_wrong_old_slide5_not_accepted(self):
        d=triage_layout(figure_id="8.3",author_slide=6,
                       graph_evidence=source_layout())
        self.assertEqual(d["actual_authored_slide"],6)
        self.assertEqual(d["actual_original_source_page"],2)
        self.assertEqual(d["slide_colored_graph_run_count_observed"],1)
        self.assertFalse(d["source_and_slide_complete_panel_geometry_approved"])
        self.assertTrue(d["reflow_reconstruction_or_individual_panel_ink_review_required"])
        self.assertIn("NONPRODUCTION",STATUS)

    def test_wrong_original_slide_number_fail_closed(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            triage_layout(figure_id="8.3",author_slide=5,
                          graph_evidence=source_layout())

    def test_graph_count_or_caption_source_mismatch_fail_closed(self):
        broken=source_layout()
        broken["original_vertical_graph_run_count"]=2
        with self.assertRaises(FigureIdentityReviewRequired):
            triage_layout(figure_id="8.3",author_slide=6,
                          graph_evidence=broken)

    def test_three_bands_alone_not_equivalent_to_three_correct_graphs(self):
        broken=source_layout(slide_bands=3)
        result=triage_layout(figure_id="8.3",author_slide=6,
                            graph_evidence=broken)
        self.assertTrue(result["old_three_separate_horizontal_bands_assumption_valid"])
        self.assertFalse(result["source_and_slide_complete_panel_geometry_approved"])

if __name__=="__main__":
    unittest.main()
