import tempfile,unittest
from pathlib import Path
from selenium_pipeline.incremental_element_review_encoder import encode_segment_highlight_review
from selenium_pipeline.encoded_audio_fingerprint_audit import audit_muxed_audio_segment_fingerprints
from selenium_pipeline.figure_source_identity import _sha
from test_incremental_element_review_encoder import inputs
class ConsecutiveSameEquation(unittest.TestCase):
 def test_two_originally_separate_wavs_same_equation_visual_persists(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);pdf,jobs,audio=inputs(root)
   jobs["chunk_jobs"][1]["target_pdf_page_bbox_pt"]=jobs["chunk_jobs"][0]["target_pdf_page_bbox_pt"][:]
   orig=_sha(pdf)
   out=encode_segment_highlight_review(slides=pdf,jobs=jobs,clips=audio,
                                       destination=root/"review")
   self.assertEqual(len(out["events"]),2)
   self.assertTrue(out["decoded_highlight_midpoint_samples_verified"])
   self.assertLess(out["actual_encoded_duration_s"],600)
   self.assertEqual(out["events"][0]["element_bbox_pdf_pt"],
                    out["events"][1]["element_bbox_pdf_pt"])
   wavs=[Path(x["wav_path"]) for x in audio]
   spectral=audit_muxed_audio_segment_fingerprints(
       mp4=root/"review"/"element_highlight_review.mp4",wavs=wavs)
   self.assertEqual(spectral["source_element_count"],2)
   self.assertEqual(_sha(pdf),orig)
   self.assertFalse(out["student_publication_authorized"])
