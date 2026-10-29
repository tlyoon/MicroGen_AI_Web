"""Real original-source and actual PCM-frame-timed 5-element media tests.

Synthetic test-only PCM tones check the technical pipeline, not text-to-speech,
Kore voice, academia, semantic sync, or student-ready courseware.
"""
import hashlib
import math
import os
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from selenium_pipeline.original_slide4_real_pcm_chunk_highlight import (
    inspect_five_original_pcm_chunks,encode_actual_chunk_highlight_review,
)
from selenium_pipeline.original_slide4_real_pcm_chunk_highlight import (
    VerifiedChunkVideoError,
)


class RealChunkHighlightContract(unittest.TestCase):
    def original(self):
        o=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        b=os.environ.get("MICROGEN_CORRECTED_SLIDE4_HANDOFF")
        if not o or not b:
            self.skipTest("Genuine source and visual handoff available only on Dell-115")
        return Path(o),Path(b)

    def test_actual_original_missing_all_corrected_audio_fails_closed(self):
        original,bundle=self.original()
        with tempfile.TemporaryDirectory() as td:
            source={name:hashlib.sha256((original/name).read_bytes()).hexdigest()
                    for name in ("source.pdf","slides.pdf","script.txt","slide4.wav")}
            with self.assertRaises((VerifiedChunkVideoError,ValueError)):
                inspect_five_original_pcm_chunks(
                    original=original,bundle=bundle,audio_dir=Path(td))
            self.assertEqual(source,{
                name:hashlib.sha256((original/name).read_bytes()).hexdigest()
                for name in source})

    def test_real_source_images_synthetic_tones_only_never_approve_voice_or_words(self):
        original,bundle=self.original()
        before={name:hashlib.sha256((original/name).read_bytes()).hexdigest()
                for name in ("source.pdf","slides.pdf","script.txt","slide4.wav","slides.mp4")}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            audio=root/"fixture_pcm"
            audio.mkdir()
            durations=(0.8,1.1,1.5,0.9,1.3)
            sample_rate=24000
            for i,dur in enumerate(durations,1):
                dest=audio/f"new_Kore_utterance_{i:03d}.wav"
                count=int(dur*sample_rate)
                pcm=bytearray()
                for j in range(count):
                    value=int(8000*math.sin(2*math.pi*(180+i*23)*j/sample_rate))
                    pcm.extend(struct.pack("<h",value))
                with wave.open(str(dest),"wb") as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(sample_rate)
                    w.writeframes(bytes(pcm))
            out=root/"fixture_only_review_video"
            report=encode_actual_chunk_highlight_review(
                original=original,bundle=bundle,audio_dir=audio,output_dir=out)
            self.assertEqual(len(report["decoded_element_frame_samples"]),5)
            self.assertEqual(len(report["units"]),5)
            self.assertTrue(report["five_source_highlight_switches_tied_to_actual_WAV_chunks"])
            self.assertEqual(report["timestamp_basis"],
                             "REAL_UNMODIFIED_CANDIDATE_WAV_FRAME_BOUNDARIES")
            self.assertFalse(report["spoken_words_match_corrected_text_verified"])
            self.assertFalse(report["voice_Kore_or_provider_verified"])
            self.assertFalse(report["source_math_independently_two_pass_approved"])
            self.assertFalse(report["student_publication_authorized"])
            self.assertAlmostEqual(report["duration_s"],sum(durations),places=3)
            self.assertLess(report["actual_encoded_duration_s"],600)
            self.assertTrue((out/report["actual_encoded_video_name"]).is_file())
            self.assertTrue(all(x["decoded_pixel_error"]<20 for x in
                                report["decoded_element_frame_samples"]))
        self.assertEqual(before,{
            name:hashlib.sha256((original/name).read_bytes()).hexdigest()
            for name in before})
if __name__=="__main__":
    unittest.main()
