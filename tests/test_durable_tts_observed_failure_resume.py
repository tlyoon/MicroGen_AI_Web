"""Offline fault injection: never rebill three observed Gemini failures."""
from __future__ import annotations
import os,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
from selenium_pipeline import tts
from selenium_pipeline.tts_attempt_evidence import AttemptEvidence
from selenium_pipeline.tts_effective_identity import LITE, FLASH

def fixture(folder,slides=2):
    (folder/"script.txt").write_text("".join(
        f"**Slide {i} [3 sec]:\nNarration sentence number {i}.\n\n"
        for i in range(1,slides+1)),encoding="utf8")
    return tts.blocks((folder/"script.txt").read_text(encoding="utf8"))

def fake_keys():
    fake=types.ModuleType("gemini_keys")
    fake.get_gemini_api_keys=lambda:["offline synthetic key"]
    fake.create_gemini_client=lambda:object()
    fake.call_with_client_failover=lambda factory,callback,**kw:callback(factory())
    return fake

def observe(ledger,slide,count,model=LITE):
    for n in range(1,count+1):
        ledger.record(provider="gemini",model=model,slide=slide,
                      round_number=n,outcome="transient_failure",
                      error_type="TimeoutError")

class DurableOutageResumeTests(unittest.TestCase):
    def test_previously_exhausted_three_calls_skip_all_repeated_paid_lite(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);items=fixture(folder)
            ledger=AttemptEvidence(folder,items)
            observe(ledger,1,3)
            with patch.dict(sys.modules,{"gemini_keys":fake_keys()}),\
                 patch("selenium_pipeline.tts._gemini_say") as primary,\
                 patch("selenium_pipeline.tts._whole_batch_fallback") as batch,\
                 patch.dict(os.environ,{"MICROGEN_TTS_QUEUE_DELAY_SECONDS":"0"}):
                tts.synthesize_folder(folder,"gemini",LITE,"Kore")
            primary.assert_not_called()
            batch.assert_called_once()
            self.assertEqual(batch.call_args.args[2]["model"],FLASH)
            self.assertEqual(len(AttemptEvidence(folder,items).read()),3)
            self.assertFalse((folder/"slide2.wav").exists())
    def test_two_prior_actual_calls_get_one_new_final_attempt_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);items=fixture(folder,1)
            ledger=AttemptEvidence(folder,items);observe(ledger,1,2)
            with patch.dict(sys.modules,{"gemini_keys":fake_keys()}),\
                 patch("selenium_pipeline.tts._gemini_say",
                       side_effect=RuntimeError("503 Gemini provider busy")) as primary,\
                 patch("selenium_pipeline.tts._whole_batch_fallback") as batch,\
                 patch.dict(os.environ,{"MICROGEN_TTS_QUEUE_DELAY_SECONDS":"0"}):
                tts.synthesize_folder(folder,"gemini",LITE,"Kore")
            self.assertEqual(primary.call_count,1)
            batch.assert_called_once()
            data=AttemptEvidence(folder,items).read()
            self.assertEqual([e["round"] for e in data],[1,2,3])
            self.assertEqual(len(data),3)
    def test_hash_chained_subprocess_round_restart_still_exhausts(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);items=fixture(folder,1)
            ledger=AttemptEvidence(folder,items)
            for _ in range(3):
                ledger.record(provider="gemini",model=LITE,slide=1,
                              round_number=1,outcome="transient_failure",
                              error_type="TimeoutError")
            with patch.dict(sys.modules,{"gemini_keys":fake_keys()}),\
                 patch("selenium_pipeline.tts._gemini_say") as primary,\
                 patch("selenium_pipeline.tts._whole_batch_fallback") as batch:
                tts.synthesize_folder(folder,"gemini",LITE,"Kore")
            primary.assert_not_called()
            batch.assert_called_once()
    def test_previous_successful_wav_and_failed_peer_are_preserved_exactly(self):
        import hashlib, io, wave
        from selenium_pipeline.tts_candidate_integrity import (
            job_identity, prepare, record_one)
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);items=fixture(folder,2)
            script_sha=hashlib.sha256(
                (folder/"script.txt").read_bytes()).hexdigest()
            identity=job_identity(items,provider="gemini",model=LITE,
                                  voice="Kore",script_sha256=script_sha)
            cache=folder/".tts_candidate";cache.mkdir()
            prepare(cache,identity)
            data=io.BytesIO()
            with wave.open(data,"wb") as out:
                out.setnchannels(1);out.setsampwidth(2)
                out.setframerate(24000);out.writeframes(b"\x00\x02"*24000)
            (cache/"slide1.wav").write_bytes(data.getvalue())
            record_one(cache,"slide1.wav",identity)
            original=(cache/"slide1.wav").read_bytes()
            ledger=AttemptEvidence(folder,items)
            ledger.record(provider="gemini",model=LITE,slide=1,
                          round_number=1,outcome="transient_failure",
                          error_type="TimeoutError")
            ledger.record(provider="gemini",model=LITE,slide=1,
                          round_number=2,outcome="success")
            observe(ledger,2,3)
            with patch.dict(sys.modules,{"gemini_keys":fake_keys()}),\
                 patch("selenium_pipeline.tts._gemini_say") as primary,\
                 patch("selenium_pipeline.tts._whole_batch_fallback") as batch:
                tts.synthesize_folder(folder,"gemini",LITE,"Kore")
            primary.assert_not_called();batch.assert_called_once()
            self.assertEqual((cache/"slide1.wav").read_bytes(),original)
            self.assertEqual(len(AttemptEvidence(folder,items).read()),5)

    def test_observed_permanent_failure_never_escalates(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);items=fixture(folder,1)
            ledger=AttemptEvidence(folder,items)
            ledger.record(provider="gemini",model=LITE,slide=1,
                          round_number=1,outcome="permanent_failure",
                          error_type="PermissionError")
            with patch.dict(sys.modules,{"gemini_keys":fake_keys()}),\
                 patch("selenium_pipeline.tts._gemini_say") as primary,\
                 patch("selenium_pipeline.tts._whole_batch_fallback") as batch:
                with self.assertRaisesRegex(RuntimeError,"Recorded permanent"):
                    tts.synthesize_folder(folder,"gemini",LITE,"Kore")
            primary.assert_not_called();batch.assert_not_called()
if __name__=="__main__":unittest.main()
