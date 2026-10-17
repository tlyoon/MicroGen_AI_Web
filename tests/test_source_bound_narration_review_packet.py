"""Test source/hash-bound reviewer packet, fail-closed cross-QA and no approval."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import test_recover_frozen_highlight_review as frozen_fixture
from selenium_pipeline.source_bound_narration_review_packet import (
    make_review_packet,
)
from selenium_pipeline.recover_frozen_highlight_review import (
    PreservedReviewRecoveryError,
)


class SourceBoundNarrationPacketTests(unittest.TestCase):
    def setUp(self):
        fixture=frozen_fixture.RecoveryFromFrozenInputsTests(
            "test_preflight_matches_all_source_and_original_wav_hashes")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture=fixture
        root=fixture.case.root
        self.receipts=root/"prior_offline"
        self.receipts.mkdir()
        self.refined=root/"prior_gemini.json"
        clips=[]
        for i,source in enumerate(fixture.tts_doc["segments"]):
            name=source["filename"]
            if i==0: status="transcript_mismatch"
            elif i==1: status="pending_independent_asr"
            else: status="machine_transcript_consistent"
            clips.append({
                "wav":name,
                "wav_sha256":source["wav_sha256"],
                "reference_sha256":source["spoken_text_sha256"],
                "human_listening_approved":False,
                "asr_status":status,
                "transcript":"untrusted machine words",
                "review_flags":["mathematical_spoken_token_discrepancy"] if i==0 else [],
                "word_error_rate":.45 if i==0 else None
            })
            offline={
                "wav":name,
                "wav_sha256":source["wav_sha256"],
                "reference_sha256":source["spoken_text_sha256"],
                "status":"machine_asr_consistent_not_certified",
                "audible_word_fidelity_certified":False,
                "academic_approval":False,
                "transcript":"historical offline words",
                "metrics":{"wer":.02}
            }
            (self.receipts/(name+".asr.json")).write_text(
                json.dumps(offline),encoding="utf-8")
        self.qa={
            "status":"QUALITY_SCREEN_REVIEW_ONLY",
            "total_clips":len(clips),
            "human_listening_complete":False,
            "academic_approved":False,
            "production_approved":False,
            "clips":clips,
        }
        self.save()
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dest=Path(temp.name)/"new_lecture_packet"
        self.kwargs={**fixture.arguments,
                     "refined_screen":self.refined,
                     "offline_receipts":self.receipts}

    def save(self):
        self.refined.write_text(json.dumps(self.qa),encoding="utf-8")

    def run_packet(self):
        return make_review_packet(**self.kwargs,destination=self.dest)

    def test_writes_complete_unapproved_html_csv_and_all_original_wavs(self):
        result=self.run_packet()
        self.assertEqual(result["clip_count"],3)
        self.assertEqual(result["priorities"],{"P1":1,"P2":1,"P3":1})
        self.assertEqual(result["prioritized_six_clips"],["s01_e01.wav"])
        self.assertFalse(result["human_listening_complete"])
        self.assertFalse(result["student_published"])
        for key in ("index.html","lecturer_listening_worklist.csv",
                    "review_packet_manifest.json"):
            self.assertTrue((self.dest/key).is_file())
        for row in self.qa["clips"]:
            name=row["wav"]
            actual=hashlib.sha256((self.dest/"audio"/name).read_bytes()).hexdigest()
            self.assertEqual(actual,row["wav_sha256"])
        html=(self.dest/"index.html").read_text(encoding="utf-8")
        self.assertIn("<audio controls",html)
        self.assertIn("REVIEW ONLY",html)
        self.assertNotIn("human_approved=true",html)

    def test_forbidden_reuse_of_same_destination(self):
        self.run_packet()
        with self.assertRaisesRegex(PreservedReviewRecoveryError,"fresh isolated"):
            self.run_packet()

    def test_earlier_machine_asr_hash_mismatch_blocks_all_output(self):
        path=self.receipts/(self.qa["clips"][0]["wav"]+".asr.json")
        data=json.loads(path.read_text())
        data["reference_sha256"]="0"*64
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(PreservedReviewRecoveryError,
                                    "Speech-screen version mismatch"):
            self.run_packet()
        self.assertFalse(self.dest.exists())

    def test_gemini_wrong_wav_identity_blocks_all_output(self):
        self.qa["clips"][0]["wav_sha256"]="b"*64
        self.save()
        with self.assertRaisesRegex(PreservedReviewRecoveryError,
                                    "Speech-screen version mismatch"):
            self.run_packet()
        self.assertFalse(self.dest.exists())

    def test_offline_review_flag_priority_even_if_gemini_consistent(self):
        row=self.qa["clips"][-1]
        name=row["wav"]
        path=self.receipts/(name+".asr.json")
        d=json.loads(path.read_text())
        d["status"]="speech_review_required"
        path.write_text(json.dumps(d))
        result=self.run_packet()
        self.assertEqual(result["priorities"],{"P1":2,"P2":1,"P3":0})

    def test_missing_offline_record_blocks_all_output(self):
        row=self.qa["clips"][0]
        (self.receipts/(row["wav"]+".asr.json")).unlink()
        with self.assertRaisesRegex(PreservedReviewRecoveryError,
                                    "Offline recognition receipt coverage"):
            self.run_packet()
        self.assertFalse(self.dest.exists())

    def test_csv_transcript_formula_cannot_execute(self):
        self.qa["clips"][0]["transcript"]="=WEBSERVICE(\"bad\")"
        self.save()
        self.run_packet()
        contents=(self.dest/"lecturer_listening_worklist.csv").read_text(
            encoding="utf-8-sig")
        self.assertIn("'=WEBSERVICE",contents)
        self.assertIn("=WEBSERVICE(&quot;bad&quot;)",(self.dest/"index.html").read_text(
            encoding="utf-8"))


if __name__=="__main__":
    unittest.main()
