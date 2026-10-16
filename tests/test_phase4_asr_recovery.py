"""Offline tests for browser-only ASR, typed mathematical review, safe resumption."""
from __future__ import annotations
import json
import tempfile
import unittest
import wave
from pathlib import Path
from selenium_pipeline.phase4_browser_asr import (
    parse_response,transcribe,AudioUnsupportedError,
    AmbiguousBrowserResponseError)
from selenium_pipeline.phase4_asr_recovery import recover

class BrowserASRTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.audio=root/"inputs";self.audio.mkdir()
        self.plan=self.audio/"plan.json"
        self.output=root/"web_asr_output"
        self.events=[]
        for index in range(1,4):
            name=f"s01_e{index:02d}.wav"
            with wave.open(str(self.audio/name),"wb") as wav:
                wav.setnchannels(1);wav.setsampwidth(2)
                wav.setframerate(24000);wav.writeframes(b"\x00\x10"*24000)
            self.events.append({"wav":name,
                "spoken_text":"Negative pi over two is the lower limit of integration."})
        self.plan.write_text(json.dumps({
            "status":"author_specified_unapproved_element_narration",
            "parts":[{"slides":[{"elements":self.events}]}]}),encoding="utf8")
        self.calls=[]
    def fake(self,path):
        self.calls.append(path.name)
        return "Negative pi over two is the lower limit of integration."
    def run_recovery(self,**kwargs):
        return recover(plan=self.plan,audio=self.audio,out=self.output,
                       confirmed=True,backend=self.fake,sleep=lambda _:None,
                       retries=1,**kwargs)

    def test_browser_json_requires_complete_audio_transcript(self):
        self.assertEqual(parse_response('{"status":"complete","transcript":"Pi over two."}'),
                         "Pi over two.")
        for raw in (
            '{"status":"unsupported","transcript":""}',
            '{"status":"complete","transcript":""}',
            '{"status":"complete","transcript":"Transcript","unknown":1}',
            'I cannot listen to this audio',
            '{"status":"complete","transcript":"two"}'):
            with self.subTest(raw=raw),self.assertRaises(Exception):
                parse_response(raw)

    def test_transport_receives_only_wav_not_reference_script(self):
        def transport(instruction,attachments):
            self.assertEqual(len(attachments),1)
            self.assertNotIn("Negative pi over two is the lower",instruction)
            self.assertTrue(attachments[0].is_file())
            return '{"status":"complete","transcript":"Pi over two is spoken"}'
        transcript=transcribe(self.audio/self.events[0]["wav"],transport=transport)
        self.assertEqual(transcript,"Pi over two is spoken")

    def test_resumes_after_partial_without_regenerating_receipts(self):
        a=self.run_recovery(max_new=2)
        self.assertEqual((a["newly_transcribed"],a["still_untranscribed"]),(2,1))
        first=self.output/"s01_e01.wav.asr.json"
        original=first.read_bytes()
        b=self.run_recovery(max_new=2)
        self.assertEqual((b["reused_verified_receipts"],b["newly_transcribed"]),(2,1))
        self.assertEqual(len(self.calls),3)
        self.assertEqual(first.read_bytes(),original)
        self.assertEqual(b["completed_receipts"],3)
        self.assertFalse(b["production_approved"])

    def test_provider_outage_blocks_with_retry_without_fake_receipts(self):
        self.fake=lambda path: (_ for _ in ()).throw(RuntimeError("503 overloaded"))
        result=recover(plan=self.plan,audio=self.audio,out=self.output,
                       confirmed=True,backend=self.fake,sleep=lambda _:None,
                       retries=2,max_new=3)
        self.assertEqual(result["attempts_this_run"],2)
        self.assertEqual(result["completed_receipts"],0)
        self.assertEqual(result["still_untranscribed"],3)
        self.assertEqual(result["status"],"WEB_ASR_INCOMPLETE_PROVIDER_ERROR")
        self.assertFalse((self.output/"s01_e01.wav.asr.json").exists())

    def test_web_audio_unsupported_does_not_retry(self):
        attempts=[]
        def unsupported(_):
            attempts.append(1)
            raise AudioUnsupportedError("No Gemini audio capability")
        data=recover(plan=self.plan,audio=self.audio,out=self.output,
                     confirmed=True,backend=unsupported,
                     retries=3,sleep=lambda _:None)
        self.assertEqual(data["status"],"WEB_AUDIO_UNSUPPORTED_REVIEW_BLOCKED")
        self.assertEqual(len(attempts),1)
        self.assertEqual(data["completed_receipts"],0)

    def test_ambiguous_browser_completion_never_resubmits(self):
        attempts=[]
        def ambiguous(_):
            attempts.append(1)
            raise AmbiguousBrowserResponseError("Quarantined")
        data=recover(plan=self.plan,audio=self.audio,out=self.output,
                     confirmed=True,backend=ambiguous,
                     retries=3,sleep=lambda _:None)
        self.assertEqual(data["status"],"WEB_RESPONSE_AMBIGUOUS_REVIEW_BLOCKED")
        self.assertEqual(len(attempts),1)

    def test_reject_stale_wav_sha_on_resume(self):
        self.run_recovery(max_new=1)
        with (self.audio/"s01_e01.wav").open("ab") as out:out.write(b"x")
        with self.assertRaisesRegex(ValueError,"stale or tampered"):
            self.run_recovery(max_new=1)

    def test_reject_rebound_plan_without_erasing_original_receipts(self):
        self.run_recovery(max_new=1)
        document=json.loads(self.plan.read_text())
        document["parts"][0]["slides"][0]["elements"][0]["spoken_text"]="Changed words"
        self.plan.write_text(json.dumps(document),encoding="utf8")
        with self.assertRaisesRegex(ValueError,"different model, plan or files"):
            self.run_recovery(max_new=1)
        self.assertTrue((self.output/"s01_e01.wav.asr.json").exists())

    def test_requires_explicit_live_optin(self):
        with self.assertRaisesRegex(ValueError,"explicit"):
            recover(plan=self.plan,audio=self.audio,out=self.output,
                    confirmed=False,backend=self.fake)
        self.assertFalse(self.output.exists())

    def test_reject_bad_model_asr_receipt(self):
        self.run_recovery(max_new=1)
        r=self.output/"s01_e01.wav.asr.json"
        data=json.loads(r.read_text())
        data["asr_model"]="gemini-3.1-flash-lite"
        r.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,"stale or tampered"):
            self.run_recovery(max_new=1)

if __name__=="__main__":
    unittest.main()
