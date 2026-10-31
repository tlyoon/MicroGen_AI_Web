"""Reject shape/figure identity overclaims from raw pixel overlap."""
import unittest
from PIL import Image, ImageDraw
from selenium_pipeline.original_figure82_raster_registration import binary,dice

class TestOriginalFigure82Registration(unittest.TestCase):
    def test_matching_foreground_is_positive_evidence(self):
        frame=Image.new("RGB",(125,41),"white")
        ImageDraw.Draw(frame).line([(12,8),(40,34),(40,8),(12,8)],fill="black",width=2)
        self.assertEqual(dice(binary(frame),binary(frame)),1.0)

    def test_different_geometry_is_not_approved(self):
        a=Image.new("RGB",(125,41),"white")
        b=Image.new("RGB",(125,41),"white")
        ImageDraw.Draw(a).rectangle((4,4,18,19),fill="black")
        ImageDraw.Draw(b).rectangle((80,25,105,35),fill="black")
        self.assertEqual(dice(binary(a),binary(b)),0)

    def test_white_background_does_not_falsely_count_as_match(self):
        blank=Image.new("RGB",(125,41),"white")
        self.assertEqual(dice(binary(blank),binary(blank)),0)

if __name__=="__main__":
    unittest.main()
