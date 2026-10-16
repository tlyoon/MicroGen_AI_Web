"""Offline regression tests for transferring real ASR receipts across visual-only edits."""
from __future__ import annotations
import hashlib,json,tempfile,unittest
from pathlib import Path
from selenium_pipeline.asr_layout_carryover import migrate,sha
from selenium_pipeline.element_series_audit import check_independent_asr

def write(p,value):
    p.write_text(json.dumps(value),encoding="utf8")

class LayoutASRCarryoverTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.orig=self.root/"old.json"
        self.rebound=self.root/"new.json"
        self.audio=self.root/"audio";self.audio.mkdir()
        self.old_asr=self.root/"old_asr";self.old_asr.mkdir()
        self.dest=self.root/"new_asr"
        self.receipt=self.root/"layout.json"
        self.wav=self.audio/"example.wav";self.wav.write_bytes(b"real audio sample")
        (self.audio/"missing.wav").write_bytes(b"untranscribed but existing audio")
        self.words="An integral can be transformed using substitution."
        self.old={
          "schema_version":1,
          "status":"author_specified_unapproved_element_narration",
          "source_sha256":"SOURCEHASH","slides_sha256":"OLDPDF",
          "parts":[{"slides":[{"elements":[
            {"wav":"example.wav","spoken_text":self.words},
            {"wav":"missing.wav","spoken_text":"Another integral is left untranscribed."}]}]}]}
        write(self.orig,self.old)
        self.new=json.loads(json.dumps(self.old))
        self.new["slides_sha256"]="NEWPDF"
        self.new["layout_only_rebind_from_voice_plan_sha256"]=sha(self.orig)
        self.new["layout_only_rebind_receipt_sha256"]="RECEIPT_HASH"
        write(self.rebound,self.new)
        write(self.receipt,{
            "old_voice_bound_plan_sha256":sha(self.orig),
            "new_slides_sha256":"NEWPDF","source_sha256":"SOURCEHASH",
            "figure_resize_receipt_sha256":"RECEIPT_HASH",
            "all_original_wav_bytes_and_text_hashes_verified":True,
            "academic_approval":False,"production_approved":False})
        self.model="gemini-3.1-flash-lite"
        write(self.old_asr/"asr_job.json",{
            "schema_version":1,"status":"independent_model_asr_review_only",
            "plan_sha256":sha(self.orig),"model":self.model,
            "source_model":"gemini-3.8-flash-lite-tts",
            "clips":["example.wav","missing.wav"]})
        write(self.old_asr/"example.wav.asr.json",{
            "status":"machine_asr_consistent_not_certified",
            "wav":"example.wav","wav_sha256":sha(self.wav),
            "reference_sha256":hashlib.sha256(self.words.encode("utf8")).hexdigest(),
            "asr_model":self.model,"transcript":self.words,
            "transcript_sha256":hashlib.sha256(self.words.encode("utf8")).hexdigest(),
            "metrics":{"machine_asr_consistent":True},
            "audible_word_fidelity_certified":False})

    def run_carryover(self):
        return migrate(original_plan=self.orig,rebound_plan=self.rebound,
                       original_asr=self.old_asr,audio=self.audio,
                       layout_receipt=self.receipt,out=self.dest)
    def test_only_completed_evidence_carries_over(self):
        result=self.run_carryover()
        self.assertEqual(result["previously_machine_transcribed"],1)
        self.assertEqual(result["unverified_clips"],1)
        self.assertFalse(result["production_approved"])
        self.assertFalse((self.dest/"missing.wav.asr.json").exists())
        self.assertEqual(check_independent_asr(self.new,self.audio,self.dest,
                             authored_sha256=sha(self.rebound))["checked"],1)
    def test_reject_changed_spoken_text_even_if_rebound_field_matches(self):
        altered=json.loads(self.rebound.read_text())
        altered["parts"][0]["slides"][0]["elements"][0]["spoken_text"]="Tampered"
        write(self.rebound,altered)
        with self.assertRaisesRegex(ValueError,"changed narration"):
            self.run_carryover()
        self.assertFalse(self.dest.exists())
    def test_reject_tampered_old_waveform(self):
        self.wav.write_bytes(b"changed waveform")
        with self.assertRaisesRegex(ValueError,"Stale or fabricated"):
            self.run_carryover()
        self.assertFalse(self.dest.exists())
    def test_refuse_existing_destination(self):
        self.dest.mkdir()
        (self.dest/"marker").write_text("keep")
        with self.assertRaisesRegex(ValueError,"output already exists"):
            self.run_carryover()
        self.assertEqual((self.dest/"marker").read_text(),"keep")
    def test_refuse_forged_original_asr_job_provenance(self):
        obj=json.loads((self.old_asr/"asr_job.json").read_text())
        obj["plan_sha256"]="forged"
        write(self.old_asr/"asr_job.json",obj)
        with self.assertRaisesRegex(ValueError,"not bound"):
            self.run_carryover()
        self.assertFalse(self.dest.exists())

if __name__=="__main__":
    unittest.main()
