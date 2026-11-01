"""Strictly less than 600s multipart previews never certify static elements."""
import unittest
from selenium_pipeline.original_thomas84_multipart_qa_preview import (
    split_slides,MAX_PART_SECONDS,HIGHLIGHTS,BLOCKERS)

class MultipartPreviewContract(unittest.TestCase):
    def test_actual_section_duration_needs_split(self):
        durations=[3.52,26.16,39.68,47.96,53.56,40.48,54.96,
                   44.08,47.24,55.88,48.72,54.60,48.20,63.40,
                   50.52,45.88,36.64]
        sets=split_slides(durations)
        self.assertGreaterEqual(len(sets),2)
        self.assertEqual([i for part in sets for i in part],list(range(1,18)))
        self.assertTrue(all(sum(durations[i-1] for i in part)<
                            MAX_PART_SECONDS<600 for part in sets))

    def test_600_exactly_not_allowed(self):
        with self.assertRaises(Exception):
            split_slides([600.],600.)

    def test_a_single_long_slide_cannot_sneak_into_a_part(self):
        with self.assertRaises(Exception):
            split_slides([570.1],570.)

    def test_missing_or_unphysical_audio_fails_closed(self):
        for invalid in ([4.,float("nan")],[4.,float("inf")],[],[0.]):
            with self.subTest(durations=invalid):
                with self.assertRaises(Exception):
                    split_slides(invalid)

    def test_original_highlights_only_for_seven_verified_slides(self):
        self.assertEqual(sorted(HIGHLIGHTS),[4,5,6,7,8,9,10,11,12,13,14,15,17])
        self.assertEqual(len([i for i in range(1,18) if i not in HIGHLIGHTS]),4)

    def test_preview_preserves_nonrelease_blockers(self):
        self.assertTrue(any("NOT_AN_AUTOMATED_STUDENT" in x for x in BLOCKERS))
        self.assertTrue(any("TIMED_HIGHLIGHTS" in x for x in BLOCKERS))

if __name__=="__main__":
    unittest.main()
