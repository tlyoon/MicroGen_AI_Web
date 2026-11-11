"""Offline source-locked crop geometry evidence and immutable metadata guards."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from selenium_pipeline.figure_crop_source_provenance import (
    build_crop_geometry_candidate, declared_picture_rect, save_page_crop_geometry,
)


def picture(*, page_no=1, origin="BOTTOMLEFT", coords=(10, 90, 75, 20)):
    l, r, t, b = coords
    return SimpleNamespace(prov=[SimpleNamespace(
        page_no=page_no,
        bbox=SimpleNamespace(l=l, r=r, t=t, b=b, coord_origin=origin))])


class SourceLockedCropGeometryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "source.pdf"
        self.source.write_bytes(b"immutable original pdf in fixture")
        self.page = self.root / "pages" / "page_2"
        self.page.mkdir(parents=True)
        self.page_png = self.page / "page_2.png"
        self.page_png.write_bytes(b"immutable original page pixels")
        self.crop = self.page / "fig_1.png"
        self.crop.write_bytes(b"actual cropped pixels")
        self.manifest = self.page / "page_2_crop_geometry.json"

    def candidate(self, item=None):
        return build_crop_geometry_candidate(
            picture=item if item is not None else picture(),
            original_pdf=self.source, page_png=self.page_png,
            crop_png=self.crop, page_number=2, page_width_pt=100,
            page_height_pt=200)

    def test_bottomleft_normalizes_to_top_left_pdf_rectangle(self):
        self.assertEqual(declared_picture_rect(
            item=picture(), page_width_pt=100, page_height_pt=200),
            [10, 125, 90, 180])
        item = self.candidate()
        self.assertEqual(item["bbox_source_pdf_top_left_pt"], [10, 125, 90, 180])
        self.assertEqual(item["status"], "DOCLING_SINGLE_SOURCE_RECT_CANDIDATE")
        self.assertEqual(item["source_page"], 2)
        self.assertEqual(item["crop_sha256"], hashlib.sha256(
            self.crop.read_bytes()).hexdigest())
        self.assertFalse(item["source_crop_pixel_correspondence_verified"])
        self.assertFalse(item["original_caption_and_panel_semantics_verified"])

    def test_top_left_origin_and_invalid_geometry_fail_closed(self):
        self.assertEqual(declared_picture_rect(item=picture(
            origin="TOPLEFT", coords=(1, 50, 5, 100)),
            page_width_pt=100, page_height_pt=200), [1, 5, 50, 100])
        for item in (
            picture(page_no=2),
            picture(origin="UNRECOGNIZED"),
            picture(coords=(-1, 90, 70, 20)),
            picture(coords=(10, 101, 70, 20)),
            SimpleNamespace(prov=[]),
            SimpleNamespace(prov=[picture().prov[0], picture().prov[0]]),
            SimpleNamespace(prov=[SimpleNamespace(page_no=1, bbox=None)]),
        ):
            self.assertIsNone(declared_picture_rect(
                item=item, page_width_pt=100, page_height_pt=200))
        self.assertIsNone(declared_picture_rect(
            item=picture(), page_width_pt="not a number", page_height_pt=200))

    def test_manifest_is_sha_bound_immutable_and_not_production_approval(self):
        entry = self.candidate()
        report = save_page_crop_geometry(
            target=self.manifest, source_pdf=self.source,
            page_png=self.page_png, records=[entry], page_number=2)
        self.assertEqual(report["crop_count"], 1)
        self.assertTrue(report["all_crops_have_declared_bbox"])
        self.assertFalse(report["figure_composite_layout_certified"])
        self.assertFalse(report["student_publication_authorized"])
        self.assertEqual(json.loads(self.manifest.read_text()), report)
        previous = self.manifest.read_bytes()
        with self.assertRaisesRegex(ValueError, "already exists"):
            save_page_crop_geometry(
                target=self.manifest, source_pdf=self.source,
                page_png=self.page_png, records=[entry], page_number=2)
        self.assertEqual(self.manifest.read_bytes(), previous)

    def test_missing_provenance_preserved_as_unknown_not_auto_filled(self):
        item = self.candidate(SimpleNamespace(prov=[]))
        self.assertEqual(item["status"], "SOURCE_CROP_BBOX_UNVERIFIED")
        self.assertIsNone(item["bbox_source_pdf_top_left_pt"])
        result = save_page_crop_geometry(
            target=self.manifest, source_pdf=self.source,
            page_png=self.page_png, records=[item], page_number=2)
        self.assertFalse(result["all_crops_have_declared_bbox"])

    def test_source_page_or_crop_byte_mutation_rejected_before_manifest(self):
        entry = self.candidate()
        for path in (self.source, self.page_png, self.crop):
            before = path.read_bytes()
            path.write_bytes(b"tampered source identity")
            with self.assertRaises(ValueError):
                save_page_crop_geometry(
                    target=self.manifest, source_pdf=self.source,
                    page_png=self.page_png, records=[entry], page_number=2)
            self.assertFalse(self.manifest.exists())
            path.write_bytes(before)

    def test_untrusted_claims_and_duplicate_crop_names_block_promotion(self):
        correct = self.candidate()
        variants = []
        for attr, val in [
            ("original_caption_and_panel_semantics_verified", True),
            ("source_crop_pixel_correspondence_verified", True),
            ("automatic_composite_or_publication_authorized", True),
            ("crop_file", "../fig_1.png"),
            ("crop_file", "different.png"),
            ("status", "APPROVED"),
            ("source_page", 99),
        ]:
            changed = copy.deepcopy(correct)
            changed[attr] = val
            variants.append([changed])
        variants.append([correct, correct])
        for entries in variants:
            with self.assertRaises(ValueError):
                save_page_crop_geometry(
                    target=self.manifest, source_pdf=self.source,
                    page_png=self.page_png, records=entries, page_number=2)
            self.assertFalse(self.manifest.exists())


if __name__ == "__main__":
    unittest.main()
