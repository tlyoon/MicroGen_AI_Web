"""Portable split-source panel admission + fail-closed raster/PDF tests."""
from __future__ import annotations
import io
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import fitz
from PIL import Image
from selenium_pipeline.source_caption_figure_chain_v1 import (
    FigureChainError, generate_candidates, verify_rendered_pdf_source_figures,
    verify_latex_figure_chain, verify_figure_crops)
from selenium_pipeline.source_split_figure_chain_v1 import (
    prepare_split_figure_chain,verify_split_figure_chain)
from selenium_pipeline.runner import valid


class SplitFigureAcrossTwoSlidesTests(TestCase):
    def setUp(self):
        tmp=TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.work=self.root/"lecture"
        self.work.mkdir()
        self._create_source_and_split()
        self._make_pdf()

    def _create_source_and_split(self):
        source=self.work/"source.pdf"
        doc=fitz.open()
        page=doc.new_page(width=612,height=783)
        cnt=0
        for y in (485,649):
            for x in (159,308,460):
                im=Image.new("RGB",(90,90),(35+cnt*22,75+cnt*14,130+cnt*10))
                blob=io.BytesIO()
                im.save(blob,format="PNG")
                page.insert_image(fitz.Rect(x,y,x+75,y+84),stream=blob.getvalue())
                page.insert_text((x+3,y-38),"Source callout",fontsize=10)
                page.insert_text((x+5,y+94),chr(ord("a")+cnt),fontsize=9)
                cnt+=1
        page.insert_text((36,707),"Figure 8.1",fontname="hebo",fontsize=10)
        page.insert_text((36,722),"Energy transfer",fontsize=10)
        page.insert_text((36,737),"mechanisms",fontsize=10)
        doc.save(source)
        doc.close()
        crop_stage=self.root/"original_crop_stage"
        crop_stage.mkdir()
        generate_candidates(source,crop_stage)
        for name in ("Figure 8.1.png","source_figure_chain_v1.json"):
            shutil.copy2(crop_stage/name,self.work/name)
        split={"Figure_8_1_upper.png":[149,425,548,595],
               "Figure_8_1_lower.png":[149,595,548,750]}
        with fitz.open(source) as src:
            for filename,rect in split.items():
                src[0].get_pixmap(
                    matrix=fitz.Matrix(3,3),clip=fitz.Rect(rect),alpha=False
                ).save(self.work/filename)
        original=json.loads((self.work/"source_figure_chain_v1.json").read_text())
        provenance={
            "source_pdf_sha256":original["source_sha256"],
            "source_pdf_page_index":0,
            "technique":"pymupdf_page_render_3x_source_anchored",
            "regions_pdf_points":split}
        (self.work/"figure_repair_provenance.json").write_text(
            json.dumps(provenance),encoding="utf-8")
        self._tex()
        prepare_split_figure_chain(self.work)

    def _tex(self,omit=False,comment=False):
        names=["Figure_8_1_upper.png","Figure_8_1_lower.png"]
        lines=[r"\documentclass{beamer}",r"\usepackage{graphicx}",
               r"\begin{document}"]
        for i,name in enumerate(names):
            if omit and i==1:continue
            line=r"\begin{frame}"+"\n"+r"\includegraphics{"+name+"}"+"\n"+r"\end{frame}"
            if comment and i==1:
                line=line.replace(r"\includegraphics",r"%\includegraphics")
            lines.append(line)
        lines.append(r"\end{document}")
        (self.work/"slides.tex").write_text("\n".join(lines),encoding="utf-8")

    def _make_pdf(self,cover=False,only_first=False):
        dest=self.work/"slides.pdf"
        doc=fitz.open()
        for i,name in enumerate(["Figure_8_1_upper.png","Figure_8_1_lower.png"]):
            if i and only_first:break
            p=doc.new_page(width=612,height=792)
            p.insert_image(fitz.Rect(80,120,530,440),
                           stream=(self.work/name).read_bytes(),
                           keep_proportion=True)
            if cover and i==1:
                for obj in p.get_images(full=True):
                    for rect in p.get_image_rects(obj[0]):
                        p.draw_rect(rect,fill=(1,1,1),color=(1,1,1),
                                    overlay=True)
        doc.save(dest)
        doc.close()

    def test_normal_runner_accepts_original_source_splits_without_new_slide(self):
        v=verify_split_figure_chain(self.work)
        self.assertEqual(v["panel_count"],6)
        self.assertEqual(v["figures"]["Figure 8.1.png"],
                         ["Figure_8_1_upper.png","Figure_8_1_lower.png"])
        self.assertEqual(verify_latex_figure_chain(self.work)
                         ["verified_split_figure_count"],1)
        render=verify_rendered_pdf_source_figures(self.work)
        self.assertEqual(render["render_assets_verified"],2)
        self.assertEqual(render["figures_verified"],1)
        self.assertEqual(render["source_figure_visible_pages"],
                         {"Figure_8_1_upper.png":[1],
                          "Figure_8_1_lower.png":[2]})
        self.assertFalse(render["scientific_approval"])
        self.assertFalse(render["student_publication_authorized"])
        self.assertTrue(valid("slides",self.work))

    def test_normal_legacy_retrofit_bootstraps_source_split_ledger(self):
        from selenium_pipeline.retrofit_image_repair import (
            bootstrap_legacy_source_figures)
        (self.work/"source_split_figure_chain_v1.json").unlink()
        result=bootstrap_legacy_source_figures(self.work)
        self.assertEqual(result["status"],"LEGACY_SOURCE_FIGURE_BOOTSTRAP_VERIFIED")
        self.assertEqual(result["figure_count"],1)
        self.assertTrue((self.work/"source_split_figure_chain_v1.json").is_file())
        self.assertTrue(valid("slides",self.work))

    def test_missing_split_panel_is_rejected(self):
        (self.work/"Figure_8_1_lower.png").unlink()
        self.assertFalse(valid("slides",self.work))

    def test_changed_split_png_is_rejected(self):
        p=self.work/"Figure_8_1_lower.png"
        im=Image.open(p).convert("RGB")
        im.putpixel((100,120),(254,5,4))
        im.save(p)
        self.assertFalse(valid("slides",self.work))

    def test_missing_latex_part_is_rejected(self):
        self._tex(omit=True)
        self.assertFalse(valid("slides",self.work))

    def test_commented_latex_part_is_rejected(self):
        self._tex(comment=True)
        self.assertFalse(valid("slides",self.work))

    def test_missing_visible_pdf_part_is_rejected(self):
        self._make_pdf(only_first=True)
        self.assertFalse(valid("slides",self.work))

    def test_opaque_overlay_over_painted_part_is_rejected(self):
        self._make_pdf(cover=True)
        self.assertFalse(valid("slides",self.work))

    def test_source_provenance_change_is_rejected(self):
        p=self.work/"figure_repair_provenance.json"
        data=json.loads(p.read_text())
        data["regions_pdf_points"]["Figure_8_1_lower.png"][2]-=20
        p.write_text(json.dumps(data),encoding="utf-8")
        self.assertFalse(valid("slides",self.work))

    def test_split_ledger_tampering_is_rejected(self):
        p=self.work/"source_split_figure_chain_v1.json"
        data=json.loads(p.read_text())
        data["figures"]["Figure 8.1.png"]["source_rasters_covered"]=5
        p.write_text(json.dumps(data),encoding="utf-8")
        self.assertFalse(valid("slides",self.work))
