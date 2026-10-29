"""Adversarial rendered figure visibility proof on actual generated PDFs.

No external Gemini/TTS, student publication, or original-asset changes.
"""
from __future__ import annotations

import unittest
from pathlib import Path
import pymupdf
import tempfile
from PIL import Image
from selenium_pipeline.figure_source_identity import (
    FigureIdentityReviewRequired, inspect_whole_raster_candidate,
)
from selenium_pipeline.figure_render_equivalence import (
    inspect_rendered_whole_raster_candidate,
)


class FigureVisibleRenderingTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.source=self.root/"source.pdf"
        self.slides=self.root/"slides.pdf"
        self.caption="Figure 2.3 The magnetic field around a solenoid."
        self.png=self.root/"original.png"
        img=Image.new("RGB",(200,150))
        for y in range(150):
            for x in range(200):
                img.putpixel((x,y),((x*3)%256,(y*5)%256,(x+y)%256))
        img.save(self.png)
        self._pdf(self.source,is_slide=False)
        self._pdf(self.slides,is_slide=True)

    def _pdf(self,path,*,is_slide,caption=None,image=None,vector=False):
        caption=self.caption if caption is None else caption
        image=self.png if image is None else image
        with pymupdf.open() as doc:
            page=doc.new_page(width=620,height=780)
            rect=(pymupdf.Rect(80,90,360,300) if is_slide
                  else pymupdf.Rect(80,80,280,230))
            page.insert_image(rect,filename=str(image))
            if vector:
                shape=page.new_shape()
                shape.draw_rect(pymupdf.Rect(390,350,540,450))
                shape.finish(color=(0,0,0))
                shape.commit()
            page.insert_text((80,rect.y1+28),caption,fontsize=11)
            doc.save(path)

    def candidate(self, **kw):
        args=dict(source=self.source,slides=self.slides,
                  source_page=1,slide_page=1,caption=self.caption)
        args.update(kw)
        return inspect_rendered_whole_raster_candidate(**args)

    def save_slide_edit(self, edit):
        with pymupdf.open(self.slides) as document:
            edit(document)
            path=self.root/"edited_slide.pdf"
            document.save(path)
        path.replace(self.slides)

    def test_exact_same_image_rendered_full_candidate_no_synthesis_authorization(self):
        result=self.candidate()
        self.assertTrue(result["rendered_raster_equivalence_verified"])
        self.assertEqual(result["source_render"]["render_scale"],2)
        self.assertEqual(result["slide_render"]["render_scale"],2)
        for key in ("image_visible_completeness_certified",
                    "figure_panel_completeness_certified",
                    "figure_semantics_certified","tts_or_video_authorized",
                    "human_review_claimed"):
            self.assertFalse(result[key])
        self.assertEqual(result["source_sha256"],
                         inspect_whole_raster_candidate(
                             source=self.source,slides=self.slides,
                             source_page=1,slide_page=1,
                             caption=self.caption)["source_sha256"])

    def test_overlay_text_same_pdf_image_digest_rejected(self):
        def edit(doc):
            doc[0].insert_text((105,170),"WRONG",fontsize=23,color=(1,0,0))
        self.save_slide_edit(edit)
        # Original PR140 cannot detect text written over the same image xref.
        inspect_whole_raster_candidate(
            source=self.source,slides=self.slides,source_page=1,
            slide_page=1,caption=self.caption)
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "visible pixels differ"):
            self.candidate()

    def test_overlay_annotation_rejected(self):
        def edit(doc):
            annot=doc[0].add_rect_annot(pymupdf.Rect(100,120,210,180))
            annot.set_colors(stroke=(1,0,0))
            annot.set_border(width=3)
            annot.update()
        self.save_slide_edit(edit)
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "vector|visible pixels differ"):
            self.candidate()

    def test_pdf_clipping_path_rejected_even_if_original_image_digest_matches(self):
        def edit(doc):
            page=doc[0]
            streams=page.get_contents()
            # PyMuPDF insert_image writes its own isolated content stream.
            self.assertGreaterEqual(len(streams),1)
            stream=doc.xref_stream(streams[0])
            # Tight PDF-space clip; original raster placement covers
            # x=80..360, y=480..690 on a 780pt page.
            doc.update_stream(streams[0],
                b"q 80 510 85 85 re W n\n"+stream+b"\nQ\n")
        self.save_slide_edit(edit)
        inspect_whole_raster_candidate(
            source=self.source,slides=self.slides,source_page=1,
            slide_page=1,caption=self.caption)
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "visible pixels differ"):
            self.candidate()

    def test_pdf_source_clipping_also_rejected(self):
        with pymupdf.open(self.source) as doc:
            streams=doc[0].get_contents()
            image=doc.xref_stream(streams[0])
            doc.update_stream(streams[0],
                b"q 80 565 60 60 re W n\n"+image+b"\nQ\n")
            tmp=self.root/"sourceclip.pdf"
            doc.save(tmp)
        tmp.replace(self.source)
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "source: PDF image visible pixels differ"):
            self.candidate()

    def test_modified_raster_blocks_as_earlier_identity_failure(self):
        from PIL import Image
        changed=self.root/"edited.png"
        with Image.open(self.png) as bitmap:
            bitmap.putpixel((52,35),(0,0,0))
            bitmap.save(changed)
        self._pdf(self.slides,is_slide=True,image=changed)
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "identity differs"):
            self.candidate()

    def test_mutating_caption_does_not_fake_image_proof(self):
        self._pdf(self.slides,is_slide=True,
                          caption="Figure 2.3 Another diagram.")
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "caption absent"):
            self.candidate()

    def test_unsupported_scale_rejected(self):
        with self.assertRaisesRegex(FigureIdentityReviewRequired,"resolution"):
            self.candidate(scale=1)

    def test_svg_vector_overlay_fails_original_guard(self):
        self._pdf(self.slides,is_slide=True,vector=True)
        with self.assertRaisesRegex(FigureIdentityReviewRequired,"vector"):
            self.candidate()

    def test_panel_caption_has_no_implicit_panel_certification(self):
        self._pdf(self.source,is_slide=False,
                          caption="Figure 2.3 (a) First panel.")
        self._pdf(self.slides,is_slide=True,
                          caption="Figure 2.3 (a) First panel.")
        with self.assertRaisesRegex(FigureIdentityReviewRequired,"Panel-labelled"):
            self.candidate(caption="Figure 2.3 (a) First panel.")
