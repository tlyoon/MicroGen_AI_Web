"""Native Windows genuine inline-PDF figure integration (not a science re-audit).

Beamer may encode figures using PDF BI/ID/EI inline images, absent from
get_images(full=True). Use a real binary image inserted into the PDF content
stream, then verify draft discovery, SHA-bound geometry and tiny-icon filters.
No TTS, academic approval or student release is granted by a visual candidate.
"""
from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.scene_candidate_authoring import draft
from selenium_pipeline.element_plan_autodraft import propose
from selenium_pipeline.element_narration_stage import rectangle, ElementStageError


def append_real_inline_pdf_image(pdf, page, *, width, height, origin_x,
                                 origin_y, rgb=b"\x40\x72\xaa"):
    """A true PDF inline BI image (not an XObject with an xref)."""
    raw=rgb*(width*height)
    script=(
        b"\nq\n" +
        f"{width} 0 0 {height} {origin_x} {origin_y} cm\n".encode("ascii") +
        f"BI /W {width} /H {height} /CS /RGB /BPC 8 ID\n".encode("ascii") +
        raw +
        b"\nEI\nQ\n"
    )
    content=page.get_contents()
    assert len(content)==1
    xref=content[0]
    pdf.update_stream(xref,pdf.xref_stream(xref)+script)


class RealInlineMathFigureMappingTests(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root=Path(td.name)
        self.source=self.root/"source.pdf"
        self.slides=self.root/"slides.pdf"
        self.script=self.root/"script.txt"
        with pymupdf.open() as d:
            p=d.new_page(width=420,height=300)
            p.insert_text((60,80),"FIGURE 8.3 original mathematical graph and panel.")
            d.save(self.source)
        with pymupdf.open() as d:
            p=d.new_page(width=420,height=300)
            p.insert_text((60,70),"Figure 8.3 shows the inverse function.")
            # Big content figure in slide body; small footer graphic is decorative.
            append_real_inline_pdf_image(
                d,p,width=120,height=75,origin_x=80,origin_y=70)
            append_real_inline_pdf_image(
                d,p,width=8,height=8,origin_x=10,origin_y=10,
                rgb=b"\x25\x45\x80")
            d.save(self.slides)
        self.script.write_text(
            "**Slide 1 [14 sec]:\nWe inspect Figure 8.3 to explain "
            "the original inverse functions in this graph.",
            encoding="utf8")

    def test_true_pdf_inline_figure_appears_as_selectable_review_target(self):
        with pymupdf.open(self.slides) as doc:
            page=doc[0]
            self.assertEqual(page.get_images(full=True),[])
            actual=[b for b in page.get_text("dict")["blocks"]
                    if b.get("type")==1]
            self.assertEqual(len(actual),2)
        result=draft(self.source,self.slides)
        figures=[x for x in result["slides"][0]["targets"]
                 if x["type"]=="inline_image_whole"]
        self.assertEqual(len(figures),1)
        self.assertEqual(result["figure_target_count"],1)
        self.assertFalse(result["automatic_approval"])
        self.assertFalse(result["all_narration_authored"])
        with pymupdf.open(self.slides) as d:
            rect,category=rectangle(d[0],figures[0]["anchor"])
        self.assertGreater(rect.width,110)
        self.assertEqual(category,"figure")

    def test_tiny_decorative_inline_image_excluded_from_element_mapping(self):
        a=draft(self.source,self.slides)
        marks=a["slides"][0]["omitted_fragment_indices_needing_review"]
        self.assertTrue(any("decorative_or_tiny_inline_image" in str(x)
                            for x in marks))
        self.assertEqual(sum(x["type"]=="inline_image_whole"
                             for x in a["slides"][0]["targets"]),1)

    def test_changing_source_image_digest_blocks_stale_anchor(self):
        a=draft(self.source,self.slides)
        found=next(x for x in a["slides"][0]["targets"]
                   if x["type"]=="inline_image_whole")
        wrong=dict(found["anchor"],digest_sha256="f"*64)
        with pymupdf.open(self.slides) as d:
            with self.assertRaisesRegex(ElementStageError,
                                        "pixels changed"):
                rectangle(d[0],wrong)

    def test_structured_narration_draft_includes_real_inline_source_target(self):
        p=propose(source_pdf=self.source,slides_pdf=self.slides,
                  script_txt=self.script)
        inline=[x for x in p["slides"][0]["auto_candidate_targets"]
                if x["kind"]=="inline_image_whole"]
        self.assertEqual(len(inline),1)
        self.assertFalse(inline[0]["source_evidence_verified"])
        self.assertFalse(p["can_stage_or_synthesize_audio"])
        self.assertTrue(p["slides"][0]["review_required"])

    def test_registered_pdf_xref_image_not_double_counted_as_inline(self):
        from PIL import Image
        with pymupdf.open() as d:
            p=d.new_page(width=420,height=300)
            p.insert_text((60,70),"An original diagram with an embedded figure.")
            buffer=io.BytesIO()
            Image.new("RGB",(100,80),(60,120,180)).save(buffer,format="PNG")
            p.insert_image(pymupdf.Rect(70,120,220,230),
                           stream=buffer.getvalue())
            d.save(self.root/"registered.pdf")
        content=draft(self.source,self.root/"registered.pdf")
        figure=[x for x in content["slides"][0]["targets"]
                if x["type"] in {"image_whole","inline_image_whole"}]
        self.assertEqual(len(figure),1)
        self.assertEqual(figure[0]["type"],"image_whole")

    def test_inline_multipanel_selection_requires_same_image_hash(self):
        with pymupdf.open(self.slides) as doc:
            page=doc[0]
            found=next(b for b in page.get_text("dict")["blocks"]
                       if b.get("type")==1
                       and pymupdf.Rect(b["bbox"]).width>50)
        # The original figure is not wide enough for panel assumptions.
        import hashlib
        digest=hashlib.sha256(found["image"]).hexdigest()
        with pymupdf.open(self.slides) as doc:
            page=doc[0]
            block_index=next(i for i,b in enumerate(
                page.get_text("dict")["blocks"])
                if b.get("type")==1 and
                pymupdf.Rect(b["bbox"]).width>50)
            with self.assertRaisesRegex(ElementStageError,
                                        "not supported"):
                rectangle(page,{"type":"inline_image_panel",
                  "index":block_index,"digest_sha256":digest,
                  "panels":3,"panel":1})


if __name__=="__main__":
    unittest.main()
