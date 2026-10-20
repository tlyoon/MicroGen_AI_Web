"""Merged drawing component boxes cannot certify source-slide equivalence."""
import unittest
from selenium_pipeline.figure_source_component_registration import crosscheck_component_registration
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

class ComponentRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.components=[
          {"drawing_indices":[1,2],"union_bbox":[10,10,100,100]},
          {"drawing_indices":[9],"union_bbox":[130,130,145,145]}]
        self.groups=[
          {"source_matched_keypoint_union_bbox_pdf":[15,15,30,30]},
          {"source_matched_keypoint_union_bbox_pdf":[65,65,90,80]}]

    def test_one_component_spanning_both_groups_not_panel_claim(self):
        r=crosscheck_component_registration(self.components,self.groups)
        self.assertEqual(r["components_without_matched_registration"],1)
        self.assertEqual(r["observations"][0]["registration_groups_intersecting_bbox"],[0,1])
        self.assertEqual(r["observations"][1]["registration_groups_intersecting_bbox"],[])
        self.assertFalse(r["original_panel_boundaries_verified"])
        self.assertFalse(r["original_stroke_to_slide_pixel_equality_verified"])

    def test_component_no_groups_stays_blocked(self):
        r=crosscheck_component_registration(self.components,[])
        self.assertEqual(r["components_without_matched_registration"],2)
        self.assertFalse(r["publication_authorized"])

    def test_duplicate_index_rejected(self):
        extra=dict(self.components[0])
        with self.assertRaises(FigureIdentityReviewRequired):
            crosscheck_component_registration(self.components+[extra],self.groups)

    def test_invalid_registration_box_rejected(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            crosscheck_component_registration(self.components,[{
              "source_matched_keypoint_union_bbox_pdf":[0,0,0,0]}])
