import unittest,tempfile
from pathlib import Path
import pymupdf
from selenium_pipeline.figure_source_identity import _sha
from selenium_pipeline.complete_original_source_excerpt_audit import verify_complete_original_excerpt
class ExcerptAudit(unittest.TestCase):
 def make(self,root):
    p=Path(root);f=p/"book";f.mkdir()
    book=pymupdf.open()
    for i in (1,2):book.new_page().insert_text((25,30),"Original textbook page "+str(i))
    book.save(f/"source.pdf");book.close()
    slides=pymupdf.open();slides.new_page().insert_text((25,30),"Original slide equation")
    slides.save(f/"slides.pdf");slides.close()
    (f/"script.txt").write_text("Spoken original equation")
    lines=["ORIGINAL SOURCE SHA256 "+_sha(f/"source.pdf"),
      "ORIGINAL SLIDE SHA256 "+_sha(f/"slides.pdf"),
      "ORIGINAL SCRIPT SHA256 "+_sha(f/"script.txt")]
    with pymupdf.open(f/"source.pdf") as b:
        for i in (1,2):lines.append("ORIGINAL TEXTBOOK PDF PHYSICAL PAGE "+str(i)+"\n"+b[i-1].get_text(sort=True))
    with pymupdf.open(f/"slides.pdf") as b:
        lines.append("ORIGINAL SLIDE PDF PHYSICAL PAGE 1\n"+b[0].get_text(sort=True))
    out=p/"excerpt.txt";out.write_text("\n".join(lines))
    return f,out
 def test_two_real_original_pages_independently_verified(self):
    with tempfile.TemporaryDirectory() as d:
        f,p=self.make(d);a=verify_complete_original_excerpt(folder=f,slide=1,excerpt=p)
        self.assertEqual(a["physical_textbook_pages"],2)
        self.assertFalse(a["visual_figure_math_semantics_verified"])
 def test_missing_alternative_page_fails_closed(self):
    with tempfile.TemporaryDirectory() as d:
        f,p=self.make(d);s=p.read_text();s=s.replace("Original textbook page 2","text silently removed");p.write_text(s)
        with self.assertRaises(ValueError):verify_complete_original_excerpt(folder=f,slide=1,excerpt=p)
 def test_mismatched_book_hash_rejected(self):
    with tempfile.TemporaryDirectory() as d:
        f,p=self.make(d);s=p.read_text();s=s.replace("ORIGINAL SOURCE SHA256 ","ORIGINAL SOURCE SHA256 altered")
        p.write_text(s)
        with self.assertRaises(ValueError):verify_complete_original_excerpt(folder=f,slide=1,excerpt=p)
