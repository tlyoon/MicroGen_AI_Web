"""Fail-closed version diagnostics for publisher-original academic QA."""
import unittest

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.original_three_section_academic_remaining_inventory import (
    EXPECTED, SOURCE, require_pinned_original_section_version,
)


class OriginalAcademicSnapshotGate(unittest.TestCase):
    def test_accepts_exact_publisher_and_authored_video_fixture(self):
        for section in ("8.5", "8.6"):
            with self.subTest(section=section):
                require_pinned_original_section_version(
                    section=section, frame_count=EXPECTED[section],
                    publisher_sha=SOURCE[section]["publisher_sha"],
                    slides_pdf_sha=SOURCE[section]["slides_pdf_sha"])

    def test_rejects_regenerated_live_lectures_without_mutating_them(self):
        # Regression of real 2026-11-02 observation: source PDF unchanged,
        # authored frame count + slideshow PDF changed in the live Drive corpus.
        for section, observed_count in (("8.5", 20), ("8.6", 17)):
            with self.subTest(section=section):
                with self.assertRaises(FigureIdentityReviewRequired) as caught:
                    require_pinned_original_section_version(
                        section=section, frame_count=observed_count,
                        publisher_sha=SOURCE[section]["publisher_sha"],
                        slides_pdf_sha="new-version-not-the-pinned-source-pdf")
                reason=str(caught.exception)
                self.assertIn("PINNED_ORIGINAL_SOURCE_SNAPSHOT_MISMATCH", reason)
                self.assertIn("section="+section, reason)
                self.assertIn("FRAME_COUNT", reason)
                self.assertIn("AUTHOR_PDF_SHA", reason)
                self.assertNotIn("PUBLISHER_SHA", reason)
                self.assertIn("do not mutate live source", reason)

    def test_rejects_changed_publisher_even_with_original_slide_count(self):
        with self.assertRaises(FigureIdentityReviewRequired) as caught:
            require_pinned_original_section_version(
                section="8.5", frame_count=11,
                publisher_sha="untrusted-publisher-version",
                slides_pdf_sha=SOURCE["8.5"]["slides_pdf_sha"])
        self.assertIn("PUBLISHER_SHA", str(caught.exception))
        self.assertNotIn("FRAME_COUNT", str(caught.exception))

    def test_rejects_unknown_section_and_bad_84_frame_count(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            require_pinned_original_section_version(
                section="8.7",frame_count=1,publisher_sha="x",slides_pdf_sha="y")
        with self.assertRaises(FigureIdentityReviewRequired) as caught:
            require_pinned_original_section_version(
                section="8.4",frame_count=18,publisher_sha="x",slides_pdf_sha="y")
        self.assertIn("FRAME_COUNT expected=17 actual=18",str(caught.exception))


if __name__=="__main__":
    unittest.main()
