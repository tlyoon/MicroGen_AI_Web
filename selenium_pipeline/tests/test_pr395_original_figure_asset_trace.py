"""No accidental acceptance of unlike figure asset or wrong figure placement."""
import unittest
from PIL import Image
from selenium_pipeline.original_thomas84_figure_asset_trace import pixels_equal,EXPECTED

class FigureAssetMatchingTests(unittest.TestCase):
    def test_same_encoded_pixels_are_equal(self):
        a=Image.new("RGB",(60,50),(150,205,230))
        self.assertTrue(pixels_equal(a,a.copy()))
    def test_changed_panel_pixel_is_not_same(self):
        a=Image.new("RGB",(60,50),(150,205,230))
        b=a.copy()
        b.putpixel((30,20),(250,100,100))
        self.assertFalse(pixels_equal(a,b))
    def test_different_size_is_not_same(self):
        self.assertFalse(pixels_equal(Image.new("RGB",(60,50)),
                                      Image.new("RGB",(60,51))))
    def test_expected_figures_cover_real_original_source_slide_placements(self):
        self.assertEqual(EXPECTED,{
            ("8.2",4):1,("8.3",6):2,("8.4",10):3,
            ("8.5",13):4,("8.6",15):4})
    def test_palette_and_rgb_same_pixels_accepted(self):
        a=Image.new("RGB",(30,20),"white")
        self.assertTrue(pixels_equal(a,a.convert("P")))

if __name__=="__main__":
    unittest.main()
