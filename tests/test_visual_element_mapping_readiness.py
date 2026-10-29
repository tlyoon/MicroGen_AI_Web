"""All visual focus gaps must be identified, none silently approved."""
from __future__ import annotations
import tempfile,unittest
from pathlib import Path
import pymupdf
from selenium_pipeline.visual_element_mapping_readiness import inspect_all

class FullDeckFocusDiagnostic(unittest.TestCase):
 def test_real_two_page_pdf_readonly_graphics_and_verbatim(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/"source.pdf";slides=root/"slides.pdf";script=root/"script.txt"
   with pymupdf.open() as pdf:
    pdf.new_page().insert_text((72,72),"Visible original source introduction.")
    pdf.new_page().insert_text((72,72),"Textbook line two contains the original example.")
    pdf.save(source)
   with pymupdf.open() as doc:
    pg=doc.new_page()
    pg.insert_text((72,72),"Visible original source introduction.")
    pg.draw_line((20,22),(98,22))
    pg=doc.new_page()
    pg.insert_text((72,72),"Textbook line two contains the original example.")
    doc.save(slides)
   script.write_text("**Slide 1 [3 sec]:\nVisible original source introduction.\n\n"
                     "**Slide 2 [3 sec]:\nTextbook line two contains the original example.",
                     encoding="utf8")
   originals=[p.read_bytes() for p in (source,slides,script)]
   a=inspect_all(source=source,slides=slides,script=script)
   self.assertEqual(a["slide_count"],2)
   self.assertGreater(a["slides_with_graphics"],0)
   self.assertEqual(a["rows"][0]["verbatim_source_page_candidates"],[1])
   self.assertIn("VISUAL_GRAPHICS_SEMANTIC_PROVENANCE_REQUIRED",a["rows"][0]["reasons"])
   self.assertEqual(a["rows"][1]["verbatim_source_page_candidates"],[2])
   self.assertFalse(a["automatic_video_approved"])
   self.assertFalse(a["student_publication_authorized"])
   self.assertEqual([p.read_bytes() for p in (source,slides,script)],originals)
 def test_mismatch_fails_before_trusting_slide(self):
  with tempfile.TemporaryDirectory() as tmp:
   b=Path(tmp);src=b/"source.pdf";sl=b/"slides.pdf";t=b/"script.txt"
   for path in (src,sl):
    with pymupdf.open() as doc:
     doc.new_page().insert_text((70,70),"Only one genuine page")
     doc.save(path)
   t.write_text("**Slide 1 [10 sec]:\nFirst narration.\n"
                "**Slide 2 [10 sec]:\nSecond narration.",encoding="utf8")
   with self.assertRaisesRegex(ValueError,"counts inconsistent"):
    inspect_all(source=src,slides=sl,script=t)
if __name__=="__main__":unittest.main()
