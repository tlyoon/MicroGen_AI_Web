"""Source triangle registration is not scientific figure-panel acceptance."""
import unittest
from PIL import Image,ImageDraw
from selenium_pipeline.original_thomas84_triangle_body_correspondence import (
    foreground,overlap_dice,CASES)

class TriangleBodyReviewTest(unittest.TestCase):
    def test_identical_geometry_has_full_dice(self):
        v=Image.new("RGB",(100,100),"white")
        ImageDraw.Draw(v).line([(10,90),(80,90),(80,10),(10,90)],fill="black",width=3)
        g=foreground(v)
        self.assertAlmostEqual(overlap_dice(g,g),1)
    def test_disjoint_figures_have_zero_overlap(self):
        a=Image.new("RGB",(100,100),"white")
        b=a.copy()
        ImageDraw.Draw(a).rectangle((3,3,12,12),fill="black")
        ImageDraw.Draw(b).rectangle((50,50,70,70),fill="black")
        self.assertEqual(overlap_dice(foreground(a),foreground(b)),0)
    def test_white_background_is_not_figure_match(self):
        g=foreground(Image.new("RGB",(100,100),"white"))
        self.assertEqual(overlap_dice(g,g),0)
    def test_source_triangle_geometry_cases_are_three_distinct_figures(self):
        self.assertEqual([(c["id"],c["page"],c["slide"]) for c in CASES],
                         [("8.4",3,10),("8.5",4,13),("8.6",4,15)])

if __name__=="__main__":
    unittest.main()
