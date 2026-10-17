"""Verify receipt-hash-matched original archived MP4s using fresh decoded pixels.

All examples create real H.264 audio-video parts with local FFmpeg. Tests use
an independent frozen-source technical bundle and NEVER issue paid requests,
write source files, create lecturer approval or publish student media.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import patch

import test_recover_frozen_highlight_review as frozen_fixture
from selenium_pipeline.highlight_video_preview import ffmpeg_path
from selenium_pipeline.recheck_archived_highlight_mp4 import audit_archived
from selenium_pipeline.recover_frozen_highlight_review import (
    PreservedReviewRecoveryError,
)
from test_recover_frozen_highlight_review import sha, snapshot


class ArchivedReviewPixelVerificationTests(unittest.TestCase):
    def setUp(self):
        fixture = frozen_fixture.RecoveryFromFrozenInputsTests(
            "test_preflight_matches_all_source_and_original_wav_hashes")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        try:
            self.exe = ffmpeg_path()
        except Exception as exc:
            self.skipTest("Offline FFmpeg required: " + str(exc))
        self.recovered = fixture.destination
        from selenium_pipeline.recover_frozen_highlight_review import recover
        recover(**fixture.arguments, destination=self.recovered)
        self.archive = fixture.destination.parent/"historical_archive"
        self.archive.mkdir()
        rendered = self.recovered/"rendered"
        self.receipt = self.archive/"series_review_receipt.json"
        shutil.copy2(rendered/"series_review_receipt.json", self.receipt)
        self.videos = []
        for index in (1,2):
            part = f"part_{index:02d}"
            target = self.archive/f"{part}_ARCHIVED_REVIEW_ONLY.mp4"
            shutil.copy2(rendered/part/f"{part}_review.mp4", target)
            self.videos.append(target)
        self.args = dict(**fixture.arguments,rebuilt_review=self.recovered,
                         archived_receipt=self.receipt,
                         archived_mp4s=self.videos)

    def test_original_mp4_fresh_pixels_timing_and_duration_without_writes(self):
        before = snapshot(self.fixture.case.root)
        saved_review = snapshot(self.recovered)
        saved_archive = snapshot(self.archive)
        result = audit_archived(**self.args)
        self.assertEqual(
            result["status"],
            "ORIGINAL_ARCHIVED_MP4_FRESH_PIXEL_RECHECK_TECHNICAL_ONLY")
        self.assertTrue(result["original_archived_mp4s_independently_redecoded"])
        self.assertEqual(result["covered_slides"],3)
        self.assertEqual(result["covered_narrated_elements"],3)
        self.assertEqual([x["narrated_events"] for x in result["archived_parts"]],[2,1])
        self.assertTrue(all(x["independent_original_mp4_pixel_checks"] == x["narrated_events"]
                            for x in result["archived_parts"]))
        self.assertTrue(all(0<x["decoded_encoded_duration_s"]<600
                            for x in result["archived_parts"]))
        self.assertTrue(all(x["max_original_frame_start_drift_s"]<=.15
                            for x in result["archived_parts"]))
        for flag in ("audible_spoken_text_verified",
                     "scientific_semantic_mapping_approved",
                     "human_listening_approved","production_approved",
                     "student_published"):
            self.assertIs(result[flag],False)
        self.assertEqual(before,snapshot(self.fixture.case.root))
        self.assertEqual(saved_review,snapshot(self.recovered))
        self.assertEqual(saved_archive,snapshot(self.archive))

    def test_historical_mp4_byte_tamper_refused(self):
        self.videos[0].write_bytes(self.videos[0].read_bytes()+b"tamper")
        before = snapshot(self.archive)
        with self.assertRaisesRegex(PreservedReviewRecoveryError,
                                    "archived MP4 differs"):
            audit_archived(**self.args)
        self.assertEqual(before,snapshot(self.archive))

    def test_forged_historical_video_receipt_refused(self):
        d = json.loads(self.receipt.read_text())
        d["parts"][0]["mp4_sha256"]="0"*64
        self.receipt.write_text(json.dumps(d))
        with self.assertRaisesRegex(PreservedReviewRecoveryError,
                                    "archived MP4 differs"):
            audit_archived(**self.args)

    def test_historical_source_plan_binding_mismatch_refused(self):
        d = json.loads(self.receipt.read_text())
        d["plan_sha256"]="a"*64
        self.receipt.write_text(json.dumps(d))
        with self.assertRaisesRegex(PreservedReviewRecoveryError,
                                    "series receipt is unbound"):
            audit_archived(**self.args)

    def test_archived_video_missing_or_reordered_is_refused(self):
        with self.assertRaisesRegex(PreservedReviewRecoveryError,
                                    "MP4 count or uniqueness"):
            audit_archived(**{**self.args,"archived_mp4s":self.videos[:1]})
        with self.assertRaisesRegex(PreservedReviewRecoveryError,
                                    "archived MP4 differs"):
            audit_archived(**{**self.args,"archived_mp4s":self.videos[::-1]})

    def test_corrupt_archived_pixels_rejected_despite_updated_archive_sha(self):
        # Forge BOTH the archived video and its SHA in the archive receipt.
        # The independent source reference frames must still catch the
        # visual defect when the decoded video shows only black.
        broken=self.archive/"black_reencoded.mp4"
        subprocess.run([
            self.exe,"-hide_banner","-loglevel","error","-y",
            "-i",str(self.videos[0]),"-vf","drawbox=c=black:t=fill",
            "-c:v","libx264","-preset","ultrafast","-c:a","copy",
            str(broken),
        ],check=True,capture_output=True,text=True,timeout=120)
        bad_bytes=broken.read_bytes()
        self.videos[0].write_bytes(bad_bytes)
        broken.unlink()
        doc=json.loads(self.receipt.read_text())
        doc["parts"][0]["mp4_sha256"]=sha(self.videos[0])
        self.receipt.write_text(json.dumps(doc))
        before=snapshot(self.archive)
        with self.assertRaisesRegex(Exception,
                                    "no verified target highlight|Encoded event"):
            audit_archived(**self.args)
        self.assertEqual(before,snapshot(self.archive))

    def test_exactly_600_second_encoded_mp4_fails_closed(self):
        from selenium_pipeline.recheck_archived_highlight_mp4 import probe_mp4
        def pretend(path, *, exe):
            observed=probe_mp4(path,exe=exe)
            observed["duration_s"]=600.0
            return observed
        before=snapshot(self.archive)
        with patch("selenium_pipeline.recheck_archived_highlight_mp4.probe_mp4",
                   side_effect=pretend):
            with self.assertRaisesRegex(PreservedReviewRecoveryError,
                                        "duration/alignment"):
                audit_archived(**self.args)
        self.assertEqual(before,snapshot(self.archive))

    def test_archived_reference_narration_mismatch_refused(self):
        d = json.loads(self.receipt.read_text())
        d["parts"][0]["wav_sha256"]="1"*64
        self.receipt.write_text(json.dumps(d))
        with self.assertRaisesRegex(PreservedReviewRecoveryError,
                                    "audio/storyboard"):
            audit_archived(**self.args)


if __name__=="__main__":
    unittest.main()
