import os,unittest
from pathlib import Path
from selenium_pipeline.offline_corrected_bundle_verify import verify_original_five_bundle,OfflineBundleError
class RealBundleReverification(unittest.TestCase):
    def test_nonexistent_fails(self):
        with self.assertRaises((OfflineBundleError,FileNotFoundError)):
            verify_original_five_bundle(original=Path("Z:/unknown_original"),
                bundle=Path("Z:/unknown_bundle"))
    def test_actual_original_immutable_five_units(self):
        original=os.getenv("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        bundle=os.getenv("MICROGEN_CORRECTED_SLIDE4_HANDOFF")
        if not original or not bundle:
            self.skipTest("Real protected Thomas review handoff is Dell-115 only")
        report=verify_original_five_bundle(original=Path(original),bundle=Path(bundle))
        self.assertEqual(report["verified_image_count"],5)
        self.assertFalse(report["tts_audio_validated"])
