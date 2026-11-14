"""Regression: figure/math visual choices exist and cannot be faked by a model."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import tempfile
import unittest

import pymupdf
from PIL import Image, ImageDraw

from selenium_pipeline.figure_source_identity import FigureIdentityReviewRequired, _sha
from selenium_pipeline.incremental_element_candidate_map import candidate_map
from selenium_pipeline.incremental_lecture_sync_queue import inspect_pre_tts_folder
from selenium_pipeline.source_grounded_element_hints import source_evidence_worklist
from selenium_pipeline.verified_slide_visual_candidates import (
    registered_raster_targets, verify_visual_target, composite_math_targets,
)


def built_image_pdf(path: Path) -> None:
    image=Image.new("RGB",(400,150),"white")
    draw=ImageDraw.Draw(image)
    draw.rectangle((0,0,190,149),fill="#345a77")
    draw.rectangle((210,0,399,149),fill="#88452a")
    draw.text((30,40),"Panel A",fill="white")
    draw.text((235,40),"Panel B",fill="white")
    stream=BytesIO()
    image.save(stream,format="PNG")
    with pymupdf.open() as doc:
        page=doc.new_page(width=550,height=340)
        page.insert_image(pymupdf.Rect(65,100,465,250),
                          stream=stream.getvalue())
        page.insert_text((60,70),"Real composite illustration review")
        doc.save(path)


class PhysicalFigureCandidateRegression(unittest.TestCase):
    def test_real_registered_image_is_shabound_candidate_not_panel_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/"slide.pdf"
            built_image_pdf(file)
            original=_sha(file)
            with pymupdf.open(file) as doc:
                options=registered_raster_targets(doc[0],1)
                self.assertEqual(len(options),1)
                one=options[0]
                self.assertEqual(one["draft_element_id"],"s001.figure.001")
                self.assertEqual(one["kind"],"image_whole")
                self.assertTrue(one["panel_identity_review_required"])
                self.assertFalse(one["figure_semantics_verified"])
                self.assertEqual(one["anchor"]["native_dimensions_px"],[400,150])
                self.assertEqual(verify_visual_target(doc[0],1,one),one)
                forged={**one,"anchor":{**one["anchor"],
                       "decoded_image_md5":"0"*32}}
                with self.assertRaises(FigureIdentityReviewRequired):
                    verify_visual_target(doc[0],1,forged)
                forged_bbox={**one,"bbox_pdf_pt":[0,0,100,100]}
                with self.assertRaises(FigureIdentityReviewRequired):
                    verify_visual_target(doc[0],1,forged_bbox)
                fake_semantics={**one,"figure_semantics_verified":True}
                with self.assertRaises(FigureIdentityReviewRequired):
                    verify_visual_target(doc[0],1,fake_semantics)
            self.assertEqual(_sha(file),original)

    def test_no_image_no_fabricated_figure_anchor(self):
        with pymupdf.open() as doc:
            page=doc.new_page(width=550,height=340)
            page.insert_text((60,95),"Only author rendered slide text.")
            self.assertEqual(registered_raster_targets(page,1),[])

    def test_actual_serway_source_review_maps_figures_and_math_without_approval(self):
        home=Path.home()/"AppData"/"Local"/"MicroGen_AI_Web_Checkpoints"
        folder=(home/"20261112_PR528_G2_SERWAY6_4_NARRATION_SOURCE_REUSE_V7"
                /"source_tree"/"6"/"6.4")
        if not (folder/"source.pdf").is_file():
            self.skipTest("Original Serway PDF available only in Dell acceptance")
        hashes={name:_sha(folder/name)
                for name in ("source.pdf","slides.pdf","script.txt")}
        record=candidate_map(folder=folder,queue=inspect_pre_tts_folder(folder))
        all_targets=[t for s in record["slides"]
                     for t in s["candidate_visual_targets"]]
        imgs=[t for t in all_targets if t["kind"]=="image_whole"]
        math=[t for t in all_targets if t["kind"]=="math_row_group"]
        self.assertGreaterEqual(len(imgs),3)
        self.assertGreaterEqual(len(math),9)
        for slide in (6,9,11):
            self.assertTrue(any(t["kind"]=="image_whole"
                for t in record["slides"][slide-1]["candidate_visual_targets"]))
        self.assertEqual(record["utterance_count"],74)
        hints=source_evidence_worklist(folder=folder,candidates=record)
        self.assertEqual(hints["utterance_count"],74)
        self.assertFalse(hints["semantic_element_approval"])
        self.assertFalse(hints["tts_authorized"])
        self.assertEqual(hashes,{name:_sha(folder/name)
                              for name in hashes})


if __name__ == "__main__":
    unittest.main()
