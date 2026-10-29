import unittest,tempfile
from pathlib import Path
from selenium_pipeline.attested_math_target_witness import audit_attested_math_target_records
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_original_packet_evidence_audit import fixture
class AttestedWitnessTests(unittest.TestCase):
    def test_genuine_pdf_source_quote_binds_individual_selection(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t)/"f";p=fixture(folder)
            row=p["review_items"][0]
            row.update({"review_target_id":"s001.text.001",
                        "reviewer_attestation":True,"reviewer_id":"independent-reviewer",
                        "source_page":1,"verbatim_source_quote":"A visible equation"})
            r=audit_attested_math_target_records(folder=folder,packet=p)
            self.assertEqual(r["specific_attestations_with_valid_source_evidence"],1)
            self.assertFalse(r["source_math_semantics_independently_verified"])
    def test_wrong_quote_and_anonymous_review_denied(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t)/"f";p=fixture(folder)
            row=p["review_items"][0]
            row.update({"review_target_id":"s001.text.001",
                        "reviewer_attestation":True,"reviewer_id":"reviewer",
                        "source_page":1,"verbatim_source_quote":"There is no such source text"})
            with self.assertRaises(FigureIdentityReviewRequired):
                audit_attested_math_target_records(folder=folder,packet=p)
            row["verbatim_source_quote"]="A visible equation";row["reviewer_id"]=" "
            with self.assertRaises(FigureIdentityReviewRequired):
                audit_attested_math_target_records(folder=folder,packet=p)
