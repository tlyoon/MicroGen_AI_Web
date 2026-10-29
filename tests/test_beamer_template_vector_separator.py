"""The Beamer header is decorative, never a mathematical figure certificate.

Exact source/body narration can advance through the text-only gate even with
recurring title/footer paths. Any NEW or body vector, mathematical equation
stroke, or real figure still blocks until separately mapped and verified.
"""
import tempfile,unittest
from pathlib import Path
import pymupdf
from selenium_pipeline.beamer_template_vector_separator import distinguish_template
from selenium_pipeline.automatic_element_narration import (
    inspect_text_only,AutomaticElementAudioError)

class BeamerTemplatePaths(unittest.TestCase):
 def data(self,root,extra=False,repeat_body=False):
  root=Path(root);source=root/"source.pdf";slides=root/"slides.pdf";script=root/"script.txt"
  a="Source formula paragraph for introduction."
  b="Another source formula paragraph for example."
  with pymupdf.open() as pdf:
   pdf.new_page().insert_text((80,120),a)
   pdf.new_page().insert_text((80,120),b)
   pdf.save(source)
  with pymupdf.open() as doc:
   for i,text in enumerate((a,b)):
    page=doc.new_page()
    page.draw_line((0,24),(300,24),color=(0,0,1))
    if extra and i==1:
     page.draw_rect(pymupdf.Rect(80,140,200,220))
    if repeat_body:
     page.draw_line((80,350),(200,350))
    page.insert_text((80,120),text)
   doc.save(slides)
  script.write_text(
      "**Slide 1 [4 sec]:\n"+a+"\n\n**Slide 2 [4 sec]:\n"+b,
      encoding="utf8")
  return source,slides,script
 def test_common_identical_header_only_is_not_a_semantic_figure(self):
  with tempfile.TemporaryDirectory() as t:
   source,slides,script=self.data(t)
   with pymupdf.open(slides) as d:
    rows=distinguish_template(list(d))
   self.assertEqual([x["non_template_vector_path_count"] for x in rows],[0,0])
   self.assertTrue(all(x["verified_repeated_margin_template_vector_count"]>0 for x in rows))
   z=inspect_text_only(source=source,slides=slides,script=script)
   self.assertEqual(len(z["elements"]),2)
 def test_unique_body_figure_never_waived(self):
  with tempfile.TemporaryDirectory() as t:
   source,slides,script=self.data(t,extra=True)
   with pymupdf.open(slides) as d:
    rows=distinguish_template(list(d))
   self.assertGreater(rows[1]["non_template_vector_path_count"],0)
   with self.assertRaisesRegex(AutomaticElementAudioError,"figure/vector"):
    inspect_text_only(source=source,slides=slides,script=script)
 def test_same_body_graphic_repeated_every_slide_is_still_not_decorative(self):
  with tempfile.TemporaryDirectory() as t:
   source,slides,script=self.data(t,repeat_body=True)
   with pymupdf.open(slides) as d:
    rows=distinguish_template(list(d))
   self.assertTrue(all(x["non_template_vector_path_count"]>0 for x in rows))
   with self.assertRaisesRegex(AutomaticElementAudioError,"figure/vector"):
    inspect_text_only(source=source,slides=slides,script=script)
if __name__=="__main__":unittest.main()
