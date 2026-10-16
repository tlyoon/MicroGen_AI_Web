"""Private review packet must be source-bound, replayable and unapproved."""
from __future__ import annotations
import hashlib,json,tempfile,unittest,wave
from pathlib import Path
from selenium_pipeline.speech_listening_packet import generate
from selenium_pipeline.offline_speech_audit import run

class ReviewPacketTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        r=Path(self.tmp.name)
        self.recordings=r/"audio";self.recordings.mkdir()
        self.asr=r/"asr"
        self.dest=r/"human_review"
        self.model=r/"model";self.model.mkdir()
        (self.model/"model.bin").write_bytes(b"weights")
        (self.model/"config.json").write_bytes(b"{}")
        self.plan=r/"plan.json"
        self.script="The right triangle has length five and height four."
        self.name="s01_e01.wav"
        self.plan.write_text(json.dumps({"schema_version":1,
            "status":"author_specified_unapproved_element_narration",
            "parts":[{"part_id":"part_01","slides":[{"slide":1,"elements":[
                {"wav":self.name,"spoken_text":self.script}]}]}]}),encoding="utf8")
        with wave.open(str(self.recordings/self.name),"wb") as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(24000)
            f.writeframes(b"\x00\x10"*24000)
        (self.recordings/"tts_synthesis_receipt.json").write_text(json.dumps({
            "voice":"Kore","model":"gemini-3.8-flash-lite-tts",
            "same_declared_voice_all_segments":True}),encoding="utf8")
        run(plan=self.plan,audio=self.recordings,out=self.asr,
            model_path=self.model,max_clips=1,transcriber=lambda x:self.script)

    def test_packet_includes_playable_original_wav_and_never_approves(self):
        result=generate(plan=self.plan,recordings=self.recordings,asr=self.asr,
               destination=self.dest)
        self.assertEqual(result["total"],1)
        self.assertEqual(result["machine_consistent"],1)
        self.assertFalse(result["academic_approval"])
        self.assertFalse(result["human_listening_approval"])
        self.assertEqual((self.dest/"audio"/self.name).read_bytes(),
                         (self.recordings/self.name).read_bytes())
        doc=(self.dest/"index.html").read_text()
        self.assertIn("NOT HUMAN VERIFIED",doc)
        self.assertIn("audio/s01_e01.wav",doc)
        self.assertTrue((self.dest/"lecturer_review_checklist.csv").exists())

    def test_output_cannot_overwrite_existing_review_packet(self):
        self.dest.mkdir()
        self.dest.joinpath("important.txt").write_text("keep")
        with self.assertRaisesRegex(ValueError,"new output"):
            generate(plan=self.plan,recordings=self.recordings,
                asr=self.asr,destination=self.dest)
        self.assertEqual(self.dest.joinpath("important.txt").read_text(),"keep")

    def test_tampered_asr_evidence_rejected_before_copy(self):
        row=self.asr/(self.name+".asr.json")
        data=json.loads(row.read_text())
        data["transcript"]="Completely changed text"
        row.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,"tampered"):
            generate(plan=self.plan,recordings=self.recordings,
                asr=self.asr,destination=self.dest)
        self.assertFalse(self.dest.exists())

if __name__=="__main__":unittest.main()
