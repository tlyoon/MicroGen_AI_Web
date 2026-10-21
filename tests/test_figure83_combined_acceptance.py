import unittest
from selenium_pipeline.figure83_combined_acceptance import evaluate_combined_preflight
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired

def packet():
    return {"status":"ORIGINAL_FIGURE83_REVIEW_ONLY",
            "source_sha256":"a"*64,"slides_sha256":"b"*64,"script_sha256":"c"*64,
            "paid_tts_authorized":False,"student_publication_authorized":False,
            "review_utterances":[
             {"utterance_id":"u1","source_math_approved":False,
              "actual_spoken_timing_approved":False,
              "candidate_full_expression_pdf_bbox_pt":[5,5,15,15]},
             {"utterance_id":"u2","source_math_approved":False,
              "actual_spoken_timing_approved":False,
              "candidate_full_expression_pdf_bbox_pt":None}]}
def wav():
    return {"status":"ELEMENT_AUDIO_PHYSICAL_INTEGRITY_ONLY",
            "production_video_authorized":False,
            "spoken_element_timing_verified":False,
            "integrity_checked_clip_count":0,
            "element_audio_integrity_receipts":[]}
class CombinedLecturePreflightTests(unittest.TestCase):
    def test_review_only_no_wav_means_no_released_video(self):
        r=evaluate_combined_preflight(packet(),wav())
        self.assertEqual(r["candidate_math_review_anchor_count"],1)
        self.assertEqual(r["physically_verified_element_clip_count"],0)
        self.assertFalse(r["encoded_sub600_production_release_authorized"])
        self.assertFalse(r["paid_tts_authorized"])
        self.assertIn("ORIGINAL_UTTERANCES_LACK_INDEPENDENT_ELEMENT_WAVS",
                      r["remaining_blockers"])
    def test_untrusted_semantic_flags_rejected(self):
        p=packet();p["review_utterances"][0]["source_math_approved"]=True
        with self.assertRaises(FigureIdentityReviewRequired):
            evaluate_combined_preflight(p,wav())
    def test_duplicate_ids_and_forged_audio_approval_rejected(self):
        p=packet();p["review_utterances"][1]["utterance_id"]="u1"
        with self.assertRaises(FigureIdentityReviewRequired):
            evaluate_combined_preflight(p,wav())
        a=wav();a["production_video_authorized"]=True
        with self.assertRaises(FigureIdentityReviewRequired):
            evaluate_combined_preflight(packet(),a)
