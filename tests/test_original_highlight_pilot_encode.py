"""Real original-WAV encoded highlight REVIEW pilot, not semantic alignment."""
from __future__ import annotations
import hashlib,struct,tempfile,unittest,wave
from pathlib import Path
import pymupdf
from selenium_pipeline.original_highlight_pilot_encode import stage_original_slide_highlight_pilot
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

class EncodedHighlightPilotTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.original=self.root/"original"
        self.original.mkdir()
        self.pdf=self.original/"slides.pdf"
        self.wav=self.original/"slide1.wav"
        self.out=self.root/"separate_candidate"
        with pymupdf.open() as doc:
            page=doc.new_page(width=400,height=300)
            page.insert_text((40,70),"First narration element")
            page.insert_text((40,180),"Second narration element")
            doc.save(self.pdf)
        signal=[1000]*20000+[0]*6000+[900]*20000
        with wave.open(str(self.wav),"wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(10000)
            w.writeframes(struct.pack(f"<{len(signal)}h",*signal))

    def test_real_encoded_video_and_decoded_highlight_samples(self):
        original=(hashlib.sha256(self.pdf.read_bytes()).hexdigest(),
                  hashlib.sha256(self.wav.read_bytes()).hexdigest())
        r=stage_original_slide_highlight_pilot(
            slides=self.pdf,wav=self.wav,slide_index=1,output=self.out)
        self.assertGreater(r["actual_encoded_mp4_duration_s"],4)
        self.assertLess(r["actual_encoded_mp4_duration_s"],5)
        self.assertTrue(r["all_sampled_encoded_highlight_pixels_plausible"])
        self.assertFalse(r["spoken_element_alignment_verified"])
        self.assertFalse(r["student_publication_authorized"])
        self.assertTrue((self.out/"slide_highlight_review.mp4").is_file())
        self.assertEqual(original,(
            hashlib.sha256(self.pdf.read_bytes()).hexdigest(),
            hashlib.sha256(self.wav.read_bytes()).hexdigest()))

    def test_existing_destination_refuses_overwrite(self):
        self.out.mkdir()
        (self.out/"keep.txt").write_text("unchanged")
        with self.assertRaises(FigureIdentityReviewRequired):
            stage_original_slide_highlight_pilot(
                slides=self.pdf,wav=self.wav,slide_index=1,output=self.out)
        self.assertEqual((self.out/"keep.txt").read_text(),"unchanged")

    def test_candidate_cannot_live_in_original_folder(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            stage_original_slide_highlight_pilot(
                slides=self.pdf,wav=self.wav,slide_index=1,
                output=self.original/"output")
