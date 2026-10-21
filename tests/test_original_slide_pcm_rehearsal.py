import tempfile,unittest
from pathlib import Path
from selenium_pipeline.original_slide_pcm_rehearsal import rehearse_original_slide
from selenium_pipeline.highlight_video_preview import ffmpeg_path
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired,_sha
from test_incremental_lecture_sync_queue import make_subchapter

class RealOriginalSlideAudioTests(unittest.TestCase):
    @unittest.skipUnless(Path(ffmpeg_path()).is_file(),"Real FFmpeg unavailable")
    def test_encoded_original_pcm_video_is_review_not_element_sync(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            folder=make_subchapter(root/"teaching","8.4")
            before=_sha(folder/"slides.pdf")
            report=rehearse_original_slide(folder=folder,slide_number=2,
                   destination=root/"preview")
            self.assertEqual(report["status"],
                "GENUINE_ORIGINAL_SLIDE_WAV_TECHNICAL_REHEARSAL_ONLY")
            self.assertTrue((root/"preview"/"original_slide_technical_rehearsal.mp4").is_file())
            self.assertFalse(report["element_level_highlighting_implemented"])
            self.assertFalse(report["student_publication_authorized"])
            self.assertEqual(_sha(folder/"slides.pdf"),before)
            with self.assertRaises(FigureIdentityReviewRequired):
                rehearse_original_slide(folder=folder,slide_number=2,
                       destination=folder/"bad_preview")
    def test_missing_slide_or_wav_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            folder=make_subchapter(root/"teaching","8.5")
            with self.assertRaises(FigureIdentityReviewRequired):
                rehearse_original_slide(folder=folder,slide_number=4,
                      destination=root/"preview")
