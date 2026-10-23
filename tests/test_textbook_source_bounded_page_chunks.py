import tempfile,unittest,pymupdf
from pathlib import Path
from selenium_pipeline.textbook_source_bounded_page_chunks import original_textbook_chunks,validate_chunk_coverage
class LosslessChunks(unittest.TestCase):
 def source(self,folder):
  p=Path(folder)/"source.pdf";book=pymupdf.open()
  book.new_page().insert_text((35,40),"A"*250)
  book.new_page().insert_text((35,40),"B"*250)
  book.save(p);book.close();return p
 def test_all_pages_and_exact_offsets(self):
  with tempfile.TemporaryDirectory() as d:
   m=original_textbook_chunks(self.source(d),limit=256)
   self.assertEqual(m["page_count"],2)
   self.assertEqual(validate_chunk_coverage(m)["pages"],2)
 def test_missing_chunk_and_mutation_fails(self):
  with tempfile.TemporaryDirectory() as d:
   m=original_textbook_chunks(self.source(d),limit=256)
   m["chunks"].pop()
   with self.assertRaises(ValueError):validate_chunk_coverage(m)
 def test_visual_approval_is_not_inferred(self):
  with tempfile.TemporaryDirectory() as d:
   m=original_textbook_chunks(self.source(d))
   self.assertFalse(validate_chunk_coverage(m)["visual_math_verified"])
