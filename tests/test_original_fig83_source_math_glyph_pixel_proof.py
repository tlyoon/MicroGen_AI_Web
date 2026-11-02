"""Unit regressions for new source-printed Figure 8.3 glyph science scope.

No previous SIFT re-run or new source art identity campaign. No original
PDF files in GitHub CI; physical source/pixel audit is on Dell-115 only.
"""
import inspect
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from selenium_pipeline.evidence_reuse_contract import EvidenceReuseBlocked
from selenium_pipeline.original_fig83_six_printed_glyph_pixel_proof import (
    STATUS, registered_patch, audit, _source_word,
)


class OriginalFigure83ActualGlyphTests(unittest.TestCase):
    def setUp(self):
        self.author=np.full((120,130),255,np.uint8)
        cv2.putText(self.author,"tan-1",(12,28),
                    cv2.FONT_HERSHEY_SIMPLEX,.55,0,2,cv2.LINE_AA)
        self.h=np.array([[2.,0,0],[0,2.,0],[0,0,1]],dtype=float)
        self.bbox=(10.,10.,62.,34.)

    def test_independent_source_printed_function_label_pixel_match(self):
        proof=registered_patch(author=self.author,source_warp=self.author.copy(),
                homography=self.h,box=self.bbox,min_correlation=.78)
        self.assertAlmostEqual(
            proof["registered_normalized_source_to_author_gray_correlation"],1.)
        self.assertTrue(proof[
            "this_exact_source_printed_glyph_has_original_author_bitmap_pixel_evidence"])

    def test_erased_glyph_fails_even_if_previous_panel_artwork_claim_passed(self):
        changed=self.author.copy()
        changed[9:37,9:67]=255
        with self.assertRaises(EvidenceReuseBlocked):
            registered_patch(author=changed,source_warp=self.author,
                  homography=self.h,box=self.bbox,min_correlation=.78)

    def test_wrong_glyph_shape_cannot_pass(self):
        changed=self.author.copy()
        changed[9:37,9:67]=255
        cv2.putText(changed,"sin-1",(12,28),
                    cv2.FONT_HERSHEY_SIMPLEX,.55,0,2,cv2.LINE_AA)
        with self.assertRaises(EvidenceReuseBlocked):
            registered_patch(author=changed,source_warp=self.author,
                  homography=self.h,box=self.bbox,min_correlation=.92)

    def test_source_words_are_tied_to_exact_page_location(self):
        class FakePage:
            def get_text(self,kind):
                self.seen=kind
                return [(1.,3.,19.,11.,"tan−1"),
                        (60.,30.,74.,39.,"tan−1")]
        p=FakePage()
        self.assertEqual(_source_word(p,"tan",0,25,0,20),
                         [1.,3.,19.,11.])
        with self.assertRaises(EvidenceReuseBlocked):
            _source_word(p,"tan",0,80,0,80)
        self.assertEqual(p.seen,"words")

    def test_missing_real_original_source_and_prior_receipt_fail_closed(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with self.assertRaises(EvidenceReuseBlocked):
                audit(original=root,registration_receipt=root/"missing.json")

    def test_no_redo_of_prior_source_artwork_registration_or_broader_release(self):
        code=inspect.getsource(audit)
        self.assertNotIn("detectAndCompute",code)
        self.assertNotIn("knnMatch",code)
        self.assertNotIn("SIFT_create",code)
        self.assertIn("warpPerspective",code)
        self.assertIn('"all_nonzero_ticks_axis_shapes_and_curve_mathematics_certified":False',
                      code)
        self.assertIn('"all_spoken_fig83_label_word_times_certified":False',code)
        self.assertIn('"student_publication_authorized":False',code)
        self.assertIn("GLYPH_PATCHES",STATUS)


if __name__=="__main__":
    unittest.main()
