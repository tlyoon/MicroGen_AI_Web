"""Independently remeasure real encoded staged media, never accept forgery."""
from __future__ import annotations
import hashlib,json,struct,tempfile,unittest,wave
from pathlib import Path
import pymupdf
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.original_multipart_review_encode import stage_original_multipart_review
from selenium_pipeline.independent_multipart_recovery_audit import (
 independent_reaudit_multipart,summarize_original_subtopic_readonly)

class IndependentMultipartReauditTests(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
  self.root=Path(tmp.name);self.orig=self.root/"original";self.orig.mkdir()
  self.staged=self.root/"staged"
  with pymupdf.open() as book:
   book.new_page(width=400,height=300);book.save(self.orig/"source.pdf")
  with pymupdf.open() as slide:
   p=slide.new_page(width=400,height=300)
   p.insert_text((50,80),"Original equation text")
   p.insert_text((50,145),"Recorded explanation text")
   slide.save(self.orig/"slides.pdf")
  with wave.open(str(self.orig/"slide1.wav"),"wb") as sound:
   sound.setnchannels(1);sound.setsampwidth(2);sound.setframerate(24000)
   s=[1000]*30000+[0]*7000+[800]*33000
   sound.writeframes(struct.pack(f"<{len(s)}h",*s))
 def test_real_video_pcm_pixels_and_duration_are_independently_verified(self):
  before={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in self.orig.iterdir()}
  stage_original_multipart_review(folder=self.orig,output=self.staged)
  checked=independent_reaudit_multipart(folder=self.orig,staged=self.staged)
  self.assertTrue(checked["source_pcm_sample_equality_verified"])
  self.assertTrue(checked["sampled_encoded_highlight_pixels_verified"])
  self.assertTrue(checked["encoded_duration_under_600_verified"])
  self.assertFalse(checked["speech_to_element_semantic_alignment_verified"])
  self.assertFalse(checked["student_publication_authorized"])
  self.assertEqual(before,{f.name:hashlib.sha256(f.read_bytes()).hexdigest()
                           for f in self.orig.iterdir()})
 def test_forged_timing_or_promoted_receipt_fails_closed(self):
  stage_original_multipart_review(folder=self.orig,output=self.staged)
  p=self.staged/"multipart_review_receipt.json"
  obj=json.loads(p.read_text())
  obj["student_publication_authorized"]=True
  p.write_text(json.dumps(obj))
  with self.assertRaises(FigureIdentityReviewRequired):
   independent_reaudit_multipart(folder=self.orig,staged=self.staged)
 def test_corrupt_staged_audio_detected(self):
  stage_original_multipart_review(folder=self.orig,output=self.staged)
  wav=self.staged/"part_01"/"narration.wav"
  with wav.open("r+b") as file:
   file.seek(80)
   b=file.read(1);file.seek(80);file.write(bytes([b[0]^0xff]))
  with self.assertRaises(FigureIdentityReviewRequired):
   independent_reaudit_multipart(folder=self.orig,staged=self.staged)
 def test_original_preflight_missing_source_never_approves(self):
  result=summarize_original_subtopic_readonly(self.root/"missing")
  self.assertEqual(result["status"],"ORIGINAL_WAV_PREFLIGHT_BLOCKED")
  self.assertFalse(result["publication_authorized"])
