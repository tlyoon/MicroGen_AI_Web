"""Safety tests for no-unjustified-auto-regeneration TTS recovery decisions."""
import json,struct,tempfile,unittest,wave
from pathlib import Path
from selenium_pipeline.tts_quality_gate import screen,digest
from selenium_pipeline.phase4_repair_triage import make

class SelectiveRepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.plan=root/"plan.json";self.audio=root/"audio";self.audio.mkdir()
        self.qa=root/"qa.json";self.out=root/"repair_plan.json"
        events=[]
        for i,value in enumerate((0,6000),1):
            name=f"s01_e0{i}.wav"
            with wave.open(str(self.audio/name),"wb") as wav:
                wav.setnchannels(1);wav.setsampwidth(2)
                wav.setframerate(24000)
                wav.writeframes(struct.pack("<h",value)*72000)
            events.append({"wav":name,
               "spoken_text":"We integrate the function over the given interval."})
        self.plan.write_text(json.dumps(
            {"status":"author_specified_unapproved_element_narration",
             "parts":[{"slides":[{"elements":events}]}]}))
        screen(plan=self.plan,audio=self.audio,output=self.qa)
    def run_triage(self):
        return make(plan=self.plan,audio=self.audio,quality=self.qa,out=self.out)
    def test_silent_clip_is_candidate_not_regenerated(self):
        before=[digest(p) for p in sorted(self.audio.glob("*.wav"))]
        result=self.run_triage()
        self.assertEqual(result["technical_regeneration_candidates"],1)
        self.assertEqual(result["pending_independent_transcription"],1)
        self.assertFalse(result["regeneration_executed"])
        self.assertFalse(result["student_publication"])
        self.assertEqual(before,[digest(p) for p in sorted(self.audio.glob("*.wav"))])
    def test_reject_forged_machine_pass_without_replacing_output(self):
        qa=json.loads(self.qa.read_text())
        qa["clips"][0]["quality_state"]="machine_screen_consistent_not_certified"
        self.qa.write_text(json.dumps(qa))
        with self.assertRaisesRegex(ValueError,"stale, tampered"):
            self.run_triage()
        self.assertFalse(self.out.exists())
    def test_reject_modified_waveform(self):
        p=self.audio/"s01_e02.wav"
        with p.open("ab") as fh:fh.write(b"extra")
        with self.assertRaisesRegex(ValueError,"stale, tampered"):
            self.run_triage()
    def test_non_overwrite_existing_plan(self):
        self.out.write_text("preserve")
        with self.assertRaisesRegex(ValueError,"Unsafe"):
            self.run_triage()
        self.assertEqual(self.out.read_text(),"preserve")

if __name__=="__main__":unittest.main()
