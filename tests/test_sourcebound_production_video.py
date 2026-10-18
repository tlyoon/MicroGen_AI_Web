"""Real FFmpeg source-grounded production bridge tests, synthetic course only."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.element_highlight_workflow import review
from selenium_pipeline.sourcebound_production_video import (
    ProductionRenderError, accept_candidate, verify_production_candidate,
    install_new_production_parts,
)
from selenium_pipeline.production_video_contract import verify_series
from tests.test_generic_element_highlight_workflow import (
    GenericHighlightWorkflowTests as OriginalFixture,
)


def hash_file(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ProductionBridgeTests(unittest.TestCase):
    def setUp(self):
        self.fixture=OriginalFixture("test_valid_any_three_slide_two_part_scene_coverage")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f=self.fixture
        self.source,self.slides,self.plan,self.audio=f.source,f.slides,f.plan,f.audio
        self.original_folder=f.source_folder
        self.review_root=f.output
        self.root=f.root
        self.candidate=f.root/"accepted_candidate"
        self.original_hashes={p:hash_file(p) for p in
              (self.source,self.slides,self.plan,*self.audio.glob("*.wav"))}
        review(source=self.source,slides=self.slides,authored=self.plan,
               audio=self.audio,output_root=self.review_root)

    def accept(self):
        return accept_candidate(source=self.source,slides=self.slides,
                 authored=self.plan,audio=self.audio,
                 review_root=self.review_root,candidate=self.candidate)

    def assert_preserved(self):
        self.assertEqual(
            {p:hash_file(p) for p in self.original_hashes},
            self.original_hashes)

    def test_fresh_real_decoded_candidate_and_install(self):
        result=self.accept()
        self.assertEqual(result["status"],
                         "ACCEPTED_TECHNICAL_HIGHLIGHT_PRODUCTION_CANDIDATE")
        self.assertEqual(len(result["parts"]),2)
        self.assertFalse(result["student_published"])
        media=verify_production_candidate(self.candidate)
        self.assertEqual(media["status"],"accepted_synchronized_series")
        self.assertEqual(media["verification_scope"],"technical_media_only")
        self.assertLess(max(p["duration_s"] for p in media["parts"]),600)
        self.assertFalse((self.original_folder/"lecture_completion.json").exists())
        self.assert_preserved()
        installed=install_new_production_parts(
            candidate=self.candidate,subchapter=self.original_folder)
        self.assertEqual(installed["part_count"],2)
        self.assertTrue((self.original_folder/"lecture_completion.json").is_file())
        self.assertEqual(
            verify_series(self.original_folder)["status"],"accepted_synchronized_series")
        self.assert_preserved()
        self.assertFalse((self.original_folder/"lecture_human_approval.json").exists())
        with self.assertRaisesRegex(ProductionRenderError,"never be overwritten"):
            install_new_production_parts(candidate=self.candidate,
                                         subchapter=self.original_folder)
        self.assert_preserved()

    def test_normal_video_runner_uses_real_source_bound_production(self):
        import os
        import shutil
        from unittest.mock import patch
        from selenium_pipeline.runner import Settings, _execute_unlocked
        from selenium_pipeline.production_video_contract import verify_series

        # The completed element plan and every original element WAV exist
        # beside the source. There is no human approval or external TTS call.
        plan_file=self.original_folder/"element_narration_plan.json"
        plan_file.write_bytes(self.plan.read_bytes())
        wav_dir=self.original_folder/"element_wav"
        wav_dir.mkdir()
        for wav in self.audio.glob("*.wav"):
            shutil.copyfile(wav,wav_dir/wav.name)
        original=json.loads(self.plan.read_text(encoding="utf-8"))
        segments=[{
            "wav":piece["wav"],
            "sha256":hash_file(wav_dir/piece["wav"]),
            "spoken_text_sha256":hashlib.sha256(
                piece["spoken_text"].encode("utf-8")).hexdigest(),
            "provider":"gemini","model":"gemini-3.8-flash-lite-tts",
            "voice":"Kore",
        } for part in original["parts"] for page in part["slides"]
          for piece in page["elements"]]
        from selenium_pipeline.tts_effective_identity import DEFAULT
        from selenium_pipeline.runner import blocks
        rows=[piece["spoken_text"] for part in original["parts"]
              for page in part["slides"] for piece in page["elements"]]
        producer=wav_dir/"_producer"
        producer.mkdir()
        producer_text="".join(f"**Slide {i} [30s]:\n\n{text}\n\n"
                              for i,text in enumerate(rows,1))
        (producer/"script.txt").write_text(producer_text,encoding="utf8")
        producer_manifest={
            "version":2,"primary":DEFAULT,
            "slides":[{"slide":i,"source_text":txt,"tts_text":txt,
                       **DEFAULT,"fallback_used":False}
                      for i,txt in enumerate(rows,1)],
        }
        (producer/"tts_input_manifest.json").write_text(
            json.dumps(producer_manifest),encoding="utf8")
        certificate={
            "producer_manifest_sha256":hash_file(producer/"tts_input_manifest.json"),
            "producer_script_sha256":hash_file(producer/"script.txt"),
            "schema_version":1,
            "status":"verified_source_bound_element_audio",
            "source_sha256":hash_file(self.source),
            "slides_sha256":hash_file(self.slides),
            "authored_plan_sha256":hash_file(plan_file),
            "provider":"gemini","model":"gemini-3.8-flash-lite-tts",
            "voice":"Kore","all_elements_one_voice":True,
            "elements":segments}
        (self.original_folder/"element_tts_manifest.json").write_text(
            json.dumps(certificate),encoding="utf-8")
        temporary=self.root/"LOCALAPPDATA"
        temporary.mkdir()
        setting=Settings(source_root=self.root/"source",work_root=None,
                         subchapter="8.4",from_stage="video",through_stage="video")
        with patch("selenium_pipeline.runner.verify_source_tree"),patch.dict(
                os.environ,{"LOCALAPPDATA":str(temporary)}):
            _execute_unlocked(setting)
        self.assertEqual(
            verify_series(self.original_folder)["status"],
            "accepted_synchronized_series")
        self.assertFalse((self.original_folder/"lecture_human_approval.json").exists())
        self.assertFalse((self.original_folder/"slides.mp4").exists())
        self.assert_preserved()
        # Rerun must reuse verified accepted parts, not regenerate them.
        snapshot=hash_file(self.original_folder/"lecture_completion.json")
        with patch("selenium_pipeline.runner.verify_source_tree"),patch.dict(
                os.environ,{"LOCALAPPDATA":str(temporary)}):
            _execute_unlocked(setting)
        self.assertEqual(snapshot,
                         hash_file(self.original_folder/"lecture_completion.json"))

    def test_unattended_video_requires_separate_element_tts_provenance(self):
        from selenium_pipeline.sourcebound_production_video import render_and_install_prepared
        root=self.root/"LOCALAPPDATA"
        root.mkdir()
        plan_file=self.original_folder/"element_narration_plan.json"
        plan_file.write_bytes(self.plan.read_bytes())
        wav_dir=self.original_folder/"element_wav"
        wav_dir.mkdir()
        for wav in self.audio.glob("*.wav"):
            (wav_dir/wav.name).write_bytes(wav.read_bytes())
        with self.assertRaisesRegex(ProductionRenderError,
                                    "per-element TTS provenance manifest"):
            render_and_install_prepared(
                source=self.source,slides=self.slides,authored=plan_file,
                audio=wav_dir,local_work_root=root)
        self.assertFalse((self.original_folder/"lecture_completion.json").exists())
        self.assert_preserved()

    def test_corrupt_original_encoded_mp4_blocks_no_new_candidate(self):
        p=self.review_root/"rendered"/"part_01"/"part_01_review.mp4"
        p.write_bytes(p.read_bytes()+b"tamper")
        with self.assertRaises((ValueError,OSError)):
            self.accept()
        self.assertFalse(self.candidate.exists())
        self.assert_preserved()

    def test_missing_source_audio_blocks_no_candidate(self):
        (self.audio/"s02_e01.wav").unlink()
        with self.assertRaises((ValueError,OSError)):
            self.accept()
        self.assertFalse(self.candidate.exists())
        self.assertEqual(hash_file(self.source),self.original_hashes[self.source])

    def test_missing_decoded_pixel_evidence_rejected(self):
        path=self.review_root/"rendered"/"part_01"/"encoded_pixel_qa.json"
        qa=json.loads(path.read_text(encoding="utf-8"))
        qa.pop("time_window_samples_checked")
        path.write_text(json.dumps(qa),encoding="utf-8")
        with self.assertRaises((ValueError,OSError)):
            self.accept()
        self.assertFalse(self.candidate.exists())

    def test_candidate_tamper_rejected_before_install(self):
        self.accept()
        path=self.candidate/"part_01"/"part_01.mp4"
        path.write_bytes(path.read_bytes()+b"changed-after-verification")
        with self.assertRaises((ValueError,OSError)):
            install_new_production_parts(
                candidate=self.candidate,subchapter=self.original_folder)
        self.assertFalse((self.original_folder/"lecture_completion.json").exists())
        self.assert_preserved()

    def test_legacy_mp4_preserved_and_no_overwrite(self):
        original=self.original_folder/"slides.mp4"
        original.write_bytes(b"historical static asset; never delete")
        self.accept()
        install_new_production_parts(candidate=self.candidate,
                                     subchapter=self.original_folder)
        self.assertEqual(original.read_bytes(),b"historical static asset; never delete")
        self.assert_preserved()

    def test_different_source_hash_refuses_install(self):
        self.accept()
        self.source.write_bytes(b"modified textbook")
        with self.assertRaisesRegex(ProductionRenderError,"different source"):
            install_new_production_parts(
                candidate=self.candidate,subchapter=self.original_folder)
        self.assertFalse((self.original_folder/"lecture_completion.json").exists())

    def test_existing_part_blocks_all_install(self):
        marker=self.original_folder/"part_01"
        marker.mkdir()
        keep=marker/"original.bin"
        keep.write_bytes(b"untouched")
        self.accept()
        with self.assertRaisesRegex(ProductionRenderError,"never be overwritten"):
            install_new_production_parts(
                candidate=self.candidate,subchapter=self.original_folder)
        self.assertEqual(keep.read_bytes(),b"untouched")
        self.assertFalse((self.original_folder/"part_02").exists())
        self.assertFalse((self.original_folder/"lecture_completion.json").exists())
        self.assert_preserved()

    def test_output_not_inside_original_source_tree(self):
        with self.assertRaisesRegex(ProductionRenderError,"must not overlap"):
            accept_candidate(source=self.source,slides=self.slides,
                authored=self.plan,audio=self.audio,review_root=self.review_root,
                candidate=self.original_folder/"candidate")


if __name__=="__main__":
    unittest.main()
