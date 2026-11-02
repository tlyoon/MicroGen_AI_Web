"""Five additional genuine source-print angular glyphs, previous ten reused."""
import inspect,tempfile,unittest
from pathlib import Path
from selenium_pipeline.evidence_reuse_contract import EvidenceReuseBlocked
from selenium_pipeline.original_fig83_five_angular_glyph_pixel_proof import (
    STATUS,GROUPS,group_vector_bbox,audit,
)


class Fig83AngularPrintedSourceEvidence(unittest.TestCase):
    def test_publisher_math_font_pi_over_two_is_a_glyph_group_not_ocr_text(self):
        words=[(97.7,90.1,103.3,98.1,"p"),
               (98.5,99.0,102.5,107.0,"2")]
        self.assertEqual(group_vector_bbox(words,(96,106,89,109),("p","2")),
                         [97.7,90.1,103.3,107.0])

    def test_exact_minus_pi_over_two_uses_unicode_minus_printed_glyph(self):
        words=[(90.9,154.7,97.6,163.2,chr(0x2212)),
               (97.7,150.8,103.3,158.8,"p"),
               (98.5,159.6,102.5,167.6,"2")]
        self.assertEqual(group_vector_bbox(words,(89,105,149,170),("-","p","2")),
                         [90.9,150.8,103.3,167.6])

    def test_source_missing_or_duplicated_angle_font_glyph_is_not_pass(self):
        words=[(97.7,90.1,103.3,98.1,"p"),
               (98.5,99.0,102.5,107.0,"2")]
        with self.assertRaises(EvidenceReuseBlocked):
            group_vector_bbox(words,(96,106,89,109),("-","p","2"))
        with self.assertRaises(EvidenceReuseBlocked):
            group_vector_bbox(words+[(98.,100.,101.,105.,"2")],
                              (96,106,89,109),("p","2"))

    def test_genuinely_new_five_and_no_duplicate_sift_or_release(self):
        self.assertEqual(len(GROUPS),5)
        self.assertEqual(len(set(x[0] for x in GROUPS)),5)
        src=inspect.getsource(audit)
        self.assertNotIn("SIFT_create",src)
        self.assertNotIn("detectAndCompute",src)
        self.assertNotIn("knnMatch",src)
        self.assertIn("previous_frozen_source_glyphs_reused_unchanged",src)
        self.assertIn("registered_patch",src)
        self.assertIn('"complete_graph_curve_mathematical_geometry_certified":False',src)
        self.assertIn('"student_publication_authorized":False',src)
        self.assertIn("ANGULAR_BOUNDARY_GLYPH",STATUS)

    def test_missing_previous_scoped_original_verification_stops(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t)
            with self.assertRaises(EvidenceReuseBlocked):
                audit(original=folder,prior_ten=folder/"missing10.json",
                      registration=folder/"missing3panel.json")


if __name__=="__main__":
    unittest.main()
