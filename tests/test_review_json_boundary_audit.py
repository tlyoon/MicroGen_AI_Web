import unittest,tempfile,json,hashlib
from pathlib import Path
from selenium_pipeline.review_json_boundary_audit import classify_raw_review_json
class OfflineJSON(unittest.TestCase):
 def make(self,root,text):
    raw=Path(root)/"gemini_model.raw.txt";payload=text.encode()
    raw.write_bytes(payload)
    raw.with_name("gemini_model.meta.json").write_text(json.dumps({
        "schema_version":1,"status":"incomplete_untrusted",
        "raw_filename":raw.name,"raw_sha256":hashlib.sha256(payload).hexdigest(),
        "model_response_chars":len(text)}))
    return raw
 def test_schema_shaped_reply_is_still_unapproved(self):
    with tempfile.TemporaryDirectory() as d:
        raw=self.make(d,json.dumps({"status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE",
            "rows":[{"utterance_id":"u1"}]}))
        out=classify_raw_review_json(raw_file=raw,expected_utterance_ids=["u1"])
        self.assertEqual(out["candidate_utterances"],1)
        self.assertFalse(out["mathematically_approved"])
 def test_duplicate_json_key_never_promoted(self):
    with tempfile.TemporaryDirectory() as d:
        raw=self.make(d,'{"status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE","status":"fake","rows":[]}')
        out=classify_raw_review_json(raw_file=raw,expected_utterance_ids=["u1"])
        self.assertNotIn("candidate_utterances",out)
 def test_source_unit_omission_rejected(self):
    with tempfile.TemporaryDirectory() as d:
        raw=self.make(d,'{"status":"ORIGINAL_TEXTBOOK_AI_REVIEW_CANDIDATE","rows":[]}')
        out=classify_raw_review_json(raw_file=raw,expected_utterance_ids=["u1"])
        self.assertEqual(out["status"],"UNTRUSTED_JSON_WRONG_ORIGINAL_SCOPE")
