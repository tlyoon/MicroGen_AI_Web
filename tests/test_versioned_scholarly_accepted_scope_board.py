"""Version-aware original mathematics/figure/PCM acceptance board, fail-closed."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf
from selenium_pipeline.evidence_reuse_contract import EvidenceReuseBlocked,file_sha256
from selenium_pipeline.original_scholarly_scope_acceptance_version_board import (
    RECEIPTS,EXPECTED_SLIDES,STATUS,board,
)
from selenium_pipeline import recover_pinned_original_thomas_corpus


class ScienceReleaseScopeBoard(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.cp=Path(temp.name)/"evidence"
        self.root=Path(temp.name)/"source"
        self.cp.mkdir()
        self.root.mkdir()
        pins={}
        for section,n in EXPECTED_SLIDES.items():
            folder=self.root/section
            folder.mkdir()
            (folder/"source.pdf").write_bytes(("original-publisher-"+section).encode())
            (folder/"slides.tex").write_text("Original LaTeX for "+section)
            with pymupdf.open() as d:
                for i in range(n):d.new_page()
                d.save(folder/"slides.pdf")
            pins[section]=(file_sha256(folder/"source.pdf"),
                           file_sha256(folder/"slides.pdf"))
        patcher=patch.dict(recover_pinned_original_thomas_corpus.ORIGINAL_PINS,pins)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.sha84=pins["8.4"]
        fixture={
            "original_41_gap":{
                "original_source_slides":41,
                "original_source_pixel_and_audio_math_focus_slides":38,
                "true_original_spoken_element_samples_total":47,
                "student_publication_authorized":False,
                "full_original_production_gate_passed":False,
                "original_sections":{
                    x:{"at_least_one_verified_source_focus_slide_count":n}
                    for x,n in (("8.4",16),("8.5",10),("8.6",12))}},
            "all_six_figure_art":{
                "original_frozen_41_source_slides":41,
                "all_six_original_author_figure_source_artwork_matched":True,
                "source_figure_identity_missing_count":0,
                "student_publication_authorized":False},
            "original_86_math_wav_video":{
                "student_publication_authorized":False,
                "all_math_WAV_and_encoded_pixels_completely_certified":False,
                "accepted_scopes":{
                    x:{"reused_existing_pass_not_newly_recalculated":True}
                    for x in ("selected_exact_reduction_math",
                              "sampled_original_WAV_word_to_visual",
                              "actual_joined_mp4_decoded_source_pixels")}},
            "prior_corrected_84":{
                "prior_scope_decision":"REUSE_VERIFIED",
                "separate_original_author_version_decision":"TARGETED_REVALIDATION",
                "prior_original_corrected_66_source_cue_automated_review_accepted":True,
                "frozen_uncorrected_original_author_pdf_sha256":self.sha84[1],
                "prior_corrected_author_pdf_sha256":"f"*64,
                "student_publication_authorized":False},
            "original_83_first_six_labels":{
                "publisher_source_pdf_sha256":self.sha84[0],
                "original_author_slides_pdf_sha256":self.sha84[1],
                "three_inverse_function_labels_pixel_matched":3,
                "three_graph_axis_zero_tick_labels_pixel_matched":3,
                "student_publication_authorized":False},
            "original_83_five_angular_boundaries":{
                "status":"ORIGINAL_FIG83_FIVE_REAL_ANGULAR_BOUNDARY_GLYPH_GROUPS_AUTHOR_PIXEL_PASS_NONPRODUCTION",
                "original_source_sha256":self.sha84[0],
                "original_author_slides_sha256":self.sha84[1],
                "previous_frozen_source_glyphs_reused_unchanged":10,
                "five_new_angular_source_font_glyph_group_pixels":{
                    x:True for x in range(5)},
                "student_publication_authorized":False},
            "original_83_four_endpoints":{
                "publisher_source_sha256":self.sha84[0],
                "author_original_slides_sha256":self.sha84[1],
                "original_previous_glyphs_accepted_without_reanalysis":6,
                "reused_existing_registration_receipt_sha256":"e"*64,
                "newly_source_anchored_nonzero_ticks":{
                    x:True for x in range(4)},
                "student_publication_authorized":False},
        }
        self.fixture=fixture
        self._save_all()

    def _save(self,key):
        path=self.cp/RECEIPTS[key]
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(self.fixture[key]),encoding="utf8")

    def _save_all(self):
        # Physical immutable proof is chained six glyphs -> four endpoints
        # -> five angles, regardless of dictionary insertion order.
        for key in (k for k in self.fixture
                    if k!="original_83_five_angular_boundaries"):
            if key=="original_83_four_endpoints":
                self.fixture[key][
                    "reused_existing_six_source_label_glyph_receipt_sha256"
                ]=file_sha256(self.cp/RECEIPTS["original_83_first_six_labels"])
            self._save(key)
        key="original_83_five_angular_boundaries"
        self.fixture[key][
            "reused_previous_ten_glyphs_source_receipt_sha256"
        ]=file_sha256(self.cp/RECEIPTS["original_83_four_endpoints"])
        self.fixture[key][
            "reused_existing_source_image_registration_sha256"
        ]="e"*64
        self._save(key)

    def test_all_original_author_versions_and_corrected_84_remain_separate(self):
        b=board(checkpoint=self.cp,original=self.root)
        self.assertEqual(b["status"],STATUS)
        self.assertEqual(b["original_38_sampled_spoken_focus_slides_only"],38)
        self.assertEqual(b["original_83_specific_vector_printed_author_bitmap_glyphs_accepted"],15)
        self.assertEqual(b["original_six_figure_publisher_artwork_identities_already_accepted"],6)
        self.assertFalse(b["corrected_prior_author_84"]["same_author_pdf_as_frozen_original_84"])
        self.assertFalse(b["student_publication_authorized"])
        self.assertFalse(b["full_41_original_scholar_scientific_release_pass"])
        self.assertEqual(len(b["prior_immutable_receipt_sha256"]),7)
        self.assertEqual(b["new_original_graph_angular_printed_glyph_groups_verified"],5)

    def test_corrupt_previous_glyph_receipt_without_new_four_receipt_is_blocked(self):
        self.fixture["original_83_first_six_labels"][
            "three_inverse_function_labels_pixel_matched"]=2
        self._save("original_83_first_six_labels")
        with self.assertRaises(EvidenceReuseBlocked):
            board(checkpoint=self.cp,original=self.root)

    def test_publisher_or_author_modified_does_not_inherit_previous_acceptance(self):
        (self.root/"8.5"/"slides.tex").write_text("changed irrelevant TeX")
        # TeX is not SHA-pinned in this limited board; PDF/source identity is.
        b=board(checkpoint=self.cp,original=self.root)
        self.assertFalse(b["student_publication_authorized"])
        (self.root/"8.5"/"source.pdf").write_bytes(b"changed original publisher")
        with self.assertRaises(EvidenceReuseBlocked):
            board(checkpoint=self.cp,original=self.root)

    def test_publication_flag_in_prior_figure_is_forbidden(self):
        self.fixture["all_six_figure_art"]["student_publication_authorized"]=True
        self._save("all_six_figure_art")
        with self.assertRaises(EvidenceReuseBlocked):
            board(checkpoint=self.cp,original=self.root)


if __name__=="__main__":
    unittest.main()
