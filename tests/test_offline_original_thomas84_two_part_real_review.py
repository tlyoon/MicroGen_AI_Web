"""Genuine Thomas 8.4 17-slide/two-actual-part *planning* and safety tests.

The two full MP4 encode is an explicit Windows/Dell acceptance command; the
ordinary CI does not silently synthesize hours of test movies or use a fake
textbook to certify real output.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import tempfile
import unittest

from selenium_pipeline.offline_original_thomas84_two_part_real_review import (
    MAX_SECONDS_EXCLUSIVE,
    encode_both_real_original_thomas84_review_parts,
    plan_real_original_thomas84_two_parts,
)


class OriginalSourceTwoRealVideos(unittest.TestCase):
    def input_paths(self):
        orig=os.environ.get("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        bundle=os.environ.get("MICROGEN_CORRECTED_SLIDE4_HANDOFF")
        audio=os.environ.get("MICROGEN_FIVE_NEW_KORE_CANDIDATES")
        if not orig or not bundle or not audio:
            self.skipTest("Genuine protected 8.4 sources and five real WAVs only on Dell")
        return Path(orig),Path(bundle),Path(audio)

    def test_nonexistent_source_and_candidate_audio_fails_before_new_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises((ValueError,FileNotFoundError)):
                plan_real_original_thomas84_two_parts(
                    original=root/"missing",bundle=root/"missing_bundle",
                    audio_dir=root/"missing_audio")
            forbidden=root/"not_created"
            with self.assertRaises((ValueError,FileNotFoundError)):
                encode_both_real_original_thomas84_review_parts(
                    original=root/"missing",bundle=root/"missing_bundle",
                    audio_dir=root/"missing_audio",out=forbidden)
            self.assertFalse(forbidden.exists())

    def test_real_original_all_17_slides_two_parts_in_source_order(self):
        root,bundle,audio=self.input_paths()
        originals={n:hashlib.sha256((root/n).read_bytes()).hexdigest()
                   for n in ("source.pdf","slides.pdf","script.txt",
                             "slide4.wav","slides.mp4")}
        plan=plan_real_original_thomas84_two_parts(
            original=root,bundle=bundle,audio_dir=audio)
        self.assertEqual(len(plan["parts"]),2)
        first,second=plan["parts"]
        self.assertEqual((first["first_slide"],first["last_slide"]),(1,8))
        self.assertEqual((second["first_slide"],second["last_slide"]),(9,17))
        self.assertEqual((first["whole_original_slide_media_count"],
                          first["source_highlighted_new_TTS_element_count"]),(7,5))
        self.assertEqual((second["whole_original_slide_media_count"],
                          second["source_highlighted_new_TTS_element_count"]),(9,0))
        self.assertEqual(sum(len(p["timeline_units"]) for p in plan["parts"]),21)
        self.assertTrue(all(p["estimated_real_PCM_s"]<540 for p in plan["parts"]))
        self.assertFalse(plan["all_seventeen_slides_have_true_element_level_synchronization"])
        self.assertFalse(plan["student_publication_authorized"])
        self.assertEqual(plan["source_hashes"],originals)
        self.assertEqual(originals,{n:hashlib.sha256((root/n).read_bytes()).hexdigest()
                                    for n in originals})

    def test_refuse_review_MP4_output_next_to_protected_original(self):
        root,bundle,audio=self.input_paths()
        # The source is on protected G:; output cannot be next to original.
        with self.assertRaisesRegex(ValueError,"external"):
            encode_both_real_original_thomas84_review_parts(
                original=root,bundle=bundle,audio_dir=audio,
                out=root.parent/"new_video_unacceptable_inside_protected_chapter")
        self.assertFalse((root.parent/"new_video_unacceptable_inside_protected_chapter").exists())


if __name__=="__main__":
    unittest.main()
