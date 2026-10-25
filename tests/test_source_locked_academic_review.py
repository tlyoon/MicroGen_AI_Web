"""Source-locked academic review must never accept model-created source citations."""
import os,copy,json
from pathlib import Path
from unittest.mock import patch
import unittest
from selenium_pipeline.ai_academic_web_review import review_instructions,build_review_job
from selenium_pipeline.source_locked_academic_review import (
    assert_original_slide4_source_packet,review_quote_whitelist,
    require_quote_locked_model_reply,recover_rendered_json_format_only,
)
from selenium_pipeline.original_slide4_exact_source_evidence import (
    build_five_original_source_evidence,
)


def fixture():
    utterances=[{"id":f"s004.utterance.{i:03d}",
                 "spoken_sha256":f"{i:064x}",
                 "spoken_text":f"Original spoken sentence {i}."}
                for i in range(1,6)]
    job={"utterance_count":5,"selected_original_slides":[4],
         "source_sha256":"a"*64,"slides_sha256":"b"*64,
         "script_sha256":"c"*64,
         "slides":[{"slide":4,"utterances":utterances,
                    "visual_targets":[{"id":f"s004.text.{i:03d}"}
                                      for i in range(1,7)]}]}
    categories=("INTRO_REFERENCE_TRIANGLES","TANGENT_SQUARED_IDENTITY",
                "SINE_SQUARED_IDENTITY","SECANT_SQUARED_IDENTITY",
                "ROOT_ABSOLUTE_VALUES_CONTEXT_ONLY")
    packet={
        "status":"FIVE_ORIGINAL_SLIDE4_SOURCE_QUOTE_PACKET_REVIEW_ONLY",
        "original_source_sha256":"a"*64,
        "original_slides_sha256":"b"*64,
        "original_script_sha256":"c"*64,
        "original_utterance_count":5,
        "source_math_semantically_approved_utterances":0,
        "source_radical_operator_academically_verified":False,
        "independent_two_pass_review_approved":False,
        "student_publication_authorized":False,
        "original_utterance_evidence":[
          {"original_utterance_id":u["id"],
           "spoken_sha256":u["spoken_sha256"],
           "exact_original_spoken_text":u["spoken_text"],
           "exact_source_quote_count":2,
           "source_evidence":[{"source_physical_page":1,
                 "exact_extracted_pdf_quote":f"The original book sentence {i} example {j}.",
                 "source_quote_sha256":f"{i*10+j:064x}",
                 "original_pdf_spatial_coherence_verified":True}
                    for j in range(1,3)],
           "evidence_kind":categories[i-1],
           "evidence_is_semantic_math_approval":False,
           "original_radical_glyph_reliably_decoded":False,
           "review_disposition":"AWAIT_INDEPENDENT_SOURCE_MATH_REVIEW"}
          for i,u in enumerate(utterances,1)]}
    rows=[]
    for i,u in enumerate(utterances,1):
        q=packet["original_utterance_evidence"][i-1]["source_evidence"][1]
        rows.append({"utterance_id":u["id"],
           "spoken_sha256":u["spoken_sha256"],
           "target_id":f"s004.text.{i:03d}",
           "source_page":q["source_physical_page"],
           "verbatim_source_quote":q["exact_extracted_pdf_quote"],
           "verdict":"SUPPORTED" if i<5 else "UNRESOLVED",
           "math_explanation":"Source text alone does not prove all interpretation details."})
    response={"status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
              "rows":rows}
    return job,packet,response


class StrictOriginalSourceReview(unittest.TestCase):
    def test_five_exact_whitelists_and_unresolved_root(self):
        job,packet,response=fixture()
        self.assertEqual(len(review_quote_whitelist(job=job,packet=packet)),5)
        require_quote_locked_model_reply(job=job,packet=packet,response=response)
        prompt=review_instructions(job,mode="INITIAL_REVIEW",verified_source_evidence=packet)
        self.assertIn("verified_source_quote_whitelist",prompt)
        self.assertIn("Mark UNRESOLVED",prompt)
        self.assertIn("ROOT_ABSOLUTE_VALUES_CONTEXT_ONLY",prompt)

    def test_hallucinated_and_cross_unit_citations_refused(self):
        job,packet,response=fixture()
        cases=[]
        m=copy.deepcopy(response);m["rows"][0]["verbatim_source_quote"]="A fabricated book quotation.";cases.append(m)
        m=copy.deepcopy(response);m["rows"][1]["verbatim_source_quote"]=response["rows"][0]["verbatim_source_quote"];cases.append(m)
        m=copy.deepcopy(response);m["rows"][2]["source_page"]=99;cases.append(m)
        m=copy.deepcopy(response);m["rows"][3]["target_id"]="fabricated.figure";cases.append(m)
        m=copy.deepcopy(response);m["rows"][4]["verdict"]="SUPPORTED";cases.append(m)
        m=copy.deepcopy(response);m["rows"][0]["verbatim_source_quote"]=None;cases.append(m)
        for i,bad in enumerate(cases):
            with self.subTest(i=i),self.assertRaises(ValueError):
                require_quote_locked_model_reply(job=job,packet=packet,response=bad)

    def test_unresolved_can_omit_citation_but_not_reason(self):
        job,packet,response=fixture()
        for row in response["rows"]:
            row.update(verdict="UNRESOLVED",source_page=None,
                       verbatim_source_quote=None,target_id=None)
        require_quote_locked_model_reply(job=job,packet=packet,response=response)
        response["rows"][0]["math_explanation"]="uncertain"
        with self.assertRaises(ValueError):
            require_quote_locked_model_reply(job=job,packet=packet,response=response)

    def test_packet_mutation_or_false_source_approval_refused(self):
        job,packet,response=fixture()
        for field,value in (("original_source_sha256","0"*64),
                            ("source_math_semantically_approved_utterances",5),
                            ("independent_two_pass_review_approved",True)):
            bad=copy.deepcopy(packet);bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                require_quote_locked_model_reply(job=job,packet=bad,response=response)

    def test_format_only_recovery_exactly_one_json_no_math_rewrite(self):
        _,_,response=fixture()
        response["rows"][0]["math_explanation"]="The visible triangle relation.\nUnverified radical sign."
        body=json.dumps(response,ensure_ascii=False)
        rendered="Gemini said\n\n"+body.replace("\\n","\n")
        decoded=recover_rendered_json_format_only(rendered)
        self.assertEqual(decoded,response)
        for malformed in ("Gemini said\n\n{","prefix"+body,
                          body+"\nUntrusted second answer"):
            with self.subTest(raw=malformed[:12]),self.assertRaises(ValueError):
                recover_rendered_json_format_only(malformed)

    def test_real_quarantined_gemini_citations_still_refused(self):
        root=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        raw=os.environ.get("MICROGEN_QUARANTINED_SLIDE4_INITIAL_RESPONSE")
        if not root or not raw:
            self.skipTest("Actual original and quarantined browser capture are Dell-only")
        job=build_review_job(folder=Path(root),slide_numbers=[4])
        packet=build_five_original_source_evidence(folder=Path(root))
        received=recover_rendered_json_format_only(Path(raw).read_text(encoding="utf8"))
        self.assertEqual(len(received["rows"]),5)
        with self.assertRaises(ValueError):
            require_quote_locked_model_reply(job=job,packet=packet,response=received)

if __name__=="__main__":
    unittest.main()
