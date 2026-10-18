"""Contract: technical video checks cannot self-approve math, audio or publication."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.lecture_release_gate import (
    LectureApprovalError, verify_academic_lecture,
    verify_student_publication, REVIEW_FLAGS,
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class HumanReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        for name,content in (
            ("source.pdf",b"source bytes"),
            ("slides.pdf",b"slides bytes"),
            ("script.txt",b"**Slide 1 [10 sec]:\\nSpoken mathematical narration**"),
            ("lecture_completion.json",b'{"technical":"synthetic-test"}'),
        ):
            (self.folder/name).write_bytes(content.replace(b"\\n", b"\n"))
        self.tts={
            "version":2,"primary":{
                "provider":"gemini","model":"gemini-3.8-flash-lite-tts","voice":"Kore"},
            "slides":[{
                "slide":1,"source_text":"Spoken mathematical narration",
                "tts_text":"Spoken mathematical narration","provider":"gemini",
                "model":"gemini-3.8-flash-lite-tts","voice":"Kore",
                "fallback_used":False,
            }],
        }
        (self.folder/"tts_input_manifest.json").write_text(
            json.dumps(self.tts),encoding="utf-8")
        self.tech={"status":"accepted_synchronized_series","parts":[
            {"part_id":"part_01","duration_s":100,"highlight_events":10}]}

    def review(self):
        value={
            "schema_version":1,"status":"human_academic_review_approved",
            "reviewed_by":"Academic Reviewer",
            "approved_at_utc":"2026-10-18T11:00:00Z",
            "human_authored_explicit_approval":True,
            "subject":"entire_source_bound_lecture",
            "source_sha256":sha(self.folder/"source.pdf"),
            "slides_sha256":sha(self.folder/"slides.pdf"),
            "narration_script_sha256":sha(self.folder/"script.txt"),
            "technical_series_sha256":sha(self.folder/"lecture_completion.json"),
            "tts_input_manifest_sha256":sha(self.folder/"tts_input_manifest.json"),
            "effective_tts_model":"gemini-3.8-flash-lite-tts",
            "effective_tts_voice":"Kore",
        }
        for flag in REVIEW_FLAGS:
            value[flag]=True
        path=self.folder/"lecture_human_approval.json"
        path.write_text(json.dumps(value),encoding="utf-8")
        return value

    def accepted(self):
        with patch("selenium_pipeline.lecture_release_gate.verify_series",return_value=self.tech):
            return verify_academic_lecture(self.folder)

    def test_no_auto_created_approval_and_no_publication(self):
        with patch("selenium_pipeline.lecture_release_gate.verify_series",return_value=self.tech):
            with self.assertRaisesRegex(LectureApprovalError,"Missing explicitly"):
                verify_academic_lecture(self.folder)
        self.assertFalse((self.folder/"lecture_human_approval.json").exists())
        self.assertFalse((self.folder/"lecture_student_publication_authorization.json").exists())

    def test_human_approval_is_separate_from_student_permission(self):
        self.review()
        result=self.accepted()
        self.assertEqual(result["status"],"explicit_human_reviewed_lecture")
        self.assertFalse(result["student_publication_permitted"])
        with patch("selenium_pipeline.lecture_release_gate.verify_series",return_value=self.tech):
            with self.assertRaises(LectureApprovalError):
                verify_student_publication(self.folder)

    def test_all_review_categories_and_identity_must_be_explicit(self):
        row=self.review()
        for flag in REVIEW_FLAGS:
            with self.subTest(flag=flag):
                changed=dict(row)
                changed[flag]=False
                (self.folder/"lecture_human_approval.json").write_text(
                    json.dumps(changed),encoding="utf-8")
                with self.assertRaisesRegex(LectureApprovalError,flag):
                    self.accepted()
        row["reviewed_by"]="?"
        (self.folder/"lecture_human_approval.json").write_text(json.dumps(row))
        with self.assertRaisesRegex(LectureApprovalError,"reviewed_by"):
            self.accepted()

    def test_approval_cannot_survive_source_slide_script_or_manifest_change(self):
        for target in ("source.pdf","slides.pdf","script.txt",
                       "lecture_completion.json","tts_input_manifest.json"):
            with self.subTest(target=target):
                self.review()
                file=self.folder/target
                original=file.read_bytes()
                file.write_bytes(original+b"modified")
                with self.assertRaisesRegex(LectureApprovalError,"not bound"):
                    self.accepted()
                file.write_bytes(original)

    def test_tampered_approval_metadata_fails(self):
        row=self.review()
        for field,bad in (("human_authored_explicit_approval",False),
                          ("status","machine_approved"),
                          ("approved_at_utc","not-a-date")):
            with self.subTest(field=field):
                changed=dict(row)
                changed[field]=bad
                (self.folder/"lecture_human_approval.json").write_text(json.dumps(changed))
                with self.assertRaises(LectureApprovalError):
                    self.accepted()

    def test_student_permission_requires_distinct_hash_bound_record(self):
        self.review()
        auth={
            "schema_version":1,
            "status":"explicit_student_publication_authorized",
            "student_publication_permitted":True,
            "authorized_by":"Academic Owner",
            "approved_at_utc":"2026-10-18T11:05:00Z",
            "human_authored_explicit_approval":True,
            "human_review_receipt_sha256":sha(self.folder/"lecture_human_approval.json"),
            "technical_series_sha256":sha(self.folder/"lecture_completion.json"),
        }
        path=self.folder/"lecture_student_publication_authorization.json"
        path.write_text(json.dumps(auth))
        with patch("selenium_pipeline.lecture_release_gate.verify_series",return_value=self.tech):
            result=verify_student_publication(self.folder)
        self.assertTrue(result["student_publication_permitted"])
        auth["human_review_receipt_sha256"]="0"*64
        path.write_text(json.dumps(auth))
        with patch("selenium_pipeline.lecture_release_gate.verify_series",return_value=self.tech):
            with self.assertRaisesRegex(LectureApprovalError,"bind"):
                verify_student_publication(self.folder)

    def test_failed_technical_gate_cannot_be_overridden_by_human_json(self):
        self.review()
        with patch("selenium_pipeline.lecture_release_gate.verify_series",
                   side_effect=ValueError("Source-bound technical verification failed")):
            with self.assertRaisesRegex(ValueError,"technical verification"):
                verify_academic_lecture(self.folder)


if __name__=="__main__":
    unittest.main()
