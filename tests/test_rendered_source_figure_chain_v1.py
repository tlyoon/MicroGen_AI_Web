"""Compiled-PDF visibility & exact pixels for every source-caption PNG."""
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

import fitz
from PIL import Image

from selenium_pipeline.source_caption_figure_chain_v1 import (
    FigureChainError,generate_candidates,promote_candidates,
    verify_rendered_pdf_source_figures,
)


class SourcePixelRenderingTests(TestCase):
    def setUp(self):
        t=TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.job=self.root/"job";self.job.mkdir()
        self.source=self.job/"source.pdf"
        doc=fitz.open()
        page=doc.new_page(width=612,height=792)
        page.draw_rect(fitz.Rect(80,65,155,225),color=(0,0,1),fill=(.2,.3,.8))
        page.insert_text((75,270),"Figure 8.2 A visual source graphic",fontname="hebo")
        page=doc.new_page(width=612,height=792)
        page.draw_circle(fitz.Point(500,170),30,color=(1,0,0),fill=(1,.2,.2))
        page.insert_text((448,290),"Figure 8.3 Another source graphic",fontname="hebo")
        doc.save(self.source)
        doc.close()
        stage=self.root/"stage";stage.mkdir()
        shutil.copy2(self.source,stage/"source.pdf")
        generate_candidates(self.source,stage)
        promote_candidates(stage,self.job)
        self.images=["Figure 8.2.png","Figure 8.3.png"]
        self.job.joinpath("slides.tex").write_text(
            "\n".join(r"\includegraphics{"+filename+"}"
                      for filename in self.images),encoding="utf8")

    def _make_pdf(self,present,wrong=False):
        doc=fitz.open()
        for filename in present:
            page=doc.new_page(width=612,height=792)
            image=self.job/filename
            if wrong:
                from io import BytesIO
                im=Image.open(image).convert("RGB")
                im.putpixel((20,20),(255,0,0))
                out=BytesIO();im.save(out,format="PNG")
                blob=out.getvalue()
            else:
                blob=image.read_bytes()
            page.insert_image(fitz.Rect(65,75,450,620),stream=blob)
        doc.save(self.job/"slides.pdf")
        doc.close()

    def test_two_source_images_visibly_render_with_exact_pixels(self):
        self._make_pdf(self.images)
        result=verify_rendered_pdf_source_figures(self.job)
        self.assertEqual(result["status"],
            "SOURCE_CAPTION_PNG_LATEX_RENDERED_PDF_CHAIN_VERIFIED")
        self.assertEqual(result["figures_verified"],2)
        self.assertEqual(result["source_figure_visible_pages"],
                         {self.images[0]:[1],self.images[1]:[2]})
        self.assertTrue(result["source_pixels_unchanged"])
        self.assertFalse(result["scientific_approval"])
        self.assertFalse(result["student_publication_authorized"])

    def test_latex_names_both_but_pdf_omits_one(self):
        self._make_pdf([self.images[0]])
        with self.assertRaisesRegex(FigureChainError,"lacks visible exact"):
            verify_rendered_pdf_source_figures(self.job)

    def test_latex_names_both_but_pdf_has_wrong_pixels(self):
        self._make_pdf([self.images[0],self.images[1]],wrong=True)
        with self.assertRaisesRegex(FigureChainError,"lacks visible exact"):
            verify_rendered_pdf_source_figures(self.job)

    def test_latex_contains_image_but_missing_slide_pdf(self):
        with self.assertRaisesRegex(FigureChainError,"Missing compiled"):
            verify_rendered_pdf_source_figures(self.job)

    def _cover_page_image(self, portion):
        self._make_pdf(self.images)
        pdf=self.job/"slides.pdf"
        doc=fitz.open(pdf)
        page=doc[0]
        image_box=fitz.Rect(65,75,450,620)
        if portion=="all":
            region=image_box
        elif portion=="half":
            region=fitz.Rect(65,75,265,620)
        else:
            raise AssertionError(portion)
        page.draw_rect(region,color=(1,1,1),fill=(1,1,1),overlay=True)
        replacement=self.job/"overlay_candidate.pdf"
        doc.save(replacement)
        doc.close()
        replacement.replace(pdf)

    def test_image_xobject_fully_covered_by_later_white_rectangle(self):
        self._cover_page_image("all")
        with self.assertRaisesRegex(FigureChainError,"lacks visible exact"):
            verify_rendered_pdf_source_figures(self.job)

    def test_image_xobject_half_covered_by_later_white_rectangle(self):
        self._cover_page_image("half")
        with self.assertRaisesRegex(FigureChainError,"lacks visible exact"):
            verify_rendered_pdf_source_figures(self.job)
