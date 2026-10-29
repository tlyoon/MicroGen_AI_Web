"""Original drawing proximity does not prove correspondence or panel completeness."""
import unittest
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_source_vector_proximity import classify_source_vector_proximity

def vector(n,bbox):
    return {"drawing_index":n,"bbox":bbox}

def group(box):
    return {"source_matched_keypoint_union_bbox_pdf":box}

class VectorProximityTests(unittest.TestCase):
    def test_unmatched_drawing_remains_visible_blocker(self):
        r=classify_source_vector_proximity(
            [vector(0,[10,10,20,20]),vector(1,[150,150,165,165])],
            [group([8,8,35,35])],padding_pt=0)
        self.assertEqual(r["without_nearby_features"],1)
        self.assertEqual(r["near_single_group"],1)
        self.assertFalse(r["complete_original_graph_geometry_verified"])
        self.assertFalse(r["video_or_publication_authorized"])

    def test_overlap_is_ambiguous_not_membership(self):
        r=classify_source_vector_proximity(
            [vector(5,[60,60,70,70])],
            [group([20,20,75,75]),group([65,50,115,95])],padding_pt=0)
        self.assertEqual(r["ambiguous_multiple_groups"],1)
        self.assertFalse(r["original_panel_ownership_verified"])
    def test_empty_correspondences_never_satisfy_original_content(self):
        r=classify_source_vector_proximity(
            [vector(8,[30,40,60,75])],[])
        self.assertEqual(r["without_nearby_features"],1)
        self.assertFalse(r["all_strokes_in_slide_verified"])

    def test_empty_source_inventory_not_proof_of_complete_figure(self):
        r=classify_source_vector_proximity([], [group([0,0,15,15])])
        self.assertEqual(r["source_vector_objects_total"],0)
        self.assertFalse(r["complete_original_graph_geometry_verified"])

    def test_duplicate_source_object_index_rejected(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            classify_source_vector_proximity(
                [vector(0,[10,10,20,20]),vector(0,[50,50,65,65])],
                [group([5,5,80,80])])

    def test_invalid_nonfinite_box_rejected(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            classify_source_vector_proximity(
                [vector(0,[10,float("nan"),20,20])],
                [group([5,5,80,80])])

    def test_nonfinite_or_oversized_padding_rejected(self):
        for padding in (-1,21,float("inf")):
            with self.subTest(padding=padding):
                with self.assertRaises(FigureIdentityReviewRequired):
                    classify_source_vector_proximity([], [],padding_pt=padding)
    def test_zero_height_line_is_valid_vector_object(self):
        r=classify_source_vector_proximity(
            [vector(14,[20,50,100,50])],
            [group([10,40,110,60])])
        self.assertEqual(r["near_single_group"],1)
        self.assertFalse(r["all_strokes_in_slide_verified"])
