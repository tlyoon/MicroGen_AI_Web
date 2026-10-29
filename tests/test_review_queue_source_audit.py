import unittest,tempfile,hashlib,json
from pathlib import Path
from selenium_pipeline.review_queue_source_audit import inspect_source_bound_queue
class QueueAudit(unittest.TestCase):
 def make(self,root):
    p=Path(root);src=p/"original";src.mkdir();q=p/"queue";q.mkdir()
    refs={}
    for name in ("source.pdf","slides.pdf","script.txt"):
        (src/name).write_bytes(name.encode());refs[name]=hashlib.sha256(name.encode()).hexdigest()
    a={"slide":1,"utterance_count":3,
       "original_source_sha256":refs["source.pdf"],
       "original_slides_sha256":refs["slides.pdf"],
       "original_script_sha256":refs["script.txt"]}
    data={"status":"IMMUTABLE_ORIGINAL_GEMINI_AI_REVIEW_QUEUE",
       "student_publication_authorized":False,"original_source_folder":str(src),
       "slide_jobs":[a],"expected_utterances":3}
    (q/"queue.json").write_text(json.dumps(data))
    return src,q,data
 def test_intact_queue_counts_real_original_bytes(self):
    with tempfile.TemporaryDirectory() as d:
        src,q,_=self.make(d);a=inspect_source_bound_queue(q)
        self.assertEqual((a["slides"],a["original_utterances"]),(1,3))
 def test_rejects_hash_drift(self):
    with tempfile.TemporaryDirectory() as d:
        src,q,_=self.make(d);(src/"source.pdf").write_bytes(b"changed")
        with self.assertRaises(ValueError):inspect_source_bound_queue(q)
 def test_missing_or_duplicate_slide_rejected(self):
    with tempfile.TemporaryDirectory() as d:
        _,q,a=self.make(d);a["slide_jobs"].append(dict(a["slide_jobs"][0]))
        a["expected_utterances"]=6;(q/"queue.json").write_text(json.dumps(a))
        with self.assertRaises(ValueError):inspect_source_bound_queue(q)
