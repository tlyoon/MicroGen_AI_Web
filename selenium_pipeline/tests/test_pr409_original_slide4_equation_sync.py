"""Source math integrity and adjacent equation row isolation."""
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
from selenium_pipeline.original_thomas84_slide4_three_equation_sync import (
    count_source_equation_side_border,TRIG,TIMED_SENTENCES)
from selenium_pipeline.original_thomas84_equation_provenance import match_line

class SourceSlide4IndependentMathSyncTests(unittest.TestCase):
    def test_three_distinct_source_timed_math_functions(self):
        self.assertEqual(TRIG,("tangent","sine","secant"))
        self.assertEqual(TIMED_SENTENCES,(2,3,4))

    def test_algebraic_operator_sign_corruption_fails(self):
        source="a2 - x2 = a2 - a2 sin2 u = a2(1 - sin2 u) = a2 cos2 u."
        self.assertEqual(len(match_line(
            "a2 −x2 = a2 cos2 θ.",[[source]],slide=4)),1)
        self.assertFalse(match_line(
            "a2 +x2 = a2 cos2 θ.",[[source]],slide=4))
        self.assertFalse(match_line(
            "a2 −x2 = a2 sin2 θ.",[[source]],slide=4))

    def test_adjacent_math_equations_do_not_share_highlight_probes(self):
        rect1=[32.727,81.746,237.162,96.614]
        rect2=[32.727,98.143,235.374,113.152]
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"encoded_like.png"
            image=Image.new("RGB",(726,544),(250,250,250))
            d=ImageDraw.Draw(image)
            x0,y0,x1,y1=rect1
            d.rectangle((int(x0*2)-4,int(y0*2)-1,
                         int(x1*2)+4,int(y1*2)+1),
                        outline=(255,240,0),width=4)
            image.save(path)
            self.assertEqual(count_source_equation_side_border(path,rect1),8)
            self.assertEqual(count_source_equation_side_border(path,rect2),0)

    def test_missing_highlight_never_looks_active(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"blank.png"
            Image.new("RGB",(726,544),(250,250,250)).save(path)
            self.assertEqual(count_source_equation_side_border(
                path,[32.727,114.681,237.162,129.69]),0)

if __name__=="__main__":
    unittest.main()
