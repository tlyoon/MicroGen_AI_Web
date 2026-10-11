import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.pdf_image_candidates import extract_candidates

class ImageCandidatesTest(unittest.TestCase):
    def test_embedded_image_is_unverified(self):
        import pymupdf
        from PIL import Image
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            png=root/"sample.png"
            Image.new("RGB",(80,80),"white").save(png)
            doc=pymupdf.open()
            page=doc.new_page()
            page.insert_image(pymupdf.Rect(10,10,90,90),filename=str(png))
            doc.save(root/"source.pdf")
            doc.close()
            result=extract_candidates(root)
            self.assertEqual(len(result["candidates"]),1)
            self.assertEqual(result["candidates"][0]["match_status"],"unverified")
            self.assertEqual(result["verified_matches"],0)
    def test_no_image_pdf(self):
        import pymupdf
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            doc=pymupdf.open()
            doc.new_page()
            doc.save(root/"source.pdf")
            doc.close()
            self.assertEqual(extract_candidates(root)["candidates"],[])
