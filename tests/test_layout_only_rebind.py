"""Fail-closed generic layout-only WAV reuse and Figure correction provenance tests."""
from __future__ import annotations
import copy,hashlib,json,tempfile,unittest,wave
from pathlib import Path
import pymupdf
from PIL import Image
from selenium_pipeline.layout_only_rebind import rebind,sha
from selenium_pipeline.element_series_audit import verify_layout_only_rebind

def write_json(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False),encoding="utf8")

class LayoutOnlyRebindTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source_folder=self.root/"textbook";self.source_folder.mkdir()
        self.source=self.source_folder/"source.pdf"
        d=pymupdf.open();d.new_page().insert_text((20,55),"Textbook source description")
        d.save(self.source);d.close()
        self.old=self.source_folder/"slides.pdf"
        self.updated_folder=self.root/"candidate";self.updated_folder.mkdir()
        self.new=self.updated_folder/"slides.pdf"
        self.picture=self.root/"diagram.png"
        Image.new("RGB",(200,110),"blue").save(self.picture)
        self.generate(self.old,60)
        self.generate(self.new,94)
        self.audio=self.root/"recorded";self.audio.mkdir()
        self.filename="narration_01.wav"
        self.transcript="The reference diagram illustrates the substitution branch."
        self.recorded=self.audio/self.filename
        with wave.open(str(self.recorded),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2)
            w.setframerate(24000);w.writeframes(b"\x01\x10"*24000)
        text_sha=hashlib.sha256(self.transcript.encode("utf8")).hexdigest()
        self.synthesis={
            "status":"real_gemini_tts_generated_review_only_word_fidelity_unverified",
            "voice":"Kore","model":"gemini-3.8-flash-lite-tts",
            "provider":"gemini","same_declared_voice_all_segments":True,
            "audible_word_fidelity_verified":False,
            "segments":[{"filename":self.filename,
                         "wav_sha256":sha(self.recorded),
                         "spoken_text_sha256":text_sha}]}
        write_json(self.audio/"tts_synthesis_receipt.json",self.synthesis)
        write_json(self.audio/(self.filename+".verified.json"),{
            "wav_sha256":sha(self.recorded),"spoken_text_sha256":text_sha,
            "voice":"Kore","model":"gemini-3.8-flash-lite-tts"})
        self.prior=self.root/"voice_plan.json"
        self.plan={
            "schema_version":1,
            "status":"author_specified_unapproved_element_narration",
            "source_sha256":sha(self.source),
            "slides_sha256":sha(self.old),
            "voice_id":"gemini_gemini-3.8-flash-lite-tts_Kore_REVIEW_ONLY",
            "parts":[{"part_id":"part_01","slides":[
                {"slide":2,"source_page":1,"source_evidence":"Textbook source description",
                 "elements":[{"anchor":{"type":"image_whole","index":0},
                    "wav":self.filename,"spoken_text":self.transcript}]}]}]
        }
        write_json(self.prior,self.plan)
        self.fig=self.updated_folder/"figure_resize_receipt.json"
        write_json(self.fig,{
            "status":"REVIEW_ONLY_ISOLATED_FIGURE_RESIZE",
            "source_slides_sha256":sha(self.old),
            "derived_slides_sha256":sha(self.new),
            "target_slide":2,"changed_rendered_slide_numbers":[2],
            "production_approved":False})
        self.new_plan=self.root/"rebound_plan.json"
        self.receipt=self.root/"rebind_receipt.json"

    def generate(self,path,width):
        doc=pymupdf.open()
        for i in range(2):
            page=doc.new_page(width=380,height=270)
            page.insert_text((25,65),"Slide rendering remains mathematically identical")
            if i==1:
                page.insert_image(pymupdf.Rect(160-width/2,115,
                    160+width/2,165),filename=str(self.picture),keep_proportion=False)
        doc.save(path);doc.close()

    def do_rebind(self):
        return rebind(source=self.source,old_slides=self.old,
            new_slides=self.new,voice_plan=self.prior,audio=self.audio,
            figure_receipt=self.fig,out_plan=self.new_plan,
            out_receipt=self.receipt)

    def verify_audit(self):
        return verify_layout_only_rebind(current=json.loads(
            self.new_plan.read_text(encoding="utf8")),source=self.source,
            slides=self.new,audio=self.audio,old_slides=self.old,
            previous_voice_plan=self.prior,rebind_receipt=self.receipt,
            figure_resize_receipt=self.fig)

    def test_valid_layout_only_rebind_preserves_every_word_wav_and_source(self):
        old_source_hash=sha(self.source)
        old_wav_hash=sha(self.recorded)
        result=self.do_rebind()
        self.assertEqual(result["changed_slides"],[2])
        self.assertEqual(result["wav_count"],1)
        self.assertEqual(len(result["changed_element_anchors"]),1)
        self.assertEqual(self.verify_audit()["status"],
                         "review_only_layout_rebind_evidence_pass")
        self.assertEqual(sha(self.source),old_source_hash)
        self.assertEqual(sha(self.recorded),old_wav_hash)
        self.assertEqual(json.loads(self.prior.read_text())["slides_sha256"],sha(self.old))

    def test_tampered_audio_rejected_before_output(self):
        self.recorded.write_bytes(self.recorded.read_bytes()+b"x")
        with self.assertRaisesRegex(ValueError,"waveform"):
            self.do_rebind()
        self.assertFalse(self.new_plan.exists())
        self.assertFalse(self.receipt.exists())

    def test_changed_original_nontarget_slide_pixels_rejected(self):
        doc=pymupdf.open(self.new)
        doc[0].insert_text((30,180),"An unintended change")
        copy_path=self.updated_folder/"wrong.pdf"
        doc.save(copy_path);doc.close()
        self.new=copy_path
        receipt=json.loads(self.fig.read_text())
        receipt["derived_slides_sha256"]=sha(self.new)
        write_json(self.fig,receipt)
        with self.assertRaisesRegex(ValueError,"Rendered slide mathematical text changed"):
            self.do_rebind()

    def test_new_authored_narration_must_equal_old_plan(self):
        self.do_rebind()
        changed=json.loads(self.new_plan.read_text())
        changed["parts"][0]["slides"][0]["elements"][0]["spoken_text"]="Tampered text"
        write_json(self.new_plan,changed)
        with self.assertRaisesRegex(ValueError,"modifies content"):
            self.verify_audit()

    def test_incomplete_rebind_audit_evidence_fails_closed(self):
        self.do_rebind()
        with self.assertRaisesRegex(ValueError,"all four"):
            verify_layout_only_rebind(current=json.loads(self.new_plan.read_text()),
                source=self.source,slides=self.new,audio=self.audio,
                old_slides=self.old,previous_voice_plan=None,
                rebind_receipt=self.receipt,figure_resize_receipt=self.fig)

if __name__=="__main__":
    unittest.main()
