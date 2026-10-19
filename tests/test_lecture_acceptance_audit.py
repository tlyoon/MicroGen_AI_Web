"""Real-PDF read-only technical acceptance tests without paid services."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.lecture_acceptance_audit import (
    inspect_real_lecture_acceptance,
)
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired


class LectureAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source=self.root/"source.pdf"
        self.slides=self.root/"slides.pdf"
        with pymupdf.open() as source:
            page=source.new_page()
            page.insert_text((50,70),"FIGURE 8.3 Source diagram",fontsize=11)
            shape=page.new_shape()
            shape.draw_rect(pymupdf.Rect(50,90,130,170))
            shape.finish(color=(0,0,0))
            shape.commit()
            source.save(self.source)
        with pymupdf.open() as deck:
            page=deck.new_page()
            page.insert_text((50,70),"Figure 8.3 sample slide",fontsize=11)
            deck.save(self.slides)
        self.before=self.hashes()

    def hashes(self):
        return {str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.root.glob("*") if p.is_file()}

    def audit(self,**kwargs):
        args=dict(source=self.source,slides=self.slides,
                  lecture_folder=self.root,
                  source_page=1,slide_page=1,figure_id="8.3",
                  probe=None)
        args.update(kwargs)
        return inspect_real_lecture_acceptance(**args)

    def test_no_media_source_gaps_reported_no_acceptance(self):
        result=self.audit()
        self.assertEqual(result["status"],"TECHNICAL_ACCEPTANCE_BLOCKED")
        self.assertEqual(result["video_candidates"],[])
        self.assertFalse(result["source_figure_evidence_complete"])
        self.assertFalse(result["multipart_media_verified"])
        self.assertFalse(result["student_publication_permitted"])
        self.assertEqual(result["source_report"]["status"],
                         "PILOT_BLOCKED_MISSING_INDEPENDENT_FIGURE_GEOMETRY")
        self.assertEqual(self.before,self.hashes())

    def test_legacy_video_5999_not_accepted_without_highlight_proof(self):
        self.root.joinpath("slides.mp4").write_bytes(b"mock media")
        report=self.audit(probe=lambda path:599.9)
        movie=report["video_candidates"][0]
        self.assertTrue(movie["duration_below_strict_600_s"])
        self.assertTrue(movie["legacy_single_file"])
        self.assertFalse(movie["duration_measured_from_actual_media"])
        self.assertFalse(movie["technical_highlight_proven"])
        self.assertFalse(report["multipart_media_verified"])
        self.assertFalse(report["student_publication_permitted"])
        self.assertTrue(report["synthetic_duration_probe_used"])

    def test_exact_600_and_over_600_rejected(self):
        self.root.joinpath("slides.mp4").write_bytes(b"mock media")
        for seconds in (600.0,623.0,600.01):
            with self.subTest(seconds=seconds):
                report=self.audit(probe=lambda _:seconds)
                self.assertTrue(report["duration_violation_observed"])
                self.assertFalse(report["actual_video_duration_violation_found"])
                self.assertFalse(
                    report["video_candidates"][0]["duration_below_strict_600_s"])

    def test_missing_unreadable_mp4_fails_closed(self):
        self.root.joinpath("slides.mp4").write_bytes(b"not an mp4")
        result=self.audit(probe=lambda _:float("nan"))
        self.assertIsNone(result["video_candidates"][0]["duration_s"])
        self.assertFalse(result["multipart_media_verified"])
        self.assertFalse(result["student_publication_permitted"])

    def test_forged_completion_manifest_cannot_promote_lecture(self):
        (self.root/"lecture_completion.json").write_text(
            json.dumps({"schema_version":1,
                        "status":"accepted_synchronized_series"}),
            encoding="utf-8")
        report=self.audit()
        self.assertFalse(report["multipart_media_verified"])
        self.assertIsNotNone(report["multipart_media_failure_reason"])

    def test_part_video_even_short_has_no_encoded_pixel_proof(self):
        part=self.root/"part_01"
        part.mkdir()
        (part/"part_01.mp4").write_bytes(b"fake short media")
        report=self.audit(probe=lambda _:42.2)
        self.assertEqual(report["video_candidates"][0]["relative_path"],
                         "part_01/part_01.mp4")
        self.assertFalse(report["video_candidates"][0]["technical_highlight_proven"])
        self.assertFalse(report["student_publication_permitted"])

    def test_malformed_figure_and_cross_directory_source_rejected(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            self.audit(figure_id="8.3; echo unsafe")
        outsider=self.root.parent/"external_source.pdf"
        # Do not create external file; outside root path itself is rejected.
        with self.assertRaises(FigureIdentityReviewRequired):
            self.audit(source=outsider)


if __name__=="__main__":
    unittest.main()
