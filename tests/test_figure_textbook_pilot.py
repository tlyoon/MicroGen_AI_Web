"""Read-only authentic-PDF pilot gates; no paid models or publication."""
from __future__ import annotations
import hashlib
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_textbook_pilot import inspect_textbook_figure_pilot

REGION=[40,40,340,140]
PANELS=[[40,40,140,140],[140,40,240,140],[240,40,340,140]]
CAPTION="Figure 8.3 Three original vector field patterns"


class ReadOnlyFigurePilotTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.src=self.root/"source.pdf"
        self.slide=self.root/"slides.pdf"
        self.make_pair()

    def make_pair(self, *, omit_last_label=False, overlay=False):
        with pymupdf.open() as src:
            pg=src.new_page(width=420,height=260)
            for i in range(3):
                if omit_last_label and i==2:
                    continue
                pg.insert_text((55+i*100,65),
                               f"({chr(97+i)})",fontsize=12)
                pg.draw_rect(pymupdf.Rect(75+i*100,85,105+i*100,105),
                             color=(0,0,0),width=1)
            if omit_last_label:
                pg.draw_rect(pymupdf.Rect(275,85,305,105),
                             color=(0,0,0),width=1)
            pg.insert_text((50,158),CAPTION,fontsize=10)
            pix=pg.get_pixmap(matrix=pymupdf.Matrix(2,2),
                   clip=pymupdf.Rect(REGION),
                   colorspace=pymupdf.csRGB,alpha=False)
            src.save(self.src)
        with pymupdf.open() as deck:
            pg=deck.new_page(width=420,height=260)
            pg.insert_image(pymupdf.Rect(REGION),
                            stream=pix.tobytes("png"),
                            keep_proportion=False)
            if overlay:
                pg.insert_text((100,100),"WRONG",fontsize=20)
            pg.insert_text((50,158),CAPTION,fontsize=10)
            deck.save(self.slide)
        self.before=tuple(hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (self.src,self.slide))

    def run_pilot(self,declared=None,**kwargs):
        args=dict(source=self.src,slides=self.slide,source_page=1,
                  slide_page=1,figure_id="8.3",declared=declared)
        args.update(kwargs)
        return inspect_textbook_figure_pilot(**args)

    def proposal(self):
        return dict(source_bbox=REGION,slide_bbox=REGION,
                    panel_boxes=PANELS,panel_ids=["a","b","c"],
                    caption=CAPTION)

    def test_real_pdf_discovery_blocked_without_source_bounding_proof(self):
        evidence=self.run_pilot()
        self.assertEqual(evidence["status"],
                         "PILOT_BLOCKED_MISSING_INDEPENDENT_FIGURE_GEOMETRY")
        self.assertGreaterEqual(evidence["source_vector_paths"],3)
        self.assertEqual(evidence["source_raster_images"],0)
        self.assertGreater(evidence["slide_raster_images"],0)
        self.assertEqual(evidence["source_figure_id_mentions"],1)
        for key in ("tts_or_video_authorized",
                    "figure_panel_completeness_certified",
                    "scientific_semantics_certified",
                    "student_publication_authorized",
                    "academic_review_claimed"):
            self.assertFalse(evidence[key])
        self.assertFalse((self.root/"element_wav").exists())
        self.assertEqual(tuple(hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (self.src,self.slide)),self.before)

    def test_explicit_candidate_still_not_production_approval(self):
        evidence=self.run_pilot(declared=self.proposal())
        self.assertEqual(evidence["status"],
                    "PILOT_TECHNICAL_CANDIDATE_SEMANTIC_QA_BLOCKED")
        self.assertTrue(evidence["figure_region_mapping_verified"])
        self.assertFalse(evidence["student_publication_authorized"])
        self.assertFalse(evidence["tts_or_video_authorized"])
        self.assertFalse(evidence["true_panel_boundary_semantics_certified"])

    def test_missing_original_panel_label_is_blocked(self):
        self.make_pair(omit_last_label=True)
        evidence=self.run_pilot(declared=self.proposal())
        self.assertEqual(evidence["status"],"PILOT_BLOCKED_SOURCE_PANEL_PROOF")
        self.assertFalse(evidence["tts_or_video_authorized"])

    def test_slide_overlay_is_blocked(self):
        self.make_pair(overlay=True)
        evidence=self.run_pilot(declared=self.proposal())
        self.assertEqual(evidence["status"],"PILOT_BLOCKED_SOURCE_PANEL_PROOF")

    def test_invalid_page_and_figure_id_rejected(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            self.run_pilot(source_page=9)
        for id in ("", "8x3", "Figure 8.3", "8.3; rm"):
            with self.subTest(id=id),self.assertRaises(FigureIdentityReviewRequired):
                self.run_pilot(figure_id=id)

    def test_partial_mapping_fields_rejected(self):
        partial=self.proposal()
        del partial["panel_ids"]
        with self.assertRaises(FigureIdentityReviewRequired):
            self.run_pilot(declared=partial)

    def test_source_equals_slide_rejected(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            self.run_pilot(slides=self.src)


if __name__=="__main__":
    unittest.main()
