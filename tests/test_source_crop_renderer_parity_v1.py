"""Cross-PyMuPDF source crop tolerance without accepting actual figure edits."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from PIL import Image,ImageDraw
from selenium_pipeline.source_crop_renderer_parity_v1 import verified_renderer_parity


class SourceCropRendererParityTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.original=Image.new("RGB",(128,128),(255,255,255))
        draw=ImageDraw.Draw(self.original)
        draw.rectangle((11,15,110,99),outline=(21,24,35),width=2)
        draw.text((20,42),"Figure 8.2",fill=(0,0,0))
        self.source=self.root/"source.png"
        self.stored=self.root/"recorded.png"
        self.original.save(self.source)
        self.original.save(self.stored)
    def parity(self):
        return verified_renderer_parity(
            reconstructed=self.source,ledger_png=self.stored)
    def test_exact_source_png_is_accepted(self):
        self.assertEqual(self.parity()["max_channel_difference"],0)
    def test_small_antialiasing_differences_are_accepted(self):
        altered=self.original.copy()
        for n in range(10):
            altered.putpixel((13+n,16),(27,30,41))
        altered.save(self.stored)
        self.assertEqual(self.parity()["status"],
                         "SAME_SOURCE_CROP_RENDERER_PARITY_VERIFIED")
    def test_missing_black_figure_label_is_rejected(self):
        altered=self.original.copy()
        ImageDraw.Draw(altered).rectangle((19,40,95,56),fill="white")
        altered.save(self.stored)
        with self.assertRaisesRegex(ValueError,"exceeds"):
            self.parity()
    def test_changed_panel_or_large_overlay_is_rejected(self):
        altered=self.original.copy()
        ImageDraw.Draw(altered).rectangle((26,22,85,77),fill=(235,239,242))
        altered.save(self.stored)
        with self.assertRaises(ValueError):
            self.parity()
    def test_localized_high_contrast_pixel_is_rejected(self):
        altered=self.original.copy()
        altered.putpixel((60,60),(0,0,0))
        altered.save(self.stored)
        with self.assertRaises(ValueError):
            self.parity()
    def test_widespread_low_difference_cannot_pass(self):
        altered=Image.new("RGB",(128,128),(251,250,248))
        altered.save(self.stored)
        with self.assertRaises(ValueError):
            self.parity()
    def test_wrong_crop_geometry_rejected(self):
        self.original.crop((1,1,125,127)).save(self.stored)
        with self.assertRaisesRegex(ValueError,"geometry"):
            self.parity()
    def test_appended_png_data_fails_even_when_pixels_equal(self):
        with self.stored.open("ab") as f:
            f.write(b"forged provenance")
        with self.assertRaisesRegex(ValueError,"intact"):
            self.parity()

    def test_non_png_cannot_attest_pdf_provenance(self):
        self.original.save(self.root/"stored.jpg",format="JPEG")
        with self.assertRaises(ValueError):
            verified_renderer_parity(
                reconstructed=self.source,ledger_png=self.root/"stored.jpg")

if __name__=="__main__":
    unittest.main()
