import unittest
from selenium_pipeline.figure83_original_equation_components import inspect_original_equations
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

def panel(i,words):
    return {"graph_index":i,"original_printed_tokens":[
        {"text":w,"original_bbox_pt":[j*10,2,j*10+5,12]}
        for j,w in enumerate(words)]}
def good():
    return [panel(i,["u","x","a","u","=",
                    name,"x","a","0"]) for i,name in
                    enumerate(["tan−1","sin−1","sec−1"],1)]
class OriginalEquationCandidatesTests(unittest.TestCase):
    def test_duplicate_axis_labels_not_falsely_approved(self):
        r=inspect_original_equations(good())
        self.assertEqual(len(r),3)
        self.assertEqual(len(r[0]["original_equation_and_axis_token_candidates"]["u"]),2)
        self.assertFalse(r[0]["fraction_x_over_a_disambiguated_from_axis_labels"])
    def test_missing_or_duplicated_inverse_rejected(self):
        for words in (["u","=","x","a"],["u","=","x","a","tan−1","sin−1"]):
            p=good();p[0]=panel(1,words)
            with self.assertRaises(FigureIdentityReviewRequired):
                inspect_original_equations(p)
    def test_invalid_original_coordinates_rejected(self):
        p=good();p[1]["original_printed_tokens"][0]["original_bbox_pt"]=[0,0,float("nan"),3]
        with self.assertRaises(FigureIdentityReviewRequired):
            inspect_original_equations(p)
