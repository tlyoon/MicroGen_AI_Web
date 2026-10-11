import json
import tempfile
import unittest
from pathlib import Path
from selenium_pipeline.figure_approval import digest,validate_approval

class FigureApprovalTests(unittest.TestCase):
    def test_requires_explicit_approval_and_unchanged_source(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            (folder/"source.pdf").write_bytes(b"pdf")
            quarantine=folder/".microgen_figure_candidates"
            quarantine.mkdir()
            candidate=quarantine/"preview.png"
            candidate.write_bytes(b"image")
            data={"source_sha256":digest(folder/"source.pdf"),
                  "figures":[{"reference":"Figure 9.19.png","candidate":str(candidate),
                              "sha256":digest(candidate),"reviewed":False}]}
            approval=folder/"review.json"
            approval.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                validate_approval(folder,approval)
            data["figures"][0]["reviewed"]=True
            approval.write_text(json.dumps(data))
            self.assertEqual(len(validate_approval(folder,approval)["approved"]),1)
            candidate.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                validate_approval(folder,approval)
    def test_rejects_external_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            (folder/"source.pdf").write_bytes(b"pdf")
            other=folder/"other.png"
            other.write_bytes(b"image")
            approval=folder/"review.json"
            approval.write_text(json.dumps({"source_sha256":digest(folder/"source.pdf"),
                "figures":[{"reference":"Figure 1.1.png","candidate":str(other),
                            "sha256":digest(other),"reviewed":True}]}))
            with self.assertRaises(ValueError):
                validate_approval(folder,approval)
