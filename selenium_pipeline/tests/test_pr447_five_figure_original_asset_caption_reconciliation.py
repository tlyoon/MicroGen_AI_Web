"""Figure caption/bitmap QA stays distinct from science and axis-label approval."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.original_five_figure_evidence_reconciliation import (
    reconcile, SOURCE_SHA, EXPECTED, STATUS
)
from selenium_pipeline.original_all41_38_source_academic_gap_reconciler import STATUS as GAP_STATUS

def fixture():
    figures=[]
    historic=[]
    records={}
    for (label,slide),page in EXPECTED.items():
        key=f"8.4_slide{slide}"
        name=f"Figure {label}.png"
        sha=(f"{slide:064x}")
        figures.append({
            "figure_id":label,"source_textbook_caption_page":page,
            "original_slide_number":slide,"original_named_figure_file":name,
            "original_asset_sha256":sha,
            "actual_embedded_slide_rect_pt":[30.,60.,210.,220.],
            "decoded_asset_pixels_identical_to_embedded_slide_bitmap":True,
            "mathematical_figure_labels_verified":False,
            "source_figure_semantics_approved":False
        })
        historic.append({"slide":key,"author_source_figure":name,
                        "author_figure_sha256":sha})
        records[key]={"actual_original_source_source_spoken_focus_scene_present":True}
    old={"status":GAP_STATUS,"student_publication_authorized":False,
         "full_original_production_gate_passed":False,
         "original_source_slides":41,
         "figure_identity_and_full_panel_label_worklist_for_this_register":historic,
         "detailed_original_slide_acceptance_deficits":records}
    source={"status":"FIVE_ORIGINAL_FIGURE_ASSETS_BITMAP_IDENTICAL_SOURCE_CAPTIONS_FOUND",
        "figure_asset_to_embedded_bitmap_identity_count":5,
        "original_source_pdf_sha256":SOURCE_SHA,
        "original_slides_pdf_sha256":"frozen-author",
        "full_figures_source_pdf_equivalence_accepted":False,
        "student_publication_authorized":False,"figures":figures}
    return old,source

class SourceFigureEvidenceReconciliationTests(unittest.TestCase):
    def _go(self,old,source):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            with patch("selenium_pipeline.original_five_figure_evidence_reconciliation._sha",
                       return_value=SOURCE_SHA), patch(
                       "selenium_pipeline.original_five_figure_evidence_reconciliation.figure_audit",
                       return_value=source):
                return reconcile(source_folder=root,prior_scholarly=old)

    def test_all_five_caption_and_embedded_bitmap_match_but_not_scholarship(self):
        old,source=fixture()
        result=self._go(old,source)
        self.assertEqual(result["status"],STATUS)
        self.assertEqual(result["figure_assets_with_confirmed_source_caption_and_author_render_identity"],5)
        self.assertEqual(result["figure_assets_with_full_source_panel_math_axis_spoken_completeness_approved"],0)
        self.assertFalse(result["student_publication_authorized"])
        for item in result["five_exact_original_caption_author_embedded_figure_identity_proofs"]:
            self.assertTrue(item["original_author_png_identical_to_rendered_slide_bitmap"])
            self.assertFalse(item["publisher_figure_all_math_symbols_and_axis_labels_verified"])

    def test_rejects_incorrect_asset_sha_even_with_matching_caption(self):
        old,source=fixture()
        old["figure_identity_and_full_panel_label_worklist_for_this_register"][0][
            "author_figure_sha256"]="bad-fingerprint"
        with self.assertRaises(FigureIdentityReviewRequired):
            self._go(old,source)

    def test_rejects_false_science_approval(self):
        old,source=fixture()
        source["figures"][0]["source_figure_semantics_approved"]=True
        with self.assertRaises(FigureIdentityReviewRequired):
            self._go(old,source)

    def test_rejects_synthetic_release_grant(self):
        old,source=fixture()
        old["student_publication_authorized"]=True
        with self.assertRaises(FigureIdentityReviewRequired):
            self._go(old,source)

if __name__=="__main__":
    unittest.main()
