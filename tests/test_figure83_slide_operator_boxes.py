import unittest
from selenium_pipeline.figure83_slide_inverse_glyph_correspondence import derive_slide_operator_boxes
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

def matrix():
    return [[{"panel_local_top_left_px":[4,10],"template_size_px":[8,9],
              "panel_size_px":[100,80]} for _ in range(3)] for _ in range(3)]
class OriginalGlyphBoundingBoxTests(unittest.TestCase):
    def test_actual_slide_coordinates(self):
        r=derive_slide_operator_boxes(matrix(),[[0,100],[100,200],[200,300]],width=300,height=80)
        self.assertEqual([a["matched_original_glyph_bbox_on_existing_slide_bitmap_px"] for a in r],
                         [[4,10,12,19],[104,10,112,19],[204,10,212,19]])
        self.assertTrue(all(not a["narrated_spoken_word_timing_verified"] for a in r))
    def test_escape_or_wrong_panel_fails_closed(self):
        cases=[([99,10],[8,9],[100,80]),([4,-1],[8,9],[100,80]),
               ([4,10],[8,90],[100,80]),([4,10],[8,9],[99,80])]
        for pos,size,panel in cases:
            x=matrix();x[1][1]["panel_local_top_left_px"]=pos
            x[1][1]["template_size_px"]=size;x[1][1]["panel_size_px"]=panel
            with self.assertRaises(FigureIdentityReviewRequired):
                derive_slide_operator_boxes(x,[[0,100],[100,200],[200,300]],width=300,height=80)
