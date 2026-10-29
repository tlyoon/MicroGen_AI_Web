import os,unittest
from pathlib import Path
from selenium_pipeline.offline_original_six_clip_remux import (
    encode_six_original_review_clips,OfflineClipError)
class ActualHistoricalReviewClip(unittest.TestCase):
    def test_wrong_original_fails_closed(self):
        with self.assertRaises(OfflineClipError):
            encode_six_original_review_clips(chapter=Path("Z:/missing_historical"),
                                             output_dir=Path("Z:/missing_output"))
    def test_existing_output_cannot_be_overwritten(self):
        c=os.environ.get("MICROGEN_ORIGINAL_THOMAS_CHAPTER")
        if not c:self.skipTest("Dell-115 only for real original content")
        with self.assertRaises(OfflineClipError):
            encode_six_original_review_clips(chapter=Path(c),output_dir=Path(c)/"8.4")
