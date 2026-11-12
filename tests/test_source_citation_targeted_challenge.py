"""No-resend targeted academic challenge from a genuinely new source quotation."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.academic_review_checkpoint import (
    prepare, mark_submission_maybe, record_observation)
from selenium_pipeline.ai_academic_web_review import (
    build_review_job, review_instructions)
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.pdf_text_source_span_witness import prove_source_quote_occurrence
from selenium_pipeline.source_citation_targeted_challenge import (
    prepare_targeted_challenge)


class NewEvidenceChallengeTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.folder=self.root/"original"/"6.4"
        self.folder.mkdir(parents=True)
        self.source=self.folder/"source.pdf"
        self.slides=self.folder/"slides.pdf"
        self.script=self.folder/"script.txt"
        self.first="A sphere falling through a liquid feels an upward resistive force."
        self.second="The magnitude of the force depends on the velocity of the sphere."
        with pymupdf.open() as pdf:
            p=pdf.new_page(width=650,height=450)
            p.insert_text((45,100),self.first,fontsize=11)
            p.insert_text((45,145),self.second,fontsize=11)
            pdf.save(self.source)
        with pymupdf.open() as pdf:
            p=pdf.new_page(width=650,height=450)
            p.insert_text((45,100),"Velocity and resistance describe linear drag.",
                          fontsize=11)
            pdf.save(self.slides)
        self.script.write_text(
            "**Slide 1 [13 sec]:\n"
            "The sphere experiences drag. The force changes with its speed.",
            encoding="utf8")
        job=build_review_job(folder=self.folder,slide_numbers=[1])
        # The old bounded quote list contained only an initial source line.
        self.assertEqual(len(job["slides"][0]["utterances"]),2)
        originals=job["verified_source_quote_candidates_v1"]["utterances"]
        proof_first=prove_source_quote_occurrence(
            source_pdf=self.source,expected_sha256=job["source_sha256"],
            page_number=1,verbatim_quote=self.first)
        proof_second=prove_source_quote_occurrence(
            source_pdf=self.source,expected_sha256=job["source_sha256"],
            page_number=1,verbatim_quote=self.second)
        self.quote_one={
            "source_page":1,"verbatim_source_quote":self.first,
            "quote_sha256":proof_first["quote_sha256"],
            "source_text_bbox_pdf_pt":[45,75,550,105]}
        self.quote_two={
            "source_page":1,"verbatim_source_quote":self.second,
            "quote_sha256":proof_second["quote_sha256"],
            "source_text_bbox_pdf_pt":[45,125,550,150]}
        for row in originals:
            row["allowed_citations"]=[self.quote_one]
        self.job_path=self.root/"frozen_original_job.json"
        self.job_path.write_text(json.dumps(job),encoding="utf8")
        self.checkpoint=self.root/"claimed_original_window"
        source_hashes={
            "source.pdf":job["source_sha256"],
            "slides.pdf":job["slides_sha256"],
            "script.txt":job["script_sha256"]}
        state=prepare(checkpoint=self.checkpoint,original_folder=self.folder,
                      request_text=review_instructions(job,mode="INITIAL_REVIEW"),
                      source_hashes=source_hashes,review_mode="INITIAL_REVIEW")
        mark_submission_maybe(self.checkpoint,
                              expected_fingerprint=state["request_fingerprint"])
        replies=[{
            "utterance_id":u["id"],"spoken_sha256":u["spoken_sha256"],
            "target_id":None,"source_page":None,"verbatim_source_quote":None,
            "verdict":"UNRESOLVED",
            "math_explanation":"The initial source quote does not establish this claim.",
        } for u in job["slides"][0]["utterances"]]
        record_observation(
            self.checkpoint,
            raw=json.dumps({"status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
                            "rows":replies}),
            expected_fingerprint=state["request_fingerprint"])
        supplemental=copy.deepcopy(job["verified_source_quote_candidates_v1"])
        for row in supplemental["utterances"]:
            row["allowed_citations"]=[self.quote_two]
        self.latest=self.root/"new_physically_verified_quotes.json"
        self.latest.write_text(json.dumps(supplemental),encoding="utf8")
        self.job=job

    def run_plan(self):
        return prepare_targeted_challenge(
            original_job=self.job_path,
            original_checkpoint=self.checkpoint,
            new_source_quotes=self.latest)

    def test_only_original_unresolved_units_with_new_quotes_enter_fresh_challenge(self):
        frozen=[p.read_bytes() for p in (
            self.source,self.slides,self.script,self.job_path,
            self.checkpoint/"model_response_untrusted.txt")]
        obj=self.run_plan()
        self.assertEqual(obj["included_original_unresolved_units"],2)
        new_job=obj["source_job"]
        self.assertEqual(new_job["utterance_count"],2)
        self.assertEqual(new_job["verified_source_quote_candidates_v1"]
                         ["utterances"][0]["allowed_citations"][0]
                         ["verbatim_source_quote"],self.second)
        self.assertTrue(new_job["targeted_independent_challenge_no_original_replay"])
        self.assertFalse(new_job["student_publication_authorized"])
        self.assertFalse(obj["new_model_request_attempted"])
        self.assertFalse(obj["academic_mathematics_independently_verified"])
        self.assertEqual(frozen,[p.read_bytes() for p in (
            self.source,self.slides,self.script,self.job_path,
            self.checkpoint/"model_response_untrusted.txt")])

    def test_no_new_citation_is_not_a_justification_to_repeat_original_request(self):
        same=copy.deepcopy(self.job["verified_source_quote_candidates_v1"])
        self.latest.write_text(json.dumps(same),encoding="utf8")
        with self.assertRaises(FigureIdentityReviewRequired):
            self.run_plan()

    def test_forged_source_quote_is_not_accepted_as_new_evidence(self):
        bogus=json.loads(self.latest.read_text("utf8"))
        bogus["utterances"][0]["allowed_citations"][0][
            "verbatim_source_quote"]="Not an original physics textbook quotation."
        self.latest.write_text(json.dumps(bogus),encoding="utf8")
        with self.assertRaises(FigureIdentityReviewRequired):
            self.run_plan()

    def test_corrupted_saved_model_response_is_never_used_as_a_retry_pretext(self):
        file=self.checkpoint/"model_response_untrusted.txt"
        file.write_text("{}",encoding="utf8")
        with self.assertRaises(FigureIdentityReviewRequired):
            self.run_plan()


if __name__=="__main__":
    unittest.main()
