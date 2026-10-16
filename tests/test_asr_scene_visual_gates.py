"""Offline fault tests for independent ASR and reusable review-only scenes."""
from __future__ import annotations
import json,tempfile,unittest,wave
from pathlib import Path
import pymupdf
from selenium_pipeline.independent_speech_audit import run,distance
from selenium_pipeline.scene_candidate_authoring import draft
from selenium_pipeline.academic_visual_preflight import inspect

class SpeechAndSceneGates(unittest.TestCase):
 def setUp(self):
    self.temp=tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root=Path(self.temp.name)
    self.parent=self.root/"plan"
    self.parent.mkdir()
    self.plan=self.parent/"authored.json"
    self.aud=self.root/"audio"
    self.aud.mkdir()
    self.out=self.root/"review"
    self.spoken="We use a right reference triangle to reverse the substitution."
    self.plan.write_text(json.dumps({
       "status":"author_specified_unapproved_element_narration",
       "parts":[{"slides":[{"elements":[{
       "wav":"n1.wav","spoken_text":self.spoken}]}]}]}),encoding="utf8")
    with wave.open(str(self.aud/"n1.wav"),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000)
        w.writeframes(b"\x01\x10"*24000)
 def call(self,fn,**kwargs):
    return run(plan=self.plan,audio=self.aud,out=self.out,max_clips=1,
               confirm=True,transcriber=fn,**kwargs)

 def test_distinct_model_asr_agreement_not_certification(self):
    result=self.call(lambda raw:self.spoken)
    self.assertEqual(result["consistent"],1)
    self.assertFalse(result["audible_word_fidelity_certified"])
    record=json.loads((self.out/"n1.wav.asr.json").read_text())
    self.assertTrue(record["model_distinct_from_tts"])
    self.assertFalse(record["audible_word_fidelity_certified"])

 def test_bad_audio_transcript_flagged_not_approved(self):
    result=self.call(lambda raw:"This recording says an entirely different statement.")
    self.assertEqual(result["flagged"],1)
    self.assertEqual(result["consistent"],0)

 def test_missing_transcription_fails_closed(self):
    with self.assertRaises(ValueError):
        run(plan=self.plan,audio=self.aud,out=self.out,max_clips=1,
            confirm=False,transcriber=lambda _:self.spoken)
    self.assertFalse(self.out.exists())

 def test_tampered_wav_rejects_prior_receipt(self):
    self.call(lambda _:self.spoken)
    with (self.aud/"n1.wav").open("ab") as f:f.write(b"corruption")
    with self.assertRaisesRegex(ValueError,"Stale/tampered"):
        self.call(lambda _:self.spoken)

 def test_stale_plan_rejects_prior_asr(self):
    self.call(lambda _:self.spoken)
    p=json.loads(self.plan.read_text())
    p["parts"][0]["slides"][0]["elements"][0]["spoken_text"]="Changed script after transcription."
    self.plan.write_text(json.dumps(p))
    with self.assertRaisesRegex(ValueError,"different plan"):
        self.call(lambda _:self.spoken)

 def test_text_similarity_normalization(self):
    self.assertTrue(distance("Three plus four.", "three, plus FOUR!")["machine_asr_consistent"])
    self.assertFalse(distance("One two three four five.", "Unrelated text.")["machine_asr_consistent"])

 def test_generic_scene_authoring_never_ready_for_tts(self):
    s=self.root/"source.pdf";sl=self.root/"slides.pdf"
    d=pymupdf.open()
    p=d.new_page(width=400,height=300)
    p.insert_text((45,80),"We calculate the antiderivative using a right reference triangle.")
    d.save(s);d.close()
    d=pymupdf.open()
    p=d.new_page(width=400,height=300)
    p.insert_text((20,25),"Lecture title")
    p.insert_text((30,90),"We calculate the antiderivative using a right reference triangle.")
    d.save(sl);d.close()
    result=draft(s,sl)
    self.assertEqual(result["slide_count"],1)
    self.assertEqual(result["status"],"REVIEW_REQUIRED_NOT_TTS_READY")
    self.assertFalse(result["automatic_approval"])
    self.assertFalse(result["all_narration_authored"])
    self.assertTrue(result["slides"][0]["targets"])
    self.assertIsNone(result["slides"][0]["targets"][0]["proposed_spoken_text"])

 def test_pdf_figure_legibility_caution_without_academic_approval(self):
    s=self.root/"slides.pdf"
    from PIL import Image
    pic=self.root/"figure.png"
    Image.new("RGB",(300,300),"white").save(pic)
    d=pymupdf.open();p=d.new_page(width=400,height=300)
    p.insert_image(pymupdf.Rect(30,80,60,120),filename=str(pic))
    d.save(s);d.close()
    result=inspect(s)
    self.assertEqual(result["pages"],1)
    self.assertGreaterEqual(result["counts"]["small_figures"],1)
    self.assertFalse(result["mathematical_correctness_verified"])
    self.assertFalse(result["human_figure_legibility_approved"])

if __name__=="__main__":unittest.main()
