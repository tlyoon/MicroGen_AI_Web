import unittest
from selenium_pipeline.figure_original_math_labels import classify_original_panel_words
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
class OriginalMathLabelsTests(unittest.TestCase):
    def test_source_word_regions_are_independent_and_never_claim_slide_labels(self):
        words=[(10,10,20,16,"tan⁻¹"),(10,110,20,116,"sin⁻¹"),(10,210,20,216,"sec⁻¹")]
        res=classify_original_panel_words(words=words,
             bands=[[0,150],[300,450],[600,750]],source_x=[20,80])
        self.assertEqual([p["original_printed_tokens"][0]["text"] for p in res["panels"]],
                         ["tan⁻¹","sin⁻¹","sec⁻¹"])
        self.assertFalse(res["original_slide_labels_equivalent"])
        self.assertFalse(res["publication_authorized"])
    def test_missing_original_label_remains_unverified_not_invented(self):
        res=classify_original_panel_words(words=[],
            bands=[[0,100],[200,300]],source_x=[0,100])
        self.assertEqual([p["original_word_count"] for p in res["panels"]],[0,0])
        self.assertFalse(res["full_graph_axes_verified"])
    def test_invalid_source_geometry_rejected(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            classify_original_panel_words(words=[(1,float("nan"),2,3,"u")],
                bands=[[0,100],[100,200]],source_x=[0,100])
