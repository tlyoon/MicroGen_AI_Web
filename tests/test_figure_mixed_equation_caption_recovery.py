"""Source-grounded mixed equation/photo caption recovery, no model resend."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import pymupdf

from selenium_pipeline.figure_mixed_equation_caption_recovery import (
    recover_mixed_source_equation_photo, MixedSourceMappingNotProven)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MixedSourceEquationPhotoTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / "source.pdf"
        self.page = self.root / "page_1.png"
        self.crops = self.root / "crops"
        self.crops.mkdir()
        self.manifest = self.crops / "page_1_crop_geometry.json"
        # Native PDF embedded photo and a separate source text equation:
        # no OCR or outside textbook knowledge.
        from PIL import Image
        import io
        picture = Image.new("RGB", (110, 90), (120, 170, 200))
        stream = io.BytesIO()
        picture.save(stream, format="PNG")
        source = pymupdf.open()
        p = source.new_page(width=612, height=783)
        for k in range(9):
            p.insert_text((45, 80+k*23),
                          "Textbook selection and verified source wording "
                          f"number {k} moves through an example.", fontsize=10)
        p.insert_text((260, 434), "12.0 m/s * 60 s/min * 1 km/1000m = 0.72 km/min")
        p.insert_image(pymupdf.Rect(383, 460, 540, 621),
                       stream=stream.getvalue())
        p.insert_text((384, 638),
                      "Figure 1.6 The speedometer of a car in physical units",
                      fontsize=10)
        source.save(self.source)
        source.close()
        self.page.write_bytes(b"original raster page image")
        self.c4 = self.crops / "fig_4.png"
        self.c5 = self.crops / "fig_5.png"
        self.c4.write_bytes(b"equation crop original bytes")
        self.c5.write_bytes(b"photograph crop original bytes")
        self.write_geometry()

    def write_geometry(self, *, reverse=False):
        rows = [
            ("fig_4.png", [259, 424, 560, 447]),
            ("fig_5.png", [381, 458, 542, 624]),
        ]
        if reverse:
            rows.reverse()
        entry = []
        for name, box in rows:
            entry.append({
                "schema_version": 1,
                "status": "DOCLING_SINGLE_SOURCE_RECT_CANDIDATE",
                "source_pdf_sha256": _sha(self.source),
                "source_page": 1, "page_image_sha256": _sha(self.page),
                "source_page_size_pt": [612, 783],
                "bbox_source_pdf_top_left_pt": box,
                "crop_file": name, "crop_sha256": _sha(self.crops / name),
                "source_crop_pixel_correspondence_verified": False,
                "original_caption_and_panel_semantics_verified": False,
                "automatic_composite_or_publication_authorized": False,
            })
        self.manifest.write_text(json.dumps({
            "schema_version": 1,
            "status": "SOURCE_DECLARED_CROP_GEOMETRY_CANDIDATES_NOT_VERIFIED",
            "page_number": 1, "crop_count": 2,
            "original_source_pdf_sha256": _sha(self.source),
            "page_image_sha256": _sha(self.page),
            "source_crop_pixel_correspondence_verified": False,
            "figure_composite_layout_certified": False,
            "student_publication_authorized": False,
            "crops": entry,
        }))

    def recover(self, response="MAPPING_REVIEW_REQUIRED"):
        return recover_mixed_source_equation_photo(
            response=response, source_pdf=self.source, page_png=self.page,
            crops_dir=self.crops, geometry_manifest=self.manifest)

    def test_only_photo_gets_author_printed_figure_caption(self):
        rows, evidence = self.recover()
        self.assertEqual(rows, [
            ("fig_4.png", "Unlabeled source equation",
             "Unlabeled source equation page_1 fig_4.png"),
            ("fig_5.png", "Figure 1.6", "Figure 1.6.png")])
        self.assertFalse(evidence["student_publication_authorized"])
        self.assertFalse(evidence["independent_scientific_and_diagram_semantics_verified"])
        self.assertEqual(evidence["new_model_sends"], 0)
        self.assertEqual(evidence["printed_figure_id"], "1.6")

    def test_crop_order_does_not_change_correct_unique_assignment(self):
        self.write_geometry(reverse=True)
        rows, _ = self.recover()
        self.assertEqual({x[0]: x[1] for x in rows},
                         {"fig_4.png": "Unlabeled source equation",
                          "fig_5.png": "Figure 1.6"})

    def test_tampered_geometry_or_crop_rejected(self):
        self.c5.write_bytes(b"changed")
        with self.assertRaises(MixedSourceMappingNotProven):
            self.recover()
        self.write_geometry()
        data = json.loads(self.manifest.read_text())
        data["crops"][1]["bbox_source_pdf_top_left_pt"] = [10, 10, 50, 50]
        self.manifest.write_text(json.dumps(data))
        with self.assertRaises(MixedSourceMappingNotProven):
            self.recover()

    def test_no_false_acceptance_for_unrelated_model_or_two_photos(self):
        with self.assertRaises(MixedSourceMappingNotProven):
            self.recover("Figure 1.6")
        data = json.loads(self.manifest.read_text())
        data["crops"][0]["bbox_source_pdf_top_left_pt"] = [385, 462, 540, 620]
        self.manifest.write_text(json.dumps(data))
        with self.assertRaises(MixedSourceMappingNotProven):
            self.recover()

    def test_vendor_integrated_without_unbounded_retry(self):
        vendor = (Path(__file__).resolve().parents[1] / "selenium_pipeline"
                  / "vendor_template_v2" / "map_and_rename_selenium_v8.py")
        code = vendor.read_text(encoding="utf8")
        self.assertIn("recover_mixed_source_equation_photo(", code)
        self.assertIn('page_png.stem + "_mixed_source_caption_evidence.json"', code)
        self.assertIn('f.write(txt + "\\n")', code)


if __name__ == "__main__":
    unittest.main()
