import unittest,tempfile,hashlib,copy
from pathlib import Path
from selenium_pipeline.nonbilled_kore_source_handoff_audit import audit_nonbilled_kore_handoff,MODEL,VOICE
class KoreHandoff(unittest.TestCase):
 def setup(self,root):
    f=Path(root);sha={}
    for name in ("source.pdf","slides.pdf","script.txt"):
        (f/name).write_bytes(name.encode());sha[name]=hashlib.sha256(name.encode()).hexdigest()
    return f,{"status":"AI_SOURCE_CITED_VERBATIM_KORE_TTS_HANDOFF_NOT_DISPATCHED",
      "source_sha256":sha["source.pdf"],"slides_sha256":sha["slides.pdf"],
      "script_sha256":sha["script.txt"],"paid_TTS_request_made":False,
      "production_release_allowed":False,"student_publication_authorized":False,
      "primary_model":MODEL,"primary_voice":VOICE,"narration_total":1,
      "AI_source_agreed_segments":0,"actual_verbatim_jobs":[],
      "unresolved_source_segments":1,"unresolved_utterance_ids":["u1"]}
 def test_real_zero_consensus_yields_zero_kore_jobs(self):
    with tempfile.TemporaryDirectory() as d:
        f,report=self.setup(d);x=audit_nonbilled_kore_handoff(folder=f,report=report)
        self.assertEqual(x["source_math_agreed_jobs"],0)
        self.assertFalse(x["student_publication_authorized"])
 def test_nonoriginal_voice_and_sha_cannot_pass(self):
    with tempfile.TemporaryDirectory() as d:
        f,report=self.setup(d);report["primary_voice"]="Other"
        with self.assertRaises(ValueError):audit_nonbilled_kore_handoff(folder=f,report=report)
        report["primary_voice"]=VOICE;(f/"script.txt").write_text("changed")
        with self.assertRaises(ValueError):audit_nonbilled_kore_handoff(folder=f,report=report)
 def test_fabricated_accepted_job_text_fails(self):
    with tempfile.TemporaryDirectory() as d:
        f,report=self.setup(d);report["AI_source_agreed_segments"]=1
        report["unresolved_source_segments"]=0;report["unresolved_utterance_ids"]=[]
        report["actual_verbatim_jobs"]=[{"job_id":"u1","spoken_text":"Original",
            "spoken_text_sha256":"0"*64,"model":MODEL,"voice":VOICE,
            "target_pdf_page_bbox_pt":[0,0,100,100]}]
        with self.assertRaises(ValueError):audit_nonbilled_kore_handoff(folder=f,report=report)
