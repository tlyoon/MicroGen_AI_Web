"""Academic source-only recovery: never promote an unverified model claim."""
from __future__ import annotations
import copy
import unittest
from pathlib import Path

from selenium_pipeline.academic_quote_reconciliation import (
    reconcile_untrusted_review,
)


def fixture():
    hashes = {
        "source_sha256": "a" * 64,
        "slides_sha256": "b" * 64,
        "script_sha256": "c" * 64,
    }
    utterances = [
        {"id": "s002.utterance.001", "spoken_sha256": "1"*64},
        {"id": "s002.utterance.002", "spoken_sha256": "2"*64},
    ]
    candidates = [
        {"utterance_id": u["id"], "spoken_sha256": u["spoken_sha256"],
         "allowed_citations": [
             {"source_page": 1, "verbatim_source_quote": f"Source quote {index}"}]}
        for index, u in enumerate(utterances, 1)
    ]
    job = {
        **hashes, "utterance_count": 2,
        "slides": [{"slide": 2, "utterances": utterances,
                    "visual_targets": [{"id":"s002.text.001"}]}],
        "verified_source_quote_candidates_v1": {
            "status": "PHYSICALLY_WITNESSED_SOURCE_CITATIONS_V1",
            **hashes, "utterances": candidates}
    }
    response = {
        "status": "ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
        "rows": [
            {"utterance_id": "s002.utterance.001", "spoken_sha256": "1"*64,
             "verdict": "SUPPORTED", "target_id": None,
             "source_page": 1, "verbatim_source_quote": "Source quote 2",
             "math_explanation": "The model said this was a supported fact but it had no slide target."},
            {"utterance_id": "s002.utterance.002", "spoken_sha256": "2"*64,
             "verdict": "SUPPORTED", "target_id": "s002.text.001",
             "source_page": 1, "verbatim_source_quote": "Source quote 2",
             "math_explanation": "This matches the original narration and its actual visual target."},
        ],
    }
    return job, response


class AcademicQuoteReconciliationTests(unittest.TestCase):
    def test_cross_utterance_quote_and_null_target_downgrade_not_promote(self):
        job, response = fixture()
        original = copy.deepcopy(response)
        validated, audit = reconcile_untrusted_review(job=job, response=response)
        self.assertEqual(response, original)  # never edit original model output
        self.assertEqual([r["verdict"] for r in validated["rows"]],
                         ["UNRESOLVED", "SUPPORTED"])
        self.assertIsNone(validated["rows"][0]["verbatim_source_quote"])
        self.assertIsNone(validated["rows"][0]["source_page"])
        self.assertEqual(validated["rows"][1], response["rows"][1])
        self.assertEqual(len(audit["downgraded_or_citation_cleared_rows"]), 1)
        self.assertEqual(audit["source_citations_added"], 0)
        self.assertEqual(audit["model_claims_promoted_to_supported"], 0)
        self.assertFalse(audit["student_publication_authorized"])

    def test_supported_without_quote_must_be_unresolved(self):
        job, response = fixture()
        response["rows"][0].update(source_page=None,verbatim_source_quote=None)
        rows, audit = reconcile_untrusted_review(job=job,response=response)
        self.assertEqual(rows["rows"][0]["verdict"], "UNRESOLVED")
        self.assertEqual(len(audit["downgraded_or_citation_cleared_rows"]), 1)

    def test_cross_slide_target_must_be_cleared(self):
        job, response = fixture()
        response["rows"][1]["target_id"] = "s004.text.999"
        result, _ = reconcile_untrusted_review(job=job,response=response)
        self.assertEqual(result["rows"][1]["verdict"], "UNRESOLVED")
        self.assertIsNone(result["rows"][1]["target_id"])

    def test_invalid_source_must_not_change_model_identity(self):
        job, response = fixture()
        for field, value in (
            ("spoken_sha256", "X"*64),
            ("utterance_id", "s002.utterance.003"),
            ("math_explanation", ""),
        ):
            with self.subTest(field=field):
                corrupt=copy.deepcopy(response)
                corrupt["rows"][1][field]=value
                with self.assertRaises(ValueError):
                    reconcile_untrusted_review(job=job,response=corrupt)
        corrupt=copy.deepcopy(job)
        corrupt["verified_source_quote_candidates_v1"]["source_sha256"]="z"*64
        with self.assertRaises(ValueError):
            reconcile_untrusted_review(job=corrupt,response=response)
        with self.assertRaises(ValueError):
            reconcile_untrusted_review(job=job,response={"status":response["status"],"rows":[]})

    def test_invalid_negative_quote_keeps_negative_verdict_only(self):
        job,response = fixture()
        response["rows"][0]["verdict"] = "INCORRECT"
        result,_=reconcile_untrusted_review(job=job,response=response)
        self.assertEqual(result["rows"][0]["verdict"],"INCORRECT")
        self.assertIsNone(result["rows"][0]["verbatim_source_quote"])

    def test_partial_review_preserves_single_original_row_and_marks_other_missing(self):
        job,response=fixture()
        original=copy.deepcopy(response)
        response["rows"]=response["rows"][1:]
        actual,report=reconcile_untrusted_review(job=job,response=response)
        self.assertEqual(response["rows"],original["rows"][1:])
        self.assertEqual(len(actual["rows"]),2)
        self.assertEqual(actual["rows"][0]["verdict"],"UNRESOLVED")
        self.assertIsNone(actual["rows"][0]["target_id"])
        self.assertEqual(actual["rows"][1],original["rows"][1])
        self.assertEqual(report["model_returned_utterance_count"],1)
        self.assertEqual(report["machine_inserted_unresolved_placeholder_count"],1)
        self.assertEqual(report["model_omitted_original_utterance_ids"],
                         ["s002.utterance.001"])
        self.assertFalse(report["all_original_utterances_actually_reviewed"])
        self.assertEqual(report["model_claims_promoted_to_supported"],0)

    def test_untrusted_extra_or_duplicate_review_rows_never_accepted(self):
        job,response=fixture()
        repeat=copy.deepcopy(response)
        repeat["rows"].append(copy.deepcopy(repeat["rows"][0]))
        with self.assertRaises(ValueError):
            reconcile_untrusted_review(job=job,response=repeat)
        forged=copy.deepcopy(response)
        forged["rows"][0]["utterance_id"]="s999.utterance.001"
        with self.assertRaises(ValueError):
            reconcile_untrusted_review(job=job,response=forged)

    def test_normal_valid_result_remains_byte_equivalent(self):
        job,response = fixture()
        response["rows"][0].update(target_id="s002.text.001",
                                   verbatim_source_quote="Source quote 1")
        result,audit=reconcile_untrusted_review(job=job,response=response)
        self.assertEqual(result,response)
        self.assertEqual(audit["downgraded_or_citation_cleared_rows"],[])

    def test_normal_and_saved_path_both_use_same_strict_source_reconcile(self):
        root=Path(__file__).resolve().parents[1]/"selenium_pipeline"
        review=(root/"ai_academic_web_review.py").read_text(encoding="utf8")
        queue=(root/"ai_academic_review_queue.py").read_text(encoding="utf8")
        self.assertIn("def validate_source_demoted_review(",review)
        self.assertIn("return validate_source_demoted_review(folder=folder",review)
        self.assertIn("validator=lambda raw: validate_source_demoted_review(",queue)
        self.assertIn("validate_model_review(",review)


if __name__ == "__main__":
    unittest.main()
