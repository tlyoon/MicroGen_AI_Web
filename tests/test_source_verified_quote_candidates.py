"""R1: generic citations are physically verified and bound to each source unit."""
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.ai_academic_web_review import (
    build_review_job,review_instructions,validate_model_review)
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.source_verified_quote_candidates import (
    build_verified_source_candidates,verify_witnessed_candidate)

EXPLAIN = ("The candidate passage is physically present; this specific "
           "reasoning must still be independently assessed for mathematics.")


def make_original(root, *, source_text, spoken, slide_text=None):
    f=Path(root)/"source";f.mkdir()
    with pymupdf.open() as pdf:
        pg=pdf.new_page(width=600,height=500)
        pg.insert_text((25,50),source_text,fontsize=11)
        pdf.save(f/"source.pdf")
    with pymupdf.open() as pdf:
        pg=pdf.new_page(width=600,height=500)
        pg.insert_text((25,50),slide_text or spoken,fontsize=11)
        pdf.save(f/"slides.pdf")
    (f/"script.txt").write_text(
        "**Slide 1 [1 sec]:\n"+spoken+"**\n",encoding="utf8")
    return f


class OriginalVerifiedCitations(unittest.TestCase):
    def make(self,root,variant=1):
        if variant==1:
            source="Magnetic flux through a coil depends on the magnetic field direction."
            spoken="Magnetic flux depends on the field direction."
        else:
            source="The gravitational orbit follows the motion of an object around the central mass."
            spoken="A gravitational orbit depends on the central mass."
        return make_original(root,source_text=source,spoken=spoken)

    def reply(self,job,source_row):
        u=job["slides"][0]["utterances"][0]
        target=job["slides"][0]["visual_targets"][0]["id"]
        return {"status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
                "rows":[{
                    "utterance_id":u["id"],
                    "spoken_sha256":u["spoken_sha256"],
                    "target_id":target,
                    "source_page":source_row["source_page"],
                    "verbatim_source_quote":source_row["verbatim_source_quote"],
                    "verdict":"SUPPORTED",
                    "math_explanation":EXPLAIN,
                }]}

    def test_two_distinct_sources_build_and_validate_source_bound_citations(self):
        for variant in (1,2):
            with self.subTest(variant=variant),tempfile.TemporaryDirectory() as t:
                folder=self.make(t,variant=variant)
                j=build_review_job(folder=folder,slide_numbers=[1])
                packet=j["verified_source_quote_candidates_v1"]
                self.assertEqual(packet["status"],
                                 "PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1")
                self.assertFalse(packet["citations_are_scientific_proof"])
                self.assertFalse(packet["all_mathematics_verified"])
                self.assertFalse(packet["student_publication_authorized"])
                self.assertEqual(len(packet["utterances"]),1)
                self.assertTrue(packet["utterances"][0]["allowed_citations"])
                citation=packet["utterances"][0]["allowed_citations"][0]
                self.assertEqual(citation["source_page"],1)
                self.assertEqual(len(citation["source_text_bbox_pdf_pt"]),4)
                self.assertLess(citation["source_text_bbox_pdf_pt"][0],
                                citation["source_text_bbox_pdf_pt"][2])
                self.assertLess(citation["source_text_bbox_pdf_pt"][1],
                                citation["source_text_bbox_pdf_pt"][3])
                result=validate_model_review(
                    folder=folder,job=j,response=self.reply(j,citation),
                    mode="INITIAL_REVIEW")
                self.assertEqual(result["review_count"],1)
                self.assertTrue(result["rows"][0]["exact_textbook_quote_verified"])
                self.assertFalse(result["academic_mathematics_independently_verified"])
                prompt=review_instructions(j,mode="INITIAL_REVIEW")
                self.assertIn("CITE ONLY one exact",prompt)
                self.assertIn(citation["verbatim_source_quote"],prompt)

    def test_exact_source_quote_not_in_speech_specific_candidates_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            folder=self.make(t,variant=1)
            j=build_review_job(folder=folder,slide_numbers=[1])
            citation=j["verified_source_quote_candidates_v1"]["utterances"][0]["allowed_citations"][0]
            fabricated=dict(citation,verbatim_source_quote="The completely fabricated equation is in this source.")
            with self.assertRaises(FigureIdentityReviewRequired):
                validate_model_review(folder=folder,job=j,
                                      response=self.reply(j,fabricated),
                                      mode="INITIAL_REVIEW")

    def test_genuine_but_unlisted_quote_cannot_be_reassigned_to_other_unit(self):
        with tempfile.TemporaryDirectory() as t:
            folder=self.make(t,variant=1)
            j=build_review_job(folder=folder,slide_numbers=[1])
            extra={"source_page":1,
                   "verbatim_source_quote":"through a coil depends on the magnetic field direction."}
            # The words are genuinely in the PDF, but a reviewer may only
            # use the quote belonging to the exact utterance whitelist.
            allowed={(c["source_page"],c["verbatim_source_quote"])
                     for c in j["verified_source_quote_candidates_v1"]
                         ["utterances"][0]["allowed_citations"]}
            self.assertNotIn(
                (extra["source_page"],extra["verbatim_source_quote"]),
                allowed, "Regression must exercise a genuine unlisted citation")
            with self.assertRaises(FigureIdentityReviewRequired):
                validate_model_review(folder=folder,job=j,
                                      response=self.reply(j,extra),
                                      mode="INITIAL_REVIEW")

    def test_source_without_relevant_passage_fails_to_unresolved_not_fabricated(self):
        with tempfile.TemporaryDirectory() as t:
            folder=make_original(
                t,
                source_text="Cloud chamber images record charged particles crossing dense vapor.",
                spoken="The torsion pendulum oscillates at a measured mechanical frequency.")
            j=build_review_job(folder=folder,slide_numbers=[1])
            self.assertEqual(
                j["verified_source_quote_candidates_v1"]["utterances"][0]["allowed_citations"],[])
            unit=j["slides"][0]["utterances"][0]
            unresolved={"status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
                        "rows":[{
                            "utterance_id":unit["id"],
                            "spoken_sha256":unit["spoken_sha256"],
                            "target_id":None,
                            "source_page":None,
                            "verbatim_source_quote":None,
                            "verdict":"UNRESOLVED",
                            "math_explanation":EXPLAIN}]}
            result=validate_model_review(
                folder=folder,job=j,response=unresolved,mode="INITIAL_REVIEW")
            self.assertEqual(result["rows"][0]["verdict"],"UNRESOLVED")
            self.assertFalse(result["rows"][0]["exact_textbook_quote_verified"])
            citation={"source_page":1,
                      "verbatim_source_quote":
                          "Cloud chamber images record charged particles crossing dense vapor."}
            with self.assertRaises(FigureIdentityReviewRequired):
                validate_model_review(folder=folder,job=j,
                                      response=self.reply(j,citation),
                                      mode="INITIAL_REVIEW")

    def test_original_file_changes_fail_packet_before_any_send(self):
        with tempfile.TemporaryDirectory() as t:
            folder=self.make(t)
            j=build_review_job(folder=folder,slide_numbers=[1])
            (folder/"script.txt").write_text("changed")
            with self.assertRaises(FigureIdentityReviewRequired):
                build_verified_source_candidates(folder=folder,job=j)


if __name__ == "__main__":
    unittest.main()
