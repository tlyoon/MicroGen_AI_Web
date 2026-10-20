"""Independent source-and-encoded-media audit; no synthetic passes promoted."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import pymupdf

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.joint_original_lecture_acceptance import (
    inspect_joint_original_lecture, main,
)


class JointOriginalLectureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        with pymupdf.open() as doc:
            page = doc.new_page(width=610, height=700)
            page.draw_line((30, 140), (182, 285))
            page.insert_text((30, 405), "FIGURE 8.3", fontsize=11)
            page.insert_text((30, 423), "Original graphs of inverse trig functions")
            page.draw_rect(pymupdf.Rect(210, 435, 520, 560))
            for y in (449, 469, 489):
                page.insert_text((220, y), "Procedure for trigonometric substitution")
            doc.save(self.folder / "source.pdf")
        with pymupdf.open() as doc:
            page = doc.new_page(width=640, height=360)
            page.insert_text((45, 45), "Lecture slide with a drawn figure")
            page.draw_rect(pymupdf.Rect(70, 80, 340, 250))
            doc.save(self.folder / "slides.pdf")

    def audit(self):
        return inspect_joint_original_lecture(
            folder=self.folder, source_page=1,
            slide_page=1, figure_id="8.3")

    def test_no_verified_media_stays_blocked_and_source_is_unchanged(self):
        original = {name: hashlib.sha256((self.folder / name).read_bytes()).hexdigest()
                    for name in ("source.pdf", "slides.pdf")}
        report = self.audit()
        self.assertEqual(report["status"], "JOINT_ORIGINAL_LECTURE_ACCEPTANCE_BLOCKED")
        self.assertFalse(report["multipart_media_verified"])
        self.assertEqual(report["video_candidates"], [])
        self.assertIn("UNVERIFIED_SPEECH_TIMED_MULTIPART_HIGHLIGHTS",
                      report["blocker_codes"])
        for key in ("complete_figure_and_panels_certified",
                    "source_to_slide_equivalence_certified",
                    "spoken_element_highlight_certified",
                    "all_video_parts_strictly_under_600_certified",
                    "human_academic_qa_certified",
                    "student_publication_authorized"):
            self.assertFalse(report[key])
        for name, digest in original.items():
            self.assertEqual(hashlib.sha256((self.folder / name).read_bytes()).hexdigest(), digest)

    def test_optional_staged_event_reaudit_is_not_original_media_approval(self):
        from selenium_pipeline import joint_original_lecture_acceptance as mod
        original = {name: hashlib.sha256((self.folder/name).read_bytes()).hexdigest()
                    for name in ("source.pdf", "slides.pdf")}
        fake = {
            "source_sha256": original["source.pdf"],
            "slides_sha256": original["slides.pdf"],
            "student_publication_authorized":False,
            "audio_to_element_semantic_correspondence_verified":False,
            "status":"ALL_ENCODED_EVENTS_INDEPENDENTLY_VERIFIED_SPOKEN_SEMANTICS_UNPROVEN",
            "total_provisional_highlight_events":4,
            "all_events_encoded_pixel_recheck_count":4,
        }
        with patch.object(mod,"verify_full_staged_element_coverage",
                          return_value=fake) as checked:
            report = inspect_joint_original_lecture(
                folder=self.folder, source_page=1, slide_page=1,
                figure_id="8.3", staged_review=self.folder.parent/"external_staging")
        self.assertTrue(checked.called)
        self.assertTrue(checked.call_args.kwargs["check_all_pixels"])
        self.assertEqual(report["staged_highlight_event_review"]["total_events"],4)
        self.assertIn(
            "STAGED_REVIEW_EVENT_PIXELS_VERIFIED_SPOKEN_ELEMENT_ALIGNMENT_MISSING",
            report["blocker_codes"])
        self.assertFalse(report["spoken_element_highlight_certified"])
        self.assertFalse(report["student_publication_authorized"])

    def test_staged_review_cannot_forge_published_alignment(self):
        from selenium_pipeline import joint_original_lecture_acceptance as mod
        with patch.object(mod,"verify_full_staged_element_coverage",
                          return_value={
                              "source_sha256": hashlib.sha256(
                                  (self.folder/"source.pdf").read_bytes()).hexdigest(),
                              "slides_sha256": hashlib.sha256(
                                  (self.folder/"slides.pdf").read_bytes()).hexdigest(),
                              "student_publication_authorized":True,
                              "audio_to_element_semantic_correspondence_verified":True,
                          }):
            with self.assertRaises(FigureIdentityReviewRequired):
                inspect_joint_original_lecture(
                    folder=self.folder,source_page=1,slide_page=1,
                    figure_id="8.3",staged_review=self.folder.parent/"external_staging")

    def test_missing_slides_fails_closed(self):
        (self.folder / "slides.pdf").unlink()
        with self.assertRaises(FigureIdentityReviewRequired):
            self.audit()
    def test_invalid_source_figure_fails_closed(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            inspect_joint_original_lecture(
                folder=self.folder, source_page=1,
                slide_page=1, figure_id="8.5")

    def test_forged_synthetic_media_probe_never_promotes(self):
        from selenium_pipeline import joint_original_lecture_acceptance as mod
        actual = mod.inspect_real_lecture_acceptance
        def fake_probe(**kwargs):
            observed = actual(**kwargs)
            observed["synthetic_duration_probe_used"] = True
            return observed
        with patch.object(mod, "inspect_real_lecture_acceptance",
                          side_effect=fake_probe):
            with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                        "Synthetic|synthetic|actual"):
                self.audit()

    def test_cli_reports_blocked_exit_code(self):
        self.assertEqual(main([
            "--folder", str(self.folder),
            "--source-page", "1",
            "--slide-page", "1",
            "--figure-id", "8.3",
        ]), 2)

    def test_available_original_wav_plan_is_actionable_not_encoded_acceptance(self):
        with wave.open(str(self.folder/"slide1.wav"),"wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(100)
            f.writeframes(bytes(200*100))
        receipt=self.audit()
        self.assertTrue(receipt["source_bound_wav_repair_plan_available"])
        proposal=receipt["original_wav_multipart_repair_plan"]
        self.assertEqual(proposal["proposed_part_count"],1)
        self.assertEqual(proposal["proposed_parts"][0]["slide_start"],1)
        self.assertFalse(receipt["replacement_encoded_mp4_created"])
        self.assertFalse(receipt["replacement_highlighted_mp4_verified"])
        self.assertFalse(receipt["student_publication_authorized"])

    def test_missing_slide_wav_plan_is_named_blocker_not_crash(self):
        receipt=self.audit()
        self.assertFalse(receipt["source_bound_wav_repair_plan_available"])
        self.assertIn("MISSING_OR_INVALID_ORIGINAL_SLIDE_WAV_BOUNDARY_EVIDENCE",
                      receipt["blocker_codes"])
        self.assertFalse(receipt["student_publication_authorized"])

    def test_forged_original_wav_plan_hash_cannot_bypass_acceptance(self):
        from selenium_pipeline import joint_original_lecture_acceptance as mod
        forged={
            "status":"ORIGINAL_SLIDE_WAV_MULTIPART_CANDIDATE_NOT_RENDERED",
            "source_sha256":"0"*64,
            "slides_sha256":"0"*64,
            "student_publication_authorized":False,
            "encoded_video_part_strictly_below_600_verified":False,
        }
        with patch.object(mod,"inspect_original_slide_wav_plan",return_value=forged):
            receipt=self.audit()
        self.assertFalse(receipt["source_bound_wav_repair_plan_available"])
        self.assertIn("MISSING_OR_INVALID_ORIGINAL_SLIDE_WAV_BOUNDARY_EVIDENCE",
                      receipt["blocker_codes"])
        self.assertFalse(receipt["all_video_parts_strictly_under_600_certified"])

    def test_corrupt_encoded_video_is_unmeasured_and_never_accepted(self):
        """Fake MP4 bytes must not gain a synthetic sub-600-second duration."""
        (self.folder / "slides.mp4").write_bytes(b"not an encoded video")
        report = self.audit()
        self.assertEqual(report["unmeasured_video_candidates"], ["slides.mp4"])
        self.assertIn("UNMEASURED_ENCODED_VIDEO", report["blocker_codes"])
        self.assertFalse(report["video_candidates"][0]["duration_measured_from_actual_media"])
        self.assertIsNone(report["video_candidates"][0]["duration_s"])

    def test_conflicting_source_sha_from_parallel_audit_rejected(self):
        from selenium_pipeline import joint_original_lecture_acceptance as mod
        actual = mod.inspect_real_lecture_acceptance
        def adversarial(**kwargs):
            observed = actual(**kwargs)
            observed["source_report"]["source_sha256"] = "0" * 64
            return observed
        with patch.object(mod, "inspect_real_lecture_acceptance",
                          side_effect=adversarial):
            with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                        "source hashes"):
                self.audit()

    def test_forged_publication_claim_rejected(self):
        from selenium_pipeline import joint_original_lecture_acceptance as mod
        actual = mod.inspect_real_lecture_acceptance
        def forged(**kwargs):
            observed = actual(**kwargs)
            observed["student_publication_permitted"] = True
            return observed
        with patch.object(mod, "inspect_real_lecture_acceptance",
                          side_effect=forged):
            with self.assertRaises(FigureIdentityReviewRequired):
                self.audit()
