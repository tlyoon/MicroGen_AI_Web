"""Adversarial real-generated PDF tests for source vector panel reflow."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import pymupdf

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired
from selenium_pipeline.figure_panel_reflow import inspect_reflowed_vector_panels


class PanelReflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.source=self.root/"source.pdf"
        self.slides=self.root/"slides.pdf"
        self.caption="FIGURE 8.3 Original multi-panel field diagram."
        self.srcboxes=[[50,50+i*100,150,150+i*100] for i in range(3)]
        self.dstboxes=[[40+110*i,40,140+110*i,140] for i in range(3)]
        self.figure=[50,50,150,350]
        self.make_pdf_pair()

    def make_pdf_pair(self, *, source_labels=("a","b","c"),
                      alter_slide=None, add_crossing=False,
                      source_extra=False, omit_image=None):
        source_bits=[]
        with pymupdf.open() as pdf:
            pg=pdf.new_page(width=480,height=600)
            for i,r in enumerate(self.srcboxes):
                if i<len(source_labels):
                    pg.insert_text((r[0]+10,r[1]+20),
                                   f"({source_labels[i]})",fontsize=11)
                shape=pg.new_shape()
                shape.draw_rect(pymupdf.Rect(r[0]+20,r[1]+37,
                                            r[0]+50,r[1]+64))
                shape.finish(color=(0,0,0), fill=None)
                shape.commit()
                pg.draw_line((r[0]+20,r[1]+75),
                             (r[0]+70,r[1]+75),color=(0,0,0))
                source_bits.append(pg.get_pixmap(
                    matrix=pymupdf.Matrix(2,2),clip=pymupdf.Rect(r),
                    colorspace=pymupdf.csRGB,alpha=False).tobytes("png"))
            if add_crossing:
                pg.draw_line((80,147),(80,153),color=(1,0,0))
            if source_extra:
                pg.insert_text((55,350),"UNASSIGNED",fontsize=10)
            pg.insert_text((50,370),self.caption,fontsize=10)
            pdf.save(self.source)
        if add_crossing:
            with pymupdf.open(self.source) as pdf:
                pg=pdf[0]
                source_bits=[]
                for r in self.srcboxes:
                    source_bits.append(pg.get_pixmap(
                        matrix=pymupdf.Matrix(2,2),
                        clip=pymupdf.Rect(r),colorspace=pymupdf.csRGB,
                        alpha=False).tobytes("png"))
        with pymupdf.open() as pdf:
            pg=pdf.new_page(width=480,height=260)
            for i,r in enumerate(self.dstboxes):
                if i==omit_image:continue
                use_idx=((i+1)%3 if alter_slide==i else i)
                pg.insert_image(pymupdf.Rect(r),
                                stream=source_bits[use_idx],
                                keep_proportion=False)
            pg.insert_text((40,170),"Source Figure 8.3 panel comparison",
                           fontsize=11)
            pdf.save(self.slides)
        self.digests=[hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (self.source,self.slides)]

    def inspect(self,**overrides):
        args=dict(source=self.source,slides=self.slides,source_page=1,
                  slide_page=1,figure_id="8.3",
                  source_figure_bbox=self.figure,
                  panels=[{"id":chr(97+i),"source_bbox":self.srcboxes[i],
                           "slide_bbox":self.dstboxes[i]}
                          for i in range(3)],render_scale=2)
        args.update(overrides)
        return inspect_reflowed_vector_panels(**args)

    def test_independent_vertically_source_horizontal_slide_reflow(self):
        result=self.inspect()
        self.assertEqual(result["declared_panel_count"],3)
        self.assertTrue(result["panel_reflow_render_identity_verified"])
        self.assertEqual([e["id"] for e in result["panels"]],
                         ["a","b","c"])
        for receipt in result["panels"]:
            self.assertEqual(receipt["render_size"],[200,200])
            self.assertTrue(receipt["source_slide_pixel_identity_verified"])
        for key in ("author_intended_complete_panel_boundaries_certified",
                    "figure_semantics_certified","tts_or_video_authorized",
                    "human_review_claimed"):
            self.assertFalse(result[key])
        self.assertEqual(self.digests,[hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in (self.source,self.slides)])

    def test_swapped_raster_panels_refused(self):
        self.make_pdf_pair(alter_slide=1)
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "pixels differ"):
            self.inspect()

    def test_missing_slide_panel_refused(self):
        self.make_pdf_pair(omit_image=0)
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "covered by a real raster"):
            self.inspect()

    def test_duplicate_source_a_label_refused(self):
        self.make_pdf_pair(source_labels=("a","a","c"))
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "unique extractable"):
            self.inspect()

    def test_missing_source_c_label_refused(self):
        self.make_pdf_pair(source_labels=("a","b"))
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "unique extractable"):
            self.inspect()

    def test_cross_panel_vector_path_refused(self):
        self.make_pdf_pair(add_crossing=True)
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "crosses panels"):
            self.inspect()

    def test_wrong_declared_source_panel_not_silent(self):
        proposal=[{"id":chr(97+i),"source_bbox":self.srcboxes[i],
                   "slide_bbox":self.dstboxes[i]} for i in range(3)]
        proposal[1]["source_bbox"]=[50,160,150,250]
        with self.assertRaises(FigureIdentityReviewRequired):
            self.inspect(panels=proposal)

    def test_source_subpanel_overlap_refused(self):
        proposal=[{"id":chr(97+i),"source_bbox":self.srcboxes[i],
                   "slide_bbox":self.dstboxes[i]} for i in range(3)]
        proposal[0]["source_bbox"]=[50,50,150,160]
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "Overlapping"):
            self.inspect(panels=proposal)

    def test_source_figure_crop_cannot_exclude_other_panels(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            self.inspect(source_figure_bbox=[50,50,150,280])

    def test_invalid_scale_boolean_and_bad_ids(self):
        for bad in (True,1,5,2.5):
            with self.subTest(bad=bad),self.assertRaises(FigureIdentityReviewRequired):
                self.inspect(render_scale=bad)
        proposal=[{"id":chr(97+i),"source_bbox":self.srcboxes[i],
                   "slide_bbox":self.dstboxes[i]} for i in range(3)]
        proposal[2]["id"]="a"
        with self.assertRaises(FigureIdentityReviewRequired):
            self.inspect(panels=proposal)

    def test_original_source_raster_must_not_replace_vector_proof(self):
        with pymupdf.open(self.source) as pdf:
            page=pdf[0]
            import io
            from PIL import Image
            buf=io.BytesIO()
            Image.new("RGB",(40,40),(0,0,0)).save(buf,"PNG")
            page.insert_image(pymupdf.Rect(70,70,90,90),
                              stream=buf.getvalue())
            tmp=self.root/"changed.pdf"
            pdf.save(tmp)
        tmp.replace(self.source)
        with self.assertRaisesRegex(FigureIdentityReviewRequired,
                                    "Mixed source raster"):
            self.inspect()

    def test_source_same_as_slide_refused(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            self.inspect(slides=self.source)


if __name__=="__main__":
    unittest.main()
