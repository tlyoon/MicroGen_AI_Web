"""Offline full-lesson acceptance guard fault-injection tests."""
from __future__ import annotations
import copy,hashlib,json,tempfile,unittest,wave
from pathlib import Path

from selenium_pipeline.element_series_audit import audit


def hash_bytes(data):
    return hashlib.sha256(data).hexdigest()


def H(path):
    return hash_bytes(path.read_bytes())


def put(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data),encoding="utf8")


class FullSeriesQAOfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.src=self.root/"source.pdf"
        self.slides=self.root/"slides.pdf"
        self.src.write_bytes(b"%PDF dummy source")
        self.slides.write_bytes(b"%PDF dummy slides")
        self.out=self.root/"new_audit.json"
        self.authored=self.root/"authored.json"
        self.audio=self.root/"audio"
        self.stage=self.root/"staged"
        self.render=self.root/"rendered"
        self.audio.mkdir();self.stage.mkdir();self.render.mkdir()
        original={"source_sha256":H(self.src),"slides_sha256":H(self.slides),
                  "parts":[]}
        tts={"status":"real_gemini_tts_generated_review_only_word_fidelity_unverified",
             "same_declared_voice_all_segments":True,
             "audible_word_fidelity_verified":False,
             "provider":"gemini","model":"gemini-3.8-flash-lite-tts",
             "voice":"Kore","segments":[]}
        series={"status":"review_only_not_approved",
                "source_sha256":H(self.src),
                "student_published":False,
                "accepted_lecture_completion_created":False,
                "parts":[]}
        for index,ids in enumerate((range(1,9),range(9,18)),1):
            name=f"part_{index:02d}"
            p=self.stage/name
            m=self.render/name
            p.mkdir();m.mkdir()
            elements=[];chunks=[];scene=[]
            recorded=[]
            audit_events=[]
            for j,slide in enumerate(ids,1):
                slide_elements=[]
                for k in range(1,4):
                    seq=len(elements)+1
                    filename=f"s{slide:02d}_e{k:02d}.wav"
                    content=f"Five words about mathematical item {slide} and step {k}."
                    transcript=hash_bytes(content.encode("utf8"))
                    wav=self.audio/filename
                    with wave.open(str(wav),"wb") as w:
                        w.setnchannels(1);w.setsampwidth(2)
                        w.setframerate(24000);w.writeframes(b"\x12\x13"*24000)
                    stamp=H(wav)
                    proof={"filename":filename,
                           "wav_sha256":stamp,
                           "spoken_text_sha256":transcript,
                           "model":"gemini-3.8-flash-lite-tts","voice":"Kore"}
                    put(self.audio/(filename+".verified.json"),proof)
                    tts["segments"].append(proof)
                    copied=p/"wav"/f"n{seq}.wav"
                    copied.parent.mkdir(exist_ok=True)
                    copied.write_bytes(wav.read_bytes())
                    seg=f"n{seq}"
                    chunks.append({"segment_id":seg,"filename":f"n{seq}.wav",
                                   "speech_sha256":transcript})
                    elements.append({"wav":filename,"spoken_text":content})
                    recorded.append({"segment_id":seg})
                    slide_elements.append({"wav":filename,"spoken_text":content})
                    audit_events.append({"event":seq,
                       "target_checks":[{"highlight_evidence_gain":9.2}]})
                scene.append({"slide":slide,"elements":slide_elements})
            original["parts"].append({"part_id":name,"slides":scene})
            put(p/"storyboard.json",{"narration_segments":recorded})
            put(p/"tts_chunks.json",{"segments":chunks})
            video=m/f"{name}_review.mp4"
            video.write_bytes(f"sample review video {name}".encode("utf8"))
            seconds=300.0
            rec={"mp4_sha256":H(video),"encoded_mp4_seconds":seconds,
                 "audio_seconds":seconds,"highlight_segments":len(elements),
                 "decoded_pixel_verified_events":len(elements),
                 "encoded_transition_qa":{
                     "verified_transition_count":len(elements),
                     "max_encoded_frame_drift_s":0.02}}
            put(m/"review_receipt.json",rec)
            put(m/"encoded_pixel_qa.json",{
                "count_events":len(elements),"checks":audit_events})
            series["parts"].append({"part_id":name})
        put(self.authored,original)
        put(self.audio/"tts_synthesis_receipt.json",tts)
        put(self.stage/"element_stage_receipt.json",{
            "source_sha256":H(self.src),
            "slides_sha256":H(self.slides),
            "complete_lecture_coverage":True,
            "audio_text_fidelity_verified":False,
            "mathematical_approval":False})
        put(self.render/"series_review_receipt.json",series)

    def runaudit(self):
        return audit(source=self.src,slides=self.slides,authored=self.authored,
                     audio=self.audio,staged=self.stage,rendered=self.render,
                     report=self.out)

    def test_whole_lecture_review_pass_does_not_approve_publication(self):
        result=self.runaudit()
        self.assertEqual(result["coverage_slides"],list(range(1,18)))
        self.assertEqual(result["coverage_elements"],51)
        self.assertFalse(result["academic_quality_human_signoff"])
        self.assertFalse(result["word_level_speech_fidelity_verified"])
        self.assertFalse(result["student_publication"])

    def test_reject_video_at_exact_ten_minutes(self):
        recfile=self.render/"part_02"/"review_receipt.json"
        rec=json.loads(recfile.read_text())
        rec["encoded_mp4_seconds"]=600.0
        put(recfile,rec)
        with self.assertRaisesRegex(ValueError,"10 minute"):
            self.runaudit()
        self.assertFalse(self.out.exists())

    def test_reject_wrong_pixel_target(self):
        recfile=self.render/"part_01"/"encoded_pixel_qa.json"
        rec=json.loads(recfile.read_text())
        rec["checks"][4]["target_checks"][0]["highlight_evidence_gain"]=-4
        put(recfile,rec)
        with self.assertRaisesRegex(ValueError,"active pixel"):
            self.runaudit()
        self.assertFalse(self.out.exists())

    def test_reject_tampered_voice_provenance(self):
        receipt=next(self.audio.glob("*.wav.verified.json"))
        rec=json.loads(receipt.read_text())
        rec["voice"]="anothervoice"
        put(receipt,rec)
        with self.assertRaisesRegex(ValueError,"voice mismatch"):
            self.runaudit()
        self.assertFalse(self.out.exists())


if __name__=="__main__":
    unittest.main()
