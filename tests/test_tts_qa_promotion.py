"""Strict, all-offline review-only audit and isolated WAV export contract."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from selenium_pipeline.tts_qa_promotion import (
    AudioPromotionBlocked, audit, export_reviewed, main,
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


class ReviewedAudioHandoffTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.source = self.root / "source" / "8.4"
        self.source.mkdir(parents=True)
        self.review = self.source / ".tts_qa_review_candidates" / "synthetic_test"
        self.review.mkdir(parents=True)
        self.destination = self.root / "separate_reviewed_audio"
        self.attestation_path = self.root / "independent_human_review.json"
        self.script = b"**Slide 1 [1 min]:\nOriginal text one.\n\n**Slide 2 [1 min]:\nCorrect physics expression."
        self.narrations = ["Original text one.", "Correct physics expression."]
        self.manifest = {
            "version": 2,
            "primary": {"provider":"gemini","model":"gemini-3.8-flash-lite-tts","voice":"Kore"},
            "slides":[
                {"slide": i, "source_text":txt, "tts_text":txt,
                 "provider":"gemini","model":"gemini-3.8-flash-lite-tts",
                 "voice":"Kore","fallback_used":False}
                for i,txt in enumerate(self.narrations,start=1)
            ],
        }
        self.originals = {"slide1.wav":b"RIFF"+b"A"*100,
                          "slide2.wav":b"RIFF"+b"B"*100}
        self.candidates = dict(self.originals)
        self.candidates["slide2.wav"] = b"RIFF"+b"C"*100
        for directory in (self.source,self.review):
            (directory / "script.txt").write_bytes(self.script)
            (directory / "tts_input_manifest.json").write_text(
                json.dumps(self.manifest),encoding="utf-8")
        for name,payload in self.originals.items():
            (self.source / name).write_bytes(payload)
        for name,payload in self.candidates.items():
            (self.review / name).write_bytes(payload)
        (self.review / "attempt1_slide2.wav").write_bytes(self.candidates["slide2.wav"])
        self.report = {
            "model":"gemini-3.8-flash",
            "threshold_percent":99.0,
            "summary":{"passed":2,"review":0,"blocking_failures":0},
            "slides":[
                {"slide":i,"status":"pass",
                 "audio_file":f"slide{i}.wav","ground_truth":txt,
                 "fidelity_percent":100.0,"pronunciation_issues":[],
                 "critical_token_issues":[],"audio_defects":[]}
                for i,txt in enumerate(self.narrations,start=1)
            ],
        }
        self.receipt = {
            "status":"REVIEW_ONLY_UNPUBLISHED",
            "source_script_sha256":sha(self.script),
            "source_manifest_sha256":sha((self.source/"tts_input_manifest.json").read_bytes()),
            "original_wav_sha256":{k:sha(v) for k,v in self.originals.items()},
            "candidate_wav_sha256":{k:sha(v) for k,v in self.candidates.items()},
            "provider":"gemini","tts_model":"gemini-3.8-flash-lite-tts",
            "voice":"Kore","fidelity_model":"gemini-3.8-flash",
            "threshold":99.0,
            "proposed_replacements":[
                {"slide":2,"round":1,"wav_sha256":sha(self.candidates["slide2.wav"])}],
            "proposed_remaining_failures":[],
            "original_audio_modified":False,
            "academic_approved":False,
            "video_publication_approved":False,
        }
        self.persist()
        self.original_snapshot={n:(self.source/n).read_bytes()
                                for n in ("script.txt","tts_input_manifest.json",
                                          "slide1.wav","slide2.wav")}

    def persist(self):
        (self.review/"tts_fidelity_report.json").write_text(
            json.dumps(self.report),encoding="utf-8")
        (self.review/"review_only_receipt.json").write_text(
            json.dumps(self.receipt),encoding="utf-8")

    def create_external_attestation(self):
        proof=audit(self.source,self.review)
        doc={
            **{k:proof[k] for k in (
                "receipt_sha256","fidelity_report_sha256",
                "source_script_sha256","source_manifest_sha256",
                "candidate_wav_sha256")},
            "reviewer":"Independent human reviewer",
            "reviewed_at_utc":"2026-10-17T06:30:00Z",
            "review_scope":"tts-audio-only",
            "audio_listened":True,
            "mathematical_pronunciation_reviewed":True,
            "voice_kore_listening_verified":True,
        }
        self.attestation_path.write_text(json.dumps(doc),encoding="utf-8")
        return doc

    def assert_originals_unchanged(self):
        for name,original in self.original_snapshot.items():
            self.assertEqual((self.source/name).read_bytes(),original)

    def test_audit_read_only_and_requires_no_attestation(self):
        before={p.name:p.read_bytes() for p in self.review.iterdir()}
        proof=audit(self.source,self.review)
        self.assertEqual(proof["status"],"VERIFIED_REVIEW_ONLY")
        self.assertEqual(proof["changed_slide_numbers"],[2])
        self.assertFalse(proof["human_review_approved"])
        self.assertFalse(proof["video_publication_approved"])
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.review.iterdir()})
        self.assertFalse(self.destination.exists())
        self.assert_originals_unchanged()

    def test_even_valid_attestation_requires_both_explicit_flags(self):
        self.create_external_attestation()
        for reviewed,isolate in [(False,False),(False,True),(True,False)]:
            with self.subTest(flags=(reviewed,isolate)):
                with self.assertRaisesRegex(AudioPromotionBlocked,"Both explicit"):
                    export_reviewed(self.source,self.review,self.destination,
                                    attestation_path=self.attestation_path,
                                    confirm_reviewed_audio=reviewed,
                                    confirm_isolated_export=isolate)
        self.assertFalse(self.destination.exists())

    def test_attested_review_exports_to_new_folder_only(self):
        self.create_external_attestation()
        handoff=export_reviewed(self.source,self.review,self.destination,
                     attestation_path=self.attestation_path,
                     confirm_reviewed_audio=True,confirm_isolated_export=True)
        self.assertEqual(handoff["status"],"AUDIO_REVIEWED_ISOLATED_COPY")
        self.assertTrue(handoff["human_review_approved"])
        self.assertFalse(handoff["video_publication_approved"])
        self.assertEqual((self.destination/"slide1.wav").read_bytes(),self.originals["slide1.wav"])
        self.assertEqual((self.destination/"slide2.wav").read_bytes(),self.candidates["slide2.wav"])
        self.assertTrue((self.destination/"tts_reviewed_handoff.json").exists())
        self.assert_originals_unchanged()
        with self.assertRaisesRegex(AudioPromotionBlocked,"Destination already exists"):
            export_reviewed(self.source,self.review,self.destination,
                            attestation_path=self.attestation_path,
                            confirm_reviewed_audio=True,confirm_isolated_export=True)

    def test_attestation_never_auto_created_by_audit_or_cli(self):
        self.assertEqual(main(["--source",str(self.source),
                               "--review",str(self.review)]),0)
        self.assertFalse(self.attestation_path.exists())
        self.assertFalse(self.destination.exists())

    def test_external_attestation_missing_audio_review_is_rejected(self):
        doc=self.create_external_attestation()
        doc["audio_listened"]=False
        self.attestation_path.write_text(json.dumps(doc),encoding="utf-8")
        with self.assertRaisesRegex(AudioPromotionBlocked,"human listening"):
            export_reviewed(self.source,self.review,self.destination,
                            attestation_path=self.attestation_path,
                            confirm_reviewed_audio=True,confirm_isolated_export=True)
        self.assertFalse(self.destination.exists())

    def test_external_attestation_cannot_bind_stale_candidate(self):
        doc=self.create_external_attestation()
        doc["candidate_wav_sha256"]["slide2.wav"]="0"*64
        self.attestation_path.write_text(json.dumps(doc),encoding="utf-8")
        with self.assertRaisesRegex(AudioPromotionBlocked,"does not match"):
            export_reviewed(self.source,self.review,self.destination,
                            attestation_path=self.attestation_path,
                            confirm_reviewed_audio=True,confirm_isolated_export=True)

    def test_source_modified_blocks_audit_without_write(self):
        (self.source/"slide1.wav").write_bytes(b"RIFF"+b"Z"*100)
        with self.assertRaisesRegex(AudioPromotionBlocked,"digest mismatch"):
            audit(self.source,self.review)
        self.assertFalse(self.destination.exists())

    def test_review_audio_tamper_blocks_export(self):
        self.create_external_attestation()
        (self.review/"slide2.wav").write_bytes(b"RIFF"+b"Z"*100)
        with self.assertRaisesRegex(AudioPromotionBlocked,"digest mismatch"):
            export_reviewed(self.source,self.review,self.destination,
                            attestation_path=self.attestation_path,
                            confirm_reviewed_audio=True,confirm_isolated_export=True)
        self.assertFalse(self.destination.exists())
        self.assert_originals_unchanged()

    def test_attempt_history_tamper_blocks_audit(self):
        (self.review/"attempt1_slide2.wav").write_bytes(b"RIFF"+b"Z"*100)
        with self.assertRaisesRegex(AudioPromotionBlocked,"Attempt WAV digest"):
            audit(self.source,self.review)

    def test_latest_attempt_must_equal_final_candidate(self):
        # Attempt 1 may pass hash validation but cannot justify a different
        # final WAV that is not documented as the final replacement.
        self.receipt["proposed_replacements"].append({
            "slide":2,"round":2,
            "wav_sha256":sha(b"RIFF"+b"D"*100)})
        (self.review/"attempt2_slide2.wav").write_bytes(b"RIFF"+b"D"*100)
        self.persist()
        with self.assertRaisesRegex(AudioPromotionBlocked,"latest recorded attempt"):
            audit(self.source,self.review)

    def test_repeated_or_reordered_attempts_are_rejected(self):
        self.receipt["proposed_replacements"].append({
            "slide":2,"round":1,
            "wav_sha256":sha(self.candidates["slide2.wav"])})
        self.persist()
        with self.assertRaisesRegex(AudioPromotionBlocked,"repeated or out of order"):
            audit(self.source,self.review)

    def test_attestation_inside_source_is_not_independent(self):
        self.create_external_attestation()
        internal = self.source / "self_approved.json"
        internal.write_bytes(self.attestation_path.read_bytes())
        with self.assertRaisesRegex(AudioPromotionBlocked,"outside the original/review"):
            export_reviewed(self.source,self.review,self.destination,
                            attestation_path=internal,
                            confirm_reviewed_audio=True,
                            confirm_isolated_export=True)
        self.assertFalse(self.destination.exists())

    def test_invalid_reviewer_is_rejected_without_export(self):
        doc=self.create_external_attestation()
        doc["reviewer"]=42
        self.attestation_path.write_text(json.dumps(doc),encoding="utf-8")
        with self.assertRaisesRegex(AudioPromotionBlocked,"human listening"):
            export_reviewed(self.source,self.review,self.destination,
                            attestation_path=self.attestation_path,
                            confirm_reviewed_audio=True,
                            confirm_isolated_export=True)
        self.assertFalse(self.destination.exists())

    def test_failed_qa_cannot_be_exported(self):
        self.receipt["proposed_remaining_failures"]=[2]
        self.persist()
        with self.assertRaisesRegex(AudioPromotionBlocked,"unresolved"):
            audit(self.source,self.review)

    def test_fake_qa_report_cannot_be_exported(self):
        self.report["slides"][1]["status"]="review"
        self.persist()
        with self.assertRaisesRegex(AudioPromotionBlocked,"strict QA"):
            audit(self.source,self.review)

    def test_report_ground_truth_mismatch_blocks(self):
        self.report["slides"][1]["ground_truth"]="different"
        self.persist()
        with self.assertRaisesRegex(AudioPromotionBlocked,"strict QA"):
            audit(self.source,self.review)

    def test_original_manifest_identity_cannot_change(self):
        self.manifest["primary"]["model"]="gemini-3.8-flash-tts"
        (self.source/"tts_input_manifest.json").write_text(json.dumps(self.manifest))
        (self.review/"tts_input_manifest.json").write_text(json.dumps(self.manifest))
        self.receipt["source_manifest_sha256"] = sha(
            (self.source/"tts_input_manifest.json").read_bytes())
        self.persist()
        with self.assertRaisesRegex(AudioPromotionBlocked,"provenance"):
            audit(self.source,self.review)

    def test_destination_inside_source_rejected(self):
        self.create_external_attestation()
        target=self.source/"new_staged"
        with self.assertRaisesRegex(AudioPromotionBlocked,"outside the original"):
            export_reviewed(self.source,self.review,target,
                            attestation_path=self.attestation_path,
                            confirm_reviewed_audio=True,confirm_isolated_export=True)
        self.assertFalse(target.exists())

    def test_candidate_review_outside_given_source_rejected(self):
        alternate=self.root/"alien"/"candidate"
        alternate.parent.mkdir()
        alternate.mkdir()
        with self.assertRaisesRegex(AudioPromotionBlocked,"not attached"):
            audit(self.source,alternate)


if __name__ == "__main__":
    unittest.main()
