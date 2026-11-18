"""Fail-closed source-page duplicate refusal detector — zero new Gemini Send."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline.evidence_reuse_contract import file_sha256
from selenium_pipeline.original_multisource_recovery_campaign import _new_atomic
from selenium_pipeline.figure_duplicate_page_presend import (
    block_duplicate_page_send, inspect_prior_identical_refusal,
    DuplicateOriginalPageSendBlocked)


class PageDuplicatePresendTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        env = patch.dict(os.environ, {"LOCALAPPDATA": str(self.base)})
        env.start()
        self.addCleanup(env.stop)
        self.registry = self.base / "trial_registry"
        self.registry.mkdir()
        self.old, self.old_work = self.make_trial("previous_failed", "1.3",
                                                  b"%PDF-1.7\nfirst source", 3)
        self.current, self.current_work = self.make_trial("fresh_1_4", "1.4",
                                                          b"%PDF-1.7\ndifferent source", 1)
        self.result_path = self.old / "figures_attempt_result.json"
        _new_atomic(self.result_path, {
            "schema_version": 1,
            "source_section": "1.3",
            "status": "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY",
            "original_source_sha256": file_sha256(self.old_work / "source.pdf"),
        })
        _new_atomic(self.old / "figures_transport_triage.json", {
            "owned_browser_send_registered": True,
            "registered_browser_send_count_in_stage_log": 1,
            "terminal_result_sha256": file_sha256(self.result_path),
            "original_submission_resend_authorized": False,
        })
        (self.old_work / "pages/page_3/page_3_mapping.txt").write_text(
            "MAPPING_REVIEW_REQUIRED\n", encoding="utf-8")

    def make_trial(self, label, section, data, page):
        trial = self.registry / label
        work = trial / "source_tree" / "1" / section / ".microgen_work"
        work.mkdir(parents=True)
        source = work / "source.pdf"
        source.write_bytes(data)
        staged = work.parent / "source.pdf"
        staged.write_bytes(data)
        _new_atomic(trial / "fresh_trial_contract.json", {
            "status": "FRESH_ORIGINAL_SOURCE_WINDOWS_IMMUTABLE_TRIAL",
            "source_sha256": file_sha256(source),
            "staged_source_path": str(staged),
            "student_publication_authorized": False,
        })
        page_dir = work / "pages" / f"page_{page}"
        page_dir.mkdir(parents=True)
        (page_dir / f"page_{page}.png").write_bytes(b"identical page raster")
        crop_dir = work / "crops" / f"page_{page}"
        crop_dir.mkdir(parents=True)
        (crop_dir / "fig_4.png").write_bytes(b"identical source crop A")
        (crop_dir / "fig_5.png").write_bytes(b"identical source crop B")
        return trial, work

    def inspect(self):
        with patch("selenium_pipeline.figure_duplicate_page_presend._render_digest",
                   return_value="a" * 64):
            return inspect_prior_identical_refusal(
                workspace=self.current_work, page_number=1)

    def test_exact_historical_refusal_blocks_duplicate_without_send(self):
        out = self.inspect()
        self.assertEqual(out["status"],
                         "PREVIOUS_IDENTICAL_SOURCE_PAGE_GEMINI_REFUSAL_NO_RESEND")
        self.assertEqual(out["prior_source_page"], 3)
        self.assertEqual(out["new_model_sends"], 0)
        self.assertFalse(out["figure_mapping_accepted"])
        with patch("selenium_pipeline.figure_duplicate_page_presend._render_digest",
                   return_value="a" * 64):
            with self.assertRaises(DuplicateOriginalPageSendBlocked):
                block_duplicate_page_send(workspace=self.current_work, page_number=1)

    def test_same_pixels_with_renumbered_crops_still_blocks(self):
        # Crop numbering can change across different overlapping source PDFs.
        folder = self.current_work / "crops/page_1"
        (folder / "fig_4.png").rename(folder / "fig_17.png")
        (folder / "fig_5.png").rename(folder / "fig_18.png")
        self.assertEqual(self.inspect()["status"],
                         "PREVIOUS_IDENTICAL_SOURCE_PAGE_GEMINI_REFUSAL_NO_RESEND")

    def test_vendor_worker_checks_before_any_model_submission(self):
        import inspect
        from pathlib import Path
        vendor = (Path(__file__).resolve().parents[1] / "selenium_pipeline"
                  / "vendor_template_v2" / "map_and_rename_selenium_v8.py")
        source = vendor.read_text(encoding="utf-8")
        self.assertIn("block_duplicate_page_send(", source)
        self.assertLess(source.index("duplicate_probe = block_duplicate_page_send("),
                        source.index("map_and_rename_single_step(\n                            client,"))

    def test_different_crop_does_not_reuse_refusal(self):
        (self.current_work / "crops/page_1/fig_5.png").write_bytes(b"different")
        self.assertEqual(
            self.inspect()["status"], "NO_VERIFIED_IDENTICAL_REFUSAL_IN_SCOPED_REGISTRY")

    def test_unowned_refusal_does_not_block(self):
        self.result_path.unlink()
        _new_atomic(self.result_path, {
            "schema_version": 1, "source_section": "1.3",
            "status": "FIGURES_ATTEMPT_FAILED_NO_AUTO_RETRY",
            "original_source_sha256": file_sha256(self.old_work / "source.pdf"),
            "different": True,
        })
        self.assertEqual(
            self.inspect()["status"], "NO_VERIFIED_IDENTICAL_REFUSAL_IN_SCOPED_REGISTRY")

    def test_previous_accepted_mapping_does_not_block(self):
        (self.old_work / "pages/page_3/page_3_mapping.txt").write_text(
            'fig_4.png : "Figure 1.6" : Figure 1.6.png\n', encoding="utf-8")
        self.assertEqual(
            self.inspect()["status"], "NO_VERIFIED_IDENTICAL_REFUSAL_IN_SCOPED_REGISTRY")

    def test_distinct_source_must_not_be_same_subchapter(self):
        self.assertNotEqual(file_sha256(self.old_work / "source.pdf"),
                            file_sha256(self.current_work / "source.pdf"))


if __name__ == "__main__":
    unittest.main()
