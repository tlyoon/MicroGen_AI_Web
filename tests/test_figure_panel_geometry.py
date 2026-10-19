"""Real-PDF adversarial verification of explicit multi-panel raster geometry.

No model API, no publisher, no original teaching outputs, no panel semantics.
"""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw

from selenium_pipeline.figure_panel_geometry import (
    inspect_declared_composite_geometry,
)
from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired


class CompositeGeometryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.pdf"
        self.slides = self.root / "slides.pdf"
        self.png = self.root / "source_figure.png"
        self.caption = "Figure 8.3 Magnetic and electric field diagrams."
        self._fixture(axis="horizontal")

    def _fixture(self, axis="horizontal", changed=None, blank_panel=False):
        w,h = ((900,300) if axis=="horizontal" else (300,900))
        img = Image.new("RGB", (w,h), "white")
        draw = ImageDraw.Draw(img)
        for i in range(3):
            if axis=="horizontal":
                left,top,right,bottom = i*w//3,0,(i+1)*w//3,h
            else:
                left,top,right,bottom = 0,i*h//3,w,(i+1)*h//3
            if blank_panel and i==1: continue
            fill=[(120,35,80),(35,120,90),(45,65,145)][i]
            draw.rectangle((left,top,right-1,bottom-1),fill=fill)
            for j in range(5):
                x=left+20+j*31
                y=top+25+j*37
                draw.ellipse((x,y,x+12,y+12),fill=(230,j*40,10+i*60))
            draw.text((left+12,top+10), f"({chr(97+i)})",fill="white")
        img.save(self.png)
        self.axis=axis
        self.boundaries=[0,300,600,900]
        self.ids=["a","b","c"]
        if changed is not None:
            img.putpixel((w//2, h//2), (245,210,120))
            changed_path=self.root/"altered.png"
            img.save(changed_path)
        for slide,path in [(False,self.source),(True,self.slides)]:
            with pymupdf.open() as doc:
                page=doc.new_page(width=750,height=800)
                rect=(pymupdf.Rect(100,100,550,250) if axis=="horizontal"
                      else pymupdf.Rect(160,75,310,525))
                page.insert_image(rect,filename=str(changed_path if slide and changed else self.png))
                page.insert_text((100,rect.y1+30),self.caption,fontsize=11)
                doc.save(path)
        self.baseline={
            "source":hashlib.sha256(self.source.read_bytes()).hexdigest(),
            "slides":hashlib.sha256(self.slides.read_bytes()).hexdigest(),
        }

    def inspect(self, **overrides):
        opts=dict(source=self.source,slides=self.slides,source_page=1,
                  slide_page=1,caption=self.caption,axis=self.axis,
                  boundaries_px=self.boundaries,declared_panel_ids=self.ids)
        opts.update(overrides)
        return inspect_declared_composite_geometry(**opts)

    def test_real_three_panel_raster_partition_maps_both_pdfs(self):
        result=self.inspect()
        self.assertEqual(result["status"],
             "EXPLICIT_PANEL_PARTITION_GEOMETRY_CANDIDATE_REVIEW_REQUIRED")
        self.assertEqual(len(result["panels"]),3)
        self.assertEqual([p["native_bbox_px"] for p in result["panels"]],
                         [[0,0,300,300],[300,0,600,300],[600,0,900,300]])
        self.assertEqual(len({p["native_pixel_sha256"] for p in result["panels"]}),3)
        self.assertTrue(result["panel_raster_partition_coverage_verified"])
        for key in ("declared_panel_labels_source_verified",
                    "figure_panel_completeness_certified",
                    "figure_semantics_certified","tts_or_video_authorized",
                    "human_review_claimed"):
            self.assertIs(result[key],False)
        self.assertTrue(all(p["source_slide_pixels_identical"]
                            and not p["panel_semantics_certified"]
                            for p in result["panels"]))
        self.assertEqual(self.baseline["source"],
            hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(self.baseline["slides"],
            hashlib.sha256(self.slides.read_bytes()).hexdigest())
        self.assertFalse((self.root/"element_wav").exists())

    def test_vertical_three_panel_partition(self):
        self._fixture(axis="vertical")
        result=self.inspect()
        self.assertEqual(result["axis"],"vertical")
        self.assertEqual([p["native_bbox_px"] for p in result["panels"]],
                         [[0,0,300,300],[0,300,300,600],[0,600,300,900]])

    def test_a_b_c_are_explicit_declarations_not_verified_semantics(self):
        out=self.inspect()
        self.assertEqual([p["declared_id"] for p in out["panels"]],self.ids)
        self.assertFalse(out["declared_panel_labels_source_verified"])
        self.assertFalse(out["tts_or_video_authorized"])

    def test_missing_last_part_blocks(self):
        with self.assertRaisesRegex(FigureIdentityReviewRequired,"incomplete coverage"):
            self.inspect(boundaries_px=[0,300,600,899])

    def test_missing_first_part_blocks(self):
        with self.assertRaisesRegex(FigureIdentityReviewRequired,"incomplete coverage"):
            self.inspect(boundaries_px=[1,300,600,900])

    def test_overlap_or_reversed_bounds_blocks(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            self.inspect(boundaries_px=[0,600,300,900])

    def test_duplicated_boundary_blocks(self):
        with self.assertRaises(FigureIdentityReviewRequired):
            self.inspect(boundaries_px=[0,300,300,900])

    def test_too_narrow_panel_blocks(self):
        with self.assertRaisesRegex(FigureIdentityReviewRequired,"too narrow"):
            self.inspect(boundaries_px=[0,10,600,900])

    def test_float_and_boolean_boundaries_block(self):
        for bounds in ([0,300.0,600,900],[0,True,600,900]):
            with self.subTest(bounds=bounds),self.assertRaises(FigureIdentityReviewRequired):
                self.inspect(boundaries_px=bounds)

    def test_duplicate_and_out_of_order_labels_block(self):
        for ids in (["a","a","c"],["b","a","c"],["a","b"],["a","b","d"]):
            with self.subTest(ids=ids), self.assertRaises(FigureIdentityReviewRequired):
                self.inspect(declared_panel_ids=ids)

    def test_wrong_axis_and_no_partition_block(self):
        for axis in ("diagonal","",None):
            with self.subTest(axis=axis), self.assertRaises(FigureIdentityReviewRequired):
                self.inspect(axis=axis)
        with self.assertRaises(FigureIdentityReviewRequired):
            self.inspect(boundaries_px=[0,900],declared_panel_ids=["a"])

    def test_changed_slide_pixels_block(self):
        self._fixture(changed=True)
        with self.assertRaisesRegex(FigureIdentityReviewRequired,"identity differs"):
            self.inspect()

    def test_blank_internal_panel_blocks(self):
        self._fixture(blank_panel=True)
        with self.assertRaisesRegex(FigureIdentityReviewRequired,"uniform-color"):
            self.inspect()

    def test_declared_four_panels_can_still_be_semantically_wrong(self):
        # Engineering deliberately cannot infer actual label count from raw
        # pixels. A complete but arbitrary partition is still review only.
        res=self.inspect(boundaries_px=[0,225,450,675,900],
                         declared_panel_ids=["a","b","c","d"])
        self.assertTrue(res["panel_raster_partition_coverage_verified"])
        self.assertFalse(res["figure_panel_completeness_certified"])
        self.assertFalse(res["figure_semantics_certified"])
