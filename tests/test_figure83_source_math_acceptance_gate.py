import unittest
from copy import deepcopy
from pathlib import Path
from selenium_pipeline.math_aware_slide5_figure_candidates import audit
from selenium_pipeline.figure83_source_math_acceptance_gate import evaluate_candidate_release
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

ROOT=Path(r'G:\My Drive\Projects\Thomas_calculus_13ed\8\8.4')
@unittest.skipUnless((ROOT/"source.pdf").is_file() and
                     (ROOT/"slides.pdf").is_file() and
                     (ROOT/"script.txt").is_file(),
                     "Real Thomas source/slide/script are only on authorized Dell-115")
class SourceMathAcceptanceFailClosedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.real=audit(source=ROOT/'source.pdf',slides=ROOT/'slides.pdf',
                       script=ROOT/'script.txt')
    def test_real_academic_and_technical_release_are_blocked(self):
        r=evaluate_candidate_release(self.real)
        self.assertEqual(r["named_review_anchor_count"],4)
        self.assertEqual(r["unresolved_utterance_count"],4)
        self.assertFalse(r["production_media_accepted"])
        self.assertFalse(r["student_publication_authorized"])
        self.assertEqual(r["verified_spoken_element_audio_jobs"],0)
        self.assertFalse(r["authorized_paid_tts_jobs"])
        self.assertIn("FULL_EXPRESSION_PIXEL_TEMPLATE_NOT_UNIQUELY_CORROBORATED",
                      r["release_blockers"])
    def test_false_permission_injection_rejected(self):
        for field in ("paid_tts_authorized","narration_to_panel_semantics_verified",
                      "complete_equation_label_and_axis_mathematics_verified"):
            d=deepcopy(self.real)
            d["utterances"][1][field]=True
            with self.assertRaises(FigureIdentityReviewRequired):
                evaluate_candidate_release(d)
    def test_false_global_permission_rejected(self):
        d=deepcopy(self.real);d["figure_element_tts_authorized"]=True
        with self.assertRaises(FigureIdentityReviewRequired):
            evaluate_candidate_release(d)
    def test_forged_ambiguous_math_target_rejected(self):
        d=deepcopy(self.real)
        d["utterances"][0]["candidate_ordered_graph_panel"]=1
        with self.assertRaises(FigureIdentityReviewRequired):
            evaluate_candidate_release(d)
    def test_duplicate_utterance_or_invalid_source_hash_rejected(self):
        d=deepcopy(self.real)
        d["utterances"][1]["utterance_id"]=d["utterances"][0]["utterance_id"]
        with self.assertRaises(FigureIdentityReviewRequired):
            evaluate_candidate_release(d)
        d=deepcopy(self.real);d["source_sha256"]="not-sha"
        with self.assertRaises(FigureIdentityReviewRequired):
            evaluate_candidate_release(d)
    def test_named_equation_box_escapes_rejected(self):
        d=deepcopy(self.real)
        x=next(e for e in d["utterances"] if e["candidate_ordered_graph_panel"] is not None)
        x["candidate_full_expression_bitmap_bbox_for_review"]=[100,10,20,30]
        with self.assertRaises(FigureIdentityReviewRequired):
            evaluate_candidate_release(d)

def _portable_review():
    def unit(uid,names,panel=None):
        return {"utterance_id":uid,
          "function_names_explicitly_spoken":names,
          "candidate_ordered_graph_panel":panel,
          "candidate_matched_operator_pixel_bbox_for_review":
              [10,10,20,20] if panel else None,
          "candidate_full_expression_bitmap_bbox_for_review":
              [5,5,40,30] if panel else None,
          "source_x_over_a_fraction_position_disambiguated":bool(panel),
          "source_full_expression_to_slide_operator_registration_consistent":bool(panel),
          "paid_tts_authorized":False,
          "narration_to_panel_semantics_verified":False,
          "complete_equation_label_and_axis_mathematics_verified":False}
    return {"figure_id":"8.3","source_sha256":"a"*64,
        "slides_sha256":"b"*64,"script_sha256":"c"*64,
        "original_slide_inverse_operator_glyph_correspondence_verified":True,
        "full_equation_operator_anchor_registration_consistent":True,
        "original_fraction_x_over_a_positions_independently_disambiguated":True,
        "full_equation_bitmap_pixel_uniqueness_verified":False,
        "figure_element_tts_authorized":False,
        "student_publication_authorized":False,
        "unique_single_function_hint_count":1,
        "unresolved_hint_count":1,
        "utterances":[unit("u1",["tangent"],1),unit("u2",[])]}

class PortableMathematicalPublicationFailClosedTests(unittest.TestCase):
    def test_review_candidates_never_authorize_paid_media(self):
        r=evaluate_candidate_release(_portable_review())
        self.assertFalse(r["production_media_accepted"])
        self.assertFalse(r["student_publication_authorized"])
        self.assertEqual(r["verified_spoken_element_audio_jobs"],0)
        self.assertEqual((r["named_review_anchor_count"],r["unresolved_utterance_count"]),(1,1))
    def test_injecting_semantic_or_paid_tts_false_approval_rejected(self):
        for name in ("paid_tts_authorized","narration_to_panel_semantics_verified",
                     "complete_equation_label_and_axis_mathematics_verified"):
            e=_portable_review()
            e["utterances"][0][name]=True
            with self.assertRaises(FigureIdentityReviewRequired):
                evaluate_candidate_release(e)
    def test_ambiguous_target_and_asset_fingerprint_forgery_rejected(self):
        e=_portable_review()
        e["utterances"][1]["candidate_ordered_graph_panel"]=2
        with self.assertRaises(FigureIdentityReviewRequired):
            evaluate_candidate_release(e)
        e=_portable_review()
        e["script_sha256"]="malformed"
        with self.assertRaises(FigureIdentityReviewRequired):
            evaluate_candidate_release(e)
