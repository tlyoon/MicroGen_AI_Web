"""Source printed panel meanings + actual slide image registration.

Use REAL original Serway 6.4 source where available; synthetic negative
tests prove missing/forged caption and source-slide occlusion never pass.
No Gemini, local model, ASR, paid TTS, video or academic approval.
"""
from __future__ import annotations

import copy
from pathlib import Path
import shutil
import tempfile
import unittest

import pymupdf

from selenium_pipeline.figure_source_identity import (
    FigureIdentityReviewRequired, _sha)
from selenium_pipeline.captioned_panel_target_router import panel_targets_for_slide
from selenium_pipeline.source_caption_panel_registration import (
    caption_parts, physical_label_rules, inspect_panel_correspondence)
from selenium_pipeline.incremental_element_candidate_map import candidate_map
from selenium_pipeline.incremental_lecture_sync_queue import inspect_pre_tts_folder
from selenium_pipeline.source_grounded_element_hints import source_evidence_worklist


def original():
    path=(Path.home()/"AppData"/"Local"/"MicroGen_AI_Web_Checkpoints"
          /"20261112_PR528_G2_SERWAY6_4_NARRATION_SOURCE_REUSE_V7"
          /"source_tree"/"6"/"6.4")
    if not (path/"source.pdf").is_file():
        raise unittest.SkipTest("Real G2 source exists only on Dell-115")
    return path


class CaptionedPanelRegistration(unittest.TestCase):
    def test_missing_panel_caption_does_not_invent_source_semantics(self):
        with pymupdf.open() as pdf:
            pg=pdf.new_page()
            pg.insert_text((100,350),
                "Figure 3.4 A beautiful figure with several graphs.")
            with self.assertRaises(FigureIdentityReviewRequired):
                caption_parts(pg,"3.4")

    def test_real_source_original_caption_and_markers_are_unique(self):
        folder=original()
        before=_sha(folder/"source.pdf")
        with pymupdf.open(folder/"source.pdf") as pdf:
            text,rect,parts=caption_parts(pdf[1],"6.12")
            self.assertEqual([c for c,_ in parts],["a","b","c"])
            self.assertIn("sphere falling through a liquid",parts[0][1])
            self.assertIn("motion diagram",parts[1][1])
            self.assertIn("speed",parts[2][1])
            physical=physical_label_rules(pdf[1],rect,parts)
            self.assertEqual([p["panel"] for p in physical],["a","b","c"])
            for p in physical:
                self.assertLess(p["underline_rect"][0],p["underline_rect"][2])
        self.assertEqual(before,_sha(folder/"source.pdf"))

    def test_real_original_slide_pixels_verified_for_each_caption_panel(self):
        folder=original()
        before={x:_sha(folder/x) for x in ("source.pdf","slides.pdf","script.txt")}
        proof=inspect_panel_correspondence(
            source=folder/"source.pdf",slides=folder/"slides.pdf",
            source_page=2,slide_page=6,figure_id="6.12")
        self.assertEqual(proof["panel_count"],3)
        self.assertTrue(proof["printed_caption_panel_meanings_verified"])
        self.assertTrue(proof["source_slide_panels_physically_registered"])
        self.assertGreater(proof["orb_ransac_inlier_count"],100)
        self.assertGreater(proof["akaze_ransac_inlier_count"],50)
        self.assertGreater(proof["panel_RGB_12_tolerance_fraction"],.93)
        self.assertFalse(proof["independent_mathematical_semantics_verified"])
        self.assertFalse(proof["per_utterance_acoustic_alignment_verified"])
        self.assertFalse(proof["G2_approved"])
        spans=[p["slide_page_bbox_pdf_pt"] for p in proof["panels"]]
        for a,b in zip(spans,spans[1:]):
            self.assertAlmostEqual(a[2],b[0],places=3)
        self.assertTrue(all(
            p["reproduced_RGB_tolerance12_fraction"]>.91
            and p["orb_inlier_feature_count"]>=6
            and p["akaze_inlier_feature_count"]>=6
            for p in proof["panels"]))
        self.assertEqual(before,{x:_sha(folder/x) for x in before})

    def test_real_normal_utterance_mapping_can_select_three_panels(self):
        folder=original()
        result=candidate_map(folder=folder,queue=inspect_pre_tts_folder(folder))
        slide=result["slides"][5]
        choices={t["draft_element_id"]:t for t in
                 slide["candidate_visual_targets"] if
                 t["kind"]=="image_caption_panel"}
        self.assertEqual(set(choices),{
            "s006.panel.a","s006.panel.b","s006.panel.c"})
        self.assertFalse(result["ready_for_paid_element_tts"])
        for ordinal,letter in [(2,"a"),(3,"b"),(5,"c")]:
            u=slide["original_utterance_candidates"][ordinal-1]
            self.assertEqual(
                u["candidate_visual_targets"][0]["target_id"],
                "s006.panel."+letter)
        hints=source_evidence_worklist(folder=folder,candidates=result)
        self.assertEqual(hints["utterance_count"],74)
        self.assertFalse(hints["tts_authorized"])

        fake=copy.deepcopy(result)
        target=next(t for t in fake["slides"][5]["candidate_visual_targets"]
                    if t["kind"]=="image_caption_panel")
        target["anchor"]["slide_image_md5"]="0"*32
        with self.assertRaises(FigureIdentityReviewRequired):
            source_evidence_worklist(folder=folder,candidates=fake)

    def test_historical_rich_lecture_worklist_reuses_source_panel_provenance(self):
        from selenium_pipeline.element_plan_autodraft import propose
        from selenium_pipeline.rich_element_mapping_checkpoint import (
            MAPPING_DETECTOR_REVISION)
        folder=original()
        self.assertGreaterEqual(MAPPING_DETECTOR_REVISION,4)
        proposal=propose(
            source_pdf=folder/"source.pdf",slides_pdf=folder/"slides.pdf",
            script_txt=folder/"script.txt")
        self.assertEqual(proposal["utterance_count"],74)
        self.assertFalse(proposal["can_stage_or_synthesize_audio"])
        targets=proposal["slides"][5]["auto_candidate_targets"]
        indexed={p["draft_element_id"]:p for p in targets
                 if p["kind"]=="image_caption_panel"}
        self.assertEqual(set(indexed),{
            "s006.panel.a","s006.panel.b","s006.panel.c"})
        for n,letter in [(2,"a"),(3,"b"),(5,"c")]:
            row=proposal["slides"][5]["proposed_utterances"][n-1]
            self.assertEqual(
                row["candidate_target_rankings_unverified"][0]["draft_element_id"],
                "s006.panel."+letter)
            self.assertFalse(row["approved_for_tts"])
        self.assertTrue(all(
            not x["author_reviewed"] and x["mathematical_semantics_verified"] is False
            for x in indexed.values()))

    def test_panel_hint_without_real_source_corroboration_is_discarded(self):
        from selenium_pipeline.element_plan_autodraft import stable_recommendations
        false_panel={
            "draft_element_id":"fake.panel.a",
            "kind":"image_caption_panel",
            "visible_text":"(a) This proves a physics law",
            "anchor":{"type":"unverified_figure_panel","panel":"a"},
            "source_caption_panel_meaning_verified":True,
            "independent_visual_registration_verified":False,
            "mathematical_semantics_verified":False,
        }
        self.assertEqual(stable_recommendations(
            "In panel a the force is upward.",[false_panel]),[])

    def test_visible_overlay_in_pdf_blocks_registration(self):
        folder=original()
        with tempfile.TemporaryDirectory() as tmp:
            copy_slide=Path(tmp)/"slides_overlay.pdf"
            shutil.copyfile(folder/"slides.pdf",copy_slide)
            with pymupdf.open(copy_slide) as doc:
                # Overpaint the actual Figure (b) visual area but retain
                # source bitmap xref and PDF text: no cached-image bypass.
                page=doc[5]
                page.draw_rect(pymupdf.Rect(128,104,198,226),
                               fill=(1,1,1),color=None,overlay=True)
                doc.saveIncr()
            with self.assertRaises(FigureIdentityReviewRequired):
                inspect_panel_correspondence(
                    source=folder/"source.pdf",slides=copy_slide,
                    source_page=2,slide_page=6,figure_id="6.12")

    def test_no_unmatched_panels_in_original_nonmultipart_slides(self):
        folder=original()
        for number in (9,11):
            self.assertEqual(panel_targets_for_slide(
                source=folder/"source.pdf",slides=folder/"slides.pdf",
                slide_number=number),[])


if __name__=="__main__":
    unittest.main()
