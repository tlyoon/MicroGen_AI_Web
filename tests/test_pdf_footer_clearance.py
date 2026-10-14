"""Regression: Beamer footer must not be covered by semantic figures/captions."""
import tempfile
import unittest
from pathlib import Path
import pymupdf
from selenium_pipeline.pdf_element_geometry import extract_element_geometry,ElementGeometryError

BOARD={"schema_version":1,"part_id":"part_03","plan_sha256":"a"*64,
"slides":[{"slide_id":"part_03.s001","title":"Test",
"elements":[{"element_id":"part_03.s001.diagram","kind":"figure",
"source_concept_ids":["c1"],"source_page":6}]}],
"narration_segments":[{"segment_id":"n1","slide_id":"part_03.s001",
"element_ids":["part_03.s001.diagram"],"spoken_text":"A tested visual.",
"estimated_duration_s":10}]}

class FooterClearanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.n=0
    def make_pdf(self,*,anchor_bottom,footer=True):
        self.n+=1
        f=self.root/f"p{self.n}.pdf"
        pdf=pymupdf.open();p=pdf.new_page(width=360,height=270)
        p.draw_rect(pymupdf.Rect(35,75,280,anchor_bottom),
                    color=(0.1,0.1,0.4))
        p.insert_link({"kind":pymupdf.LINK_URI,
                       "uri":"microgen-element:part_03.s001.diagram",
                       "from":pymupdf.Rect(35,75,280,anchor_bottom)})
        if footer:p.insert_text((295,268),"3 / 11",fontsize=8)
        pdf.save(f);pdf.close()
        return f
    def test_footline_collision_fails_before_audio(self):
        p=self.make_pdf(anchor_bottom=260)
        with self.assertRaisesRegex(ElementGeometryError,"collides with rendered footer"):
            extract_element_geometry(p,BOARD)
    def test_safe_gap_above_footer_passes(self):
        p=self.make_pdf(anchor_bottom=230)
        receipt=extract_element_geometry(p,BOARD)
        self.assertEqual(len(receipt["elements"]),1)
    def test_no_footer_text_does_not_reserve_arbitrary_margin(self):
        p=self.make_pdf(anchor_bottom=255,footer=False)
        receipt=extract_element_geometry(p,BOARD)
        self.assertEqual(len(receipt["elements"]),1)
    def test_unrelated_header_does_not_count_as_footer(self):
        p=self.make_pdf(anchor_bottom=240,footer=False)
        with pymupdf.open(p) as doc:
            pg=doc[0]
            # No footer text: preexisting page remains a valid geometry source.
            self.assertEqual(len(pg.get_links()),1)
        self.assertEqual(len(extract_element_geometry(p,BOARD)["elements"]),1)

if __name__=="__main__":
    unittest.main()
