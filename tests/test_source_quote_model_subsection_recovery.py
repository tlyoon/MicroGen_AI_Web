"""Physical section-aware academic citation recovery, no model Send.

Exercise the exact two real-world TTS claims previously returned
UNRESOLVED because of quoted baseball / pre-derivation text. The improved
candidate search must find relevant original source scope, not assume truth.
"""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import pymupdf

from selenium_pipeline.figure_source_identity import _sha, FigureIdentityReviewRequired
from selenium_pipeline.pdf_text_source_span_witness import prove_source_quote_occurrence
from selenium_pipeline.source_verified_quote_candidates import (
    _source_model_sections, _slide_model_title,
    _source_example_sections, _slide_example_title,
    _same_physical_quote_region, build_verified_source_candidates,
)
from selenium_pipeline.ai_academic_web_review import build_review_job


class SourceSubsectionCitationTests(unittest.TestCase):
    def test_source_model_boundaries_are_physical_and_sha_locked(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"source.pdf"
            with pymupdf.open() as doc:
                page=doc.new_page()
                page.insert_text((40,100),"Model 1: Linear resistive force")
                page.insert_text((40,135),"A sphere released from rest initially has a zero drag force.")
                page.insert_text((40,300),"Model 2: Quadratic resistive force")
                page.insert_text((40,330),"A baseball moving with high speed has a quadratic drag.")
                doc.save(source)
            before=_sha(source)
            model=_source_model_sections(source,before)
            self.assertEqual(set(model),{1,2})
            self.assertLess(model[1][1],model[1][3])
            with self.assertRaises(FigureIdentityReviewRequired):
                _source_model_sections(source,"0"*64)
            self.assertEqual(before,_sha(source))

    def test_numbered_example_boundary_is_physical_not_keyword_similarity(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"source.pdf"
            with pymupdf.open() as doc:
                page=doc.new_page(width=580,height=760)
                page.insert_text((45,140),"Example 6.8 A Sphere Released in Oil")
                page.insert_text((45,200),"Time constant follows the terminal speed calculation.")
                page.insert_text((45,450),"Conceptual Example 6.9 A Skysurfer")
                page.insert_text((45,515),"The surfer air drag changes after falling.")
                doc.save(source)
            proof=_source_example_sections(source,_sha(source))
            self.assertEqual(set(proof),{(6,8),(6,9)})
            self.assertLess(proof[(6,8)][1],proof[(6,8)][3])
            self.assertEqual(proof[(6,8)][2:],(1,proof[(6,9)][1]))

    def test_same_physical_text_slice_does_not_consume_both_citation_slots(self):
        a=(3,(45,300,500,390))
        b=(3,(55,310,490,372))
        c=(3,(45,420,500,500))
        d=(4,(55,310,490,372))
        self.assertTrue(_same_physical_quote_region(a,b))
        self.assertFalse(_same_physical_quote_region(a,c))
        self.assertFalse(_same_physical_quote_region(a,d))

    def test_real_serway_example6_8_never_cites_example6_9(self):
        home=Path.home()/"AppData"/"Local"/"MicroGen_AI_Web_Checkpoints"
        folder=(home/"20261112_PR528_G2_SERWAY6_4_NARRATION_SOURCE_REUSE_V7"
                /"source_tree"/"6"/"6.4")
        if not (folder/"source.pdf").is_file():
            self.skipTest("Real original source only available on Dell-115")
        original={name:_sha(folder/name)
                  for name in ("source.pdf","slides.pdf","script.txt")}
        job=build_review_job(folder=folder,slide_numbers=[6,7])
        self.assertEqual(_slide_example_title(job["slides"][1]),(6,8))
        examples=_source_example_sections(folder/"source.pdf",original["source.pdf"])
        self.assertIn((6,8),examples)
        self.assertIn((6,9),examples)
        citations={x["utterance_id"]:x for x in
                   job["verified_source_quote_candidates_v1"]["utterances"]}
        for i in range(3,8):
            uid=f"s007.utterance.{i:03d}"
            options=citations[uid]["allowed_citations"]
            self.assertGreater(len(options),0)
            for q in options:
                self.assertIn(q["source_page"],(3,4))
                self.assertNotIn("skysurfer",
                                 q["verbatim_source_quote"].lower())
                proof=prove_source_quote_occurrence(
                    source_pdf=folder/"source.pdf",
                    expected_sha256=original["source.pdf"],
                    page_number=q["source_page"],
                    verbatim_quote=q["verbatim_source_quote"])
                self.assertEqual(proof["quote_sha256"],q["quote_sha256"])
        self.assertEqual(original,{name:_sha(folder/name) for name in original})

    def test_real_serway_model1_acoustic_claims_retrieve_exact_derivation(self):
        home=Path.home()/"AppData"/"Local"/"MicroGen_AI_Web_Checkpoints"
        folder=(home/"20261112_PR528_G2_SERWAY6_4_NARRATION_SOURCE_REUSE_V7"
                /"source_tree"/"6"/"6.4")
        if not (folder/"source.pdf").is_file():
            self.skipTest("Real immutable source only available on Dell-115")
        before={key:_sha(folder/key)
                for key in ("source.pdf","slides.pdf","script.txt")}
        job=build_review_job(folder=folder,slide_numbers=[4,5])
        source=folder/"source.pdf"
        model=_source_model_sections(source,before["source.pdf"])
        self.assertTrue(model[1][0]<=3 and model[1][2]>=4)
        self.assertEqual(_slide_model_title(job["slides"][1]),1)
        rows={r["utterance_id"]:r
              for r in job["verified_source_quote_candidates_v1"]["utterances"]}
        initial=rows["s005.utterance.001"]["allowed_citations"]
        terminal=rows["s005.utterance.003"]["allowed_citations"]
        self.assertGreater(len(initial),0)
        self.assertGreater(len(terminal),0)
        self.assertTrue(any("acceleration of the sphere is simply g"
                            in x["verbatim_source_quote"] for x in initial))
        self.assertTrue(any("terminal speed is obtained"
                            in x["verbatim_source_quote"] for x in terminal))
        for quote in initial+terminal:
            self.assertNotIn("baseball",quote["verbatim_source_quote"].lower())
            self.assertEqual(quote["source_page"],3)
            proof=prove_source_quote_occurrence(
                source_pdf=source,expected_sha256=before["source.pdf"],
                page_number=quote["source_page"],
                verbatim_quote=quote["verbatim_source_quote"])
            self.assertEqual(proof["quote_sha256"],quote["quote_sha256"])
        self.assertEqual(before,{key:_sha(folder/key) for key in before})


if __name__ == "__main__":
    unittest.main()
