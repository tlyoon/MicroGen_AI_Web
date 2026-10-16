"""No-network and fail-closed offline Whisper ASR recovery tests."""
import json,tempfile,unittest,wave
from pathlib import Path
from selenium_pipeline.phase4_local_asr import run,model_identity
from selenium_pipeline.tts_quality_gate import screen
from selenium_pipeline.element_series_audit import check_independent_asr
from selenium_pipeline.phase4_local_asr import filehash

class OfflineASRTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name)
        self.audio=root/"audio";self.audio.mkdir()
        self.model=root/"models"/"small.en";self.model.mkdir(parents=True)
        for f in ("model.bin","config.json","tokenizer.json"):
            (self.model/f).write_bytes(b"offline test fixture "+f.encode())
        self.plan=root/"plan.json";self.out=root/"asr"
        self.words="Negative pi over two is the limit of integration."
        scenes=[]
        for index in range(1,4):
            name=f"s01_e0{index}.wav"
            with wave.open(str(self.audio/name),"wb") as w:
                w.setnchannels(1);w.setsampwidth(2)
                w.setframerate(24000);w.writeframes(b"\x00\x10"*24000)
            scenes.append({"wav":name,"spoken_text":self.words})
        self.plan.write_text(json.dumps({
            "status":"author_specified_unapproved_element_narration",
            "parts":[{"slides":[{"elements":scenes}]}]}),encoding="utf8")
        self.calls=[]
    def fake(self,wav):
        self.calls.append(wav.name)
        return self.words
    def run_local(self,**kwargs):
        return run(plan=self.plan,audio=self.audio,model_dir=self.model,
                   model_size="small.en",out=self.out,
                   recognizer=self.fake,**kwargs)

    def test_model_requirements_offline_fail_closed(self):
        self.assertEqual(len(model_identity(self.model,"small.en")["model_sha256"]),64)
        (self.model/"model.bin").unlink()
        with self.assertRaisesRegex(ValueError,"Missing or unsafe local model"):
            self.run_local(max_new=1)
        self.assertFalse(self.out.exists())

    def test_reuse_immutable_per_wav_receipts(self):
        first=self.run_local(max_new=1)
        self.assertEqual((first["new_receipts"],first["remaining"]),(1,2))
        receipt=self.out/"s01_e01.wav.asr.json"
        old=receipt.read_bytes()
        second=self.run_local(max_new=2)
        self.assertEqual(second["new_receipts"],2)
        self.assertEqual(second["reused"],1)
        self.assertEqual(second["completed_receipts"],3)
        self.assertEqual(receipt.read_bytes(),old)
        self.assertEqual(len(self.calls),3)
        self.assertFalse(second["production_approved"])
        self.assertFalse(second["api_calls_performed"])

    def test_reject_changed_model_file_hash(self):
        self.run_local(max_new=1)
        (self.model/"model.bin").write_bytes(b"changed weights")
        with self.assertRaisesRegex(ValueError,"identity changed"):
            self.run_local(max_new=2)

    def test_reject_edited_model_asr_transcript(self):
        self.run_local(max_new=1)
        p=self.out/"s01_e01.wav.asr.json"
        data=json.loads(p.read_text());data["transcript"]="FAKE"
        p.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,"stale or tampered"):
            self.run_local(max_new=2)

    def test_wrong_script_resumption_rejected(self):
        self.run_local(max_new=1)
        job=json.loads(self.plan.read_text())
        job["parts"][0]["slides"][0]["elements"][0]["spoken_text"]="altered words"
        self.plan.write_text(json.dumps(job))
        with self.assertRaisesRegex(ValueError,"identity changed"):
            self.run_local(max_new=2)

    def test_local_receipts_are_accepted_by_existing_quality_gates(self):
        result=self.run_local(max_new=3)
        self.assertEqual(result["completed_receipts"],3)
        qa=screen(plan=self.plan,audio=self.audio,asr_dir=self.out,
                  output=self.out.parent/"quality.json")
        self.assertEqual(qa["pending_asr"],0)
        self.assertEqual(qa["machine_screen_passed"],0) # synthetic WAVs are not speech
        self.assertFalse(qa["production_approved"])
        job=json.loads(self.plan.read_text())
        audit=check_independent_asr(job,self.audio,self.out,
                   authored_sha256=filehash(self.plan),required=True)
        self.assertEqual((audit["checked"],audit["matched"]),(3,3))
        self.assertFalse(audit["human_certified"])

    def test_forged_local_model_hash_fails_quality_acceptance(self):
        self.run_local(max_new=3)
        receipt=self.out/"s01_e01.wav.asr.json"
        v=json.loads(receipt.read_text())
        v["model_sha256"]="not really the local model"
        receipt.write_text(json.dumps(v))
        with self.assertRaisesRegex(ValueError,"Unverifiable local ASR"):
            screen(plan=self.plan,audio=self.audio,asr_dir=self.out,
                  output=self.out.parent/"quality.json")

    def test_no_model_path_never_tries_network(self):
        with self.assertRaisesRegex(ValueError,"No local model"):
            run(plan=self.plan,audio=self.audio,
                model_dir=self.model.parent/"missing",model_size="small.en",
                out=self.out,max_new=1,recognizer=self.fake)
        self.assertFalse(self.out.exists())

    def test_backend_inference_failure_retains_prior_receipts(self):
        self.run_local(max_new=1)
        existing=(self.out/"s01_e01.wav.asr.json").read_bytes()
        def broken(w):raise RuntimeError("offline compute exhausted")
        data=run(plan=self.plan,audio=self.audio,model_dir=self.model,
                 model_size="small.en",out=self.out,max_new=2,recognizer=broken)
        self.assertEqual(data["new_receipts"],0)
        self.assertEqual(data["completed_receipts"],1)
        self.assertEqual(data["remaining"],2)
        self.assertEqual(data["error_type"],"RuntimeError")
        self.assertEqual((self.out/"s01_e01.wav.asr.json").read_bytes(),existing)

    def test_normalized_word_errors_fail_mismatch(self):
        def bad(_):return "Positive pi over two is the limit of integration."
        data=run(plan=self.plan,audio=self.audio,model_dir=self.model,
                 model_size="small.en",out=self.out,max_new=1,recognizer=bad)
        receipt=json.loads((self.out/"s01_e01.wav.asr.json").read_text())
        self.assertGreater(receipt["metrics"]["wer"],0)
        self.assertEqual(data["completed_receipts"],1)
        self.assertFalse(receipt["academic_approval"])

if __name__=="__main__":unittest.main()
