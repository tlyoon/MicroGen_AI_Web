import unittest,os
from pathlib import Path
from selenium_pipeline.offline_original_production_readiness import offline_original_readiness
class OfflineAcceptance(unittest.TestCase):
    def test_no_project_fails_closed(self):
        with self.assertRaises((ValueError,FileNotFoundError)):
            offline_original_readiness(chapter=Path("Z:/missing"))
    def test_actual_original_readiness_does_not_self_approve(self):
        root=os.getenv("MICROGEN_ORIGINAL_THOMAS_CHAPTER")
        if not root:self.skipTest("Authentic chapter input Dell-115 only")
        report=offline_original_readiness(chapter=Path(root))
        self.assertEqual(len(report["original_source_sha256"]),3)
        self.assertFalse(report["student_publication_authorized"])
        self.assertGreaterEqual(len(report["release_blockers"]),5)
        self.assertEqual(report["strict_new_corrected_video_parts_accepted"],0)
