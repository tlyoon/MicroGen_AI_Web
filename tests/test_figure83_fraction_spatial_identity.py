import unittest
from copy import deepcopy
from pathlib import Path
from selenium_pipeline.figure_original_math_labels import audit_original_graph_labels
from selenium_pipeline.figure83_fraction_spatial_identity import disambiguate_original_fraction
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

def real_evidence():
    p=Path(r'G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4')
    return audit_original_graph_labels(source=p/'source.pdf',slides=p/'slides.pdf',
                                      source_page=2,slide_page=5,figure_id='8.3')["panels"]

class SourceFractionSpatialIdentityTests(unittest.TestCase):
    def test_real_source_fraction_assignment(self):
        result=disambiguate_original_fraction(real_evidence())
        self.assertEqual(len(result),3)
        self.assertTrue(all(x["source_fraction_x_over_a_spatially_disambiguated"] for x in result))
        self.assertTrue(all(not x["existing_slide_bitmap_equation_verified"] for x in result))
        self.assertTrue(all(x["source_numerator_x_bbox_pt"][0]>x["source_inverse_operator_bbox_pt"][2]
                            for x in result))
    def test_source_fraction_removed_rejected(self):
        p=real_evidence()
        for i in range(3):
            mutated=deepcopy(p)
            op=next(w for w in mutated[i]["original_printed_tokens"]
                    if w["text"].startswith(("tan","sin","sec")))
            mutated[i]["original_printed_tokens"]=[
                w for w in mutated[i]["original_printed_tokens"]
                if not (w["text"]=="a" and 0<=w["original_bbox_pt"][0]-op["original_bbox_pt"][2]<=6)]
            with self.assertRaises(FigureIdentityReviewRequired):
                disambiguate_original_fraction(mutated)
    def test_duplicate_fraction_rejected(self):
        p=real_evidence()
        token=next(w for w in p[0]["original_printed_tokens"] if
                   w["text"]=="a" and w["original_bbox_pt"][0]<100)
        p[0]["original_printed_tokens"].append(deepcopy(token))
        with self.assertRaises(FigureIdentityReviewRequired):
            disambiguate_original_fraction(p)
    def test_swap_fraction_numerator_with_axis_rejected(self):
        p=real_evidence()
        p[1]["original_printed_tokens"]=[
            w for w in p[1]["original_printed_tokens"]
            if w["text"]!="x" or w["original_bbox_pt"][0]<145]
        with self.assertRaises(FigureIdentityReviewRequired):
            disambiguate_original_fraction(p)
