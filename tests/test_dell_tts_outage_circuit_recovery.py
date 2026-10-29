"""Regression for live Dell-115 Flash-Lite sustained outage without false Cloud proof."""
import os,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline import tts
from selenium_pipeline.tts_attempt_evidence import AttemptEvidence
from selenium_pipeline.tts_effective_identity import LITE

class Dell115OutageCircuitTests(unittest.TestCase):
    def test_real_three_observed_failures_trigger_homogeneous_fallback_without_hammering_untried_slides(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            (folder/"script.txt").write_text(
                "**Slide 1 [3 sec]:\nOne.\n"
                "**Slide 2 [3 sec]:\nTwo.\n"
                "**Slide 3 [3 sec]:\nThree.",encoding="utf8")
            items=tts.blocks((folder/"script.txt").read_text(encoding="utf8"))
            self.assertEqual(len(items),3)
            fake=types.ModuleType("gemini_keys")
            fake.get_gemini_api_keys=lambda:["fake-offline-only"]
            fake.create_gemini_client=lambda:object()
            fake.call_with_client_failover=lambda factory, callback,**kwargs:callback(factory())
            calls=[]
            def failed(client,text,model,voice):
                calls.append(text)
                raise TimeoutError("synthetic Gemini API server busy")
            with patch.dict(sys.modules,{"gemini_keys":fake}),patch.dict(
                os.environ,{"MICROGEN_TTS_QUEUE_ROUNDS":"3",
                "MICROGEN_TTS_QUEUE_CIRCUIT_BREAKER_FAILURES":"2",
                "MICROGEN_TTS_QUEUE_DELAY_SECONDS":"0",
                "MICROGEN_TTS_ENABLE_PROVIDER_FALLBACK":"1",
                "MICROGEN_TTS_ENABLE_BATCH_FALLBACK":"1"}),patch(
                "selenium_pipeline.tts._gemini_say",side_effect=failed
                ),patch("selenium_pipeline.tts._whole_batch_fallback") as fallback:
                tts.synthesize_folder(folder,"gemini",LITE,"Kore")
            self.assertEqual(len(calls),6)
            self.assertEqual(calls,["One.","Two."]*3)
            fallback.assert_called_once()
            journal=AttemptEvidence(folder,items)
            events=journal.read()
            self.assertEqual(len(events),6)
            self.assertEqual(sorted(set(e["slide"] for e in events)),[1,2])
            self.assertEqual([e["round"] for e in events],[1,1,2,2,3,3])
            self.assertEqual(journal.verify_before("gemini","gemini-3.8-flash-tts")["lite"]["failed_slides"],[1,2])
            self.assertFalse((folder/"slide3.wav").exists())

    def test_restarted_local_rounds_are_distinct_hash_linked_real_failures(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            (folder/"script.txt").write_text("**Slide 1 [3 sec]:\nOne.",encoding="utf8")
            items=tts.blocks((folder/"script.txt").read_text(encoding="utf8"))
            ledger=AttemptEvidence(folder,items)
            for _ in range(3):
                ledger.record(provider="gemini",model=LITE,slide=1,
                    round_number=1,outcome="transient_failure",error_type="TimeoutError")
            self.assertEqual(ledger.verify_exhausted(LITE)["failed_slides"],[1])

if __name__=="__main__":unittest.main()
