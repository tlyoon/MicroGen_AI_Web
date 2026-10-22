import tempfile,unittest
from pathlib import Path
from selenium_pipeline.thomas_element_production_readiness import audit_series_element_production_readiness
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_original_packet_evidence_audit import fixture
class ThomasReadinessGate(unittest.TestCase):
    def test_incomplete_real_series_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);folder=root/"f";pkt=fixture(folder)
            with self.assertRaises(FigureIdentityReviewRequired):
                audit_series_element_production_readiness(
                    folders={"8.4":folder,"8.5":folder,"8.6":folder},
                    packets={"8.4":pkt,"8.5":pkt,"8.6":pkt},
                    owner_allows_manual_review=True)
    def test_owner_permission_cannot_bypass_source_presence(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(FigureIdentityReviewRequired):
                audit_series_element_production_readiness(
                    folders={},packets={},owner_allows_manual_review=True)
