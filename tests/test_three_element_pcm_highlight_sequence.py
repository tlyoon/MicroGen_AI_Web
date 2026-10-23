"""Three actual encoded highlight transitions across one original slide."""
import math,tempfile,unittest,wave
from pathlib import Path
import pymupdf
from selenium_pipeline.incremental_element_review_encoder import encode_segment_highlight_review
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired,_sha
from selenium_pipeline.encoded_part_audio_fidelity import verify_encoded_part_audio
from test_incremental_element_review_encoder import inputs

class ThreeElementSequence(unittest.TestCase):
 def setup_three(self,root):
  slide,jobs,clips=inputs(root)
  # Extend only fresh synthetic test PDF, never textbook originals.
  with pymupdf.open(slide) as doc:
   doc[0].insert_text((185,150),"Synthetic area three",fontsize=9)
   doc.save(root/"third_slide.pdf")
  (root/"third_slide.pdf").replace(slide)
  clips_dir=root/"recorded"
  wav=clips_dir/"3.wav"
  with wave.open(str(wav),"wb") as w:
   w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
   w.writeframes(b"".join(int(7800*math.sin(2*math.pi*760*t/16000))
            .to_bytes(2,byteorder="little",signed=True) for t in range(10400)))
  name="s001.utterance.003"
  jobs["slides_sha256"]=_sha(slide)
  jobs["chunk_jobs"].append({"job_id":name,"target_slide_index":1,
                             "target_pdf_page_bbox_pt":[185,115,310,180]})
  clips.append({"job_id":name,"voice_id":"Kore","wav_path":str(wav),
                "wav_sha256":_sha(wav)})
  return slide,jobs,clips
 def test_three_distinct_equations_follow_exact_pcm_boundaries(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);pdf,jobs,clips=self.setup_three(root);before=_sha(pdf)
   out=encode_segment_highlight_review(slides=pdf,jobs=jobs,clips=clips,
                                         destination=root/"review")
   events=out["events"]
   self.assertEqual(len(events),3)
   self.assertEqual(len(out["decoded_highlight_transition_samples"]),3)
   self.assertTrue(all(row["only_expected_encoded_target_red"] for row in
                       out["decoded_highlight_transition_samples"]))
   for earlier,later in zip(events,events[1:]):
    self.assertAlmostEqual(earlier["end_seconds"],later["start_seconds"],places=5)
    self.assertEqual(earlier["end_frame"],later["start_frame"])
   self.assertAlmostEqual(events[-1]["end_seconds"],1.85,places=4)
   self.assertFalse(out["all_encoded_element_transition_frames_verified"])
   self.assertFalse(out["student_publication_authorized"])
   self.assertEqual(_sha(pdf),before)
   mux=verify_encoded_part_audio(
       mp4=root/"review"/"element_highlight_review.mp4",
       wav=root/"review"/"narration.wav")
   self.assertGreater(min(mux["window_correlations"]),.78)
 def test_missing_third_wav_blocks_any_new_video(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);pdf,jobs,clips=self.setup_three(root)
   Path(clips[-1]["wav_path"]).unlink()
   with self.assertRaises((FigureIdentityReviewRequired,ValueError)):
    encode_segment_highlight_review(slides=pdf,jobs=jobs,clips=clips,
                                    destination=root/"reject")
   self.assertFalse((root/"reject").exists())
