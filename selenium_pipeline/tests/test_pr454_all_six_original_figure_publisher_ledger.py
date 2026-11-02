import copy
import unittest
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.original_all_six_figure_source_evidence_ledger import aggregate
def fixtures():
    five={"status":"ORIGINAL_FIVE_FIGURE_PNG_SLIDE_CAPTION_IDENTITY_RECONCILED_SCIENCE_REVIEW_PENDING","student_publication_authorized":False,"original_source_pdf_sha256":"a"*64,"figure_assets_with_confirmed_source_caption_and_author_render_identity":5,"five_exact_original_caption_author_embedded_figure_identity_proofs":[]}
    three={"status":"ORIGINAL_THOMAS84_THREE_SOURCE_BODY_ARTWORK_MATCHES_NOT_FULL_SCIENCE","original_source_sha256":"a"*64,"student_publication_authorized":False,"three_unique_correct_textbook_page_visual_matches":3,"source_body_three_independent_figure_visual_witnesses":{}}
    two={"status":"ORIGINAL_FIGURE82_83_ALL_THREE_PANELS_TEXTBOOK_SOURCE_FEATURE_PROVEN_LABELS_PENDING","publisher_source_sha256":"a"*64,"original_figures_publisher_panel_visual_match_count":2,"student_publication_authorized":False,"two_exact_source_figure_panel_image_matches":{}}
    for n in range(2,7):
        key="8."+str(n);sha=(str(n)*64)[:64]
        five["five_exact_original_caption_author_embedded_figure_identity_proofs"].append({"figure":key,"original_slide_id":"8.4_slide"+str({2:4,3:6,4:10,5:13,6:15}[n]),"original_author_image_sha256":sha,"publisher_caption_number_source_verified":True,"original_author_png_identical_to_rendered_slide_bitmap":True})
        if n<4:two["two_exact_source_figure_panel_image_matches"][key]={"original_author_png_sha256":sha,"all_three_source_image_panel_artwork_correspondence_proven":True,"geometric_RANSAC_inliers":42,"per_panel_matched_source_feature_inliers":[12,15,15]}
        else:three["source_body_three_independent_figure_visual_witnesses"][key]={"author_original_png_sha256":sha,"original_author_png_to_textbook_source_body_visual_pattern_match":True,"source_visual_normalized_correlation":.84,"source_visual_page_margin":.32}
    tank={"status":"ORIGINAL_THOMAS86_EXERCISE62_SOURCE_FIGURE_MATH_VERIFIED_NONPRODUCTION","student_publication_authorized":False,"author_exercise_62_png_sha256":"b1e379795edfadb88088fb41f63bfc5c4d1475e4d8dad3e11670b5336b8c340f","author_source_image_same_publisher_visual_verified":True,"symbolic_volume_derivative_equals_2L_sqrt_2rd_minus_d_squared":True,"all_original_figure_panel_labels_word_timed":False,"normalized_matching_correlation":.89}
    academic={"status":"UPDATED_ORIGINAL_THOMAS_41_38_SPOKEN_FOCUS_SCHOLARLY_GAPS_NONPRODUCTION","student_publication_authorized":False,"original_source_slides":41,"original_source_pixel_and_audio_math_focus_slides":38,"source_images_inventory_total":6}
    return dict(five=five,three=three,two=two,tank=tank,academic=academic)
class CrossFigureLedgerTests(unittest.TestCase):
    def test_six_images_not_all_science(self):
        r=aggregate(**fixtures())
        self.assertEqual(len(r["six_independently_version_bound_figure_identity_receipts"]),6)
        self.assertEqual(r["source_figure_identity_missing_count"],0)
        self.assertFalse(r["student_publication_authorized"])
        self.assertEqual(r["source_figure_full_symbol_axes_label_and_spoken_semantic_approval_count"],0)
    def test_rejects_weak_one_panel_mapping(self):
        f=fixtures();f["two"]["two_exact_source_figure_panel_image_matches"]["8.3"]["per_panel_matched_source_feature_inliers"]=[30,12,0]
        with self.assertRaises(FigureIdentityReviewRequired):aggregate(**f)
    def test_rejects_wrong_source_art_png_sha(self):
        f=fixtures();f["three"]["source_body_three_independent_figure_visual_witnesses"]["8.5"]["author_original_png_sha256"]="wrong"
        with self.assertRaises(FigureIdentityReviewRequired):aggregate(**f)
    def test_rejects_any_released_old_evidence(self):
        f=fixtures();f["academic"]["student_publication_authorized"]=True
        with self.assertRaises(FigureIdentityReviewRequired):aggregate(**f)
if __name__=="__main__":unittest.main()
