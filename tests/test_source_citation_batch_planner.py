"""No-model bounded batching when full original quote packets exceed prompt budget."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from selenium_pipeline.source_citation_batch_planner import plan
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.evidence_reuse_contract import file_sha256

class AcademicCitationBatchTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        for name in ["source.pdf","slides.pdf","script.txt"]:
            (self.root/name).write_bytes(b"Original immutable bytes "+name.encode())
        self.spoken=[(n,f"Slide {n} script") for n in range(1,7)]
    def fake_job(self,folder,slide_numbers):
        if len(slide_numbers)>2:
            raise FigureIdentityReviewRequired(
                "Too many source citation candidates for bounded academic prompt")
        return {"selected_original_slides":slide_numbers,
                "source_sha256":file_sha256(self.root/"source.pdf"),
                "slides_sha256":file_sha256(self.root/"slides.pdf"),
                "script_sha256":file_sha256(self.root/"script.txt"),
                "student_publication_authorized":False,
                "verified_source_quote_candidates_v1":{
                    "status":"PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1"},
                "utterance_count":len(slide_numbers)}
    def test_oversized_jobs_shrink_without_model_or_quote_loss(self):
        with patch("selenium_pipeline.runner.check_valid",return_value=True), \
             patch("selenium_pipeline.source_citation_batch_planner.blocks",return_value=self.spoken):
            result=plan(folder=self.root,max_batch=4,job_builder=self.fake_job)
        self.assertEqual(result["status"],
                         "ALL_SOURCE_CITED_REVIEW_JOBS_READY_NOT_DISPATCHED")
        self.assertEqual([x["selected_original_slides"] for x in result["jobs"]],
                         [[1,2],[3,4],[5,6]])
        self.assertEqual(result["model_or_tts_calls"],0)
        self.assertFalse(result["student_publication_authorized"])
    def test_unresolvable_single_slide_stops_without_loop(self):
        def reject_first(folder,slide_numbers):
            if 1 in slide_numbers:
                raise FigureIdentityReviewRequired(
                    "Too many source citation candidates for bounded academic prompt")
            return self.fake_job(folder,slide_numbers)
        with patch("selenium_pipeline.runner.check_valid",return_value=True), \
             patch("selenium_pipeline.source_citation_batch_planner.blocks",return_value=self.spoken):
            result=plan(folder=self.root,max_batch=4,job_builder=reject_first)
        self.assertEqual(result["status"],
                         "PARTIAL_SOURCE_CITED_REVIEW_JOBS_UNRESOLVED_NO_SEND")
        self.assertEqual(result["unresolved"][0]["slide"],1)
        self.assertEqual([n for x in result["jobs"]
                          for n in x["selected_original_slides"]], [2,3,4,5,6])
        self.assertEqual(result["model_or_tts_calls"],0)

if __name__=="__main__":
    unittest.main()
