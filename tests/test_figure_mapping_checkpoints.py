"""Fail-closed resumable Gemini figure-page mapping receipts."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from selenium_pipeline.figure_mapping_checkpoints import (
    checkpoint_can_resume,save_checkpoint,
)


class FigurePageCheckpointTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.r=Path(t.name)
        self.source=self.r/"source.pdf"
        self.source.write_bytes(b"source fixed hash")
        self.page=self.r/"pages"/"page_3"
        self.page.mkdir(parents=True)
        (self.page/"page_3.png").write_bytes(b"page content")
        self.crop=self.r/"crops"/"page_3"
        self.crop.mkdir(parents=True)
        (self.crop/"fig_1.png").write_bytes(b"original three-panel figure bytes")
        self.mapped=self.crop/"Figure 2.10.png"
        self.mapped.write_bytes(b"original three-panel figure bytes")
        self.public=self.r/"Figure 2.10.png"
        self.public.write_bytes(b"original three-panel figure bytes")
        (self.page/"page_3_mapping.txt").write_text(
            'fig_1.png : "Figure 2.10" : Figure 2.10.png\n',encoding="utf-8"
        )
        self.transport=self.crop/"gemini_transport_attempts.json"
        self.transport.write_text(json.dumps({
            "mode":"selenium","page":3,
            "attempts":[{"backend":"selenium","attempt":1,"status":"validated"}],
            "completed":True,
        }),encoding="utf-8")

    def test_no_checkpoint_means_no_auto_resume(self):
        self.assertFalse(checkpoint_can_resume(self.r,3))
        target=save_checkpoint(self.r,3)
        self.assertTrue(target.is_file())
        self.assertTrue(checkpoint_can_resume(self.r,3))
        self.assertEqual(save_checkpoint(self.r,3),target)

    def test_original_source_change_invalidates_checkpoint(self):
        save_checkpoint(self.r,3)
        self.source.write_bytes(b"changed source")
        self.assertFalse(checkpoint_can_resume(self.r,3))
        with self.assertRaises(ValueError):
            save_checkpoint(self.r,3)

    def test_page_image_change_invalidates_checkpoint(self):
        save_checkpoint(self.r,3)
        (self.page/"page_3.png").write_bytes(b"new page text and caption")
        self.assertFalse(checkpoint_can_resume(self.r,3))

    def test_mapped_crop_or_original_change_invalidates_checkpoint(self):
        save_checkpoint(self.r,3)
        self.mapped.write_bytes(b"cropped panel (a) only")
        self.assertFalse(checkpoint_can_resume(self.r,3))

    def test_published_root_conflict_invalidates_checkpoint(self):
        save_checkpoint(self.r,3)
        self.public.write_bytes(b"wrong image bytes")
        self.assertFalse(checkpoint_can_resume(self.r,3))

    def test_malformed_or_missing_mappings_are_rejected(self):
        (self.page/"page_3_mapping.txt").write_text(
            "MAPPING_REVIEW_REQUIRED\n",encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError,"malformed"):
            save_checkpoint(self.r,3)

    def test_incomplete_transport_cannot_be_adopted(self):
        self.transport.write_text(json.dumps({
            "mode":"selenium","page":3,
            "attempts":[{"status":"rejected"}],"completed":False
        }),encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"did not validate"):
            save_checkpoint(self.r,3)

    def test_missing_root_copy_blocks_publication_checkpoint(self):
        self.public.unlink()
        with self.assertRaisesRegex(ValueError,"Root publication"):
            save_checkpoint(self.r,3)
        save_checkpoint(self.r,3,copy_to_root=False)
        self.assertTrue(checkpoint_can_resume(self.r,3,copy_to_root=False))
        self.assertFalse(checkpoint_can_resume(self.r,3,copy_to_root=True))

    def test_mapping_change_invalidates_checkpoint(self):
        save_checkpoint(self.r,3)
        (self.page/"page_3_mapping.txt").write_text(
            'fig_1.png : "Other label" : Figure 2.10.png\n',encoding="utf-8"
        )
        self.assertFalse(checkpoint_can_resume(self.r,3))

    def test_new_untracked_extra_crop_blocks_checkpoint(self):
        save_checkpoint(self.r,3)
        (self.crop/"fig_2.png").write_bytes(b"another source crop")
        self.assertFalse(checkpoint_can_resume(self.r,3))

    def test_vendor_does_not_auto_merge_unverified_lettered_panels(self):
        source=(Path(__file__).resolve().parents[1]
                /"selenium_pipeline"/"vendor_template_v2"/"map_and_rename_selenium_v8.py")
        txt=source.read_text(encoding="utf-8")
        self.assertNotIn("merge_lettered_figs_v3.main([])",txt)
        self.assertIn("Automatic lettered-panel merging disabled",txt)

    def test_source_geometry_manifest_is_immutable_resume_dependency(self):
        import hashlib
        import shutil
        from types import SimpleNamespace
        from selenium_pipeline.figure_crop_source_provenance import (
            build_crop_geometry_candidate, save_page_crop_geometry)
        original_crop = self.crop / "fig_1.png"
        page_crop = self.page / original_crop.name
        shutil.copy2(original_crop, page_crop)
        picture = SimpleNamespace(prov=[SimpleNamespace(
            page_no=1, bbox=SimpleNamespace(
                l=10, r=110, t=70, b=20, coord_origin="BOTTOMLEFT"))])
        entry = build_crop_geometry_candidate(
            picture=picture, original_pdf=self.source,
            page_png=self.page / "page_3.png", crop_png=page_crop,
            page_number=3, page_width_pt=200, page_height_pt=150)
        source_manifest = self.page / "page_3_crop_geometry.json"
        save_page_crop_geometry(
            target=source_manifest, source_pdf=self.source,
            page_png=self.page / "page_3.png",
            records=[entry], page_number=3)
        destination_manifest = self.crop / source_manifest.name
        shutil.copy2(source_manifest, destination_manifest)
        checkpoint = save_checkpoint(self.r, 3)
        self.assertTrue(checkpoint_can_resume(self.r, 3))
        record = json.loads(checkpoint.read_text())
        self.assertEqual(
            record["source_geometry_manifest_sha256"],
            hashlib.sha256(source_manifest.read_bytes()).hexdigest())
        before = source_manifest.read_bytes()
        destination_manifest.write_bytes(before + b"tAMPER")
        self.assertFalse(checkpoint_can_resume(self.r, 3))
        with self.assertRaises(ValueError):
            save_checkpoint(self.r, 3)
        destination_manifest.write_bytes(before)
        self.assertTrue(checkpoint_can_resume(self.r, 3))
        source_manifest.unlink()
        self.assertFalse(checkpoint_can_resume(self.r, 3))

    def test_one_sided_geometry_declaration_fails_closed(self):
        (self.page / "page_3_crop_geometry.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "Source geometry manifest"):
            save_checkpoint(self.r, 3)
        self.assertFalse(checkpoint_can_resume(self.r, 3))

    def test_only_int_page_and_only_allowed_root(self):
        self.assertFalse(checkpoint_can_resume(self.r,-1))
        self.assertFalse(checkpoint_can_resume(self.r,1.5))
        with self.assertRaises(ValueError):
            save_checkpoint(self.r,0)


if __name__=="__main__":
    unittest.main()
