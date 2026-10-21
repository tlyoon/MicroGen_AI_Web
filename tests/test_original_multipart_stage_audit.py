import tempfile,unittest
from pathlib import Path
from selenium_pipeline.original_multipart_preview_batch import stage_original_preview_batch
from selenium_pipeline.original_multipart_stage_audit import audit_whole_slide_staging
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_incremental_lecture_sync_queue import make_subchapter

class StagedRealAudioPreviewAuditTests(unittest.TestCase):
    def test_independent_reprobe_original_source_and_encoded_mp4(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t);root=folder/"teaching"
            make_subchapter(root,"8.4")
            stage_original_preview_batch(root=root,subchapters=("8.4",),
                                          destination=folder/"stage")
            audit=audit_whole_slide_staging(root=root,staged=folder/"stage",
                                            names=("8.4",))
            self.assertEqual(audit["total_verified_preview_parts"],1)
            self.assertTrue(audit["all_lecture_parts_technically_present"])
            self.assertFalse(audit["source_semantic_element_sync_verified"])
            self.assertFalse(audit["student_publication_authorized"])
    def test_preview_modification_is_rejected_by_hash_check(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t);root=folder/"teaching"
            make_subchapter(root,"8.5")
            stage_original_preview_batch(root=root,subchapters=("8.5",),
                                          destination=folder/"stage")
            movie=folder/"stage"/"8.5"/"part_01"/"whole_slide_multipart_review.mp4"
            with movie.open("ab") as output:
                output.write(b"mutated")
            with self.assertRaises(FigureIdentityReviewRequired):
                audit_whole_slide_staging(root=root,staged=folder/"stage",
                                           names=("8.5",))
