import unittest, tempfile
from pathlib import Path
from selenium_pipeline.figure83_narration_review_packet import build
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

class Figure83ReviewPacketTests(unittest.TestCase):
    def test_requires_separate_new_review_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('source.pdf','slides.pdf','script.txt'):
                (root/name).write_text(name)
            with self.assertRaises(FigureIdentityReviewRequired):
                build(source=root/'source.pdf',slides=root/'slides.pdf',
                      script=root/'script.txt',output=root/'review')
    def test_cannot_replace_existing_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            src=root/'src';src.mkdir()
            for name in ('source.pdf','slides.pdf','script.txt'):
                (src/name).write_text(name)
            dest=root/'review';dest.mkdir()
            with self.assertRaises(FigureIdentityReviewRequired):
                build(source=src/'source.pdf',slides=src/'slides.pdf',
                      script=src/'script.txt',output=dest)
