import tempfile,unittest
from pathlib import Path
from selenium_pipeline.independent_encoded_transition_audit import verify_encoded_boundaries
from selenium_pipeline.incremental_element_review_encoder import encode_segment_highlight_review
from selenium_pipeline.highlight_video_preview import ffmpeg_path
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from test_incremental_element_review_encoder import inputs

class IndependentTransitionTests(unittest.TestCase):
    @unittest.skipUnless(Path(ffmpeg_path()).exists(),"FFmpeg binary missing")
    def test_genuine_encoded_two_element_video_changes_at_pcm_boundary(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t);slides,jobs,clips=inputs(folder)
            rec=encode_segment_highlight_review(
                slides=slides,jobs=jobs,clips=clips,destination=folder/"r")
            report=verify_encoded_boundaries(
                slides=slides,mp4=folder/"r"/"element_highlight_review.mp4",
                receipt=rec)
            self.assertEqual(report["transition_count"],1)
            self.assertFalse(report["student_publication_authorized"])
            forged=dict(rec)
            forged["encoded_review_sha256"]="0"*64
            with self.assertRaises(FigureIdentityReviewRequired):
                verify_encoded_boundaries(slides=slides,
                    mp4=folder/"r"/"element_highlight_review.mp4",receipt=forged)
    @unittest.skipUnless(Path(ffmpeg_path()).exists(),"FFmpeg binary missing")
    def test_forged_pcm_boundary_cannot_pass_actual_video_pixels(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t);slides,jobs,clips=inputs(folder)
            rec=encode_segment_highlight_review(
                slides=slides,jobs=jobs,clips=clips,destination=folder/"r")
            altered=dict(rec)
            altered["events"]=[dict(e) for e in rec["events"]]
            altered["events"][0]["end_seconds"]=.3
            altered["events"][1]["start_seconds"]=.3
            with self.assertRaises(FigureIdentityReviewRequired):
                verify_encoded_boundaries(
                    slides=slides,mp4=folder/"r"/"element_highlight_review.mp4",
                    receipt=altered)
