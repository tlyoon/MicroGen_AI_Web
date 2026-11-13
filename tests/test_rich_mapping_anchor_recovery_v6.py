"""Cross-entrypoint recovery: rich PDF anchors must not break safe prose.

Only existing physical validators are used; new mapping categories are
review inputs, not automatic math/figure/speech or learner approvals.
Synthetic CI fixtures exercise the public normal request + fallback paths.
The authentic Dell-only Serway case checks actual caption/panel registration.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import pymupdf
from PIL import Image

from selenium_pipeline.rich_element_model_alignment import (
    RichMappingError, request_for_slide, assess_response)
from selenium_pipeline.rich_element_safe_prose_fallback import fully_audited_slide
from selenium_pipeline.sourcebound_math_row_focus import (
    math_row_rect, digest)


def sha(file:Path)->str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


class RichPhysicalAnchorNormalPathTests(TestCase):
    def setUp(self):
        tmp=TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.src=self.root/"source"
        self.src.mkdir()
        self.checkpoint=self.root/"checkpoint"
        self.checkpoint.mkdir()
        phrase="The surrounding fluid exerts a drag force on the falling sphere."
        with pymupdf.open() as pdf:
            pg=pdf.new_page(width=600,height=540)
            pg.insert_text((42,70),phrase)
            pg.insert_text((42,100),"The experiment illustrates terminal speed.")
            pdf.save(self.src/"source.pdf")
        with pymupdf.open() as pdf:
            pg=pdf.new_page(width=600,height=540)
            pg.insert_text((42,67),phrase)
            pg.insert_text((44,140),"R = 1")
            # A vertically offset but spatially coherent second authored
            # PDF block represents a genuinely fragmented equation row.
            pg.insert_text((88,153),"2D rho A v = 2")
            picture=Image.new("RGB",(180,95),"white")
            stream=io.BytesIO()
            picture.save(stream,format="PNG")
            pg.insert_image(pymupdf.Rect(45,220,270,350),
                            stream=stream.getvalue())
            pdf.save(self.src/"slides.pdf")
        (self.src/"script.txt").write_text(
            "**Slide 1 [15 sec]:\n"+phrase,encoding="utf8")
        with pymupdf.open(self.src/"slides.pdf") as pdf:
            pg=pdf[0]
            blocks=pg.get_text("blocks")
            candidate=next((i,b) for i,b in enumerate(blocks)
                           if phrase in b[4])
            text_index,text_block=candidate
            maths=[(i,b) for i,b in enumerate(blocks)
                   if "R = 1" in b[4] or "2D rho A v = 2" in b[4]]
            self.assertEqual(len(maths),2)
            indices=[i for i,b in maths]
            self.assertEqual(indices,[indices[0],indices[0]+1])
            anchor={"type":"math_row_group","indices":indices,
                    "text_sha256":[digest(b[4]) for i,b in maths]}
            mathrect=math_row_rect(pg,anchor)
            image=pg.get_image_rects(pg.get_images(full=True)[0][0])[0]
            self.records={
                "prose":{
                    "draft_element_id":"s001.text.001",
                    "kind":"text_block",
                    "anchor":{"type":"text_block","index":text_index,
                              "text_evidence":phrase[:36]},
                    "rendered_rect_pt":[round(float(x),2)
                                         for x in text_block[:4]],
                    "visible_text":phrase,
                    "panel_identity_review_required":False},
                "math":{
                    "draft_element_id":"s001.math_row.002-003",
                    "kind":"math_row_group",
                    "anchor":anchor,
                    "rendered_rect_pt":[round(float(x),2) for x in mathrect],
                    "visible_text":"R = 1 2D rho A v = 2",
                    "panel_identity_review_required":False,
                    "original_math_block_hashes_verified":True,
                    "mathematical_semantics_verified":False},
                "figure":{
                    "draft_element_id":"s001.figure.000",
                    "kind":"image_whole",
                    "anchor":{"type":"image_whole","index":0},
                    "rendered_rect_pt":[round(float(x),2) for x in image],
                    "visible_text":None,
                    "panel_identity_review_required":True},
            }
        panelanchor={
            "type":"original_pdf_panel_visual_provenance",
            "source_sha256":sha(self.src/"source.pdf"),
            "slides_sha256":sha(self.src/"slides.pdf"),
            "source_page":1,
            "figure_id":"1.1",
            "panel":"a",
        }
        self.records["panel"]={
            "draft_element_id":"s001.panel.a",
            "kind":"image_caption_panel",
            "anchor":panelanchor,
            "rendered_rect_pt":[45.0,220.0,140.0,350.0],
            "visible_text":"(a) Falling sphere.",
            "panel_identity_review_required":False,
            "source_caption_panel_meaning_verified":True,
            "independent_visual_registration_verified":True,
            "mathematical_semantics_verified":False,
        }
        self.canonical_panel={
            "draft_element_id":"s001.panel.a",
            "kind":"image_caption_panel",
            "anchor":panelanchor,
            "bbox_pdf_pt":[45.0,220.0,140.0,350.0],
            "visible_text":"(a) Falling sphere.",
            "panel_identity_review_required":False,
        }
        self.meta={
            "slide_count":1,
            "source_inputs_sha256":{
                "source.pdf":sha(self.src/"source.pdf"),
                "slides.pdf":sha(self.src/"slides.pdf"),
                "script.txt":sha(self.src/"script.txt")},
        }
        self.phrase=phrase

    def _draft(self,changes:dict|None=None)->dict:
        rows={k:copy.deepcopy(v) for k,v in self.records.items()}
        if changes:
            for name,patches in changes.items():
                rows[name].update(patches)
        return {
            "slides":[{
                "slide_number":1,
                "source_page_candidates_unverified":[{"source_page":1}],
                "auto_candidate_targets":list(rows.values()),
                "proposed_utterances":[{
                    "proposal_id":"s001.utterance.001",
                    "verbatim_script_fragment":self.phrase}],
                "verbatim_slide_narration":self.phrase,
            }]
        }

    def _run(self,changes=None,*,panels=None,full=False):
        panel=([copy.deepcopy(self.canonical_panel)] if panels is None
               else panels)
        with patch("selenium_pipeline.rich_element_model_alignment."
                   "load_accepted_checkpoint",
                   return_value=(self.meta,self._draft(changes))),patch(
                   "selenium_pipeline.captioned_panel_target_router."
                   "panel_targets_for_slide",return_value=panel) as registered:
            if full:
                proposal,assessment=fully_audited_slide(
                    source_folder=self.src,checkpoint=self.checkpoint,slide=1)
                return proposal,assessment,registered.call_count
            result=request_for_slide(
                source_folder=self.src,checkpoint=self.checkpoint,
                slide_number=1)
            return result,registered.call_count

    def test_all_rich_kinds_are_physical_unapproved_review_inputs(self):
        request,count=self._run()
        self.assertEqual(count,1)
        self.assertEqual(len(request["visible_targets"]),4)
        self.assertEqual({x["kind"] for x in request["visible_targets"]},{
            "text_block","math_row_group","image_whole","image_caption_panel"})
        self.assertFalse(request["figure_source_identification_is_approved"])
        self.assertFalse(request["audio_generation_authorized"])
        self.assertFalse(request["student_publication_authorized"])
        self.assertEqual(len(request["request_sha256"]),64)

    def test_safe_prose_second_entrypoint_retains_math_figure_holds(self):
        answer,assessment,count=self._run(full=True)
        # The fallback makes three physical revalidations: initial
        # request, first independent audit, and post-decision audit.
        self.assertEqual(count,3)
        self.assertEqual(len(answer["associations"]),1)
        self.assertEqual(answer["associations"][0]["target_id"],
                         "s001.text.001")
        self.assertEqual(assessment["text_source_and_author_anchors_passed"],1)
        self.assertFalse(assessment["paid_tts_authorized"])
        self.assertFalse(assessment["student_publication_authorized"])
        # The formula/picture/panel are visible *choices*, not accepted
        # for the prose; the safe fallback never guessed their meaning.
        request,_=self._run()
        for visual in request["visible_targets"]:
            if visual["kind"] != "text_block":
                self.assertNotEqual(answer["associations"][0]["target_id"],
                                    visual["target_id"])

    def test_wrong_caption_registry_fails_closed(self):
        with self.assertRaisesRegex(RichMappingError,
                                    "geometry or source panel"):
            self._run(panels=[])

    def test_spoofed_panel_provenance_or_region_fails_closed(self):
        with self.assertRaises(RichMappingError):
            self._run(changes={"panel":{
                "anchor":{"type":"original_pdf_panel_visual_provenance",
                          "source_sha256":"f"*64}}})
        with self.assertRaisesRegex(RichMappingError,
                                    "geometry or source panel"):
            self._run(changes={"panel":{"rendered_rect_pt":[5,5,12,12]}})

    def test_wrong_math_fragment_and_whole_image_coords_fail_closed(self):
        old=copy.deepcopy(self.records["math"]["anchor"])
        old["text_sha256"][0]="f"*64
        with self.assertRaises(RichMappingError):
            self._run(changes={"math":{"anchor":old}})
        with self.assertRaises(RichMappingError):
            self._run(changes={"figure":{
                "rendered_rect_pt":[1,1,4,4]}})

    def test_unknown_visual_kind_has_no_fallback_guess(self):
        with self.assertRaises(RichMappingError):
            self._run(changes={"math":{"kind":"generated_equation_guess"}})


class ActualSerwayRichPanelRecoveryTests(TestCase):
    def test_unchanged_original_rich_panel_and_all_slide_safe_prose(self):
        base=(Path.home()/"AppData"/"Local"/"MicroGen_AI_Web_Checkpoints")
        original=(base/
            "20261112_PR528_G2_SERWAY6_4_NARRATION_SOURCE_REUSE_V7"/
            "source_tree"/"6"/"6.4")
        checkpoint=(base/
            "20261113_G2_RICH_MATH_RECOVERY_CHECKPOINT_V5"/
            "rich_element_map_945d5c66ec52f0bcb2c34513")
        if not (original/"source.pdf").is_file() or not checkpoint.is_dir():
            self.skipTest("Real Serway/PDF mapping only on authorized Dell-115")
        before={p:sha(original/p)
                for p in ("source.pdf","slides.pdf","script.txt")}
        with patch("selenium_pipeline.series_gemini._browser_request",
                   side_effect=AssertionError("No previously consumed Gemini Send")),patch(
             "selenium_pipeline.tts._gemini_say_with_watchdog",
             side_effect=AssertionError("No paid TTS allowed")):
            rows=[
                fully_audited_slide(source_folder=original,
                                    checkpoint=checkpoint,slide=i)
                for i in range(1,15)]
        proven=[(i,u["utterance_id"]) for i,(resp,audit) in
                enumerate(rows,1) for u in resp["associations"]
                if u["target_id"] is not None]
        self.assertEqual(len(proven),7)
        self.assertEqual(sum(len(r["associations"]) for r,a in rows),74)
        self.assertTrue(all(a["paid_tts_authorized"] is False
                            and a["student_publication_authorized"] is False
                            for r,a in rows))
        self.assertEqual(before,{p:sha(original/p) for p in before})


if __name__=="__main__":
    import unittest
    unittest.main()
