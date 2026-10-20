import struct,tempfile,unittest,wave
from pathlib import Path
import pymupdf
from selenium_pipeline.original_wav_element_cues import _candidate_pause_boundaries, propose_wav_pdf_element_highlights
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
class ElementCueTests(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.folder=Path(tmp.name)
  self.pdf=self.folder/"slides.pdf";self.wav=self.folder/"slide1.wav"
  with pymupdf.open() as doc:
   page=doc.new_page(width=400,height=300)
   page.insert_text((30,60),"First real equation")
   page.insert_text((30,130),"Second element narration")
   doc.save(self.pdf)
 def make(self,quiet=True):
  hz=1000
  a=[1000]*2000+[0 if quiet else 1000]*500+[1000]*2500
  with wave.open(str(self.wav),"wb") as w:
   w.setnchannels(1);w.setsampwidth(2);w.setframerate(hz)
   w.writeframes(struct.pack(f"<{len(a)}h",*a))
 def test_real_pcm_gap_candidate_never_certified(self):
  self.make()
  r=propose_wav_pdf_element_highlights(slides=self.pdf,wav=self.wav,slide_index=1)
  self.assertEqual(len(r["events"]),2)
  self.assertLess(abs(r["events"][1]["start_s"]-2.25),.1)
  self.assertFalse(r["speech_alignment_verified"])
  self.assertFalse(r["student_publication_authorized"])
 def test_no_pause_fails_instead_of_inventing_word_alignment(self):
  self.make(quiet=False)
  with self.assertRaises(FigureIdentityReviewRequired):
   propose_wav_pdf_element_highlights(slides=self.pdf,wav=self.wav,slide_index=1)
 def test_invalid_source_bounds_and_audio(self):
  with self.assertRaises(FigureIdentityReviewRequired):
   _candidate_pause_boundaries(b"\x00",1000,2)
  self.make()
  with self.assertRaises(FigureIdentityReviewRequired):
   propose_wav_pdf_element_highlights(slides=self.pdf,wav=self.wav,slide_index=2)
