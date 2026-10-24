"""Independent figure-layout and visible nonblank regression checks."""
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf
from PIL import Image, ImageDraw

from selenium_pipeline.original_figure_raster_preflight import (
    inspect_material_image, inspect_original_slide_figure,
)
from selenium_pipeline.figure_source_identity import _sha


def make_pdf(root,blank=False,material=True):
    root=Path(root)
    with pymupdf.open() as doc:
        page=doc.new_page(width=360,height=270)
        page.insert_text((45,45),"Original right triangle visual example")
        if material:
            image=Image.new("RGB",(100,80),"white")
            if not blank:
                draw=ImageDraw.Draw(image)
                draw.line([(6,70),(90,70),(90,5),(6,70)],
                          fill="black",width=3)
            buf=io.BytesIO()
            image.save(buf,format="PNG")
            page.insert_image(pymupdf.Rect(65,90,165,170),stream=buf.getvalue())
        doc.save(root/"slides.pdf")
    (root/"source.pdf").write_bytes((root/"slides.pdf").read_bytes())
    (root/"script.txt").write_text("Narration source",encoding="utf8")


def stub_job(root):
    r=Path(root)
    return {"source_sha256":_sha(r/"source.pdf"),
            "slides_sha256":_sha(r/"slides.pdf"),
            "script_sha256":_sha(r/"script.txt"),
            "utterance_count":5}


class OriginalFigureQA(unittest.TestCase):
    def test_realistic_visible_raster_is_accepted_structurally_only(self):
        with tempfile.TemporaryDirectory() as d:
            make_pdf(d)
            with patch("selenium_pipeline.original_figure_raster_preflight."
                       "build_review_job",return_value=stub_job(d)):
                r=inspect_original_slide_figure(folder=Path(d),slide=1)
            self.assertEqual(r["material_figure_count"],1)
            self.assertTrue(r["technical_figure_bbox_and_contrast_accepted"])
            self.assertFalse(r["composite_figure_subpanels_independently_mapped"])
            self.assertFalse(r["student_publication_authorized"])
            self.assertFalse(r["independent_academic_consensus_verified"])

    def test_blank_figure_cannot_be_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            make_pdf(d,blank=True)
            with patch("selenium_pipeline.original_figure_raster_preflight."
                       "build_review_job",return_value=stub_job(d)):
                with self.assertRaises(ValueError):
                    inspect_original_slide_figure(folder=Path(d),slide=1)

    def test_material_figure_missing_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            make_pdf(d,material=False)
            with patch("selenium_pipeline.original_figure_raster_preflight."
                       "build_review_job",return_value=stub_job(d)):
                with self.assertRaises(ValueError):
                    inspect_original_slide_figure(folder=Path(d),slide=1)

    def test_clipped_or_distorted_bbox_never_gets_source_approval(self):
        with tempfile.TemporaryDirectory() as d:
            make_pdf(d)
            with pymupdf.open(Path(d)/"slides.pdf") as doc:
                pg=doc[0]
                im=next(x for x in pg.get_image_info() if x["width"]>=48)
                clipped={**im,"bbox":(-10,90,90,170)}
                distorted={**im,"bbox":(60,90,260,170)}
                for candidate in (clipped,distorted):
                    with self.assertRaises(ValueError):
                        inspect_material_image(page=pg,image=candidate)

    def test_original_slide_sha_drift_blocks_raster_check(self):
        with tempfile.TemporaryDirectory() as d:
            make_pdf(d)
            job=stub_job(d)
            (Path(d)/"slides.pdf").write_bytes(b"tampered")
            with patch("selenium_pipeline.original_figure_raster_preflight."
                       "build_review_job",return_value=job):
                with self.assertRaises(ValueError):
                    inspect_original_slide_figure(folder=Path(d),slide=1)

    def test_decorative_tiny_images_do_not_count_as_teaching_figures(self):
        with tempfile.TemporaryDirectory() as d:
            make_pdf(d)
            with pymupdf.open(Path(d)/"slides.pdf") as doc:
                image={"width":6,"height":6,"bbox":(10.,10.,20.,20.)}
                with self.assertRaises(ValueError):
                    inspect_material_image(page=doc[0],image=image)


if __name__=="__main__":
    unittest.main()
