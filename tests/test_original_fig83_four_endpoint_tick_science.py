"""PR467: four new nonzero printed source ticks, no repeat art similarity."""
import inspect,tempfile,unittest
from pathlib import Path
from selenium_pipeline.evidence_reuse_contract import EvidenceReuseBlocked
from selenium_pipeline.original_fig83_four_nonzero_tick_pixel_proof import (
  pick_tick,audit,TICKS,STATUS,
)


class FrozenOriginalFourEndpointGlyphTests(unittest.TestCase):
    def test_unicode_source_minus_is_mathematically_not_a_new_glyph(self):
        words=[(72.8,246.56,83.5,255.1,chr(0x2212)+"1"),
               (127.5,247.1,131.5,255.1,"1")]
        self.assertEqual(pick_tick(words,"-1",(70,90,242,258))[:2],
                         [72.8,246.56])
        self.assertEqual(pick_tick(words,"1",(124,136,242,258))[:2],
                         [127.5,247.1])

    def test_absent_or_ambiguous_old_source_endpoint_blocks(self):
        with self.assertRaises(EvidenceReuseBlocked):
            pick_tick([(1,2,3,4,"1")],"1",(70,90,242,258))
        words=[(70,247,75,256,"1"),(80,247,85,256,"1")]
        with self.assertRaises(EvidenceReuseBlocked):
            pick_tick(words,"1",(69,90,242,258))
        with self.assertRaises(EvidenceReuseBlocked):
            pick_tick(words,"2",(69,90,242,258))

    def test_these_are_four_new_labels_not_repeated_previous_six(self):
        self.assertEqual(len(TICKS),4)
        self.assertEqual([n for n,_,_,_ in TICKS],[
            "2_arcsine_negative_one","2_arcsine_positive_one",
            "3_arcsecant_negative_one","3_arcsecant_positive_one"])
        body=inspect.getsource(audit)
        self.assertNotIn("SIFT_create",body)
        self.assertNotIn("detectAndCompute",body)
        self.assertNotIn("knnMatch",body)
        self.assertIn("registered_patch",body)
        self.assertIn("reused_existing_six_source_label_glyph_receipt_sha256",body)
        self.assertIn('"student_publication_authorized":False',body)

    def test_stale_immutable_original_or_prior_six_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t)
            with self.assertRaises(EvidenceReuseBlocked):
                audit(original=d,previous_six=d/"never.json",
                      registration=d/"no_registration.json")

    def test_publisher_artwork_identity_is_not_equated_with_full_graph_approval(self):
        self.assertIn("FOUR_PRINTED_ENDPOINT",STATUS)
        self.assertIn('"complete_all_pi_half_curve_axes_and_spoken_times_certified":False',
                      inspect.getsource(audit))


if __name__=="__main__":
    unittest.main()
