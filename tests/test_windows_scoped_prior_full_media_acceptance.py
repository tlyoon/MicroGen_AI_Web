"""Historical accepted source proof reuse: exact SHA, no re-generation."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.windows_scoped_prior_full_media_acceptance import (
    verify_scoped, HistoricalScopeMismatch, _STATUS,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ReuseScopedSourceFullMediaTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.source = self.root / "source.pdf"
        self.slides = self.root / "slides.pdf"
        self.videos = [self.root / "one.mp4", self.root / "two.mp4"]
        for path in [self.source, self.slides, *self.videos]:
            path.write_bytes(b"%PDF accepted scope only" * 18)
        self.qa = self.root / "accepted_historical_qa.json"
        self.record = {
            "schema_version": 1,
            "status": _STATUS,
            "original_textbook_sha256": sha(self.source),
            "corrected_actual_source_pdf_sha256": sha(self.slides),
            "independently_audited_actual_final_movie_SHA256": [
                sha(p) for p in self.videos],
            "all_66_original_narration_meanings_referenced_to_actual_PDF": 66,
            "all_actual_final_movies_under_600_s": True,
            "math_source_automated_review_criteria_satisfied": True,
            "owner_flexible_soundalike_TTS_criteria_satisfied": True,
            "source_visual_element_relevance_criteria_satisfied": True,
            "actual_H264_AAC_media_integrity_criteria_satisfied": True,
            "three_requested_QA_checks_completed": True,
            "release_candidate_QA_gate_pass": True,
            "strict_no_original_source_or_prior_movie_overwrite": True,
            "publication_was_performed": False,
            "student_publication_authorized": False,
            "real_complete_movies_seconds": [426.89, 313.81],
            "independent_human_aural_voice_identity_certified": False,
        }
        self.save()

    def save(self):
        self.qa.write_text(json.dumps(self.record), encoding="utf8")
        self.anchor = {
            "qa_sha256": sha(self.qa),
            "source_sha256": sha(self.source),
            "slides_sha256": sha(self.slides),
            "movie_sha256": [sha(p) for p in self.videos],
        }

    def check(self):
        return verify_scoped(qa=self.qa, source=self.source,
                             slides=self.slides, movies=self.videos,
                             anchor=self.anchor)

    def test_accepted_previously_audited_source_does_not_need_redo(self):
        result = self.check()
        self.assertEqual(result["accepted_scoped_original_source_count"], 1)
        self.assertFalse(result["new_synthesis_or_media_generation"])
        self.assertFalse(result["new_independent_second_source_accepted"])
        self.assertFalse(result["student_publication_authorized"])

    def test_tampered_movie_rejected_without_regenerating(self):
        self.check()
        self.videos[0].write_bytes(b"corrupt " + self.videos[0].read_bytes())
        with self.assertRaises(HistoricalScopeMismatch):
            self.check()

    def test_different_unmatched_publisher_source_rejected(self):
        self.source.write_bytes(b"changed publisher source" * 15)
        with self.assertRaises(HistoricalScopeMismatch):
            self.check()

    def test_false_approval_cannot_be_hidden_in_self_declared_new_qa(self):
        self.record["student_publication_authorized"] = True
        self.save()
        with self.assertRaises(HistoricalScopeMismatch):
            self.check()

    def test_historical_under_600s_gate_mandatory(self):
        self.record["real_complete_movies_seconds"] = [601.0, 313.81]
        self.save()
        with self.assertRaises(HistoricalScopeMismatch):
            self.check()


if __name__ == "__main__":
    unittest.main()
