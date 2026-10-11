import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.caption_locator import locate

class CaptionLocatorTests(unittest.TestCase):
    def test_locates_caption_but_does_not_claim_verified(self):
        import pymupdf
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            doc=pymupdf.open()
            page=doc.new_page()
            page.insert_text((40,80),"Figure 9.16 An illustrative diagram")
            doc.save(folder/"source.pdf")
            doc.close()
            (folder/"slides.tex").write_text(r"\\includegraphics{Figure 9.16.png}",encoding="utf-8")
            report=locate(folder)
            self.assertEqual(report["verified_matches"],0)
            self.assertTrue(report["caption_candidates"])
            self.assertEqual(report["caption_candidates"][0]["page"],1)
