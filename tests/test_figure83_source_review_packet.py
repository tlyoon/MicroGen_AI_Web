import unittest,tempfile
from pathlib import Path
from selenium_pipeline.figure83_source_review_packet import assemble_review_packet,export_review_packet
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

def fake_review():
    entry=lambda uid,words,panel,box: {
        "utterance_id":uid,"original_narration":uid,
        "function_names_explicitly_spoken":words,"candidate_ordered_graph_panel":panel,
        "candidate_matched_operator_pixel_bbox_for_review":box,
        "candidate_full_expression_bitmap_bbox_for_review":box,
        "source_x_over_a_fraction_position_disambiguated":bool(panel),
        "source_full_expression_to_slide_operator_registration_consistent":bool(panel),
        "paid_tts_authorized":False,"narration_to_panel_semantics_verified":False,
        "complete_equation_label_and_axis_mathematics_verified":False}
    return {"figure_id":"8.3","source_sha256":"a"*64,"slides_sha256":"b"*64,
            "script_sha256":"c"*64,"original_slide_inverse_operator_glyph_correspondence_verified":True,
            "full_equation_operator_anchor_registration_consistent":True,
            "original_fraction_x_over_a_positions_independently_disambiguated":True,
            "full_equation_bitmap_pixel_uniqueness_verified":False,
            "figure_element_tts_authorized":False,"student_publication_authorized":False,
            "unique_single_function_hint_count":1,"unresolved_hint_count":1,
            "utterances":[entry("u1",["sine"],2,[10,5,30,15]),
                          entry("u2",[],None,None)]}
def place():
    return {"original_slides_sha256":"b"*64,"slide_page":5,
            "figure_coordinate_transform_verified":True,
            "figure_placement_pdf_pt":[10,20,210,120],
            "bitmap_dimensions_px":[200,100]}
class PacketTests(unittest.TestCase):
    def test_page_bound_hashed_packet(self):
        r=assemble_review_packet(review=fake_review(),placement=place())
        self.assertEqual(r["review_utterances"][0]["candidate_full_expression_pdf_bbox_pt"],
                         [20.,25.,40.,35.])
        self.assertIsNone(r["review_utterances"][1]["candidate_full_expression_pdf_bbox_pt"])
        self.assertEqual(len(r["packet_content_sha256"]),64)
        self.assertFalse(r["paid_tts_authorized"])
    def test_asset_mismatch_rejected(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            assemble_review_packet(review=fake_review(),placement={
                **place(),"original_slides_sha256":"z"*64})
    def test_export_new_file_only_outside_teaching_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            teaching=base/"original";teaching.mkdir()
            source=teaching/"source.pdf"
            evidence=assemble_review_packet(review=fake_review(),placement=place())
            target=base/"review.json"
            export_review_packet(evidence,output=target,originals=[source]*3)
            self.assertTrue(target.exists())
            with self.assertRaises(FileExistsError):
                export_review_packet(evidence,output=target,originals=[source]*3)
            with self.assertRaises(FigureIdentityReviewRequired):
                export_review_packet(evidence,output=teaching/"review.json",
                                     originals=[source]*3)
