import tempfile,unittest
from pathlib import Path
from selenium_pipeline.original_slide_multipart_rehearsal import rehearse_contiguous_original_slides
from selenium_pipeline.highlight_video_preview import ffmpeg_path
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_incremental_lecture_sync_queue import make_subchapter

class WholeSlideMultipartTests(unittest.TestCase):
    @unittest.skipUnless(Path(ffmpeg_path()).is_file(),"FFmpeg unavailable")
    def test_actual_encoded_contiguous_original_pcm_slides(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=make_subchapter(root/"teaching","8.4")
            report=rehearse_contiguous_original_slides(
                folder=folder,slide_start=1,slide_end=3,
                destination=root/"preview")
            self.assertEqual(report["independently_encoded_whole_slide_count"],3)
            self.assertLess(report["actual_encoded_mp4_duration_s"],600)
            self.assertFalse(report["element_level_highlight_verified"])
            self.assertTrue((root/"preview"/"whole_slide_multipart_review.mp4").exists())
    def test_out_of_bounds_and_inplace_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=make_subchapter(root/"teaching","8.5")
            with self.assertRaises(FigureIdentityReviewRequired):
                rehearse_contiguous_original_slides(folder=folder,
                    slide_start=1,slide_end=4,destination=root/"review")
            with self.assertRaises(FigureIdentityReviewRequired):
                rehearse_contiguous_original_slides(folder=folder,
                    slide_start=1,slide_end=2,destination=folder/"overwrite")
