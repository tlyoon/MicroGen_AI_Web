"""Isolated, synthetic acceptance tests for evidence-locked candidate handoff.

No Google/Gemini calls, paid TTS, source replacement or student publication.
No real review approval is created: mock approval in temporary test folders
is synthetic fixture data only.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.element_highlight_workflow import (
    HighlightReviewGateError, review, verify_rendered,
)
from selenium_pipeline.review_candidate_handoff import (
    CandidateHandoffError, REVIEW_FLAGS,
    check_human_review, inspect_candidate, sha, stage_human_reviewed_candidate,
    stage_technically_verified_candidate,
)
from tests.test_generic_element_highlight_workflow import (
    GenericHighlightWorkflowTests as _BaseReviewFixture,
)


class CandidateHandoffTests(unittest.TestCase):
    def setUp(self):
        # Reuse the already source-grounded, real-FFmpeg three-slide/two-part
        # test fixture without inheriting and duplicating its existing tests.
        self.fixture=_BaseReviewFixture(
            "test_valid_any_three_slide_two_part_scene_coverage")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.original=self.fixture
        self.review=self.fixture.output
        self.audio=self.fixture.audio
        self.source=self.fixture.source
        self.slides=self.fixture.slides
        self.authored=self.fixture.plan
        self.root=self.fixture.root
        self.approvals=self.root/"independent_owner_review"
        self.approvals.mkdir()
        self.approval=self.approvals/"human_review.json"
        self.destination=self.root/"reviewed_candidate_package"
        self.source_sha=sha(self.source)
        self.slides_sha=sha(self.slides)
        self.wav_sha={p.name:sha(p) for p in self.audio.glob("*.wav")}
        review(source=self.source,slides=self.slides,authored=self.authored,
               audio=self.audio,output_root=self.review)

    def args(self):
        return dict(source=self.source,slides=self.slides,
                    authored=self.authored,audio=self.audio,review_root=self.review)

    def signed(self,candidate=None):
        candidate=candidate or inspect_candidate(**self.args())
        signed={
            "schema_version":1,
            "status":"human_candidate_review_approved",
            "human_authored_explicit_approval":True,
            "reviewed_by":"Synthetic Test Lecturer",
            "approved_at_utc":"2026-10-18T06:00:00Z",
            "candidate_sha256":candidate["candidate_sha256"],
            "source_sha256":candidate["evidence"]["source_sha256"],
            "slides_sha256":candidate["evidence"]["slides_sha256"],
            "student_publication_permitted":False,
        }
        signed.update({key:True for key in REVIEW_FLAGS})
        self.approval.write_text(json.dumps(signed),encoding="utf-8")
        return signed

    def test_no_human_approval_does_not_create_candidate_or_approval(self):
        candidate=inspect_candidate(**self.args())
        self.assertEqual(candidate["status"],
                         "TECHNICALLY_VERIFIED_CANDIDATE_READY_FOR_NEXT_INTERNAL_STAGE")
        self.assertFalse(candidate["production_approved"])
        self.assertFalse(candidate["student_published"])
        self.assertFalse(self.destination.exists())
        self.assertFalse(self.approval.exists())
        with self.assertRaisesRegex(ValueError,"Required receipt missing"):
            # The technical evidence alone is not a production lecture receipt.
            from selenium_pipeline.production_video_contract import verify_series
            verify_series(self.review)

    def test_unattended_technical_candidate_advances_without_any_human_review(self):
        packet=stage_technically_verified_candidate(
            **self.args(),destination=self.destination)
        self.assertEqual(
            packet["status"],"TECHNICALLY_VERIFIED_ISOLATED_CANDIDATE_NOT_PUBLISHED")
        self.assertFalse(packet["human_review_record_verified"])
        self.assertFalse(packet["human_review_required_for_next_stage"])
        self.assertIsNone(packet["independent_review_sha256"])
        self.assertFalse(packet["production_approved"])
        self.assertFalse(packet["student_published"])
        self.assertFalse((self.destination/"independent_human_review.json").exists())
        self.assertFalse((self.destination/"lecture_completion.json").exists())
        self.assertFalse(self.approval.exists())
        for name,digest in packet["evidence"]["files"].items():
            self.assertEqual(sha(self.destination/name),digest)
        restored=verify_rendered(
            source=self.destination/"source.pdf",
            slides=self.destination/"slides.pdf",
            authored=self.destination/"authored_element_plan.json",
            audio=self.destination/"frozen_audio",
            staged=self.destination/"staged",
            rendered=self.destination/"rendered",output=None)
        self.assertEqual(restored["status"],"COMPLETE_ELEMENT_HIGHLIGHT_TECHNICAL_REVIEW_ONLY")
        self.assertEqual(sha(self.source),self.source_sha)
        self.assertEqual(sha(self.slides),self.slides_sha)
        self.assertEqual({p.name:sha(p) for p in self.audio.glob("*.wav")},self.wav_sha)

    def test_unattended_candidate_rejects_corrupt_original_and_existing_target(self):
        self.assertFalse(self.destination.exists())
        stage_technically_verified_candidate(**self.args(),destination=self.destination)
        with self.assertRaisesRegex(CandidateHandoffError,"destination"):
            stage_technically_verified_candidate(**self.args(),destination=self.destination)
        self.assertFalse((self.destination/"lecture_student_publication_authorization.json").exists())

    def test_missing_human_review_fail_closed_without_creating_destination(self):
        with self.assertRaises((ValueError, OSError)):
            stage_human_reviewed_candidate(
                **self.args(),approval=self.approval,destination=self.destination)
        self.assertFalse(self.destination.exists())
        self.assertFalse(self.approval.exists())

    def test_approval_must_have_all_five_real_review_flags(self):
        candidate=inspect_candidate(**self.args())
        row=self.signed(candidate)
        for flag in REVIEW_FLAGS:
            with self.subTest(flag=flag):
                bad=dict(row);bad[flag]=False
                self.approval.write_text(json.dumps(bad),encoding="utf-8")
                with self.assertRaisesRegex(CandidateHandoffError,flag):
                    check_human_review(candidate,self.approval,
                         source=self.source,audio=self.audio,review_root=self.review)
        self.assertFalse(self.destination.exists())

    def test_review_source_audio_and_plan_fingerprints_bind_every_byte(self):
        candidate=inspect_candidate(**self.args())
        row=self.signed(candidate)
        self.assertEqual(candidate["evidence"]["covered_elements"],3)
        self.assertEqual(len(candidate["evidence"]["parts"]),2)
        self.assertEqual(candidate["evidence"]["files"]["source.pdf"],self.source_sha)
        for name,expected in self.wav_sha.items():
            self.assertEqual(candidate["evidence"]["files"][f"frozen_audio/{name}"],expected)
        # Replacing the approved fingerprint with fabricated one is rejected.
        row["candidate_sha256"]="0"*64
        self.approval.write_text(json.dumps(row),encoding="utf-8")
        with self.assertRaisesRegex(CandidateHandoffError,"does not bind"):
            check_human_review(candidate,self.approval,
                source=self.source,audio=self.audio,review_root=self.review)

    def test_review_does_not_authorize_student_publication(self):
        candidate=inspect_candidate(**self.args())
        human=self.signed(candidate)
        human["student_publication_permitted"]=True
        self.approval.write_text(json.dumps(human),encoding="utf-8")
        with self.assertRaisesRegex(CandidateHandoffError,"cannot itself authorize"):
            check_human_review(candidate,self.approval,
                source=self.source,audio=self.audio,review_root=self.review)
        self.assertFalse(self.destination.exists())

    def test_invalid_reviewer_date_and_implicit_review_are_rejected(self):
        candidate=inspect_candidate(**self.args())
        human=self.signed(candidate)
        for changed in (
            {"approved_at_utc":"not a date"},
            {"approved_at_utc":"2026-10-18T06:00:00+08:00"},
            {"reviewed_by":"?"},
            {"human_authored_explicit_approval":False},
        ):
            with self.subTest(changed=changed):
                row=dict(human);row.update(changed)
                self.approval.write_text(json.dumps(row),encoding="utf-8")
                with self.assertRaises((CandidateHandoffError,ValueError)):
                    check_human_review(candidate,self.approval,
                        source=self.source,audio=self.audio,review_root=self.review)

    def test_changed_original_wav_cannot_reuse_human_approval(self):
        self.signed()
        wav=self.audio/"s02_e01.wav"
        wav.write_bytes(wav.read_bytes()+b"malicious edit")
        with self.assertRaises((ValueError,OSError)):
            stage_human_reviewed_candidate(
                **self.args(),approval=self.approval,destination=self.destination)
        self.assertFalse(self.destination.exists())

    def test_fake_saved_review_receipt_rejected_even_with_current_sha(self):
        self.signed()
        receipt=self.review/"highlight_technical_review.json"
        row=json.loads(receipt.read_text(encoding="utf-8"))
        row["production_approved"]=True
        receipt.write_text(json.dumps(row),encoding="utf-8")
        with self.assertRaises((ValueError,OSError)):
            stage_human_reviewed_candidate(
                **self.args(),approval=self.approval,destination=self.destination)
        self.assertFalse(self.destination.exists())

    def test_same_voice_declaration_must_cover_all_parts(self):
        self.signed()
        path=self.review/"staged"/"part_02"/"tts_chunks.json"
        manifest=json.loads(path.read_text(encoding="utf-8"))
        manifest["segments"][0]["voice_id"]="another_model_another_voice"
        path.write_text(json.dumps(manifest),encoding="utf-8")
        with self.assertRaisesRegex(CandidateHandoffError,"Mixed or stale"):
            inspect_candidate(**self.args())
        self.assertFalse(self.destination.exists())

    def test_explicit_synthetic_review_creates_isolated_reauditable_packet(self):
        candidate=inspect_candidate(**self.args())
        self.signed(candidate)
        packet=stage_human_reviewed_candidate(
            **self.args(),approval=self.approval,destination=self.destination)
        self.assertEqual(packet["status"],
                         "HUMAN_REVIEWED_TECHNICAL_CANDIDATE_NOT_PUBLISHED")
        self.assertEqual(packet["candidate_sha256"],candidate["candidate_sha256"])
        self.assertTrue(packet["human_review_record_verified"])
        self.assertFalse(packet["production_approved"])
        self.assertFalse(packet["student_published"])
        self.assertFalse(packet["voice_origin_independently_verified"])
        self.assertFalse((self.destination/"lecture_completion.json").exists())
        self.assertFalse((self.destination/"lecture_student_publication_authorization.json").exists())
        for name,expected in packet["evidence"]["files"].items():
            self.assertEqual(sha(self.destination/name),expected)
        verification=verify_rendered(
            source=self.destination/"source.pdf",
            slides=self.destination/"slides.pdf",
            authored=self.destination/"authored_element_plan.json",
            audio=self.destination/"frozen_audio",
            staged=self.destination/"staged",
            rendered=self.destination/"rendered",output=None)
        self.assertEqual(verification["status"],
                         "COMPLETE_ELEMENT_HIGHLIGHT_TECHNICAL_REVIEW_ONLY")
        self.assertEqual(sha(self.source),self.source_sha)
        self.assertEqual(sha(self.slides),self.slides_sha)
        self.assertEqual({p.name:sha(p) for p in self.audio.glob("*.wav")},
                         self.wav_sha)
        # Existing destination must never be recycled/overwritten.
        with self.assertRaisesRegex(CandidateHandoffError,"destination"):
            stage_human_reviewed_candidate(
                **self.args(),approval=self.approval,destination=self.destination)

    def test_repacked_candidate_can_detect_later_media_corruption(self):
        self.signed()
        packet=stage_human_reviewed_candidate(
            **self.args(),approval=self.approval,destination=self.destination)
        self.assertFalse(packet["student_published"])
        candidate_mp4=self.destination/"rendered"/"part_02"/"part_02_review.mp4"
        candidate_mp4.write_bytes(candidate_mp4.read_bytes()+b"tampered")
        with self.assertRaises((ValueError,OSError)):
            verify_rendered(
                source=self.destination/"source.pdf",
                slides=self.destination/"slides.pdf",
                authored=self.destination/"authored_element_plan.json",
                audio=self.destination/"frozen_audio",
                staged=self.destination/"staged",
                rendered=self.destination/"rendered",output=None)

    def test_destination_under_original_source_or_audio_refused(self):
        self.signed()
        for output in (self.source.parent/"candidate_out",
                       self.audio/"candidate_out",
                       self.review/"candidate_out"):
            with self.subTest(output=output):
                with self.assertRaisesRegex(CandidateHandoffError,"isolated"):
                    stage_human_reviewed_candidate(
                        **self.args(),approval=self.approval,destination=output)
                self.assertFalse(output.exists())


if __name__=="__main__":
    unittest.main()
