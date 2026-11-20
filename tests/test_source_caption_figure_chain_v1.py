"""Source-PDF vector+composite crop and LaTeX coverage fault-injection tests.

No live Gemini/API, no edits to user's original Serway §8.2 material.
"""
from __future__ import annotations

import io
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import fitz
from PIL import Image

from selenium_pipeline.source_caption_figure_chain_v1 import (
    LEDGER, FigureChainError, generate_candidates, _sha, promote_candidates,
    printed_source_captions, recover_printed_source_figures,
    verify_figure_crops, verify_latex_figure_chain,
    missing_required_latex_figures,
)


class OriginalPDFCropChainTests(TestCase):
    def setUp(self):
        tmp=TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.work=self.root/"lecture";self.work.mkdir()
        self.source=self.work/"source.pdf"
        self._create_pdf()

    def _create_pdf(self, *, omit_panel=None, omit_first_graphic=False):
        doc=fitz.open()
        p=doc.new_page(width=612,height=783)
        # Source is drawn as VECTORS; no raster image for Figure 8.2.
        if not omit_first_graphic:
            for y in (99,154,214):
                p.draw_rect(fitz.Rect(60,y,135,y+28),color=(0,.3,.7),
                            fill=(.8,.9,.99))
            p.draw_line(fitz.Point(67,89),fitz.Point(67,244),
                        color=(0,0,0),width=1)
        p.insert_text((36,270),"Figure 8.2 Book released from rest",
                      fontsize=10, fontname="hebo")
        p.insert_text((210,130),"The text refers to Figure 8.7, but",
                      fontsize=10)
        p.insert_text((210,147),"Figure 8.7 has no printed caption here.",
                      fontsize=10)
        p=doc.new_page(width=612,height=783)
        for x in (84,158,310,384):
            p.draw_line(fitz.Point(x,101),fitz.Point(x,243),
                        color=(0,.4,.8),width=1)
        canvas=Image.new("RGB",(45,65),(120,160,185))
        stream=io.BytesIO();canvas.save(stream,format="PNG")
        p.insert_image(fitz.Rect(160,110,206,176),stream=stream.getvalue())
        for letter,x in (("a",89),("b",316),("c",384)):
            if letter!=omit_panel:
                p.insert_text((x,249),letter,fontsize=9)
        # Same PyMuPDF caption block, including 3 declared panels.
        p.insert_textbox(fitz.Rect(444,180,598,256),
                         "Figure 8.5 (a) actor\nactor on a rope\n"
                         "(b) force on actor\nsource panel\n"
                         "(c) force on bag\nsource panel\nlast note",
                         fontsize=9.0,fontname="hebo",lineheight=1.12)
        p=doc.new_page(width=612,height=783)
        p.insert_text((80,190),
                      "As discussed with Figure 8.7, there is no picture.",
                      fontsize=10)
        doc.save(self.source)
        doc.close()

    def _stage(self):
        folder=self.root/"stage";folder.mkdir()
        shutil.copy2(self.source,folder/"source.pdf")
        generate_candidates(self.source,folder)
        return folder

    def _complete(self):
        stage=self._stage()
        promote_candidates(stage,self.work)
        return stage

    def test_inventory_captions_not_cross_references(self):
        c=printed_source_captions(self.source)
        self.assertEqual([(r["id"],r["page"]) for r in c],
                         [("8.2",1),("8.5",2)])
        self.assertEqual(c[1]["expected_panels"],["a","b","c"])
        self.assertNotIn("8.7",[row["id"] for row in c])

    def test_real_vector_only_first_figure_and_composite_second_figure(self):
        stage=self._stage()
        report=verify_figure_crops(stage)
        self.assertEqual(report["status"],
                         "ALL_PRINTED_SOURCE_FIGURE_CROPS_VERIFIED")
        self.assertEqual(report["figure_count"],2)
        self.assertEqual(report["verified_panels"],3)
        entries=json.loads((stage/LEDGER).read_text())["figures"]
        self.assertEqual(entries[0]["object_evidence"]["raster_objects"],0)
        self.assertGreater(entries[0]["object_evidence"]["vector_paths"],0)
        self.assertGreater(entries[1]["object_evidence"]["raster_objects"],0)
        self.assertEqual([r["panel"] for r in entries[1]["panel_witnesses"]],
                         ["a","b","c"])
        self.assertFalse(entries[1]["semantic_accuracy_or_publication_approved"])

    def test_partial_existing_crop_replaced_only_after_complete_verification(self):
        old_hash=_sha(self.source)
        old_file=self.work/"Figure 8.5.png"
        old_file.write_bytes(b"incomplete panel-only original")
        stage=self._complete()
        backup=stage/"Figure 8.5.png.previous_incomplete"
        self.assertEqual(backup.read_bytes(),b"incomplete panel-only original")
        self.assertEqual(_sha(self.source),old_hash)
        self.assertNotEqual(old_file.read_bytes(),backup.read_bytes())
        self.assertEqual(verify_figure_crops(self.work)["figure_count"],2)
        # Repeating a verified recovery reuses on-disk source crops unchanged.
        previous=_sha(self.work/"Figure 8.5.png")
        result=recover_printed_source_figures(self.work)
        self.assertTrue(result["reused_verified_crops"])
        self.assertEqual(result["new_local_recovery_attempts"],0)
        self.assertEqual(_sha(self.work/"Figure 8.5.png"),previous)

    def test_missing_declared_panel_rejected_before_any_figure_promotion(self):
        self._create_pdf(omit_panel="c")
        with self.assertRaisesRegex(FigureChainError,"Missing source PDF panel"):
            self._stage()
        self.assertFalse((self.work/LEDGER).exists())
        with self.assertRaisesRegex(FigureChainError,"BOUNDED_TWO_ATTEMPTS"):
            recover_printed_source_figures(self.work)
        self.assertFalse((self.work/LEDGER).exists())
        self.assertFalse((self.work/"Figure 8.5.png").exists())

    def test_absent_vector_picture_rejected_not_saved_as_blank_png(self):
        self._create_pdf(omit_first_graphic=True)
        with self.assertRaises(FigureChainError):
            self._stage()

    def test_tampered_raster_png_and_source_pdf_are_rejected(self):
        self._complete()
        file=self.work/"Figure 8.5.png"
        file.write_bytes(file.read_bytes()+b"changed")
        with self.assertRaisesRegex(FigureChainError,"changed"):
            verify_figure_crops(self.work)
        # Even if a malicious ledger update matches PNG SHA, render-equivalence
        # still fails against the original source region.
        ledger=json.loads((self.work/LEDGER).read_text())
        ledger["figures"][1]["crop_png_sha256"]=_sha(file)
        (self.work/LEDGER).write_text(json.dumps(ledger),encoding="utf8")
        with self.assertRaisesRegex(FigureChainError,"exact source PDF crop"):
            verify_figure_crops(self.work)
        self._create_pdf()
        with self.assertRaises(FigureChainError):
            verify_figure_crops(self.work)

    def test_missing_cropped_png_rejected_and_no_silent_latex_approval(self):
        self._complete()
        (self.work/"Figure 8.2.png").unlink()
        with self.assertRaises(FigureChainError):
            verify_figure_crops(self.work)
        with self.assertRaises(FigureChainError):
            verify_latex_figure_chain(self.work)

    def test_latex_missing_figure_and_iffileexists_are_strict_rejections(self):
        self._complete()
        tex=self.work/"slides.tex"
        tex.write_text(
            r"\IfFileExists{Figure 8.5.png}{}{}"
            +r"\includegraphics{Figure 8.5.png}",encoding="utf8")
        with self.assertRaisesRegex(FigureChainError,"omitted"):
            verify_latex_figure_chain(self.work)
        tex.write_text(
            r"\IfFileExists{Figure 8.5.png}{}{}"
            +r"\includegraphics{Figure 8.5.png}"
            +r"\includegraphics{Figure 8.2.png}",encoding="utf8")
        with self.assertRaisesRegex(FigureChainError,"hidden"):
            verify_latex_figure_chain(self.work)
        tex.write_text(
            r"\includegraphics[width=0.7\linewidth]{Figure 8.2.png}"
            +"\n"+r"\includegraphics{Figure 8.5.png}",
            encoding="utf8")
        self.assertEqual(verify_latex_figure_chain(self.work)["figures_verified"],2)

    def test_source_caption_figure_stage_rejects_missing_ledgers(self):
        from selenium_pipeline.runner import valid
        (self.work/"pages"/"page_1").mkdir(parents=True)
        p=self.work/"crops"/"page_1";p.mkdir(parents=True)
        (p/"page_1.png").write_bytes(b"original full page, not figure crop")
        self.assertFalse(valid("figures",self.work))
        self._complete()
        self.assertTrue(valid("figures",self.work))
        (self.work/"Figure 8.5.png").unlink()
        self.assertFalse(valid("figures",self.work))

    def test_wrong_or_missing_source_crop_registry_halts_before_writes(self):
        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value=None):
            with self.assertRaisesRegex(FigureChainError,"not registered"):
                recover_printed_source_figures(self.work)
        self.assertEqual(list(self.work.glob("Figure*.png")),[])
        self.assertFalse((self.work/LEDGER).exists())

    def test_source_caption_latex_missing_helper_is_exact(self):
        report=missing_required_latex_figures(
            r"\includegraphics{Figure 8.2.png}"
            r"\IfFileExists{Figure 8.5.png}{}{}",
            ["Figure 8.2.png","Figure 8.5.png"])
        self.assertEqual(report["missing"],["Figure 8.5.png"])
        self.assertEqual(report["guarded"],["Figure 8.5.png"])


class RealSerway82SourceOnlyIntegrationTests(TestCase):
    def test_real_pdf_source_five_captioned_figures_recoverable(self):
        source=Path(r"G:\My Drive\Serway\Serway_8_14\8\8.2\source.pdf")
        if not source.is_file():
            self.skipTest("Dell-115 Serway G: source is absent on this CI host")
        self.assertEqual([row["id"] for row in printed_source_captions(source)],
                         ["8.2","8.3","8.4","8.5","8.6"])
        with TemporaryDirectory() as tmp:
            folder=Path(tmp)/"lecture";folder.mkdir()
            shutil.copy2(source,folder/"source.pdf")
            before=_sha(folder/"source.pdf")
            report=recover_printed_source_figures(folder)
            self.assertEqual(report["figure_count"],5)
            self.assertEqual(report["status"],"SOURCE_CAPTION_COMPLETE_CROPS_PROMOTED")
            self.assertEqual(_sha(folder/"source.pdf"),before)
            result=verify_figure_crops(folder)
            self.assertEqual(result["figure_count"],5)
            self.assertEqual(result["verified_panels"],9)
            self.assertFalse((folder/"Figure 8.7.png").exists())
            self.assertEqual(report["new_local_recovery_attempts"],1)
            expected=["Figure 8.2.png","Figure 8.3.png","Figure 8.4.png",
                      "Figure 8.5.png","Figure 8.6.png"]
            self.assertEqual(result["figures"],expected)
            (folder/"slides.tex").write_text(
                "\n".join(r"\includegraphics{"+name+"}"
                          for name in expected),encoding="utf8")
            self.assertEqual(
                verify_latex_figure_chain(folder)["figures_verified"],5)
