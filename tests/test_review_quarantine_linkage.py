import tempfile,unittest,json,hashlib
from pathlib import Path
from selenium_pipeline.review_quarantine_linkage import verify_failed_attempt_link
class Linkage(unittest.TestCase):
 def setup(self,path):
    d=Path(path);q=d/"quarantine";q.mkdir()
    raw=q/"gemini_x.raw.txt";raw.write_bytes(b"")
    (q/"gemini_x.meta.json").write_text(json.dumps({
        "schema_version":1,"status":"incomplete_untrusted",
        "not_scientifically_reviewed":True,"raw_filename":raw.name,
        "model_response_chars":0,"generation_active_at_capture":True,
        "raw_sha256":hashlib.sha256(b"").hexdigest()}))
    receipt=d/"slide_001_independent_challenge_attempt_01.json"
    receipt.write_text(json.dumps({"status":"FAILED_GEMINI_REVIEW_ATTEMPT_QUARANTINED",
        "slide":1,"mode":"INDEPENDENT_CHALLENGE","attempt":1,
        "reason":"No stable complete JSON; untrusted response quarantined at "+str(raw)+".",
        "student_publication_authorized":False}))
    return receipt,q
 def test_links_actual_hash_verified_failed_attempt(self):
    with tempfile.TemporaryDirectory() as d:
        a,q=self.setup(d);r=verify_failed_attempt_link(attempt_file=a,quarantine_root=q)
        self.assertEqual(r["capture_classification"],"PENDING_EMPTY")
        self.assertFalse(r["retry_automatically_authorized"])
 def test_rejects_forged_attempt_identity(self):
    with tempfile.TemporaryDirectory() as d:
        a,q=self.setup(d);m=json.loads(a.read_text());m["attempt"]=2;a.write_text(json.dumps(m))
        with self.assertRaises(ValueError):verify_failed_attempt_link(attempt_file=a,quarantine_root=q)
 def test_rejects_moved_unowned_quarantine(self):
    with tempfile.TemporaryDirectory() as d:
        a,q=self.setup(d)
        with self.assertRaises(ValueError):verify_failed_attempt_link(attempt_file=a,quarantine_root=Path(d)/"wrong")
