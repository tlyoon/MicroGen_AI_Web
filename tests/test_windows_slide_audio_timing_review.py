"""Pure deterministic grouping/adversarial gates for genuine WAV review route."""
import unittest
from pathlib import Path
from selenium_pipeline.windows_slide_audio_timing_review import (
    groups_for_duration,SlideTimingReviewBlocked,_line)


class SlideAudioGroupingTests(unittest.TestCase):
    def test_exact_600_boundary_is_split(self):
        vals=[210.0,210.0,180.0,20.0]
        grouped=groups_for_duration(vals,max_part_seconds=570)
        self.assertEqual(grouped,[[1,2],[3,4]])
        self.assertTrue(all(sum(vals[x-1] for x in row)<600 for row in grouped))

    def test_compact_stable_contiguous_groups(self):
        vals=[69.0,70.0,110.0,100.0,90.0,80.0,20.0]
        rows=groups_for_duration(vals)
        self.assertEqual([v for row in rows for v in row],list(range(1,8)))
        self.assertEqual(len(rows),1)

    def test_multi_part_and_duration_rejection(self):
        vals=[110.0]*14
        rows=groups_for_duration(vals)
        self.assertEqual([v for row in rows for v in row],list(range(1,15)))
        self.assertEqual(len(rows),3)
        with self.assertRaises(SlideTimingReviewBlocked):
            groups_for_duration([float("nan")])
        with self.assertRaises(SlideTimingReviewBlocked):
            groups_for_duration([600.0])
        with self.assertRaises(SlideTimingReviewBlocked):
            groups_for_duration([1.0],max_part_seconds=600.0)

    def test_refuses_unsafe_ffconcat_path(self):
        with self.assertRaises(SlideTimingReviewBlocked):
            _line(Path("example' unsafe.png"))
        self.assertIn("file '",_line(Path("C:/safe directory/slide1.png")))

if __name__=="__main__":
    unittest.main()
