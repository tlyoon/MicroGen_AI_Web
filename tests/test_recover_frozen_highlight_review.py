"""Real FFmpeg synthetic checks for nondestructive historical review recovery."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from selenium_pipeline.element_narration_stage import canonical,prepare
from selenium_pipeline.highlight_video_preview import ffmpeg_path
from selenium_pipeline.read_only_video_review_audit import audit_existing
from selenium_pipeline.recover_frozen_highlight_review import (
    PreservedReviewRecoveryError, preflight, recover,
)

import test_generic_element_highlight_workflow as source_fixture


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(root):
    return {str(x.relative_to(root)): sha(x)
            for x in root.rglob("*") if x.is_file()}


class RecoveryFromFrozenInputsTests(unittest.TestCase):
    def setUp(self):
        fixture=source_fixture.GenericHighlightWorkflowTests(
            "test_valid_any_three_slide_two_part_scene_coverage")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.case=fixture
        root=fixture.root
        self.stage=root/"preserved_frozen_inputs"
        prepare(source_pdf=fixture.source,slides_pdf=fixture.slides,
                authored_json=fixture.plan,recorded_audio=fixture.audio,
                destination=self.stage)
        self.tts_receipt=root/"tts_synthesis_receipt.json"
        plan=json.loads(fixture.plan.read_text(encoding="utf-8"))
        segments=[]
        for part in plan["parts"]:
            for slide in part["slides"]:
                for item in slide["elements"]:
                    segments.append({
                        "filename":item["wav"],
                        "spoken_text_sha256":hashlib.sha256(
                            item["spoken_text"].encode("utf-8")).hexdigest(),
                        "wav_sha256":sha(fixture.audio/item["wav"]),
                        "model":"gemini-3.8-flash-lite-tts",
                        "voice":"Kore",
                    })
        self.tts_doc={
            "status":"real_gemini_tts_generated_review_only_word_fidelity_unverified",
            "original_plan_sha256":canonical(plan),
            "provider":"gemini",
            "model":"gemini-3.8-flash-lite-tts",
            "voice":"Kore",
            "same_declared_voice_all_segments":True,
            "audible_word_fidelity_verified":False,
            "segments":segments,
        }
        self.persist_receipt()
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.destination=Path(temp.name)/"isolated_recovery"
        self.arguments=dict(
            source=fixture.source,slides=fixture.slides,
            authored=fixture.plan,frozen=self.stage,
            synthesis_receipt=self.tts_receipt)

    def persist_receipt(self):
        self.tts_receipt.write_text(
            json.dumps(self.tts_doc),encoding="utf-8")

    def test_preflight_matches_all_source_and_original_wav_hashes(self):
        before=snapshot(self.case.root)
        result=preflight(**self.arguments)
        self.assertEqual(result["part_count"],2)
        self.assertEqual(result["audio_elements"],3)
        self.assertEqual(len(result["bindings"]),3)
        self.assertEqual(before,snapshot(self.case.root))
        self.assertFalse(self.destination.exists())

    def test_changed_single_wav_blocks_before_creating_destination(self):
        original=self.stage/"part_01"/"wav"/"n1.wav"
        original.write_bytes(original.read_bytes()+b"tamper")
        with self.assertRaisesRegex(PreservedReviewRecoveryError,"WAV differs"):
            recover(**self.arguments,destination=self.destination)
        self.assertFalse(self.destination.exists())

    def test_removed_source_bound_receipt_blocks_any_render(self):
        self.tts_doc["original_plan_sha256"]="0"*64
        self.persist_receipt()
        with self.assertRaisesRegex(PreservedReviewRecoveryError,
                                    "No source-bound"):
            recover(**self.arguments,destination=self.destination)
        self.assertFalse(self.destination.exists())

    def test_output_inside_preserved_tree_is_forbidden(self):
        with self.assertRaisesRegex(PreservedReviewRecoveryError,
                                    "must not contain or overwrite"):
            recover(**self.arguments,
                    destination=self.case.root/"inside_originals")
        self.assertFalse((self.case.root/"inside_originals").exists())

    def test_real_offline_rebuild_has_3_verified_highlights_and_no_source_writes(self):
        try:
            ffmpeg_path()
        except Exception as exc:
            self.skipTest(f"FFmpeg unavailable: {exc}")
        before=snapshot(self.case.root)
        result=recover(**self.arguments,destination=self.destination)
        self.assertEqual(result["status"],
                         "ISOLATED_REBUILT_MEDIA_TECHNICALLY_CHECKED_ONLY")
        self.assertEqual(result["covered_slides"],3)
        self.assertEqual(result["covered_elements"],3)
        self.assertEqual([p["narrated_highlight_events"] for p in result["parts"]],
                         [2,1])
        self.assertTrue(all(p["encoded_pixels_rechecked"] for p in result["parts"]))
        self.assertTrue(all(p["encoded_duration_s"]<600 for p in result["parts"]))
        self.assertIs(result["archive_mp4s_independently_redecoded"],False)
        self.assertIs(result["real_tts_audio_transcription_verified"],False)
        self.assertIs(result["student_published"],False)
        self.assertEqual(before,snapshot(self.case.root))
        archived=snapshot(self.destination)
        rechecked=audit_existing(
            source=self.case.source,slides=self.case.slides,
            authored=self.case.plan,
            audio=self.destination/"frozen_original_element_audio",
            review_root=self.destination)
        self.assertEqual(rechecked["covered_elements"],3)
        self.assertEqual(archived,snapshot(self.destination))
        with self.assertRaisesRegex(PreservedReviewRecoveryError,"new isolated"):
            recover(**self.arguments,destination=self.destination)


if __name__=="__main__":
    unittest.main()
