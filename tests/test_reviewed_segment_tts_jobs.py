import unittest
from pathlib import Path
from unittest.mock import patch
from selenium_pipeline.reviewed_segment_tts_jobs import prepare

class ReviewedSegmentJobTests(unittest.TestCase):
    def test_unreviewed_source_creates_no_billable_jobs(self):
        check={'original_source_sha256':'a','original_slides_sha256':'a','original_script_sha256':'a','paid_tts_execution_authorized':False,'element_mapping_prerequisite_passed':False}
        with patch('selenium_pipeline.reviewed_segment_tts_jobs._sha',return_value='a'),patch('selenium_pipeline.reviewed_segment_tts_jobs.preflight',return_value=check):
            r=prepare(source=Path('s'),slides=Path('d'),script=Path('t'))
        self.assertEqual(r['job_count'],0)
        self.assertFalse(r['paid_provider_call_performed'])
        self.assertFalse(r['student_publication_authorized'])
