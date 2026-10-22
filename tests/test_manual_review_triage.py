import unittest,tempfile
from pathlib import Path
from selenium_pipeline.manual_review_triage import build_manual_review_triage
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_original_packet_evidence_audit import fixture
class Triage(unittest.TestCase):
    def test_explicit_owner_permission_keeps_unreviewed_status(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t)/"f";p=fixture(folder)
            p["review_items"][0]["candidate_targets"]=[]
            r=build_manual_review_triage(folder=folder,packet=p,owner_allows_review=True)
            self.assertEqual(r["candidate_free_count"],1)
            self.assertEqual(r["review_queue"][0]["priority"],"MISSING_TEXT_TARGET")
            self.assertFalse(r["owner_approval_is_math_evidence"])
    def test_no_owner_permission_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t)/"f";p=fixture(folder)
            with self.assertRaises(FigureIdentityReviewRequired):
                build_manual_review_triage(folder=folder,packet=p,owner_allows_review=False)
