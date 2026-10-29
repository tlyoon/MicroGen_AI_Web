"""Real original source math glyph and encoded highlighted MP4 audit."""
from __future__ import annotations
import os,tempfile,unittest,hashlib
from pathlib import Path
from selenium_pipeline.original_figure82_raster_math_packet import (
    render_original_figure82_glyph_packet,
)
from selenium_pipeline.offline_original_slide4_highlight_mp4 import (
    create_original_slide4_highlight_pilot,OriginalVideoPilotError,
)

class GenuineSourceFigureAndHighlightPilot(unittest.TestCase):
    def inputs(self):
        folder=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        bundle=os.environ.get("MICROGEN_CORRECTED_SLIDE4_HANDOFF")
        if not folder or not bundle:
            self.skipTest("Actual Thomas 8.4 textbook/slide4 originals on Dell-115 only")
        return Path(folder),Path(bundle)

    def test_absent_actual_original_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises((ValueError,FileNotFoundError)):
                render_original_figure82_glyph_packet(
                    folder=Path(td)/"no-original",
                    output_dir=Path(td)/"images")
            with self.assertRaises((ValueError,FileNotFoundError)):
                create_original_slide4_highlight_pilot(
                    original=Path(td)/"no-original",
                    bundle=Path(td)/"no-bundle",
                    output_dir=Path(td)/"highlight")

    def test_real_source_figure82_radical_pixels_not_fabricated(self):
        folder,_=self.inputs()
        originals={x:hashlib.sha256((folder/x).read_bytes()).hexdigest()
                   for x in ("source.pdf","slides.pdf","script.txt","slide4.wav")}
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"genuine_original_figure82"
            result=render_original_figure82_glyph_packet(
                folder=folder,output_dir=out)
            self.assertTrue((out/result["actual_source_png"]).is_file())
            self.assertEqual(result["source_physical_page"],1)
            self.assertEqual(result["source_sha256"],originals["source.pdf"])
            self.assertFalse(result["source_glyph_math_independently_two_pass_approved"])
            self.assertFalse(result["student_publication_authorized"])
        self.assertEqual(originals,{x:hashlib.sha256((folder/x).read_bytes()).hexdigest()
                                    for x in originals})

    def test_real_encoded_five_source_highlights_still_unsynced(self):
        folder,bundle=self.inputs()
        originals={x:hashlib.sha256((folder/x).read_bytes()).hexdigest()
                   for x in ("source.pdf","slides.pdf","script.txt","slide4.wav","slides.mp4")}
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"real_slide4_review_video"
            result=create_original_slide4_highlight_pilot(
                original=folder,bundle=bundle,output_dir=out)
            self.assertEqual(result["actual_encoded_pixel_sample_count"],5)
            self.assertTrue(all(x["original_pdf_highlight_pixels_recovered"]
                                for x in result["actual_encoded_pixel_samples"]))
            self.assertFalse(result["actual_utterance_to_spoken_audio_alignment_verified"])
            self.assertFalse(result["student_publication_authorized"])
            self.assertLess(result["actual_encoded_review_mp4_duration_s"],600)
            self.assertTrue((out/result["actual_review_mp4_file"]).is_file())
        self.assertEqual(originals,{x:hashlib.sha256((folder/x).read_bytes()).hexdigest()
                                    for x in originals})
if __name__=="__main__":
    unittest.main()
