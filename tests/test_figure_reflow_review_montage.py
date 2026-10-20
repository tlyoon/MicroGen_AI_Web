"""Read-only review montage cannot overwrite original lecture files."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf
from selenium_pipeline.figure_reflow_review_montage import source_slide_plot_montage
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired


class SourceGraphMontageTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.orig=self.root/"lecture"
        self.orig.mkdir()
        self.source=self.orig/"source.pdf"
        self.slides=self.orig/"slides.pdf"
        self.out=self.root/"review"
        with pymupdf.open() as book:
            page=book.new_page(width=200,height=200)
            page.draw_line((30,30),(70,45),color=(0,0,0))
            page.draw_line((30,80),(90,100),color=(0,0,0))
            book.save(self.source)
        with pymupdf.open() as img:
            page=img.new_page(width=300,height=100)
            page.draw_line((20,30),(130,65))
            page.draw_line((170,20),(275,80))
            png=page.get_pixmap(alpha=False).tobytes("png")
        with pymupdf.open() as deck:
            page=deck.new_page(width=400,height=300)
            page.insert_image(pymupdf.Rect(30,60,330,160),stream=png)
            deck.save(self.slides)

    def report(self):
        return {
            "original_pdf_sha256":hashlib.sha256(self.source.read_bytes()).hexdigest(),
            "existing_slides_pdf_sha256":hashlib.sha256(self.slides.read_bytes()).hexdigest(),
            "detected_graph_count":2,
            "three_graph_black_ink_geometry_plausible":True,
            "source_scan_pixel_x_bounds":[30,270],
            "graph_correspondence_evidence":[
                {"source_scan_band_px":[60,160],
                 "slide_bitmap_scan_band_px":[0,145]},
                {"source_scan_band_px":[210,330],
                 "slide_bitmap_scan_band_px":[155,295]},
            ],
        }

    def make(self,*,out=None,report=None):
        with patch("selenium_pipeline.figure_reflow_review_montage."
                   "audit_real_three_graph_reflow",
                   return_value=self.report() if report is None else report):
            return source_slide_plot_montage(
                source=self.source,slides=self.slides,
                source_page=1,slide_page=1,figure_id="8.3",
                output=out or self.out)

    def test_writes_new_manifest_and_exact_source_slide_crops(self):
        before=(self.source.read_bytes(),self.slides.read_bytes())
        receipt=self.make()
        self.assertEqual(receipt["detected_graph_count"],2)
        self.assertFalse(receipt["publication_authorized"])
        self.assertFalse(receipt["actual_axes_and_math_label_correctness_verified"])
        self.assertTrue((self.out/"source_slide_comparison.png").is_file())
        self.assertTrue((self.out/"review_manifest.json").is_file())
        self.assertEqual(before,(self.source.read_bytes(),self.slides.read_bytes()))

    def test_existing_review_directory_never_overwritten(self):
        self.out.mkdir()
        (self.out/"prior.txt").write_text("preserve")
        with self.assertRaises(FigureIdentityReviewRequired):
            self.make()
        self.assertEqual((self.out/"prior.txt").read_text(),"preserve")

    def test_output_cannot_be_inside_original_lecture_folder(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            self.make(out=self.orig/"review")

    def test_stale_or_incomplete_figure_audit_rejected(self):
        forged=self.report()
        forged["original_pdf_sha256"]="0"*64
        with self.assertRaises(FigureIdentityReviewRequired):
            self.make(report=forged)
        self.assertFalse(self.out.exists())
        incomplete=self.report()
        incomplete["graph_correspondence_evidence"]=[]
        with self.assertRaises(FigureIdentityReviewRequired):
            self.make(report=incomplete)
        self.assertFalse(self.out.exists())
