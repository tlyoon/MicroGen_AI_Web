import tempfile,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
import pymupdf
from PIL import Image
from selenium_pipeline.figure_resize_review import make,sha

class FigureResizeReviewTests(unittest.TestCase):
 def setUp(self):
    self.tmp=tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)
    self.root=Path(self.tmp.name)
    self.src=self.root/'source'
    self.src.mkdir()
    self.dst=self.root/'candidate'
    Image.new('RGB',(200,100),'blue').save(self.src/'triangle.png')
    (self.src/'slides.tex').write_text(r'\includegraphics[height=0.22\textheight,keepaspectratio]{triangle.png}',encoding='utf8')
    self.source_pdf=self.src/'slides.pdf'
    self.build(self.source_pdf,60)
    self.old_hash=sha(self.source_pdf)
 def build(self,path,width):
    doc=pymupdf.open()
    for i in range(2):
        page=doc.new_page(width=400,height=300)
        page.insert_text((30,20),f'Test slide {i+1}')
        if i==1:
            page.insert_image(pymupdf.Rect(180-width/2,90,180+width/2,150),filename=str(self.src/'triangle.png'))
    doc.save(path)
    doc.close()
 def simulate(self,width):
    def fake_run(args,*,cwd,**kwargs):
        self.build(Path(cwd)/'slides.pdf',width)
        return subprocess.CompletedProcess(args,0,'','')
    return fake_run
 def run_resize(self):
    return make(source=self.src,dest=self.dst,image_name='triangle.png',old_height=.22,new_height=.30,slide_number=2)
 def test_pass_single_changed_slide_and_no_source_mutation(self):
    with patch('selenium_pipeline.figure_resize_review.subprocess.run',side_effect=self.simulate(110)):
        result=self.run_resize()
    self.assertEqual(result['changed_rendered_slide_numbers'],[2])
    self.assertGreater(result['after_width_fraction'],.18)
    self.assertFalse(result['production_approved'])
    self.assertEqual(self.old_hash,sha(self.source_pdf))
 def test_fail_when_image_still_too_small(self):
    with patch('selenium_pipeline.figure_resize_review.subprocess.run',side_effect=self.simulate(50)):
        with self.assertRaisesRegex(ValueError,'too narrow'):
            self.run_resize()
    self.assertFalse((self.dst/'figure_resize_receipt.json').exists())
 def test_existing_destination_preserved(self):
    self.dst.mkdir()
    keep=self.dst/'keep.txt';keep.write_text('preserve')
    with self.assertRaisesRegex(ValueError,'Destination'):
        self.run_resize()
    self.assertEqual(keep.read_text(),'preserve')
 def test_unsafe_image_and_reverse_height_rejected(self):
    with self.assertRaisesRegex(ValueError,'Unsafe image'):
        make(source=self.src,dest=self.dst,image_name='../triangle.png',old_height=.22,new_height=.30,slide_number=2)
    with self.assertRaisesRegex(ValueError,'sizing parameters'):
        make(source=self.src,dest=self.dst,image_name='triangle.png',old_height=.22,new_height=.20,slide_number=2)
    self.assertFalse(self.dst.exists())
 def test_canonical_vertical_spacing_changes_only_selected_figure_frame(self):
    tex=(r"\begin{frame}{Test}"+"\n"+
         r"\IfFileExists{triangle.png}{%"+"\n"+
         r"\begin{figure}"+"\n"+
         r"\includegraphics[height=0.22\textheight,keepaspectratio]{triangle.png}"+"\n"+
         r"\end{figure}"+"\n"+
         r"}{}"+"\n"+
         r"\begin{itemize}"+"\n"+
         r"\item Step two"+"\n"+
         r"\end{itemize}"+"\n"+
         r"\end{frame}"+"\n")
    (self.src/"slides.tex").write_text(tex,encoding="utf8")
    with patch("selenium_pipeline.figure_resize_review.subprocess.run",
               side_effect=self.simulate(110)):
        receipt=make(source=self.src,dest=self.dst,image_name="triangle.png",
                     old_height=.22,new_height=.30,slide_number=2,
                     compact_before_image_pt=8,compact_after_image_pt=-1.5)
    derived=(self.dst/"slides.tex").read_text(encoding="utf8")
    self.assertIn(r"\vspace{-8pt}",derived)
    self.assertIn(r"\vspace{1.5pt}",derived)
    self.assertNotIn(r"\vspace{--1.5pt}",derived)
    self.assertEqual(derived.count(r"\vspace"),2)
    self.assertEqual(receipt["changed_rendered_slide_numbers"],[2])
    self.assertFalse(receipt["production_approved"])

 def test_compaction_rejects_missing_procedural_followup(self):
    with self.assertRaisesRegex(ValueError,"conditional"):
        make(source=self.src,dest=self.dst,image_name="triangle.png",
             old_height=.22,new_height=.30,slide_number=2,
             compact_before_image_pt=8)
    self.assertFalse((self.dst/"figure_resize_receipt.json").exists())
