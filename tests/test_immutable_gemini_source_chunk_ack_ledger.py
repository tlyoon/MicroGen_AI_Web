import tempfile,unittest,pymupdf
from pathlib import Path
from selenium_pipeline.textbook_source_bounded_page_chunks import original_textbook_chunks
from selenium_pipeline.immutable_gemini_source_chunk_ack_ledger import record_chunk_ack
class AckJournal(unittest.TestCase):
 def setup(self,d):
  p=Path(d)/"source.pdf";doc=pymupdf.open();doc.new_page().insert_text((40,50),"First original page text");doc.new_page().insert_text((40,50),"Second original page text");doc.save(p);doc.close()
  m=original_textbook_chunks(p,limit=256);return m,Path(d)/"external_ack.jsonl"
 def ack(self,m,i):
  c=m["chunks"][i];return dict(chunk_sha256=c["fragment_sha256"],received=True,
                  physical_page=c["physical_page"],start_char=c["start_char"])
 def test_verified_same_session_ack_in_order(self):
  with tempfile.TemporaryDirectory() as d:
   m,p=self.setup(d)
   for i in range(len(m["chunks"])):
    x=record_chunk_ack(manifest=m,log=p,chunk_index=i,response=self.ack(m,i),
                       owned_session_id="owned-test-12345")
    self.assertFalse(x["mathematics_approved"])
 def test_no_missing_or_cross_session_ack(self):
  with tempfile.TemporaryDirectory() as d:
   m,p=self.setup(d)
   with self.assertRaises(ValueError):
    record_chunk_ack(manifest=m,log=p,chunk_index=1,response=self.ack(m,1),
                     owned_session_id="owned-test-12345")
   record_chunk_ack(manifest=m,log=p,chunk_index=0,response=self.ack(m,0),
                    owned_session_id="owned-test-12345")
   with self.assertRaises(ValueError):
    record_chunk_ack(manifest=m,log=p,chunk_index=1,response=self.ack(m,1),
                     owned_session_id="wrong-session")
 def test_wrong_sha_fails_without_progress(self):
  with tempfile.TemporaryDirectory() as d:
   m,p=self.setup(d);row=self.ack(m,0);row["chunk_sha256"]="0"*64
   with self.assertRaises(ValueError):
    record_chunk_ack(manifest=m,log=p,chunk_index=0,response=row,
                     owned_session_id="owned-test-12345")
   self.assertFalse(p.exists())
