"""Source PDF vector proximity components never claim author panels."""
import unittest
from selenium_pipeline.figure_source_connected_components import connected_source_drawings
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

class ConnectedComponentsTests(unittest.TestCase):
    def test_two_clusters_from_disconnected_source_strokes(self):
        r=connected_source_drawings([
          {"drawing_index":3,"bbox":[0,0,10,0]},
          {"drawing_index":4,"bbox":[10,0,10,30]},
          {"drawing_index":8,"bbox":[100,0,110,0]}])
        self.assertEqual(r["candidate_connected_component_count"],2)
        self.assertEqual(r["candidate_components"][0]["drawing_indices"],[3,4])
        self.assertFalse(r["panel_count_and_labels_verified"])

    def test_distant_regions_merge_only_at_explicit_margin(self):
        objs=[{"drawing_index":3,"bbox":[0,0,10,10]},
              {"drawing_index":5,"bbox":[13,0,20,10]}]
        self.assertEqual(connected_source_drawings(objs,gap_pt=2)
                         ["candidate_connected_component_count"],2)
        self.assertEqual(connected_source_drawings(objs,gap_pt=4)
                         ["candidate_connected_component_count"],1)

    def test_duplicate_and_nan_fail_closed(self):
        objs=[{"drawing_index":0,"bbox":[0,0,10,0]}]
        with self.assertRaises(FigureIdentityReviewRequired):
            connected_source_drawings(objs*2)
        with self.assertRaises(FigureIdentityReviewRequired):
            connected_source_drawings([{"drawing_index":1,
                                      "bbox":[0,0,float("nan"),10]}])
        with self.assertRaises(FigureIdentityReviewRequired):
            connected_source_drawings(objs,gap_pt=-1)

    def test_no_vectors_is_zero_without_approval(self):
        r=connected_source_drawings([])
        self.assertEqual(r["candidate_connected_component_count"],0)
        self.assertFalse(r["video_or_publication_authorized"])
