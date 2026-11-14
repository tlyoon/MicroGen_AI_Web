"""Regression: plural narration retrieves actual singular textbook relations.

The author-written question and original publisher may differ by harmless
English inflection; exact source quotes, PDF geometry and SHA never may.
This test never calls Gemini, TTS, or treats search match as physics proof.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from selenium_pipeline.ai_academic_web_review import build_review_job
from selenium_pipeline.figure_source_identity import _sha, FigureIdentityReviewRequired
from selenium_pipeline.pdf_text_source_span_witness import prove_source_quote_occurrence
from selenium_pipeline.source_verified_quote_candidates import (
    _retrieval_lexeme, _content_pairs, _terms,
    verify_witnessed_candidate,
)


class InflectionSourceQuoteRecoveryTests(unittest.TestCase):
    def test_regular_scientific_plural_search_only(self):
        pairs={
            "speeds":"speed",
            "constants":"constant",
            "spheres":"sphere",
            "velocities":"velocity",
            "masses":"mass",
            "force":"force",
            "plus":"plus",
            "minus":"minus",
            "analysis":"analysis",
            "physics":"physic",
        }
        self.assertEqual({a:_retrieval_lexeme(a) for a in pairs},pairs)
        self.assertIn(("terminal","speed"),
                      _content_pairs("terminal speeds and time constants"))
        self.assertIn(("time","constant"),
                      _content_pairs("terminal speeds and time constants"))
        self.assertEqual(_terms("speeds"),_terms("speed"))
        self.assertNotEqual(_terms("minus"),_terms("plus"))

    def _make(self,root:Path)->Path:
        lecture=root/"course"
        lecture.mkdir()
        with pymupdf.open() as doc:
            page=doc.new_page(width=610,height=500)
            page.insert_text((40,75),
                "Table 1 reports terminal speeds for balls falling through air.")
            page=doc.new_page(width=610,height=500)
            page.insert_text((40,76),
                "The sphere moving in oil approaches a terminal speed.")
            page.insert_text((40,112),
                "For this sphere the time constant depends on its mass.")
            doc.save(lecture/"source.pdf")
        with pymupdf.open() as doc:
            page=doc.new_page(width=610,height=500)
            page.insert_text((40,80),
                "Compare terminal speeds and time constants of two spheres.")
            doc.save(lecture/"slides.pdf")
        (lecture/"script.txt").write_text(
            "**Slide 1 [10 sec]:\n"
            "Compare terminal speeds and time constants of two spheres.**\n",
            encoding="utf8")
        return lecture

    def test_real_pdf_selects_cooccurring_technical_terms_not_distractor(self):
        with tempfile.TemporaryDirectory() as t:
            lecture=self._make(Path(t))
            before={x:_sha(lecture/x)
                    for x in ("source.pdf","slides.pdf","script.txt")}
            with patch("selenium_pipeline.series_gemini._browser_request",
                       side_effect=AssertionError("model request forbidden")):
                job=build_review_job(folder=lecture,slide_numbers=[1])
            packet=job["verified_source_quote_candidates_v1"]
            self.assertFalse(packet["all_mathematics_verified"])
            self.assertFalse(packet["citations_are_scientific_proof"])
            self.assertFalse(packet["student_publication_authorized"])
            row=packet["utterances"][0]
            self.assertTrue(row["allowed_citations"])
            self.assertEqual(row["allowed_citations"][0]["source_page"],2)
            for candidate in row["allowed_citations"]:
                proof=prove_source_quote_occurrence(
                    source_pdf=lecture/"source.pdf",
                    expected_sha256=before["source.pdf"],
                    page_number=candidate["source_page"],
                    verbatim_quote=candidate["verbatim_source_quote"])
                self.assertEqual(candidate["quote_sha256"],proof["quote_sha256"])
            unit=job["slides"][0]["utterances"][0]
            forged={"source_page":1,
                    "verbatim_source_quote":
                    "This equation was not printed in the real source."}
            with self.assertRaises(FigureIdentityReviewRequired):
                verify_witnessed_candidate(job=job,utterance=unit,guess=forged,
                                           source_pdf=lecture/"source.pdf")
            self.assertEqual(before,{x:_sha(lecture/x)for x in before})

    def test_real_serway_review_question_recovers_math_and_skydiver_pages(self):
        root=Path.home()/"AppData"/"Local"/"MicroGen_AI_Web_Checkpoints"
        lecture=(root/
            "20261112_PR528_G2_SERWAY6_4_NARRATION_SOURCE_REUSE_V7"/
            "source_tree"/"6"/"6.4")
        if not (lecture/"source.pdf").is_file():
            self.skipTest("Authentic source only on Dell-115")
        before={x:_sha(lecture/x)for x in
                ("source.pdf","slides.pdf","script.txt")}
        with patch("selenium_pipeline.series_gemini._browser_request",
                   side_effect=AssertionError("Do not repeat consumed model Send")):
            job=build_review_job(folder=lecture,slide_numbers=[14])
        rows={row["utterance_id"]:row for row in
              job["verified_source_quote_candidates_v1"]["utterances"]}
        for uid,page in (("s014.utterance.003",3),
                         ("s014.utterance.004",5)):
            allowed=rows[uid]["allowed_citations"]
            self.assertTrue(allowed,uid)
            self.assertEqual(allowed[0]["source_page"],page)
            proof=prove_source_quote_occurrence(
                source_pdf=lecture/"source.pdf",
                expected_sha256=before["source.pdf"],
                page_number=allowed[0]["source_page"],
                verbatim_quote=allowed[0]["verbatim_source_quote"])
            self.assertEqual(proof["quote_sha256"],
                             allowed[0]["quote_sha256"])
        self.assertFalse(
            job["verified_source_quote_candidates_v1"]["all_mathematics_verified"])
        self.assertFalse(job["student_publication_authorized"])
        self.assertEqual(before,{x:_sha(lecture/x)for x in before})


if __name__=="__main__":
    unittest.main()
