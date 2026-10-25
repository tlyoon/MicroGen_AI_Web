"""Exact WAV-byte provider receipts for original Slide4, with no audio calls."""
from copy import deepcopy
from pathlib import Path
import tempfile
import math
import struct
import wave
import unittest

from selenium_pipeline.figure_source_identity import _sha
from selenium_pipeline.incremental_chunk_tts_requests import DEFAULT_MODEL,DEFAULT_VOICE
from selenium_pipeline.original_slide4_external_pcm_receipt_gate import (
    verify_original_slide4_external_audio,
)


def one_wav(path,rate=8000,silent=False):
    count=rate
    values=[0 if silent else int(1600*math.sin(2*math.pi*300*i/rate))
            for i in range(count)]
    with wave.open(str(path),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate)
        w.writeframes(struct.pack("<"+"h"*len(values),*values))


class RealPCMReceiptIntegration(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        root=Path(self.temp.name)
        self.original=root/"source-original"
        self.original.mkdir()
        self.jobs=[]
        self.receipts=[]
        for i in range(1,6):
            utterance_id=f"s004.utterance.{i:03d}"
            sha=f"{i:064x}"
            self.jobs.append({"id":utterance_id,"spoken_sha256":sha})
            path=root/f"chunk{i}.wav"
            one_wav(path)
            self.receipts.append({
                "job_id":utterance_id,"spoken_text_sha256":sha,
                "provider_receipt_present":True,
                "execution_id":f"test-run-{i:04d}",
                "model":DEFAULT_MODEL,"voice":DEFAULT_VOICE,
                "pcm_wav_path":str(path),"wav_sha256":_sha(path),
            })
        self.job={
            "status":"SOURCE_BOUND_AI_REVIEW_REQUEST_NOT_DISPATCHED",
            "source_sha256":"a"*64,
            "slides_sha256":"b"*64,
            "script_sha256":"c"*64,
            "utterance_count":5,
            "slides":[{"slide":4,"utterances":self.jobs}],
        }
        self.readiness={
            "source_sha256":"a"*64,"slides_sha256":"b"*64,
            "script_sha256":"c"*64,
            "original_slide_utterances":5,
            "visual_candidate_utterances":5,
            "unmapped_visual_utterances":0,
            "real_speech_timing_evidence_accepted":False,
            "student_publication_authorized":False,
        }

    def tearDown(self):
        self.temp.cleanup()

    def validate(self,receipts=None):
        return verify_original_slide4_external_audio(
            readiness=self.readiness,job=self.job,
            receipts=self.receipts if receipts is None else receipts,
            original_folder=self.original)

    def test_real_five_pcm16_files_and_distinct_provider_claims(self):
        report=self.validate()
        self.assertEqual(report["external_pcm_clip_count"],5)
        self.assertEqual(report["provider_execution_claim_count"],5)
        self.assertEqual(report["total_sample_frames"],40000)
        self.assertEqual(report["measured_total_audio_duration_s"],5)
        self.assertEqual(
            [x["proposed_concatenation_start_sample"]
             for x in report["byte_verified_audio_segments"]],
            [0,8000,16000,24000,32000])
        self.assertFalse(report["source_script_spoken_content_verified"])
        self.assertFalse(report["Kore_acoustic_voice_id_verified"])
        self.assertFalse(report["speech_to_visual_highlight_verified"])
        self.assertFalse(report["student_publication_authorized"])

    def test_missing_or_duplicate_or_reordered_record_refused(self):
        for corrupt in (self.receipts[:-1],
                        self.receipts+[self.receipts[-1]],
                        list(reversed(self.receipts))):
            with self.assertRaises(ValueError):
                self.validate(receipts=corrupt)

    def test_wrong_declared_voice_or_model_or_utterance_sha_refused(self):
        for k,value in (("voice","different"),("model","different"),
                        ("spoken_text_sha256","0"*64),
                        ("provider_receipt_present",False)):
            corrupted=deepcopy(self.receipts)
            corrupted[2][k]=value
            with self.subTest(k=k),self.assertRaises(ValueError):
                self.validate(receipts=corrupted)

    def test_duplicate_wav_path_or_execution_receipt_refused(self):
        for k in ("pcm_wav_path","execution_id"):
            corrupted=deepcopy(self.receipts)
            corrupted[1][k]=corrupted[0][k]
            if k=="pcm_wav_path":
                corrupted[1]["wav_sha256"]=corrupted[0]["wav_sha256"]
            with self.subTest(k=k),self.assertRaises(ValueError):
                self.validate(receipts=corrupted)

    def test_changed_pcm_sha_refused(self):
        corrupted=deepcopy(self.receipts)
        corrupted[3]["wav_sha256"]="0"*64
        with self.assertRaises(ValueError):
            self.validate(receipts=corrupted)

    def test_silent_wav_or_mixed_sample_rates_refused(self):
        p=Path(self.receipts[1]["pcm_wav_path"])
        one_wav(p,silent=True)
        self.receipts[1]["wav_sha256"]=_sha(p)
        with self.assertRaises(ValueError):
            self.validate()
        one_wav(p,rate=11025)
        self.receipts[1]["wav_sha256"]=_sha(p)
        with self.assertRaises(ValueError):
            self.validate()

    def test_wav_inside_protected_source_directory_refused(self):
        p=self.original/"forbidden.wav"
        one_wav(p)
        self.receipts[0]["pcm_wav_path"]=str(p)
        self.receipts[0]["wav_sha256"]=_sha(p)
        with self.assertRaises(ValueError):
            self.validate()

    def test_forged_source_math_or_video_approval_not_accepted(self):
        r=self.validate()
        self.assertFalse(r["original_mathematics_independently_agreed"])
        self.assertFalse(r["approved_sub_600_second_mp4_produced"])
        self.readiness["student_publication_authorized"]=True
        with self.assertRaises(ValueError):
            self.validate()


if __name__=="__main__":
    unittest.main()
