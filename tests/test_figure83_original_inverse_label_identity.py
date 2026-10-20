"""Adversarial original-PDF inverse-function identity tests, no OCR."""
import unittest
from selenium_pipeline.figure83_original_inverse_label_identity import identify_original_panel_labels
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

def panel(idx, name):
    return {"graph_index":idx,"original_printed_tokens":[
        {"text":word,"original_bbox_pt":[float(k),float(idx*20),float(k+2),float(idx*20+4)]}
        for k,word in enumerate(("u","=",name,"x","a"),1)]}

class PrintedInverseIdentityTests(unittest.TestCase):
    def test_original_source_equations_identified_from_actual_symbols(self):
        result=identify_original_panel_labels([
            panel(1,"tan−1"),panel(2,"sin−1"),panel(3,"sec−1")])
        self.assertEqual([x["original_printed_inverse_function_family"]
                          for x in result],["tangent","sine","secant"])
        self.assertTrue(all(x["original_pdf_label_identity_evidenced"] for x in result))
        self.assertTrue(all(not x["existing_slide_bitmap_equation_labels_verified"]
                            for x in result))
    def test_different_source_order_is_read_not_hardcoded(self):
        result=identify_original_panel_labels([
            panel(1,"sec−1"),panel(2,"tan−1"),panel(3,"sin−1")])
        self.assertEqual([x["original_printed_inverse_function_family"]
                          for x in result],["secant","tangent","sine"])
    def test_duplicated_trig_label_fails_closed(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            identify_original_panel_labels([panel(1,"tan−1"),panel(2,"tan−1"),panel(3,"sec−1")])
    def test_missing_equation_fraction_fails_closed(self):
        p=panel(1,"tan−1")
        p["original_printed_tokens"]=[x for x in p["original_printed_tokens"] if x["text"]!="a"]
        with self.assertRaises(FigureIdentityReviewRequired):
            identify_original_panel_labels([p,panel(2,"sin−1"),panel(3,"sec−1")])

    def test_narration_mapping_follows_pdf_labels_not_assumed_order(self):
        from pathlib import Path
        from unittest.mock import patch
        from selenium_pipeline.math_aware_slide5_figure_candidates import audit
        labels={"source_sha256":"a","slides_sha256":"a",
                "panels":[{"graph_index":1,
                           "original_printed_inverse_function_family":"secant",
                           "original_printed_inverse_function_token":"sec−1"},
                          {"graph_index":2,
                           "original_printed_inverse_function_family":"tangent",
                           "original_printed_inverse_function_token":"tan−1"},
                          {"graph_index":3,
                           "original_printed_inverse_function_family":"sine",
                           "original_printed_inverse_function_token":"sin−1"}]}
        graph={"original_pdf_sha256":"a","existing_slides_pdf_sha256":"a",
               "detected_graph_count":3,"three_graph_black_ink_geometry_plausible":True}
        scripted={"script_sha256":"a","slides":[
            {"slide_number":i,
             "proposed_utterances":(
                 [{"proposal_id":"slide5-u1",
                   "verbatim_script_fragment":"The tangent inverse rises"}]
                 if i==5 else [])} for i in range(1,6)]}
        with patch("selenium_pipeline.math_aware_slide5_figure_candidates._sha",
                   return_value="a"),patch(
                "selenium_pipeline.math_aware_slide5_figure_candidates.audit_original_inverse_labels",
                return_value=labels),patch(
                "selenium_pipeline.math_aware_slide5_figure_candidates.audit_real_three_graph_reflow",
                return_value=graph),patch(
                "selenium_pipeline.math_aware_slide5_figure_candidates.propose",
                return_value=scripted),patch(
                "selenium_pipeline.math_aware_slide5_figure_candidates.audit_source_to_slide_inverse_glyphs",
                return_value={"original_source_sha256":"a","existing_slides_sha256":"a",
                    "all_three_source_inverse_operator_glyphs_in_slide_verified":True}):
            result=audit(source=Path("original.pdf"),slides=Path("slide.pdf"),
                         script=Path("script.txt"))
        self.assertEqual(result["utterances"][0]["candidate_ordered_graph_panel"],2)
        self.assertTrue(result["original_source_printed_function_labels_verified"])
        self.assertFalse(result["figure_element_tts_authorized"])

    def test_unknown_function_and_noninverse_not_accepted(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            identify_original_panel_labels([panel(1,"tan"),panel(2,"sin−1"),panel(3,"sec−1")])
