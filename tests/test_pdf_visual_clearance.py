"""Part 1 Figure 2.8 source-panel/text collision regression."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import pymupdf
from PIL import Image

from selenium_pipeline.pdf_visual_clearance import audit_raster_image_text_clearance
from selenium_pipeline.pdf_element_geometry import (
    ElementGeometryError, extract_element_geometry,
)


class RasterFigureClearanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        im = Image.new("RGB", (200, 100), "white")
        self.png = self.folder / "complete_source_panels.png"
        im.save(self.png)
        self.file_count = 0

    def make_pdf(self, text_baseline=169, *, text_x=80,
                 add_picture=True, with_header=False, with_footer=False,
                 with_marker=False):
        self.file_count += 1
        pdf = self.folder / f"sample_{self.file_count}.pdf"
        doc = pymupdf.open()
        page = doc.new_page(width=360, height=260)
        if add_picture:
            page.insert_image(pymupdf.Rect(50, 65, 210, 155),
                              filename=str(self.png))
        if text_baseline is not None:
            page.insert_text((text_x, text_baseline), "Source label explanation",
                             fontsize=12)
        if with_header:
            page.insert_text((80, 20), "Header", fontsize=10)
        if with_footer:
            page.insert_text((80, 255), "Footer", fontsize=10)
        if with_marker:
            page.insert_link({
                "kind": pymupdf.LINK_URI,
                "from": pymupdf.Rect(50,65,210,155),
                "uri": "microgen-element:part_01.s001.fig",
            })
        doc.save(pdf)
        doc.close()
        return pdf

    def test_nearly_touching_figure_and_caption_is_rejected(self):
        issues = audit_raster_image_text_clearance(self.make_pdf(169))
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["page"], 1)
        self.assertLess(issues[0]["gap_pt"], 8.0)

    def test_actual_overlap_is_rejected(self):
        issues = audit_raster_image_text_clearance(self.make_pdf(150))
        self.assertEqual(len(issues), 1)
        self.assertLess(issues[0]["gap_pt"], 0)

    def test_well_separated_caption_and_labels_pass(self):
        self.assertEqual(audit_raster_image_text_clearance(self.make_pdf(190)), [])

    def test_unrelated_text_and_beamer_header_footer_do_not_fail(self):
        self.assertEqual(audit_raster_image_text_clearance(
            self.make_pdf(169,text_x=220,with_header=True,with_footer=True)
        ), [])

    def test_vector_only_page_without_raster_images_still_passes(self):
        self.assertEqual(audit_raster_image_text_clearance(
            self.make_pdf(150,add_picture=False)
        ), [])

    def test_invalid_clearance_configuration_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Invalid min_clearance"):
            audit_raster_image_text_clearance(self.make_pdf(190),
                                              min_clearance_pt=-1)

    def test_geometry_gate_blocks_raster_collisions_before_tts(self):
        path = self.make_pdf(169,with_marker=True)
        board = {
            "schema_version": 1,
            "part_id": "part_01",
            "plan_sha256": "a"*64,
            "slides": [{
                "slide_id": "part_01.s001",
                "title": "A",
                "elements": [{
                    "element_id": "part_01.s001.fig",
                    "kind": "figure",
                    "source_page": 1,
                    "source_concept_ids": ["c1"],
                }],
            }],
            "narration_segments": [{
                "segment_id":"n1", "slide_id":"part_01.s001",
                "element_ids":["part_01.s001.fig"],
                "spoken_text":"This figure.",
                "estimated_duration_s": 2,
            }],
        }
        with self.assertRaisesRegex(ElementGeometryError, "Figure/body text clearance"):
            extract_element_geometry(path,board)


if __name__ == "__main__":
    unittest.main()
