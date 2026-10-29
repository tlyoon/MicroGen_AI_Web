"""Real decoded-MP4 regression for an EXISTING review bundle.

This uses genuine local FFmpeg/PyMuPDF encoding, never generated speech or
paid APIs, and asserts every audit leaves the original folder byte-for-byte
unchanged.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

import test_generic_element_highlight_workflow as generic
from selenium_pipeline.element_highlight_workflow import (
    HighlightReviewGateError, review,
)
from selenium_pipeline.read_only_video_review_audit import audit_existing


def file_state(root: Path) -> dict[str, str]:
    return {str(path.relative_to(root)):
            hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file()}


class ExistingReviewTechnicalAuditTests(unittest.TestCase):
    def case(self):
        case = generic.GenericHighlightWorkflowTests(
            "test_valid_any_three_slide_two_part_scene_coverage")
        case.setUp()
        self.addCleanup(case.doCleanups)
        return case

    def run_real_preview(self, case):
        from selenium_pipeline.highlight_video_preview import ffmpeg_path
        try:
            ffmpeg_path()
        except Exception as exc:
            self.skipTest("Real offline FFmpeg required: "+str(exc))
        review(
            source=case.source, slides=case.slides, authored=case.plan,
            audio=case.audio, output_root=case.output)

    def audit(self, case):
        return audit_existing(
            source=case.source, slides=case.slides, authored=case.plan,
            audio=case.audio, review_root=case.output)

    def test_reaudit_real_encoded_pixels_twice_without_writing_or_approving(self):
        case = self.case()
        self.run_real_preview(case)
        before = file_state(case.root)
        first = self.audit(case)
        second = self.audit(case)
        self.assertEqual(first, second)
        self.assertEqual(first["status"],
                         "EXISTING_VIDEO_REVIEW_TECHNICAL_RECHECK_ONLY")
        self.assertTrue(first["mp4_pixel_qa_fresh"])
        self.assertEqual(first["covered_slides"], 3)
        self.assertEqual(first["covered_elements"], 3)
        self.assertEqual(len(first["parts"]), 2)
        self.assertTrue(all(part["encoded_duration_s"] < 600
                            for part in first["parts"]))
        self.assertTrue(all(part["encoded_pixels_rechecked"]
                            for part in first["parts"]))
        for key in ("student_published", "production_approved",
                    "scientific_semantic_mapping_approved",
                    "human_listening_approved"):
            self.assertIs(first[key], False)
        self.assertEqual(before, file_state(case.root))
        self.assertFalse((case.output/"lecture_completion.json").exists())

    def test_altered_saved_highlight_reference_is_caught_on_fresh_redecode(self):
        case = self.case()
        self.run_real_preview(case)
        first = self.audit(case)
        self.assertTrue(first["mp4_pixel_qa_fresh"])
        part = case.output/"rendered"/"part_01"
        base = part/"scratch_frames"/"base_0001.png"
        active = part/"scratch_frames"/"event_0001.png"
        self.assertTrue(base.is_file() and active.is_file())
        active.write_bytes(base.read_bytes())
        changed = file_state(case.root)
        with self.assertRaisesRegex(Exception,
                                    "no verified target highlight|pixel"):
            self.audit(case)
        self.assertEqual(changed, file_state(case.root),
                         "Audit must not attempt to repair original defective frames")

    def test_stale_edited_mp4_never_passes_existing_bundle_audit(self):
        case = self.case()
        self.run_real_preview(case)
        mp4 = case.output/"rendered"/"part_01"/"part_01_review.mp4"
        original = mp4.read_bytes()
        mp4.write_bytes(original+b"tamper-after-encode")
        before = file_state(case.root)
        with self.assertRaisesRegex(HighlightReviewGateError,
                                    "Encoded video|changed"):
            self.audit(case)
        self.assertEqual(before, file_state(case.root))

    def test_strict_600_seconds_is_never_accepted(self):
        case = self.case()
        self.run_real_preview(case)
        from selenium_pipeline.element_highlight_workflow import probe_mp4
        original_probe = probe_mp4
        def measure(mp4, *, exe):
            data = original_probe(mp4, exe=exe)
            data["duration_s"] = 600.0
            return data
        before = file_state(case.root)
        with patch("selenium_pipeline.element_highlight_workflow.probe_mp4",
                   side_effect=measure):
            with self.assertRaisesRegex(HighlightReviewGateError,
                                        "strict ten-minute"):
                self.audit(case)
        self.assertEqual(before, file_state(case.root))

    def test_legacy_video_without_source_bound_review_cannot_be_audited(self):
        case = self.case()
        case.output.mkdir()
        (case.output/"slides.mp4").write_bytes(b"historical static media")
        before = file_state(case.root)
        with self.assertRaisesRegex(HighlightReviewGateError,
                                    "Existing staged review folder"):
            self.audit(case)
        self.assertEqual(before, file_state(case.root))


if __name__ == "__main__":
    unittest.main()
