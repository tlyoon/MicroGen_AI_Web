import unittest,tempfile,pathlib
from unittest.mock import patch
import pymupdf
from selenium_pipeline.strict_source_element_mapping import norm,classify
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
class StrictMappingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=pathlib.Path(self.tmp.name)
  self.source=self.root/"source.pdf";self.slides=self.root/"slides.pdf"
  self.script=self.root/"script.txt"
  with pymupdf.open() as p:
   q=p.new_page(width=300,height=200);q.insert_text((20,65),"Unique Equation A")
   p.save(self.source)
  with pymupdf.open() as p:
   q=p.new_page(width=300,height=200);q.insert_text((20,65),"Unique Equation A")
   p.save(self.slides)
  self.script.write_text("**Slide 1 [30s]:\n\nUnique Equation A\n",encoding="utf8")
 def test_norm_preserves_math_semantic_difference(self):
  self.assertNotEqual(norm("sin x"),norm("cos x"))
 def test_no_false_upgrade_when_semantic_or_source_ambiguous(self):
  with pymupdf.open(self.source) as p:
   q=p.new_page(width=300,height=200);q.insert_text((20,65),"Unique Equation A")
   p.saveIncr()
  report=classify(source=self.source,slides=self.slides,script=self.script)
  self.assertEqual(report["literal_source_text_evidence_count"],0)
  self.assertFalse(report["per_element_tts_authorized"])
 def test_missing_source_fails_closed(self):
  self.source.unlink()
  with self.assertRaises(FigureIdentityReviewRequired):
   classify(source=self.source,slides=self.slides,script=self.script)
