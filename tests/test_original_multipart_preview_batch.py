import tempfile,unittest
from pathlib import Path
from selenium_pipeline.original_multipart_preview_batch import stage_original_preview_batch
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_incremental_lecture_sync_queue import make_subchapter

class OriginalWholeSlideBatchTests(unittest.TestCase):
    def test_synthetic_independent_valid_and_missing_chapter(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);original=root/"teaching"
            make_subchapter(original,"8.4")
            result=stage_original_preview_batch(root=original,
                subchapters=("8.4","8.5"),destination=root/"review")
            self.assertEqual(result["completed_review_only_subchapters"],1)
            self.assertEqual(result["subchapters"][0]["original_audio_part_count"],1)
            self.assertEqual(result["subchapters"][1]["status"],
                             "SOURCE_SUBCHAPTER_BLOCKED_INDEPENDENTLY")
            self.assertTrue((root/"review"/"8_4_receipt.json").exists())
            self.assertFalse(result["production_media_approved"])
            with self.assertRaises(FigureIdentityReviewRequired):
                stage_original_preview_batch(root=original,
                    subchapters=("8.4",),destination=root/"review")
    def test_out_of_range_second_part_reports_unprocessed_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);root=base/"teaching"
            make_subchapter(root,"8.6")
            report=stage_original_preview_batch(root=root,subchapters=("8.6",),
                destination=base/"second_only",start_part=2,max_parts_per_subchapter=1)
            self.assertEqual(report["subchapters"][0]["parts"],[])
            self.assertEqual(report["subchapters"][0]["status"],
                             "PARTIAL_OR_BLOCKED_TECHNICAL_PREVIEW")
    def test_invalid_names_and_original_destination_fail(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);original=root/"teaching"
            make_subchapter(original,"8.4")
            with self.assertRaises(FigureIdentityReviewRequired):
                stage_original_preview_batch(root=original,
                    subchapters=("../8.4",),destination=root/"r")
            with self.assertRaises(FigureIdentityReviewRequired):
                stage_original_preview_batch(root=original,
                    subchapters=("8.4",),destination=original/"r")
