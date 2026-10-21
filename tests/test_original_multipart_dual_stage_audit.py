import tempfile,unittest
from pathlib import Path
from selenium_pipeline.original_multipart_dual_stage_audit import audit_two_part_preview_sets
from selenium_pipeline.original_multipart_preview_batch import stage_original_preview_batch
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_incremental_lecture_sync_queue import make_subchapter

class DualStageAuditTests(unittest.TestCase):
    def test_reused_original_part_does_not_fake_complete_two_part_preview(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/"source"
            make_subchapter(source,"8.4")
            stage_original_preview_batch(root=source,subchapters=("8.4",),
                                          destination=root/"stageA")
            stage_original_preview_batch(root=source,subchapters=("8.4",),
                                          destination=root/"stageB")
            with self.assertRaises(FigureIdentityReviewRequired):
                audit_two_part_preview_sets(root=source,first_stage=root/"stageA",
                                             second_stage=root/"stageB",names=("8.4",))
    def test_same_stage_folder_cannot_count_twice(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with self.assertRaises(FigureIdentityReviewRequired):
                audit_two_part_preview_sets(root=root,first_stage=root/"stage",
                    second_stage=root/"stage",names=("8.4",))
