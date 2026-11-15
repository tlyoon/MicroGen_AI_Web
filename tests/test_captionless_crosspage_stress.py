"""Regression: captionless local recovery must be page-agnostic and fail closed."""
import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.figure_uncaptioned_source_recovery import (
    recover_source_uncaptioned_crop, UncaptionedSourceNotProven,
)
from selenium_pipeline.figures_failed_source_only_resume import recover as recover_failed_trial


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CaptionlessCrossPageStress(unittest.TestCase):
    def test_failed_trial_uses_discovered_page_for_all_evidence_names(self):
        source = inspect.getsource(recover_failed_trial)
        for suffix in (
            "mapping.original_refusal.txt",
            "uncaptioned_model_reply.raw.txt",
            "uncaptioned_source_evidence.json",
        ):
            self.assertIn('f"page_{page_number}_' + suffix + '"', source)
        self.assertNotIn('page_6_', source)

    def test_source_only_different_pages_and_tampering(self):
        import fitz
        for target in (1, 7, 12):
            with self.subTest(page=target), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                pdfpath = root / "source.pdf"
                pdf = fitz.open()
                for i in range(target):
                    page = pdf.new_page(width=612, height=783)
                    if i == target - 1:
                        for line in range(24):
                            page.insert_text(
                                (72, 78 + line * 13),
                                "A source paragraph provides selectable physics context for graphics.",
                                fontsize=9,
                            )
                pdf.save(pdfpath)
                pdf.close()
                png = root / f"page_{target}.png"
                png.write_bytes(b"source page raster placeholder")
                crops = root / "crops"
                crops.mkdir()
                crop = crops / "fig_1.png"
                crop.write_bytes(b"isolated original cropped diagram")
                manifest = crops / f"page_{target}_crop_geometry.json"
                item = {
                    "schema_version": 1,
                    "status": "DOCLING_SINGLE_SOURCE_RECT_CANDIDATE",
                    "source_pdf_sha256": sha(pdfpath),
                    "page_image_sha256": sha(png),
                    "source_page": target,
                    "crop_file": crop.name,
                    "crop_sha256": sha(crop),
                    "bbox_source_pdf_top_left_pt": [480., 480., 570., 560.],
                    "source_page_size_pt": [612., 783.],
                    "source_crop_pixel_correspondence_verified": False,
                    "original_caption_and_panel_semantics_verified": False,
                    "automatic_composite_or_publication_authorized": False,
                }
                manifest.write_text(json.dumps({
                    "schema_version": 1,
                    "status": "SOURCE_DECLARED_CROP_GEOMETRY_CANDIDATES_NOT_VERIFIED",
                    "original_source_pdf_sha256": sha(pdfpath),
                    "page_image_sha256": sha(png),
                    "page_number": target,
                    "crop_count": 1,
                    "crops": [item],
                    "source_crop_pixel_correspondence_verified": False,
                    "figure_composite_layout_certified": False,
                    "student_publication_authorized": False,
                }), encoding="utf-8")
                def resolve():
                    return recover_source_uncaptioned_crop(
                        response="MAPPING_REVIEW_REQUIRED",
                        source_pdf=pdfpath, page_png=png,
                        crops_dir=crops, geometry_manifest=manifest,
                    )
                rows, receipt = resolve()
                self.assertEqual(rows[0][2], f"Unlabeled source graphic page_{target} fig_1.png")
                self.assertEqual(receipt["source_page_number"], target)
                self.assertEqual(receipt["new_model_sends"], 0)
                self.assertFalse(receipt["student_publication_authorized"])
                crop.write_bytes(b"tampered")
                with self.assertRaises(UncaptionedSourceNotProven):
                    resolve()
