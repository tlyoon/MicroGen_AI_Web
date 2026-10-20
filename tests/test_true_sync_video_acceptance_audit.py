import unittest
from pathlib import Path
from unittest.mock import patch
from selenium_pipeline.true_sync_video_acceptance_audit import inspect
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

class TrueSyncAuditTests(unittest.TestCase):
    def test_preview_pixels_cannot_approve_spoken_sync(self):
        plan={'source_sha256':'a','slides_sha256':'a','original_wav_count':2}
        jobs={'source_sha256':'a','slides_sha256':'a','script_sha256':'a','paid_provider_call_performed':False,'student_publication_authorized':False,'job_count':0,'jobs':[]}
        reviewed={'source_sha256':'a','slides_sha256':'a','student_publication_authorized':False,'audio_to_element_semantic_correspondence_verified':False,'all_events_encoded_pixel_recheck_count':9,'verified_part_count':2}
        with patch('selenium_pipeline.true_sync_video_acceptance_audit._sha',return_value='a'),patch('selenium_pipeline.true_sync_video_acceptance_audit.inspect_original_slide_wav_plan',return_value=plan),patch('selenium_pipeline.true_sync_video_acceptance_audit.prepare',return_value=jobs),patch('selenium_pipeline.true_sync_video_acceptance_audit.verify_full_staged_element_coverage',return_value=reviewed):
            data=inspect(folder=Path('source'),staged_review=Path('review'))
        self.assertEqual(data['actual_staged_visual_events_rechecked'],9)
        self.assertFalse(data['all_visual_elements_highlighted_as_spoken_verified'])
        self.assertFalse(data['student_publication_authorized'])
    def test_tampered_preview_approval_rejected(self):
        with patch('selenium_pipeline.true_sync_video_acceptance_audit._sha',return_value='a'),patch('selenium_pipeline.true_sync_video_acceptance_audit.inspect_original_slide_wav_plan',return_value={'source_sha256':'a','slides_sha256':'a','original_wav_count':1}),patch('selenium_pipeline.true_sync_video_acceptance_audit.prepare',return_value={'source_sha256':'a','slides_sha256':'a','script_sha256':'a','paid_provider_call_performed':False,'student_publication_authorized':True,'job_count':0}):
            with self.assertRaises(FigureIdentityReviewRequired):
                inspect(folder=Path('source'))
