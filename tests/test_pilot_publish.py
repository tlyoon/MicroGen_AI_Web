import json
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.pilot_publish import repair
from selenium_pipeline.figure_approval import digest

class PilotPublishSafetyTests(unittest.TestCase):
    def test_rejects_unreviewed_without_changing_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"source.pdf").write_bytes(b"source")
            (root/"slides.pdf").write_bytes(b"original slides")
            (root/"slides.tex").write_text("original tex")
            quarantine=root/".microgen_figure_candidates"
            quarantine.mkdir()
            image=quarantine/"candidate.png"
            image.write_bytes(b"image")
            approval=quarantine/"review.json"
            approval.write_text(json.dumps({"source_sha256":digest(root/"source.pdf"),
                "figures":[{"reference":"Figure 1.1.png","candidate":str(image),
                            "sha256":digest(image),"reviewed":False}]}))
            with self.assertRaises(ValueError):
                repair(root,approval)
            self.assertEqual((root/"slides.pdf").read_bytes(),b"original slides")
            self.assertFalse((root/"Figure 1.1.png").exists())
    def test_rejects_empty_approval(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"source.pdf").write_bytes(b"source")
            approval=root/"approval.json"
            approval.write_text(json.dumps({"source_sha256":digest(root/"source.pdf"),"figures":[]}))
            with self.assertRaises(ValueError):
                repair(root,approval)
