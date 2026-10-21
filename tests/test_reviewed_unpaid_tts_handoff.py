import tempfile,unittest
from pathlib import Path
from selenium_pipeline.reviewed_unpaid_tts_handoff import stage_reviewed_unpaid_audio_jobs
from selenium_pipeline.source_review_packet_bridge import export_review_packet
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_incremental_lecture_sync_queue import make_subchapter

class ReviewedUnpaidAudioJobsTests(unittest.TestCase):
    def test_unreviewed_originals_issue_zero_paid_jobs(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);folder=make_subchapter(root/"original","8.4")
            p=export_review_packet(folder=folder,output=root/"review.json")
            jobs=stage_reviewed_unpaid_audio_jobs(folder=folder,packet=p,
                                                   destination=root/"unpaid_jobs.json")
            self.assertEqual(jobs["physical_audio_chunks_generated"],0)
            self.assertEqual(jobs["candidate_tts_jobs"]["job_count"],0)
            self.assertEqual(jobs["unresolved_utterances"],p["utterance_count"])
            self.assertFalse(jobs["paid_tts_execution_authorized"])
            self.assertTrue((root/"unpaid_jobs.json").is_file())
    def test_false_attestation_cannot_turn_into_paid_job(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);folder=make_subchapter(root/"original","8.5")
            p=export_review_packet(folder=folder,output=root/"review.json")
            p["review_items"][0]["review_target_id"]="s001.text.001"
            p["review_items"][0]["reviewer_attestation"]=True
            p["review_items"][0]["reviewer_id"]="untrusted-pretend"
            with self.assertRaises(FigureIdentityReviewRequired):
                stage_reviewed_unpaid_audio_jobs(folder=folder,packet=p)
