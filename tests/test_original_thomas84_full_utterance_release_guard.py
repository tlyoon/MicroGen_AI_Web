"""Enforce original source utterance coverage, never promote preview MP4s."""
from __future__ import annotations
import unittest
from selenium_pipeline.original_thomas84_full_utterance_release_guard import (
    release_eligible,classify_utterance
)
class FullSourceReleaseGuard(unittest.TestCase):
    def test_incomplete_speech_mapping_never_releases(self):
        self.assertFalse(release_eligible({
            "actual_independently_audited_complete_videos":2,
            "historical_utterances_with_no_element_mapping":37,
            "all_source_audio_video_consistency_accepted":True,
            "actual_each_video_under_600s":True}))
    def test_fake_29_complete_highlight_is_not_source_math_approval(self):
        info=classify_utterance({
            "sentence_index":3,
            "spoken_original_fragment_sha256":"a"*64,
            "actual_recorded_word_start_second":1.0,
            "actual_recorded_word_end_second":3.0,
            "unique_target_review_priority":True,
            "candidate_targets":[{"original_pdf_element_id":"s003.text.002"}],
            "eligible_for_final_student_highlight":False,
            "speech_to_visible_math_semantics_approved":False,
        })
        self.assertFalse(info["student_release_eligible"])
        self.assertEqual(info["release_blocker_reason"],
                         "PDF_TARGET_CANDIDATE_NOT_MATH_SEMANTICALLY_APPROVED")
    def test_missing_acoustic_timing_reported_not_invented(self):
        info=classify_utterance({"sentence_index":1,
            "spoken_original_fragment_sha256":"a"*64,
            "actual_recorded_word_start_second":None,
            "actual_recorded_word_end_second":None,
            "unique_target_review_priority":False,
            "candidate_targets":[],
            "eligible_for_final_student_highlight":False,
            "speech_to_visible_math_semantics_approved":False})
        self.assertEqual(info["release_blocker_reason"],
                         "NO_INDEPENDENT_ACOUSTIC_WORD_TIMING")
    def test_false_source_approval_is_rejected(self):
        with self.assertRaises(ValueError):
            classify_utterance({"sentence_index":1,
                "eligible_for_final_student_highlight":True,
                "speech_to_visible_math_semantics_approved":True})
if __name__=="__main__":unittest.main()
