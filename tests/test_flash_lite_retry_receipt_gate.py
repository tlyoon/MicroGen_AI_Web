import unittest
from selenium_pipeline.flash_lite_retry_receipt_gate import inspect_primary_tts_attempts
from selenium_pipeline.incremental_chunk_tts_requests import DEFAULT_MODEL,DEFAULT_VOICE
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
class RetryProof(unittest.TestCase):
    def setUp(self):
        self.j={"job_id":"unit_123456","spoken_text_sha256":"a"*64}
    def event(self,i,voice=DEFAULT_VOICE):
        return {"job_id":self.j["job_id"],"spoken_text_sha256":"a"*64,
                "model":DEFAULT_MODEL,"voice":voice,"attempt_number":i,
                "execution_id":"execution-123-"+str(i),
                "result":"OBSERVED_FAILURE","provider_receipt_attached":True}
    def test_only_three_actual_failures_open_fallback_review_not_bill(self):
        for n in (0,1,2):
            self.assertFalse(inspect_primary_tts_attempts(job=self.j,
                attempts=[self.event(i) for i in range(1,n+1)])["may_consider_cloud_fallback"])
        r=inspect_primary_tts_attempts(job=self.j,
            attempts=[self.event(i) for i in range(1,4)])
        self.assertTrue(r["may_consider_cloud_fallback"])
        self.assertFalse(r["cloud_fallback_execution_authorized"])
    def test_wrong_voice_and_duplicate_receipts_rejected(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            inspect_primary_tts_attempts(job=self.j,attempts=[self.event(1,voice="Corey")])
        e=self.event(1)
        with self.assertRaises(FigureIdentityReviewRequired):
            inspect_primary_tts_attempts(job=self.j,attempts=[e,e])
