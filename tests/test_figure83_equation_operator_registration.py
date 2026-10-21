import unittest
from copy import deepcopy
from pathlib import Path
from selenium_pipeline.figure83_full_expression_pixel_candidates import extract_real_equation_pixel_matrix
from selenium_pipeline.figure83_slide_inverse_glyph_correspondence import audit_source_to_slide_inverse_glyphs
from selenium_pipeline.figure83_equation_operator_registration import compare_equation_operator_anchors
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

ROOT=Path(r'G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4')
@unittest.skipUnless((ROOT/"source.pdf").is_file() and (ROOT/"slides.pdf").is_file(), "Real Thomas PDFs are only available on authorized Dell-115")
class IndependentExpressionOperatorRegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expression=extract_real_equation_pixel_matrix(
            source=ROOT/'source.pdf',slides=ROOT/'slides.pdf')
        cls.operator=audit_source_to_slide_inverse_glyphs(
            source=ROOT/'source.pdf',slides=ROOT/'slides.pdf')
    def test_real_correct_registration_not_semantics(self):
        r=compare_equation_operator_anchors(self.expression,self.operator)
        self.assertTrue(r["every_full_expression_template_registration_agrees_with_operator"])
        self.assertTrue(all(z["operator_registration_distance_px"]<1 for z in r["panels"]))
        self.assertFalse(r["mathematical_equivalence_verified"])
        self.assertFalse(r["paid_tts_authorized"])
    def test_wrong_full_expression_location_rejected(self):
        e=deepcopy(self.expression)
        e["image_match_details"][0][0]["panel_local_top_left_px"][0]+=30
        r=compare_equation_operator_anchors(e,self.operator)
        self.assertFalse(r["every_full_expression_template_registration_agrees_with_operator"])
    def test_cross_asset_hash_rejected(self):
        bad=deepcopy(self.operator);bad["existing_slides_sha256"]="different"
        with self.assertRaises(FigureIdentityReviewRequired):
            compare_equation_operator_anchors(self.expression,bad)
    def test_invalid_tolerance_rejected(self):
        for value in (-1,0,26,True):
            with self.assertRaises(FigureIdentityReviewRequired):
                compare_equation_operator_anchors(self.expression,self.operator,max_offset_px=value)


def _synthetic_operator_registration():
    equation={"source_sha256":"a"*64,"slides_sha256":"b"*64,
        "existing_slide_bitmap_bounds":[[0,100],[100,200],[200,300]],
        "printed_source_equations":[
          {"source_equation_bbox_pt":[10,10,40,25],
           "source_inverse_operator_bbox_pt":[20,10,30,20]}
          for _ in range(3)],
        "image_match_details":[
          [{"relative_pixel_scale":.5,"panel_local_top_left_px":[10,10]}
           for j in range(3)] for i in range(3)]}
    original={"original_source_sha256":"a"*64,"existing_slides_sha256":"b"*64,
        "source_operator_target_pixel_boxes_for_review":[
           {"matched_original_glyph_bbox_on_existing_slide_bitmap_px":
               [100*i+25,10,100*i+35,20]}
           for i in range(3)]}
    return equation,original

class PortableOriginalOperatorCrossRegistrationTests(unittest.TestCase):
    def test_synthetic_exact_anchoring_is_only_geometric(self):
        a,b=_synthetic_operator_registration()
        r=compare_equation_operator_anchors(a,b)
        self.assertTrue(r["every_full_expression_template_registration_agrees_with_operator"])
        self.assertFalse(r["mathematical_equivalence_verified"])
        self.assertFalse(r["paid_tts_authorized"])
    def test_synthetic_swapped_operator_anchor_rejected(self):
        a,b=_synthetic_operator_registration()
        b["source_operator_target_pixel_boxes_for_review"][1]["matched_original_glyph_bbox_on_existing_slide_bitmap_px"][0]+=40
        self.assertFalse(compare_equation_operator_anchors(
            a,b)["every_full_expression_template_registration_agrees_with_operator"])
    def test_source_hash_mismatch_rejected(self):
        a,b=_synthetic_operator_registration()
        b["original_source_sha256"]="c"*64
        with self.assertRaises(FigureIdentityReviewRequired):
            compare_equation_operator_anchors(a,b)

