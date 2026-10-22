import tempfile,unittest,json,hashlib
from pathlib import Path
from selenium_pipeline.review_quarantine_integrity import audit_quarantine_metadata

class QuarantineAudit(unittest.TestCase):
    def setup(self,root,text="",active=True):
        p=Path(root)/"model_abc.meta.json";raw=p.with_name("model_abc.raw.txt")
        data=text.encode();raw.write_bytes(data)
        p.write_text(json.dumps({"schema_version":1,"status":"incomplete_untrusted",
            "not_scientifically_reviewed":True,
            "raw_filename":raw.name,"model_response_chars":len(text),
            "generation_active_at_capture":active,
            "raw_sha256":hashlib.sha256(data).hexdigest()}))
        return p,raw
    def test_actual_empty_pending_not_approved(self):
        with tempfile.TemporaryDirectory() as d:
            p,_=self.setup(d)
            a=audit_quarantine_metadata(p)
            self.assertEqual(a["classification"],"PENDING_EMPTY")
            self.assertFalse(a["retry_or_approval_authorized"])
    def test_completed_untrusted_is_not_scientific_approval(self):
        with tempfile.TemporaryDirectory() as d:
            p,_=self.setup(d,'{"valid":false}',False)
            a=audit_quarantine_metadata(p)
            self.assertEqual(a["classification"],"COMPLETED_UNTRUSTED_TEXT")
    def test_modified_payload_and_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p,raw=self.setup(d,"abc")
            raw.write_text("tampered")
            with self.assertRaises(ValueError):audit_quarantine_metadata(p)
            m=json.loads(p.read_text());m["raw_filename"]="../other.raw.txt"
            p.write_text(json.dumps(m))
            with self.assertRaises(ValueError):audit_quarantine_metadata(p)
