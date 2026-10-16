"""Regression tests for genuinely separate offline speech-recognition evidence."""
from __future__ import annotations
import hashlib,json,tempfile,unittest,wave
from pathlib import Path
from selenium_pipeline.offline_speech_audit import run,model_digest
from selenium_pipeline.element_series_audit import check_independent_asr

class OfflineSpeechTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.plan_dir=self.root/"plan";self.plan_dir.mkdir()
        self.plan=self.plan_dir/"voice.json"
        self.audio=self.root/"audio";self.audio.mkdir()
        self.model=self.root/"model";self.model.mkdir()
        (self.model/"model.bin").write_bytes(b"fake-compressed-weights")
        (self.model/"config.json").write_text('{"test":true}')
        self.out=self.root/"asr"
        self.transcript="The right triangle illustrates secant substitution for this integral."
        self.name="s01_e01.wav"
        with wave.open(str(self.audio/self.name),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2)
            w.setframerate(24000);w.writeframes(b"\x40\x10"*24000)
        self.plan_json={
            "status":"author_specified_unapproved_element_narration",
            "parts":[{"slides":[{"elements":[{"wav":self.name,
                    "spoken_text":self.transcript}]}]}]}
        self.plan.write_text(json.dumps(self.plan_json),encoding="utf8")
        (self.audio/"tts_synthesis_receipt.json").write_text(json.dumps({
            "voice":"Kore","model":"gemini-3.8-flash-lite-tts",
            "same_declared_voice_all_segments":True}),encoding="utf8")

    def invoke(self,text=None,max_clips=1):
        return run(plan=self.plan,audio=self.audio,out=self.out,model_path=self.model,
                   max_clips=max_clips,transcriber=lambda b:
                        self.transcript if text is None else text)

    def validate_audit(self,required):
        return check_independent_asr(self.plan_json,self.audio,self.out,
            required=required,
            authored_sha256=hashlib.sha256(self.plan.read_bytes()).hexdigest())

    def test_independent_provider_receipt_not_academic_approval(self):
        result=self.invoke()
        self.assertTrue(result["all_clips_model_checked"])
        self.assertEqual(result["consistent"],1)
        row=json.loads((self.out/(self.name+".asr.json")).read_text())
        self.assertFalse(row["same_vendor_not_human_independent"])
        self.assertEqual(row["model_sha256"],model_digest(self.model))
        self.assertFalse(row["audible_word_fidelity_certified"])
        audit=self.validate_audit(required=True)
        self.assertTrue(audit["distinct_provider"])
        self.assertEqual(audit["checked"],1)
        self.assertFalse(audit["human_certified"])

    def test_wrong_words_flagged_and_required_gate_rejects(self):
        r=self.invoke("The audio describes a completely unrelated sentence instead.")
        self.assertEqual(r["flagged"],1)
        self.assertEqual(self.validate_audit(False)["flagged"],1)
        with self.assertRaisesRegex(ValueError,"incomplete or mismatched"):
            self.validate_audit(True)

    def test_model_weight_change_rejects_resumption(self):
        self.invoke()
        (self.model/"model.bin").write_bytes(b"different weights")
        with self.assertRaisesRegex(ValueError,"another model"):
            self.invoke()

    def test_audio_change_rejects_immutable_receipt(self):
        self.invoke()
        with (self.audio/self.name).open("ab") as f:f.write(b"unexpected")
        with self.assertRaisesRegex(ValueError,"stale/tampered"):
            self.invoke()

    def test_plan_change_rejects_job(self):
        self.invoke()
        self.plan_json["parts"][0]["slides"][0]["elements"][0]["spoken_text"]="Altered speech script"
        self.plan.write_text(json.dumps(self.plan_json),encoding="utf8")
        with self.assertRaisesRegex(ValueError,"another model or script"):
            self.invoke()

    def test_missing_receipts_stays_fail_closed(self):
        self.out.mkdir()
        self.out.joinpath("asr_job.json").write_text(json.dumps({
            "status":"offline_machine_asr_review_only",
            "model":"faster-whisper-small.en-cpu-int8",
            "backend":"offline_faster_whisper",
            "source_model":"gemini-3.8-flash-lite-tts",
            "plan_sha256":hashlib.sha256(self.plan.read_bytes()).hexdigest(),
            "tts_synthesis_receipt_sha256":hashlib.sha256(
               (self.audio/"tts_synthesis_receipt.json").read_bytes()).hexdigest(),
            "model_sha256":model_digest(self.model),
            "clips":[self.name]}),encoding="utf8")
        with self.assertRaisesRegex(ValueError,"incomplete or mismatched"):
            self.validate_audit(True)

if __name__=="__main__":
    unittest.main()
