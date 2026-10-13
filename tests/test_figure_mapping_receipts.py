"""Figure stage acceptance uses verified mappings, not Figure* filename prefixes."""
from pathlib import Path
import hashlib
import tempfile
import unittest
from selenium_pipeline.runner import valid

class FigureReceiptValidation(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.work = Path(self.t.name)
        self.page = self.work / "pages" / "page_9"
        self.crop = self.work / "crops" / "page_9"
        self.page.mkdir(parents=True)
        self.crop.mkdir(parents=True)
        (self.page / "page_9.png").write_bytes(b"page")
        (self.crop / "page_9.png").write_bytes(b"page")
        (self.crop / "fig_1.png").write_bytes(b"image-one")
        (self.crop / "fig_2.png").write_bytes(b"image-two")
        self.names = ["graph of y equals 1.png","graph of y equals 2.png"]
        for i, name in enumerate(self.names,1):
            blob = (self.crop / f"fig_{i}.png").read_bytes()
            (self.crop / name).write_bytes(blob)
            (self.work / name).write_bytes(blob)
        self.record = self.page/"page_9_mapping.txt"
        self.record.write_text(
          "\n".join(f'fig_{i}.png : "Unlabeled image" : {name}'
                    for i,name in enumerate(self.names,1)),encoding="utf-8")

    def test_descriptive_names_are_valid_when_mappings_match_bytes(self):
        self.assertTrue(valid("figures",self.work))
    def test_mapping_receipt_missing_is_rejected(self):
        self.record.unlink()
        self.assertFalse(valid("figures",self.work))
    def test_missing_copied_image_is_rejected(self):
        (self.work/self.names[0]).unlink()
        self.assertFalse(valid("figures",self.work))
    def test_modified_image_is_rejected(self):
        (self.work/self.names[0]).write_bytes(b"corruption")
        self.assertFalse(valid("figures",self.work))
    def test_incomplete_mapping_is_rejected(self):
        self.record.write_text(f'fig_1.png : "Unlabeled image" : {self.names[0]}')
        self.assertFalse(valid("figures",self.work))
    def test_unsafe_traversal_mapping_is_rejected(self):
        self.record.write_text('fig_1.png : "test" : ../bad.png')
        self.assertFalse(valid("figures",self.work))
    def test_no_actual_crops_is_valid(self):
        for f in list(self.crop.glob("fig_*.png")):
            f.unlink()
        for f in list(self.crop.glob("graph*.png")):
            f.unlink()
        self.assertTrue(valid("figures",self.work))


if __name__ == "__main__":
    unittest.main()
