"""Finite academic to real media integration, with strict no-bypass gates."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from selenium_pipeline.windows_g2_autonomous_qa_supervisor import step


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class WindowsG2AutonomousQASupervisorTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.folder=self.root/"immutable_original_lecture"
        self.queue=self.root/"independent_qa_queue"
        self.work=self.root/"local_checkpoints"
        for p in (self.folder,self.queue,self.work):
            p.mkdir()
        for name in ("source.pdf","slides.pdf","script.txt"):
            (self.folder/name).write_bytes(("original "+name).encode())
        hashes={name:sha(self.folder/name)
                for name in ("source.pdf","slides.pdf","script.txt")}
        self.queue.joinpath("queue.json").write_text(json.dumps({
            "status":"IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE",
            "original_source_folder":str(self.folder.absolute()),
            "slide_jobs":[{
                "slide":1,"utterance_count":2,
                "original_source_sha256":hashes["source.pdf"],
                "original_slides_sha256":hashes["slides.pdf"],
                "original_script_sha256":hashes["script.txt"],
            }],
            "expected_utterances":2,
            "student_publication_authorized":False,
        }),encoding="utf8")
        self.selector={
            "status":"ONE_SAFE_ACADEMIC_REVIEW_UNIT_READY",
            "next_slide":1,"next_mode":"INITIAL_REVIEW",
            "action":"FRESH_FIRST_ATTEMPT"
        }
        self.pending={
            "status":"INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE",
            "original_utterances":2,
            "accepted_ai_evidence":[],
            "pending_or_disputed":2,
            "student_publication_authorized":False,
        }
        self.full={
            **self.pending,
            "accepted_ai_evidence":[{"utterance_id":"u1"},{"utterance_id":"u2"}],
            "pending_or_disputed":0,
        }
        self.handoff={
            "unresolved_source_segments":0,
            "AI_source_agreed_segments":2,
            "actual_verbatim_jobs":[{"job_id":"u1"},{"job_id":"u2"}],
            "paid_TTS_request_made":False,
            "student_publication_authorized":False,
        }

    def call(self, **params):
        return step(
            folder=self.folder,queue_root=self.queue,work_root=self.work,
            **params)

    def patch_queue(self):
        return patch(
            "selenium_pipeline.ai_academic_review_queue._check_queue",
            return_value={})

    def test_pending_academic_blocks_all_media_and_limits_budget(self):
        with self.patch_queue(), patch(
            "selenium_pipeline.ai_academic_review_queue.select_next_safe_review",
            return_value=self.selector), patch(
            "selenium_pipeline.ai_academic_review_audio_bridge.prepare_real_source_ai_kore_jobs",
            side_effect=AssertionError("No media without 2-pass consensus")):
            runner=Mock(return_value={"status":"BOUNDED_REVIEW_LIMIT_REACHED"})
            result=self.call(
                execute=True,max_units=2,review_advance=runner,
                consensus_reader=lambda **kw:self.pending)
        self.assertEqual(result["status"],
                         "G2_ACADEMIC_QA_INCOMPLETE_REVIEW_OR_SOURCE_REPAIR")
        self.assertEqual(result["pending_or_disputed_segments"],2)
        self.assertFalse(result["new_paid_tts_dispatched"])
        self.assertFalse(result["real_mp4_encoded_this_cycle"])
        runner.assert_called_once()
        self.assertEqual(runner.call_args.kwargs["max_units"],2)

    def test_two_pass_complete_readonly_prepares_no_media(self):
        with self.patch_queue(), patch(
            "selenium_pipeline.ai_academic_review_queue.select_next_safe_review",
            return_value={"status":"ALL_ACADEMIC_REVIEW_PASSES_RECORDED"}), patch(
            "selenium_pipeline.ai_academic_review_audio_bridge.prepare_real_source_ai_kore_jobs",
            return_value=self.handoff):
            result=self.call(
                execute=False,consensus_reader=lambda **kw:self.full)
        self.assertEqual(result["status"],
                         "G2_ACADEMIC_TWO_PASS_SOURCE_QA_READY_FOR_REAL_AUDIO")
        self.assertEqual(result["source_verified_tts_jobs"],2)
        self.assertFalse(result["new_paid_tts_dispatched"])

    def test_complete_ai_but_ambiguous_figure_blocks_before_any_cost(self):
        with self.patch_queue(), patch(
            "selenium_pipeline.ai_academic_review_queue.select_next_safe_review",
            return_value={"status":"ALL_ACADEMIC_REVIEW_PASSES_RECORDED"}), patch(
            "selenium_pipeline.ai_academic_review_audio_bridge.prepare_real_source_ai_kore_jobs",
            return_value=self.handoff),patch(
            "selenium_pipeline.automatic_element_narration.inspect_text_only",
            side_effect=ValueError("Unmapped original figure caption")):
            audio=Mock(side_effect=AssertionError("Should not bill"))
            result=self.call(
                execute=True,max_units=0,
                consensus_reader=lambda **kw:self.full,
                audio_producer=audio)
        self.assertEqual(result["status"],
                         "G2_SOURCE_REVIEW_PASSED_COMPLEX_ELEMENT_AUDIO_ROUTE_REQUIRED")
        self.assertFalse(result["new_paid_tts_dispatched"])
        audio.assert_not_called()

    def test_full_agreement_executes_actual_audio_then_video_hooks(self):
        def audio(**params):
            self.folder.joinpath("element_narration_plan.json").write_text("{}")
            self.folder.joinpath("element_wav").mkdir()
            return {"status":"ELEMENT_AUDIO_READY_FOR_AUTOMATIC_VIDEO_STAGE"}
        def video(**params):
            self.assertTrue((self.folder/"element_narration_plan.json").is_file())
            self.assertTrue((self.folder/"element_wav").is_dir())
            return {"status":"REAL_MP4_ENCODED"}
        with self.patch_queue(), patch(
            "selenium_pipeline.ai_academic_review_queue.select_next_safe_review",
            return_value={"status":"ALL_ACADEMIC_REVIEW_PASSES_RECORDED"}), patch(
            "selenium_pipeline.ai_academic_review_audio_bridge.prepare_real_source_ai_kore_jobs",
            return_value=self.handoff),patch(
            "selenium_pipeline.automatic_element_narration.inspect_text_only",
            return_value={"status":"EXACT_TEXT_ONLY_ELEMENT_MATCH_TECHNICAL"}):
            result=self.call(
                execute=True,max_units=0,
                consensus_reader=lambda **kw:self.full,
                audio_producer=audio, video_producer=video)
        self.assertEqual(result["status"],
                         "G2_MEDIA_GENERATED_AWAITING_INDEPENDENT_ACOUSTIC_QA")
        self.assertTrue(result["new_paid_tts_dispatched"])
        self.assertTrue(result["real_mp4_encoded_this_cycle"])
        self.assertFalse(result["acoustic_qa_accepted"])

    def test_source_sha_tamper_and_budget_stop_before_dispatch(self):
        self.folder.joinpath("source.pdf").write_bytes(b"changed textbook")
        with self.assertRaises(ValueError):
            self.call(execute=True,max_units=1,
                      review_advance=Mock(side_effect=AssertionError(
                          "Old source must stop before Gemini")))
        with self.assertRaises(ValueError):
            self.call(max_units=4)

    def test_rejects_corrupted_total_despite_success_label(self):
        invalid={**self.full,"pending_or_disputed":1}
        with self.patch_queue(), patch(
            "selenium_pipeline.ai_academic_review_queue.select_next_safe_review",
            return_value=self.selector):
            with self.assertRaises(ValueError):
                self.call(execute=False,consensus_reader=lambda **kw:invalid)


if __name__ == "__main__":
    unittest.main()
