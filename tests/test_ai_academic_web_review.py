import tempfile,unittest,hashlib,json
from pathlib import Path
import pymupdf
from selenium_pipeline.ai_academic_web_review import validate_model_review,review_instructions,run_web_review
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_original_packet_evidence_audit import fixture
def job(path):
    p=fixture(path)
    return {"status":"SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED",
            "source_sha256":p["original_source_sha256"],
            "slides_sha256":p["original_slides_sha256"],
            "script_sha256":p["original_script_sha256"],
            "utterance_count":1,"slides":[{"slide":1,
               "visual_targets":[{"id":"s001.text.001","bbox_pdf_pt":[20,15,100,33]}],
               "utterances":[{"id":"s001.utterance.001","spoken_sha256":"f"*64,
                              "spoken_text":"A visible equation."}]}]}
def response(target="s001.text.001",quote="A visible equation",verdict="SUPPORTED"):
    return {"status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
        "rows":[{"utterance_id":"s001.utterance.001",
            "spoken_sha256":"f"*64,"target_id":target,"source_page":1,
            "verbatim_source_quote":quote,"verdict":verdict,
            "math_explanation":"This visible source equation explains the actual supplied original narration exactly."}]}
class AcademicWebJobs(unittest.TestCase):
    def test_source_witnessed_ai_result_requires_real_pdf_quote(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t)/"source";j=job(folder)
            r=validate_model_review(folder=folder,job=j,response=response(),
                    mode="INITIAL_REVIEW")
            self.assertEqual(r["review_count"],1)
            self.assertFalse(r["academic_mathematics_independently_verified"])
            with self.assertRaises(FigureIdentityReviewRequired):
                validate_model_review(folder=folder,job=j,response=response(quote="fabricated textbook text"),
                    mode="INITIAL_REVIEW")
    def test_fake_visual_and_missing_academic_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t)/"source";j=job(folder)
            with self.assertRaises(FigureIdentityReviewRequired):
                validate_model_review(folder=folder,job=j,response=response(target="fake"),
                    mode="INITIAL_REVIEW")
            model=lambda prompt,files:json.dumps(response())
            r=run_web_review(folder=folder,job=j,mode="INITIAL_REVIEW",transport=model)
            self.assertFalse(r["student_publication_authorized"])
