import unittest
from copy import deepcopy
from pathlib import Path
from selenium_pipeline.figure83_full_expression_pixel_candidates import extract_real_equation_pixel_matrix
from selenium_pipeline.figure83_slide_inverse_glyph_correspondence import audit_source_to_slide_inverse_glyphs
from selenium_pipeline.figure83_equation_operator_registration import compare_equation_operator_anchors
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

ROOT=Path(r'G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4')
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
