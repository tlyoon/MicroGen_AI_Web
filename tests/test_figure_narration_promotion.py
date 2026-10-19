"""Production promotion blocks unverified composite figures before FFmpeg/IO."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium_pipeline.figure_narration_promotion import (
    FigureNarrationPromotionBlocked,check_production_anchor_provenance)
from selenium_pipeline.sourcebound_production_video import (
    ProductionRenderError,accept_candidate,
)


def plan_with_anchor(kind):
    return {
        "schema_version":1,
        "status":"author_specified_unapproved_element_narration",
        "source_sha256":"0"*64,
        "slides_sha256":"1"*64,
        "parts":[{
            "part_id":"part_01",
            "slides":[{
                "slide":1,"source_page":1,"source_evidence":"Textbook quote",
                "elements":[{
                    "spoken_text":"This is an independently source-bound paragraph.",
                    "wav":"s001_e01.wav",
                    "anchor":{"type":kind,"index":0,"panel":1,"panels":3},
                }],
            }],
        }],
    }


class FigurePromotionTests(unittest.TestCase):
    def test_exact_text_only_remains_permitted(self):
        result=check_production_anchor_provenance(plan_with_anchor("text_block"))
        self.assertEqual(result["narrated_text_anchor_count"],1)
        self.assertFalse(result["self_declared_figure_approvals_accepted"])

    def test_all_unverified_figure_anchor_types_fail_before_video(self):
        for anchor in ("image_whole","image_panel","vector_figure",
                       "figure_panel","figure","diagram_region"):
            with self.subTest(anchor=anchor),self.assertRaisesRegex(
                FigureNarrationPromotionBlocked,"review-only"):
                check_production_anchor_provenance(plan_with_anchor(anchor))

    def test_forged_semantic_approvals_do_not_bypass(self):
        forged=plan_with_anchor("image_panel")
        forged.update({"tts_or_video_authorized":True,
                       "figure_semantics_certified":True,
                       "author_intended_complete_panel_boundaries_certified":True})
        forged["parts"][0]["slides"][0]["elements"][0]["anchor"].update({
            "source_verified":True,"human_review_claimed":True,
            "approval_status":"APPROVED",
        })
        with self.assertRaisesRegex(FigureNarrationPromotionBlocked,"review-only"):
            check_production_anchor_provenance(forged)

    def test_unknown_or_malformed_anchor_rejected(self):
        for kind in ("",None,"pdf_bitmap","OCR",17,True):
            with self.subTest(kind=kind),self.assertRaises(
                FigureNarrationPromotionBlocked):
                check_production_anchor_provenance(plan_with_anchor(kind))
        for broken in ([],{},{"parts":[]},{"parts":[{"slides":[]}]}):
            with self.subTest(broken=broken),self.assertRaises(
                FigureNarrationPromotionBlocked):
                check_production_anchor_provenance(broken)

    def test_unverified_figure_rejected_before_expensive_ffmpeg_or_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            original=root/"original"
            original.mkdir()
            source=original/"source.pdf"
            slides=original/"slides.pdf"
            authored=original/"plan.json"
            source.write_bytes(b"%PDF-mock-source-preserve")
            slides.write_bytes(b"%PDF-mock-slide-preserve")
            plan=plan_with_anchor("image_panel")
            authored.write_text(json.dumps(plan),encoding="utf-8")
            wav=root/"audio"
            wav.mkdir()
            reviewed=root/"review"
            reviewed.mkdir()
            candidates=root/"candidates"
            candidates.mkdir()
            destination=candidates/"new-candidate"
            before={p:hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (source,slides,authored)}
            with patch(
                "selenium_pipeline.sourcebound_production_video.verify_rendered"
            ) as expensive:
                with self.assertRaisesRegex(ProductionRenderError,"review-only"):
                    accept_candidate(
                        source=source,slides=slides,authored=authored,
                        audio=wav,review_root=reviewed,candidate=destination)
                expensive.assert_not_called()
            self.assertFalse(destination.exists())
            self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in (source,slides,authored)})

    def test_image_after_text_still_blocked(self):
        plan=plan_with_anchor("text_block")
        plan["parts"][0]["slides"][0]["elements"].append({
            "anchor":{"type":"image_whole","index":0},
            "wav":"s001_e02.wav","spoken_text":"Unverified diagram claim.",
        })
        with self.assertRaises(FigureNarrationPromotionBlocked):
            check_production_anchor_provenance(plan)


if __name__=="__main__":
    unittest.main()
