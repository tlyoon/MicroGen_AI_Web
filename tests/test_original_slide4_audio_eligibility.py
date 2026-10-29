"""Evidence-required audio eligibility after original Slide4 figure matching."""
from copy import deepcopy
import os
from pathlib import Path
import unittest

from selenium_pipeline.original_slide4_audio_eligibility import (
    summarize_slide4_audio_gate,inspect_original_slide4_audio_readiness,
)


def witness():
    speech=[{"id":f"s004.utterance.{i:03d}",
             "spoken_sha256":f"{i:064x}",
             "spoken_text":f"original narration number {i}"}
            for i in range(1,6)]
    job={"status":"SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED",
         "source_sha256":"a"*64,"slides_sha256":"b"*64,
         "script_sha256":"c"*64,"utterance_count":5,
         "slides":[{"slide":4,"utterances":speech}]}
    candidates={
        "status":"ORIGINAL_SLIDE4_THREE_RASTER_REGION_CANDIDATES_REVIEW_ONLY",
        "original_utterance_count":5,
        "proposed_figure_region_utterance_count":3,
        "unmapped_original_utterance_count":2,
        "original_source_sha256":"a"*64,
        "original_slides_sha256":"b"*64,
        "original_script_sha256":"c"*64,
        "utterance_candidates":[{
            "utterance_id":u["id"],
            "original_spoken_sha256":u["spoken_sha256"],
            "candidate_panel_id":f"strip{i}" if 2<=i<=4 else None,
            "speech_to_visual_sync_verified":False,
            "speaking_start_s":None,"speaking_end_s":None,
        } for i,u in enumerate(speech,1)],
    }
    unresolved=[{"utterance_id":x["id"],"reason":"NO_INITIAL_SOURCE_REVIEW"}
                for x in speech]
    unresolved += [{"utterance_id":f"s001.utterance.{n:03d}",
                    "reason":"UNREVIEWED"} for n in range(1,67)]
    academic={
        "status":"INDEPENDENTLY_REVALIDATED_AI_SOURCE_MATH_AGREEMENT_QUEUE",
        "student_publication_authorized":False,
        "original_utterances":71,
        "agreed_source_witnessed_segments":0,
        "pending_or_disputed":71,
        "accepted_ai_evidence":[],"unresolved":unresolved,
    }
    return job,candidates,academic


class OriginalSlide4AudioEligibility(unittest.TestCase):
    def test_unapproved_original_audio_gate_does_not_invent_timing(self):
        result=summarize_slide4_audio_gate(**witness_positional())
        self.assertEqual(result["original_slide_utterances"],5)
        self.assertEqual(result["unreviewed_original_slide_utterances"],5)
        self.assertEqual(result["visual_candidate_utterances"],3)
        self.assertEqual(result["unmapped_visual_utterances"],2)
        self.assertEqual(result["audited_original_element_WAV_count"],0)
        self.assertEqual(result["original_slide_level_archived_WAV_existence_here"],"NOT_CHECKED")
        self.assertTrue(all(row["individual_audio_duration_s"] is None
                            and not row["claimed_voice_acoustically_verified"]
                            for row in result["original_utterance_rows"]))
        self.assertFalse(result["permission_to_synthesize_or_publish"])
        self.assertFalse(result["real_speech_timing_evidence_accepted"])

    def test_forged_provider_receipt_cannot_promote_audio(self):
        j,c,a=witness()
        bogus={"job_id":"s004.utterance.002","voice":"Kore",
               "provider_receipt_present":True,
               "wav_sha256":"d"*64,"individual_audio_duration_s":12.}
        result=summarize_slide4_audio_gate(
            job=j,candidates=c,independently_reconciled=a,
            per_utterance_deliveries=[bogus])
        self.assertEqual(result["provider_deliveries_presented_not_validated"],1)
        self.assertEqual(result["audited_original_element_WAV_count"],0)
        self.assertFalse(result["real_speech_timing_evidence_accepted"])

    def test_duplicate_foreign_receipts_refused(self):
        j,c,a=witness()
        for receipts in (
            [{"job_id":"foreign"}],
            [{"job_id":"s004.utterance.002"}]*2,
            [None],
        ):
            with self.assertRaises(ValueError):
                summarize_slide4_audio_gate(
                    job=j,candidates=c,independently_reconciled=a,
                    per_utterance_deliveries=receipts)

    def test_stale_original_spoken_sha_refused(self):
        j,c,a=witness()
        c["utterance_candidates"][2]["original_spoken_sha256"]="0"*64
        with self.assertRaises(ValueError):
            summarize_slide4_audio_gate(job=j,candidates=c,
                                        independently_reconciled=a)

    def test_fake_audio_timestamps_refused(self):
        j,c,a=witness()
        c["utterance_candidates"][1]["speaking_start_s"]=0.0
        with self.assertRaises(ValueError):
            summarize_slide4_audio_gate(job=j,candidates=c,
                                        independently_reconciled=a)

    def test_missing_one_original_slide_utterance_refused(self):
        j,c,a=witness()
        j["slides"][0]["utterances"].pop()
        with self.assertRaises(ValueError):
            summarize_slide4_audio_gate(job=j,candidates=c,
                                        independently_reconciled=a)

    def test_corrupt_review_accounting_refused(self):
        j,c,a=witness()
        a["pending_or_disputed"]=70
        with self.assertRaises(ValueError):
            summarize_slide4_audio_gate(job=j,candidates=c,
                                        independently_reconciled=a)

    def test_missing_slide4_consensus_decision_refused(self):
        j,c,a=witness()
        a["unresolved"].pop(0)
        a["unresolved"].append({
            "utterance_id":"s002.utterance.099","reason":"UNREVIEWED"})
        with self.assertRaises(ValueError):
            summarize_slide4_audio_gate(job=j,candidates=c,
                                        independently_reconciled=a)

    def test_wrong_source_hash_refused(self):
        j,c,a=witness()
        c["original_source_sha256"]="0"*64
        with self.assertRaises(ValueError):
            summarize_slide4_audio_gate(job=j,candidates=c,
                                        independently_reconciled=a)

    def test_forged_academic_approval_sha_refused(self):
        j,c,a=witness()
        a["unresolved"].pop(0)
        a["accepted_ai_evidence"].append({
            "utterance_id":"s004.utterance.001",
            "original_spoken_sha256":"0"*64,
            "author_human_attestation":False})
        a["agreed_source_witnessed_segments"]=1
        a["pending_or_disputed"]=70
        with self.assertRaises(ValueError):
            summarize_slide4_audio_gate(job=j,candidates=c,
                                        independently_reconciled=a)

    def test_real_immutable_original_and_queue_when_authorized(self):
        root=os.getenv("MICROGEN_ORIGINAL_THOMAS84_FOLDER")
        queue=os.getenv("MICROGEN_ORIGINAL_71_REVIEW_QUEUE")
        if not root or not queue:
            self.skipTest("Original textbook and source receipts only on Dell-115")
        report=inspect_original_slide4_audio_readiness(
            folder=Path(root),queue_root=Path(queue))
        self.assertEqual(report["full_original_queue_total"],71)
        self.assertEqual(report["original_slide_utterances"],5)
        self.assertEqual(report["audited_original_element_WAV_count"],0)
        self.assertFalse(report["permission_to_synthesize_or_publish"])


def witness_positional():
    j,c,a=witness()
    return {"job":j,"candidates":c,"independently_reconciled":a}


if __name__=="__main__":
    unittest.main()
