"""Independent source provenance candidate: distinct technical != academic approval."""
from __future__ import annotations

import unittest
from unittest.mock import patch
from pathlib import Path

from selenium_pipeline.windows_second_source_candidate import (
    compare_source_provenance,
)


class WindowsDistinctSecondSourceTests(unittest.TestCase):
    def historic(self):
        return {
            "status": "ONE_SCOPED_HISTORICAL_ORIGINAL_FULL_MEDIA_ACCEPTANCE_REUSED",
            "accepted_scoped_original_source_count": 1,
            "source_sha256": "a" * 64,
            "new_independent_second_source_accepted": False,
            "student_publication_authorized": False,
        }

    def media(self, source="b" * 64):
        return {
            "status": "EXACT_SOURCEBOUND_MP4_TECHNICAL_EVIDENCE_VERIFIED_ONLY",
            "source_sha256": source,
            "technical_sourcebound_mp4_verified": True,
            "decoded_mp4_parts_verified": 2,
            "full_lecture_release_authorized": False,
            "student_publication_authorized": False,
            "new_model_or_tts_calls": False,
        }

    def test_different_sha_and_verified_mp4_is_only_technical_candidate(self):
        r = compare_source_provenance(
            historic=self.historic(), candidate=self.media())
        self.assertEqual(r["status"],
                         "DISTINCT_SECOND_SOURCE_TECHNICAL_MEDIA_FOR_INDEPENDENT_REVIEW")
        self.assertTrue(r["distinct_original_source_sha256_verified"])
        self.assertTrue(r["technical_second_source_candidate_ready_for_academic_review"])
        self.assertFalse(r["second_distinct_original_academic_acceptance_verified"])
        self.assertFalse(r["independent_human_math_figure_audio_signoff"])
        self.assertFalse(r["release_authorized"])
        self.assertFalse(r["student_publication_authorized"])
        self.assertFalse(r["new_model_or_tts_calls"])

    def test_identical_original_never_becomes_second(self):
        r = compare_source_provenance(
            historic=self.historic(), candidate=self.media("a" * 64))
        self.assertEqual(r["status"], "SAME_ORIGINAL_SOURCE_CANNOT_BE_SECOND_CANDIDATE")
        self.assertFalse(r["technical_second_source_candidate_ready_for_academic_review"])

    def test_missing_old_anchor_or_no_media_stays_incomplete(self):
        for hist, cand in (
            (None, self.media()),
            (self.historic(), None),
            ({"source_sha256": "a"*64}, self.media()),
            (self.historic(), {"source_sha256": "b"*64}),
        ):
            with self.subTest(hist=bool(hist), cand=bool(cand)):
                r = compare_source_provenance(historic=hist, candidate=cand)
                self.assertEqual(r["status"], "SECOND_SOURCE_PROVENANCE_INCOMPLETE")
                self.assertFalse(r["technical_second_source_candidate_ready_for_academic_review"])

    def test_invalid_prior_approval_or_published_source_fails_closed(self):
        for key, value in (
            ("new_independent_second_source_accepted", True),
            ("student_publication_authorized", True),
            ("accepted_scoped_original_source_count", 2),
            ("status", "fake"),
            ("source_sha256", "notsha"),
        ):
            with self.subTest(key=key):
                hist = self.historic()
                hist[key] = value
                r = compare_source_provenance(historic=hist, candidate=self.media())
                self.assertFalse(r["technical_second_source_candidate_ready_for_academic_review"])

    def test_tainted_media_outcome_cannot_be_academic_review_candidate(self):
        for key, value in (
            ("technical_sourcebound_mp4_verified", False),
            ("decoded_mp4_parts_verified", 0),
            ("decoded_mp4_parts_verified", True),
            ("full_lecture_release_authorized", True),
            ("student_publication_authorized", True),
            ("new_model_or_tts_calls", True),
            ("status", "MOCK_APPROVED"),
            ("source_sha256", "notsha"),
        ):
            with self.subTest(key=key):
                media = self.media()
                media[key] = value
                r = compare_source_provenance(historic=self.historic(), candidate=media)
                self.assertFalse(r["technical_second_source_candidate_ready_for_academic_review"])


if __name__ == "__main__":
    unittest.main()
