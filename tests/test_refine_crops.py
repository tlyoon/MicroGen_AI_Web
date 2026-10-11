import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.refine_crops import refine

class RefineCropsTest(unittest.TestCase):
    def test_refines_without_publishing(self):
        import json
        import pymupdf
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            doc=pymupdf.open()
            page=doc.new_page()
            page.draw_rect(pymupdf.Rect(100,100,200,200))
            page.insert_text((105,98),"x")
            doc.save(folder/"source.pdf")
            doc.close()
            base=folder/".microgen_figure_candidates"/"drawing_previews"
            base.mkdir(parents=True)
            (base/"proposals.json").write_text(json.dumps({"proposals":[{"reference":"Figure 9.19.png","page":1,"bbox":[100,100,200,200],"preview":"candidate.png"}]}))
            result=refine(folder)
            self.assertEqual(result["verified"],0)
            self.assertEqual(len(result["proposals"]),1)
            self.assertTrue(Path(result["proposals"][0]["preview"]).exists())
            self.assertFalse((folder/"Figure 9.19.png").exists())
