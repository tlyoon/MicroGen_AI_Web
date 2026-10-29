import tempfile, unittest,json
from pathlib import Path
import pymupdf
from selenium_pipeline.ai_chunked_original_challenge import (
    prepare_independent_page_prompts,run_independent_chunked_source_challenge)
from selenium_pipeline.ai_academic_web_review import validate_model_review
from test_ai_compact_original_challenge import TextExcerptReview

class ChunkedPhysicalPages(unittest.TestCase):
 def setup(self,t):
    return TextExcerptReview().setup(t,extra_source_pages=2)
 def test_complete_original_pages_without_truncation(self):
    with tempfile.TemporaryDirectory() as t:
        root,f,q,j,proposal=self.setup(t)
        plan=prepare_independent_page_prompts(folder=f,slide=1)
        self.assertEqual(plan["page_count"],3)
        with pymupdf.open(f/"source.pdf") as book:
            for k,page in enumerate(plan["pages"]):
                self.assertIn(book[k].get_text(sort=True),page["request"])
                self.assertLessEqual(page["character_count"],8500)
        self.assertFalse(plan["page_image_semantics_reviewed"])
 def test_distinct_complete_page_ack_and_validated_math_model_output(self):
    with tempfile.TemporaryDirectory() as t:
        root,f,q,j,reply=self.setup(t)
        reply["rows"][0]["math_explanation"]="This mathematically independent source check compares original visible and spoken equations."
        plan=prepare_independent_page_prompts(folder=f,slide=1)
        calls=[]
        def send(prompt):
            i=len(calls); calls.append(prompt)
            if i<plan["page_count"]:
                row=plan["pages"][i]
                return json.dumps({"page":row["physical_page"],
                    "page_text_sha256":row["source_text_sha256"],"received":True})
            return json.dumps(reply)
        report=run_independent_chunked_source_challenge(
            folder=f,slide=1,send_text=send,receipt=root/"journal.jsonl")
        self.assertEqual(report["status"],"SOURCE_WITNESSED_AI_MATH_REVIEW_ONE_PASS")
        self.assertEqual(len(calls),4)
        self.assertTrue((root/"journal.jsonl").is_file())
        self.assertFalse(report["academic_mathematics_independently_verified"])
 def test_wrong_page_hash_fails_closed_and_no_math_request(self):
    with tempfile.TemporaryDirectory() as t:
        root,f,q,j,reply=self.setup(t)
        with self.assertRaises(Exception):
            run_independent_chunked_source_challenge(
                folder=f,slide=1,send_text=lambda _:json.dumps({
                    "page":1,"page_text_sha256":"0"*64,"received":True}),
                receipt=root/"no_math.jsonl")
        self.assertEqual(len((root/"no_math.jsonl").read_text().splitlines()),1)
