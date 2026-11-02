"""Math, WAV and encoded MP4 source-evidence reuse without repeat generation."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.evidence_reuse_contract import EvidenceReuseBlocked, file_sha256
from selenium_pipeline.original_math_wav_video_scoped_reuse import (
    STATUS, decision_for_domain, check_existing,
)
from selenium_pipeline import recover_pinned_original_thomas_corpus

def create_synthetic_source(base:Path):
    original=base/"8.6"
    original.mkdir()
    checkpoint=base/"checkpoints"
    part=checkpoint/"20261102_PR444_ALL41_38_REAL_FOCUS_JOINED_V2"
    part.mkdir(parents=True)
    files={
        "source":original/"source.pdf",
        "author":original/"slides.pdf",
        "math":original/"slides.tex",
        "audio":original/"slide6.wav",
        "video":part/"THOMAS_8.6_38_FOCUS_SOURCE_QA_part01.mp4",
    }
    for kind,p in files.items():
        p.write_bytes(("REAL_FROZEN_"+kind).encode())
    ledger=base/"reused-math-audio-video.json"
    claims={
        "status":STATUS,
        "student_publication_authorized":False,
        "all_math_WAV_and_encoded_pixels_completely_certified":False,
        "accepted_scopes":{
            key:{"artifact_sha256":file_sha256(files[artifact]),
                 "previous_pr":pr,
                 "reused_existing_pass_not_newly_recalculated":True}
            for key,artifact,pr in (
                ("selected_exact_reduction_math","math","#449"),
                ("sampled_original_WAV_word_to_visual","audio","#443"),
                ("actual_joined_mp4_decoded_source_pixels","video","#444"))
        },
    }
    ledger.write_text(json.dumps(claims),encoding="utf8")
    return original,checkpoint,files,ledger

class ThreeIndependentSourceScopeReuseTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name)
        self.original,self.checkpoint,self.files,self.ledger=create_synthetic_source(self.base)
        pin=patch.dict(recover_pinned_original_thomas_corpus.ORIGINAL_PINS,
                       {"8.6":(file_sha256(self.files["source"]),
                               file_sha256(self.files["author"]))})
        pin.start()
        self.addCleanup(pin.stop)

    def test_three_exact_old_scopes_are_reused_without_executing_providers(self):
        for lane in ("math","audio","video"):
            with self.subTest(lane=lane):
                result=decision_for_domain(
                    ledger=self.ledger,original=self.original,
                    checkpoint=self.checkpoint,domain=lane)
                self.assertEqual(result.decision,"REUSE_VERIFIED")
                self.assertFalse(result.new_production_release_granted)

    def test_full_math_or_pronunciation_is_new_unverified_scope_not_fake_pass(self):
        for lane,full in (("math","all_41_source_equations_exact"),
                          ("audio","all_spoken_math_phonemes"),
                          ("video","every_figure_pixel_all_original_41_slides")):
            with self.subTest(lane=lane):
                result=decision_for_domain(
                    ledger=self.ledger,original=self.original,
                    checkpoint=self.checkpoint,domain=lane,
                    requested_scope=full)
                self.assertEqual(result.decision,"COMPLETE_UNVERIFIED_SCOPE")
                self.assertTrue(result.original_verified_scope_preserved)

    def test_modified_source_rejected_without_old_qa_promotion(self):
        self.files["source"].write_bytes(b"DIFFERENT_CONTENT")
        with self.assertRaises(EvidenceReuseBlocked):
            decision_for_domain(ledger=self.ledger,original=self.original,
                                checkpoint=self.checkpoint,domain="math")

    def test_changed_audio_or_joined_encoded_media_requires_new_scoped_proof(self):
        for lane,kind in (("audio","audio"),("video","video")):
            with self.subTest(lane=lane):
                previous=self.files[kind].read_bytes()
                self.files[kind].write_bytes(b"mutated evidence")
                try:
                    with self.assertRaises(EvidenceReuseBlocked):
                        decision_for_domain(ledger=self.ledger,original=self.original,
                                            checkpoint=self.checkpoint,domain=lane)
                finally:
                    self.files[kind].write_bytes(previous)

    def test_forged_source_claim_does_not_trigger_repeat_creation(self):
        data=json.loads(self.ledger.read_text("utf8"))
        data["student_publication_authorized"]=True
        self.ledger.write_text(json.dumps(data),encoding="utf8")
        with self.assertRaises(EvidenceReuseBlocked):
            decision_for_domain(ledger=self.ledger,original=self.original,
                                checkpoint=self.checkpoint,domain="video")

    def test_unsupported_domain_fails_before_file_changes(self):
        with self.assertRaises(EvidenceReuseBlocked):
            decision_for_domain(ledger=self.ledger,original=self.original,
                                checkpoint=self.checkpoint,domain="gemini_paid_tts")

    def test_no_original_source_physical_inputs_no_old_proof(self):
        with self.assertRaises(EvidenceReuseBlocked):
            check_existing(self.original,self.checkpoint)

if __name__=="__main__":
    unittest.main()
