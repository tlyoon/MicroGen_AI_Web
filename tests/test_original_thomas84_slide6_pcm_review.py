"""Four physical real-word windows must reconstruct every original sample."""
from __future__ import annotations
import unittest
from selenium_pipeline.original_thomas84_slide6_pcm_review import windows_for_steps
class Slide6RealPCMTimeWindows(unittest.TestCase):
    def test_full_source_coverage_four_measured_steps(self):
        rows=windows_for_steps(45.0,[(5.31,13.74,1),(18.09,26.13,2),
                                      (26.16,31.38,3),(32.04,42.03,4)])
        self.assertEqual([i for _,_,i in rows if i],[1,2,3,4])
        self.assertAlmostEqual(sum(b-a for a,b,_ in rows),45)
        self.assertEqual(rows[0][0],0)
        self.assertEqual(rows[-1][1],45)
    def test_overlap_rejected(self):
        with self.assertRaises(ValueError):
            windows_for_steps(50,[(1,8,1),(7,10,2),(20,30,3),(35,40,4)])
    def test_wrong_step_order_rejected(self):
        with self.assertRaises(ValueError):
            windows_for_steps(50,[(1,8,1),(9,20,3),(21,30,2),(35,40,4)])
    def test_small_gap_attached_without_losing_samples(self):
        r=windows_for_steps(50,[(5,10,1),(10.05,20,2),(22,30,3),(35,48,4)])
        self.assertAlmostEqual(sum(b-a for a,b,_ in r),50)
    def test_missing_step_refused(self):
        with self.assertRaises(ValueError):
            windows_for_steps(50,[(5,10,1),(20,30,2)])
if __name__=="__main__":unittest.main()
