"""No-Send recovery of individually validated rows from a claimed review reply."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline.academic_review_checkpoint import (
    prepare,mark_submission_maybe,record_observation)
from selenium_pipeline.ai_academic_web_review import review_instructions
from selenium_pipeline.source_citation_partial_rescue import (
    salvage,AcademicPartialRecoveryBlocked)

class PartialAcademicReviewNoResendTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.source=self.root/"source"
        self.source.mkdir()
        for n in ("source.pdf","slides.pdf","script.txt"):
            (self.source/n).write_bytes(("Synthetic immutable "+n).encode())
        h=lambda n:hashlib.sha256((self.source/n).read_bytes()).hexdigest()
        self.u=[{
            "id":f"s001.utterance.00{i}",
            "spoken_sha256":hashlib.sha256(str(i).encode()).hexdigest(),
            "spoken_text":f"Original meaning fragment number {i}",
        } for i in (1,2)]
        self.job={
            "status":"SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED",
            "source_sha256":h("source.pdf"),
            "slides_sha256":h("slides.pdf"),
            "script_sha256":h("script.txt"),
            "selected_original_slides":[1],"utterance_count":2,
            "slides":[{
                "slide":1,"visual_targets":[{"id":"s001.text.001",
                                          "bbox_pdf_pt":[1,2,3,4]}],
                "utterances":self.u}],
            "verified_source_quote_candidates_v1":{
                "status":"PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1",
                "source_sha256":h("source.pdf"),
                "slides_sha256":h("slides.pdf"),
                "script_sha256":h("script.txt"),
                "utterances":[{"utterance_id":u["id"],
                                "spoken_sha256":u["spoken_sha256"],
                                "allowed_citations":[]} for u in self.u]},
            "student_publication_authorized":False}
        self.model={
            "status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
            "rows":[{
                "utterance_id":u["id"],
                "spoken_sha256":u["spoken_sha256"],
                "target_id":None,"source_page":None,
                "verbatim_source_quote":None,
                "verdict":"UNRESOLVED" if i==0 else "SUPPORTED",
                "math_explanation":"Scientific explanation that cannot be guessed without source validation."
            } for i,u in enumerate(self.u)]}
        self.checkpoint=self.root/"checkpoint"
        prep={
            "checkpoint":self.checkpoint,
            "original_folder":self.source,
            "request_text":review_instructions(self.job,mode="INITIAL_REVIEW"),
            "source_hashes":{n:h(n) for n in ("source.pdf","slides.pdf","script.txt")},
            "review_mode":"INITIAL_REVIEW",
        }
        state=prepare(**prep)
        mark_submission_maybe(self.checkpoint,
                              expected_fingerprint=state["request_fingerprint"])
        record_observation(
            self.checkpoint,
            raw=json.dumps(self.model,indent=2).replace("\n","\r\n"),
            expected_fingerprint=state["request_fingerprint"])
        self.manifest=self.root/"manifest.json"
        self.manifest.write_text("{}")
        self.job_path=self.root/"job.json"
        self.job_path.write_text(json.dumps(self.job))
        self.dest=self.root/"out.json"

    def _run(self):
        def only_source_validates(*,folder,job,response,mode):
            row=response["rows"][0]
            if row["verdict"]=="SUPPORTED":
                raise ValueError("Invented quote cannot be validated")
            return {"review_count":1,
                    "student_publication_authorized":False,
                    "rows":[row]}
        with patch("selenium_pipeline.source_citation_partial_rescue.inspect_batch",
                   return_value=(self.source,self.job)), \
             patch("selenium_pipeline.source_citation_partial_rescue.validate_model_review",
                   side_effect=only_source_validates):
            return salvage(manifest_path=self.manifest,job_path=self.job_path,
                           checkpoint_dir=self.checkpoint,out=self.dest)

    def test_recovers_only_validated_rows_without_resend(self):
        result=self._run()
        self.assertEqual(result["individually_validated"],1)
        self.assertEqual(result["individually_untrusted"],1)
        self.assertEqual(result["unresolved"],1)
        self.assertEqual(result["supported"],0)
        self.assertFalse(result["full_source_and_math_review_accepted"])
        self.assertEqual(result["new_model_or_tts_requests"],0)
        self.assertTrue(self.dest.is_file())

    def test_changed_source_claimed_response_is_rejected(self):
        original=self.checkpoint/"model_response_untrusted.txt"
        original.write_bytes(original.read_bytes()+b"tamper")
        with self.assertRaises(AcademicPartialRecoveryBlocked):
            self._run()
        self.assertFalse(self.dest.exists())

if __name__=="__main__":
    unittest.main()
