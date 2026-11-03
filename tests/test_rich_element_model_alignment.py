"""End-to-end offline independent audit of machine proposed lecture element IDs.

Uses actual source/author PyMuPDF bytes and real immutable rich-mapping
checkpoint. No browser, Gemini, synthetic spoken words, TTS or video requests.
"""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

from selenium_pipeline.rich_element_mapping_checkpoint import (
    ElementMappingCheckpointBlocked, require_automatic_mapping_or_checkpoint)
from selenium_pipeline.rich_element_model_alignment import (
    RichMappingError, assess_response, request_for_slide,
    prompt_for_request, parse_response, complete_json_response, trig_families)


class SourceVerifiedModelElementMappingTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        self.original = root/"8"/"8.4"
        self.original.mkdir(parents=True)
        self.checkpoint_root = root/"immutable_scope"
        self.checkpoint_root.mkdir()
        self.source = self.original/"source.pdf"
        self.slides = self.original/"slides.pdf"
        self.script = self.original/"script.txt"
        with pymupdf.open() as d:
            page = d.new_page()
            page.insert_text((62,102),
                "Trigonometric substitutions replace an integration variable.")
            page.insert_text((62,138),
                "For tangent substitution, x equals a times tangent theta.")
            d.save(self.source)
        with pymupdf.open() as d:
            page = d.new_page()
            page.insert_text((62,115),
                "Trigonometric substitutions replace an integration variable.")
            page.insert_text((62,154),
                "For tangent substitution, x equals a times tangent theta.")
            page.draw_line((65,225),(205,198))  # content—not a text-only slide
            d.save(self.slides)
        self.script.write_text(
            "**Slide 1 [16 sec]:\n"
            "Trigonometric substitutions replace an integration variable. "
            "For tangent substitution, x equals a times tangent theta.",
            encoding="utf8")
        try:
            require_automatic_mapping_or_checkpoint(source=self.source,
                slides=self.slides,script=self.script,
                checkpoint_root=self.checkpoint_root)
        except ElementMappingCheckpointBlocked:
            pass
        found=list(self.checkpoint_root.glob("rich_element_map_*"))
        self.assertEqual(len(found),1)
        self.ck=found[0]
        self.req=request_for_slide(source_folder=self.original,
            checkpoint=self.ck,slide_number=1)

    def choices(self):
        units=self.req["original_utterances"]
        targets=[t for t in self.req["visible_targets"]
                 if t["kind"]=="text_block"]
        self.assertEqual(len(units),2)
        self.assertEqual(len(targets),2)
        return {
            "slide":1,
            "request_sha256":self.req["request_sha256"],
            "associations":[
                {"utterance_id":units[i]["utterance_id"],
                 "target_id":targets[i]["target_id"],
                 "source_page":1,
                 "source_quote":("Trigonometric substitutions replace an "
                    "integration variable." if i==0 else
                    "For tangent substitution, x equals a times tangent theta."),
                 "reason":"Same exact source-backed mathematical statement",
                 "needs_review":False}
                for i in range(2)
            ],
        }

    def test_full_actual_source_pdf_match_is_audited_without_tts_approval(self):
        response=self.choices()
        original=[p.read_bytes() for p in (self.source,self.slides,self.script)]
        audited=assess_response(source_folder=self.original,
            checkpoint=self.ck,slide_number=1,proposed=response)
        self.assertEqual(audited["text_source_and_author_anchors_passed"],1)
        self.assertEqual(audited["remaining_review_items"],1)
        self.assertIn("mathematical_equation_or_domain_requires_independent_proof",
                      audited["entries"][1]["remaining_independent_scientific_review_reasons"])
        self.assertEqual(audited["utterances_total"],2)
        self.assertFalse(audited["paid_tts_authorized"])
        self.assertFalse(audited["student_publication_authorized"])
        self.assertEqual(original,
            [p.read_bytes() for p in (self.source,self.slides,self.script)])

    def test_request_is_an_actual_bounded_source_pdf_prompt(self):
        prompt=prompt_for_request(self.req)
        self.assertIn("Trigonometric substitutions replace",prompt)
        self.assertIn("original_utterances",prompt)
        self.assertIn(self.req["request_sha256"],prompt)
        self.assertFalse(self.req["audio_generation_authorized"])
        self.assertEqual(len(self.req["source_page_excerpts"]),1)

    def test_model_can_leave_genuinely_unproven_mapping_for_review(self):
        response=self.choices()
        response["associations"][1].update(
            target_id=None,source_page=None,source_quote=None,
            needs_review=True)
        audited=assess_response(source_folder=self.original,
            checkpoint=self.ck,slide_number=1,proposed=response)
        self.assertEqual(audited["text_source_and_author_anchors_passed"],1)
        self.assertEqual(audited["remaining_review_items"],1)
        self.assertIn("unassigned_original_utterance",
            audited["entries"][1]["remaining_independent_scientific_review_reasons"])

    def test_hallucinated_pdf_quote_is_refused_not_promoted(self):
        response=self.choices()
        response["associations"][1]["source_quote"]=(
            "Trigonometric substitution directly proves that gravity is zero.")
        with self.assertRaisesRegex(RichMappingError,
                                    "fabricated"):
            assess_response(source_folder=self.original,
                checkpoint=self.ck,slide_number=1,proposed=response)

    def test_utterance_swap_or_forged_visual_target_fails(self):
        response=self.choices()
        response["associations"][0]["target_id"]="nonexistent.figure.88"
        with self.assertRaisesRegex(RichMappingError,"nonexisting"):
            assess_response(source_folder=self.original,
                checkpoint=self.ck,slide_number=1,proposed=response)
        response=self.choices()
        response["associations"].reverse()
        with self.assertRaisesRegex(RichMappingError,"swapped"):
            assess_response(source_folder=self.original,
                checkpoint=self.ck,slide_number=1,proposed=response)

    def test_browser_success_saves_raw_and_independent_audit_without_paid_calls(self):
        import json
        from unittest.mock import patch
        from selenium_pipeline.rich_element_model_alignment import main
        output=self.checkpoint_root/"slide001_independent_audit.json"
        with patch("selenium_pipeline.series_gemini._browser_request",
                   return_value=json.dumps(self.choices())) as browser:
            main(["--source-folder",str(self.original),
                  "--checkpoint",str(self.ck),"--slide","1",
                  "--out",str(output),"--gemini-web","--wait-s","10"])
        browser.assert_called_once()
        self.assertTrue(output.is_file())
        raw=self.checkpoint_root/"slide_001.json"
        self.assertTrue(raw.is_file())
        self.assertEqual(json.loads(raw.read_text("utf8"))["slide"],1)
        self.assertFalse(json.loads(output.read_text("utf8"))["paid_tts_authorized"])
        ledger=output.with_suffix(".submission_held.json")
        self.assertEqual(json.loads(ledger.read_text("utf8"))["status"],
                         "CAPTURED_SOURCE_AUDITED_REVIEW_ONLY")

    def test_unknown_browser_submission_is_held_not_resubmitted(self):
        from unittest.mock import patch
        from selenium_pipeline.rich_element_model_alignment import main
        output=self.checkpoint_root/"retry_safety_audit.json"
        args=["--source-folder",str(self.original),"--checkpoint",str(self.ck),
              "--slide","1","--out",str(output),"--gemini-web","--wait-s","10"]
        with patch("selenium_pipeline.series_gemini._browser_request",
                   side_effect=TimeoutError("Response already submitted, capture lost")) as browser:
            with self.assertRaises(TimeoutError):main(args)
            with self.assertRaisesRegex(RichMappingError,"Previous Gemini submission"):
                main(args)
        browser.assert_called_once()
        ledger=output.with_suffix(".submission_held.json")
        self.assertEqual(__import__("json").loads(ledger.read_text("utf8"))["status"],
                         "MAY_HAVE_SENT_AWAIT_RECONCILIATION")
        self.assertFalse(output.exists())

    def test_wrong_trig_family_is_not_source_grounded_provenance(self):
        self.assertEqual(trig_families("x equals a times tangent theta"),{"tangent"})
        self.assertEqual(trig_families("for sine substitution"),{"sine"})
        self.assertEqual(trig_families("the theta is the arctangent"),{"tangent"})
        self.assertEqual(trig_families("a secant of theta"),{"secant"})
        self.assertEqual(trig_families("ordinary model-generated text"),set())

    def test_duplicate_JSON_key_or_non_json_response_rejected(self):
        self.assertFalse(complete_json_response("{\"slide\": 1,"))
        self.assertFalse(complete_json_response("Busy, no valid model response"))
        self.assertTrue(complete_json_response("{\"slide\": 1}"))
        with self.assertRaises(RichMappingError):
            parse_response('{"slide":1,"slide":99,"associations":[]}')
        with self.assertRaises(RichMappingError):
            parse_response("Non JSON output from a busy server")

    def test_original_source_SHA_change_does_not_inherit_prior_approval(self):
        self.source.write_bytes(b"wrong original physical publisher PDF")
        with self.assertRaises((RichMappingError,ValueError)):
            assess_response(source_folder=self.original,
                checkpoint=self.ck,slide_number=1,proposed=self.choices())

    def test_forged_student_publication_and_paid_authorization_rejected(self):
        response=self.choices()
        response["student_publication_authorized"]=True
        with self.assertRaisesRegex(RichMappingError,"authority"):
            assess_response(source_folder=self.original,
                checkpoint=self.ck,slide_number=1,proposed=response)
        response=self.choices()
        response["audio_generation_authorized"]=True
        with self.assertRaisesRegex(RichMappingError,"authority"):
            assess_response(source_folder=self.original,
                checkpoint=self.ck,slide_number=1,proposed=response)


if __name__=="__main__":
    unittest.main()
