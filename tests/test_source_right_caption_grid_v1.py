"""Regression for Serway 8.1: six-source-panel grid right of caption."""
import io
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import fitz
from PIL import Image

from selenium_pipeline.source_caption_figure_chain_v1 import (
    FigureChainError, _crop_proposal, generate_candidates,
    printed_source_captions, verify_figure_crops,
)


class RightCaptionGridRecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp=TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.source=self.root/"source.pdf"

    def _make_pdf(self, rows=2, touch_boundary=False):
        pdf=fitz.open()
        page=pdf.new_page(width=612,height=783)
        i=0
        for yy in (485,649)[:rows]:
            for xx in (159,308,460):
                image=Image.new("RGB",(90,90),(45+i*18,70+i*14,105+i*12))
                blob=io.BytesIO()
                image.save(blob,format="PNG")
                page.insert_image(fitz.Rect(xx,yy,xx+75,yy+84),
                                  stream=blob.getvalue())
                page.insert_text((xx+3, yy-38),f"Energy example {i+1}",fontsize=10)
                page.insert_text((xx+5, yy+94),chr(ord("a")+i),fontsize=9)
                i+=1
        page.insert_text((36,707),"Figure 8.1",fontname="hebo",fontsize=10)
        page.insert_text((36,722),"Energy transfer",fontsize=10)
        page.insert_text((36,737),"mechanisms",fontsize=10)
        if touch_boundary:
            page.draw_line(fitz.Point(149,440),fitz.Point(149,500),
                           color=(0,0,0),width=3)
        pdf.save(self.source)
        pdf.close()

    def test_all_six_panels_left_caption_are_cropped_and_sha_verified(self):
        self._make_pdf()
        row=printed_source_captions(self.source)
        self.assertEqual([a["id"] for a in row],["8.1"])
        with fitz.open(self.source) as doc:
            clip, mode=_crop_proposal(doc[0],row[0])
        self.assertEqual(mode,"source_raster_vector_grid_right_of_caption")
        self.assertGreater(clip.x0,138)
        self.assertLess(clip.y0,485)
        self.assertGreater(clip.y1,733)
        stage=self.root/"stage";stage.mkdir()
        generated=generate_candidates(self.source,stage)
        shutil.copy2(self.source,stage/"source.pdf")
        self.assertEqual(generated["figure_count"],1)
        self.assertEqual(generated["figures"][0]["object_evidence"]["raster_objects"],6)
        self.assertEqual(verify_figure_crops(stage)["figure_count"],1)

    def test_legacy_retrofit_bootstraps_source_ledger_inside_staging(self):
        self._make_pdf()
        staged=self.root/"legacy_stage"
        staged.mkdir()
        shutil.copy2(self.source,staged/"source.pdf")
        (staged/"slides.tex").write_text(
            r"\\includegraphics{Figure 8.1.png}",encoding="utf-8")
        from selenium_pipeline.retrofit_image_repair import (
            bootstrap_legacy_source_figures)
        result=bootstrap_legacy_source_figures(staged)
        self.assertEqual(result["figure_count"],1)
        self.assertTrue((staged/"source_figure_chain_v1.json").is_file())
        self.assertTrue((staged/"Figure 8.1.png").is_file())
        again=bootstrap_legacy_source_figures(staged)
        self.assertEqual(again["recovery_status"],"ALL_PRINTED_SOURCE_FIGURE_CROPS_VERIFIED")
        self.assertEqual(verify_figure_crops(staged)["figure_count"],1)

    def test_legacy_bootstrap_rejects_silent_latex_omission(self):
        self._make_pdf()
        staged=self.root/"omission_stage"
        staged.mkdir()
        shutil.copy2(self.source,staged/"source.pdf")
        (staged/"slides.tex").write_text(
            r"\\begin{document} no figure here \\end{document}",
            encoding="utf-8")
        from selenium_pipeline.retrofit_image_repair import (
            bootstrap_legacy_source_figures)
        with self.assertRaisesRegex(FigureChainError,"LaTeX omitted"):
            bootstrap_legacy_source_figures(staged)

    def test_three_photo_row_must_not_trigger_two_row_grid_recovery(self):
        self._make_pdf(rows=1)
        row=printed_source_captions(self.source)
        with fitz.open(self.source) as doc:
            _, mode=_crop_proposal(doc[0],row[0])
        self.assertNotEqual(mode,"source_raster_vector_grid_right_of_caption")

    def test_source_geometry_rejects_drawn_content_at_crop_edge(self):
        self._make_pdf(touch_boundary=True)
        stage=self.root/"staged_rejection";stage.mkdir()
        with self.assertRaisesRegex(FigureChainError,"touches crop boundary"):
            generate_candidates(self.source,stage)


if __name__=="__main__":
    unittest.main()
