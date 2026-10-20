"""Geometric threshold changes are sensitivity, not content proof."""
import unittest
from selenium_pipeline.figure_source_margin_sensitivity import compare_vector_proximity_margins
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

class ProximitySensitivityTests(unittest.TestCase):
    def setUp(self):
        self.objects=[
            {"drawing_index":0,"bbox":[0,0,10,10]},
            {"drawing_index":1,"bbox":[49,15,59,25]},
            {"drawing_index":2,"bbox":[100,100,110,110]}]
        self.groups=[{"source_matched_keypoint_union_bbox_pdf":[16,0,30,10]}]

    def test_stable_and_padding_sensitive_drawing_classes(self):
        r=compare_vector_proximity_margins(self.objects,self.groups)
        self.assertEqual(r["without_nearby_features_by_margin"],[3,3,2,2,1])
        self.assertEqual(r["robustly_unmatched_at_20pt"],1)
        self.assertEqual(r["sensitivity_rows"][0]["acquires_first_group_at_margin_pt"],8)
        self.assertIsNone(r["sensitivity_rows"][2]["acquires_first_group_at_margin_pt"])
        self.assertFalse(r["slide_omission_certified"])

    def test_overlapping_source_is_near_even_without_margin(self):
        r=compare_vector_proximity_margins(
            [{"drawing_index":9,"bbox":[17,1,18,9]}],self.groups)
        self.assertEqual(r["without_nearby_features_by_margin"],[0]*5)

    def test_duplicate_rejected(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            compare_vector_proximity_margins(
                self.objects+[self.objects[0]],self.groups)

    def test_nonfinite_group_rejected(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            compare_vector_proximity_margins(
                self.objects,[{"source_matched_keypoint_union_bbox_pdf":
                               [1,2,float("nan"),5]}])
