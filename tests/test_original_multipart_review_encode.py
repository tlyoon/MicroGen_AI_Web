"""Actual original-slide multipart MP4 staging; never publish review media."""
from __future__ import annotations
import hashlib,struct,tempfile,unittest,wave
from pathlib import Path
import pymupdf
from selenium_pipeline.original_multipart_review_encode import stage_original_multipart_review
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

class MultipartEncodingTests(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory()
  self.addCleanup(tmp.cleanup)
  self.root=Path(tmp.name)
  self.orig=self.root/"original"
  self.orig.mkdir()
  self.out=self.root/"staged"
  with pymupdf.open() as pdf:
   p=pdf.new_page(width=400,height=300)
   p.insert_text((30,90),"Source text")
   pdf.save(self.orig/"source.pdf")
  with pymupdf.open() as deck:
   for idx in (1,2):
    p=deck.new_page(width=400,height=300)
    p.insert_text((30,70),f"Slide {idx} first text element")
    p.insert_text((30,160),f"Slide {idx} second element")
   deck.save(self.orig/"slides.pdf")
  for i in (1,2):
   signal=[1000]*24000+[0]*7000+[800]*25000
   with wave.open(str(self.orig/f"slide{i}.wav"),"wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(24000)
    w.writeframes(struct.pack(f"<{len(signal)}h",*signal))
 def test_real_encoded_full_lecture_coverage_but_not_speech_approval(self):
  before={x.name:hashlib.sha256(x.read_bytes()).hexdigest()
          for x in self.orig.iterdir()}
  data=stage_original_multipart_review(folder=self.orig,output=self.out)
  self.assertEqual(data["part_count"],1)
  self.assertEqual(data["parts"][0]["slide_count"],2)
  self.assertLess(data["parts"][0]["encoded_mp4_duration_s"],600)
  self.assertTrue((self.out/"part_01"/"part_01_review.mp4").is_file())
  self.assertFalse(data["spoken_element_highlight_semantics_verified"])
  self.assertFalse(data["student_publication_authorized"])
  self.assertEqual(before,{x.name:hashlib.sha256(x.read_bytes()).hexdigest()
                            for x in self.orig.iterdir()})
 def test_existing_staging_is_never_overwritten(self):
  self.out.mkdir()
  (self.out/"prior.txt").write_text("untouched")
  with self.assertRaises(FigureIdentityReviewRequired):
   stage_original_multipart_review(folder=self.orig,output=self.out)
  self.assertEqual((self.out/"prior.txt").read_text(),"untouched")
 def test_staging_cannot_live_inside_lecture_folder(self):
  with self.assertRaises(FigureIdentityReviewRequired):
   stage_original_multipart_review(folder=self.orig,output=self.orig/"review")
