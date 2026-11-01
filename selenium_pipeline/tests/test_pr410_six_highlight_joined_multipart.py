"""Six source-correct highlights integrated without weakening release gates."""
import unittest
from selenium_pipeline.original_thomas84_multipart_qa_preview import (
    HIGHLIGHTS,PROVENANCE,BLOCKERS,split_slides)
from selenium_pipeline.original_thomas84_slide4_three_equation_sync import (
    TRIG,TIMED_SENTENCES)

class SixSourceHighlightedSlidesContract(unittest.TestCase):
    def test_real_verified_six_slide_set(self):
        self.assertEqual(sorted(HIGHLIGHTS),[4,5,6,9,12,17])
        self.assertEqual(len(set(range(1,18))-set(HIGHLIGHTS)),11)

    def test_slide4_has_independent_source_audio_and_pixel_receipts(self):
        self.assertEqual(PROVENANCE[4],(
            "ORIGINAL_SLIDE4_THREE_MATH_EQUATIONS_INDEPENDENT_PIXEL_QA_PASS",
            "actual_mp4_sha256"))
        self.assertEqual(TRIG,("tangent","sine","secant"))
        self.assertEqual(TIMED_SENTENCES,(2,3,4))

    def test_unapproved_figure_and_other_elements_stay_blocked(self):
        self.assertIn(
            "ELEVEN_SLIDES_STILL_LACK_CERTIFIED_ELEMENT_LEVEL_TIMED_HIGHLIGHTS",
            BLOCKERS)
        self.assertIn("NOT_AN_AUTOMATED_STUDENT_PRODUCTION_RELEASE",BLOCKERS)

    def test_real_wav_duration_plan_splits_under_600(self):
        # Original WAVs, with slide6/17 corrected PCM, as source evidence.
        pcm=[3.52,26.16,39.68,47.96,53.56,40.48,54.96,
             44.08,47.24,55.88,48.72,54.60,48.20,63.40,
             50.52,45.88,36.64]
        parts=split_slides(pcm)
        self.assertEqual([s for group in parts for s in group],list(range(1,18)))
        self.assertEqual(len(parts),2)
        self.assertTrue(all(sum(pcm[i-1] for i in group)<600 for group in parts))

if __name__=="__main__":
    unittest.main()
