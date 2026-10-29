import tempfile,unittest
from pathlib import Path
from selenium_pipeline.original_thomas84_signed_triangle_two_full_mp4s import (
 final_render,PIECE_TO_SENTENCE,STATUS)
class TwoSignedMathMovies(unittest.TestCase):
 def test_sentence_tail_both_chunks_replaced(self):
  self.assertEqual(PIECE_TO_SENTENCE[2],2)
  self.assertNotIn(3,PIECE_TO_SENTENCE)
  self.assertIn("REVIEW",STATUS)
 def test_missing_source_fails_before_output(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)
   with self.assertRaises((ValueError,FileNotFoundError)):
    final_render(original=p/"orig",paired_source=p/"paired",
      new_audio=p/"audio",offline_speech_receipt=p/"asr.json",
      pr351_video_receipt=p/"351.json",pr355_video_receipt=p/"355.json",
      out=p/"output")
   self.assertFalse((p/"output").exists())
if __name__=="__main__":unittest.main()
