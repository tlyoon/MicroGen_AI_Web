"""No-network math-aware audio/actual slide reviewer packet regressions."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import test_source_bound_narration_review_packet as original_fixture
from selenium_pipeline.flagged_narration_slide_review import build
from selenium_pipeline.recover_frozen_highlight_review import PreservedReviewRecoveryError


def hashes(root):
    return {str(p.relative_to(root)):
            hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()}


class FlaggedNarrationSlideReviewTests(unittest.TestCase):
    def setUp(self):
        f=original_fixture.SourceBoundNarrationPacketTests(
            "test_writes_complete_unapproved_html_csv_and_all_original_wavs")
        f.setUp()
        self.addCleanup(f.doCleanups)
        self.fixture=f
        self.kwargs=f.kwargs.copy()
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.destination=Path(temp.name)/"new_source_bound_slide_packet"

    def build(self, **changes):
        return build(destination=self.destination,**{**self.kwargs,**changes})

    def test_original_audio_with_actual_rendered_slide_image_is_review_only(self):
        originals=hashes(self.fixture.case.root)
        record=self.build()
        self.assertEqual(record["status"],
                         "ORIGINAL_SPEECH_AND_SLIDE_MATH_REVIEW_PENDING")
        self.assertEqual(record["all_original_recorded_wav_count"],3)
        self.assertEqual(record["flagged_wav_count"],1)
        self.assertEqual(record["flagged_clips"][0]["wav"],"s01_e01.wav")
        self.assertIs(record["student_published"],False)
        self.assertIs(record["academic_approval"],False)
        self.assertEqual(len(list((self.destination/"audio").glob("*.wav"))),1)
        self.assertEqual(len(list((self.destination/"slides").glob("*.png"))),1)
        self.assertTrue((self.destination/"slides"/"slide_01.png").read_bytes().startswith(
            b"\x89PNG"))
        self.assertEqual(record["flagged_clips"][0]["original_wav_sha256"],
            hashlib.sha256((self.destination/"audio"/"s01_e01.wav").read_bytes()).hexdigest())
        self.assertEqual(hashes(self.fixture.case.root),originals)
        html=(self.destination/"index.html").read_text(encoding="utf8")
        self.assertIn("<audio controls",html)
        self.assertIn("<img src='slides/slide_01.png'",html)
        self.assertIn("REVIEW ONLY",html)
        self.assertNotIn("human_listening_approved=true",html)

    def test_both_independent_flag_sources_form_union(self):
        name=self.fixture.qa["clips"][-1]["wav"]
        path=self.fixture.receipts/(name+".asr.json")
        q=json.loads(path.read_text())
        q["status"]="speech_review_required"
        path.write_text(json.dumps(q))
        report=self.build()
        self.assertEqual(report["flagged_wav_count"],2)
        self.assertEqual({x["wav"] for x in report["flagged_clips"]},
                         {"s01_e01.wav",name})
        self.assertEqual(len(list((self.destination/"slides").glob("*.png"))),2)

    def test_gemini_source_audio_hash_mismatch_aborts_without_output(self):
        self.fixture.qa["clips"][0]["wav_sha256"]="0"*64
        self.fixture.save()
        with self.assertRaisesRegex(PreservedReviewRecoveryError,
                                    "cannot be bound"):
            self.build()
        self.assertFalse(self.destination.exists())

    def test_offline_source_text_hash_mismatch_aborts(self):
        name=self.fixture.qa["clips"][0]["wav"]
        path=self.fixture.receipts/(name+".asr.json")
        row=json.loads(path.read_text())
        row["reference_sha256"]="0"*64
        path.write_text(json.dumps(row))
        with self.assertRaisesRegex(PreservedReviewRecoveryError,
                                    "cannot be bound"):
            self.build()
        self.assertFalse(self.destination.exists())

    def test_changed_slide_pdf_aborts_without_output(self):
        with self.fixture.case.slides.open("ab") as f:
            f.write(b"bad-mutation")
        with self.assertRaisesRegex(PreservedReviewRecoveryError,
                                    "Source or slides differ"):
            self.build()
        self.assertFalse(self.destination.exists())

    def test_refuse_output_inside_origins_or_reusing_output(self):
        with self.assertRaisesRegex(PreservedReviewRecoveryError,
                                    "inside or above original evidence"):
            build(destination=self.fixture.case.root/"unsafe",**self.kwargs)
        self.build()
        with self.assertRaisesRegex(PreservedReviewRecoveryError,
                                    "new isolated"):
            self.build()

    def test_transcript_html_is_escaped_and_never_executed(self):
        self.fixture.qa["clips"][0]["transcript"]="<script>alert('x')</script>"
        self.fixture.save()
        report=self.build()
        self.assertEqual(report["flagged_wav_count"],1)
        document=(self.destination/"index.html").read_text(encoding="utf8")
        self.assertNotIn("<script>",document)
        self.assertIn("&lt;script&gt;",document)

    def test_false_human_approval_in_prior_machine_record_aborts(self):
        self.fixture.qa["clips"][0]["human_listening_approved"]=True
        self.fixture.save()
        with self.assertRaisesRegex(PreservedReviewRecoveryError,
                                    "cannot be bound"):
            self.build()
        self.assertFalse(self.destination.exists())


if __name__=="__main__":
    unittest.main()
