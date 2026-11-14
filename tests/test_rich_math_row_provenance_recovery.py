"""Regression: rich mathematical row candidates revalidate source once.

Existing rich mapper already contains 2-8-block math candidates; the historical
remedy is to reverify and annotate THEM, not duplicate their geometry. A fake
math proof cannot influence recommendations or authorize any audio.
"""
from __future__ import annotations

import copy
from pathlib import Path
import unittest

from selenium_pipeline.element_plan_autodraft import (
    propose, stable_recommendations)
from selenium_pipeline.rich_element_mapping_checkpoint import (
    MAPPING_DETECTOR_REVISION)


class RichMathRowSourceRecoveryTests(unittest.TestCase):
    def test_redundant_equation_group_does_not_create_spurious_second_choice(self):
        targets=[
            {"draft_element_id":"s002.text.006","kind":"text_block",
             "anchor":{"type":"text_block","index":6},
             "visible_text":"Model 2: resistive force proportional to speed squared R = 1"},
            {"draft_element_id":"s002.math_row.006-007","kind":"math_row_group",
             "anchor":{"type":"math_row_group","indices":[6,7]},
             "visible_text":"Model 2: resistive force proportional to speed squared R = 1 2",
             "original_math_block_hashes_verified":True,
             "mathematical_semantics_verified":False},
        ]
        sentence="The quadratic model is resistive force proportional to speed squared."
        result=stable_recommendations(sentence,targets)
        self.assertTrue(result)
        self.assertEqual(result[0]["draft_element_id"],"s002.text.006")
        self.assertFalse(any("math_row" in r["draft_element_id"] for r in result))

    def test_unwitnessed_or_falsely_approved_math_row_cannot_rank(self):
        target={"draft_element_id":"s007.math_row.001-002",
                "kind":"math_row_group","anchor":{"type":"math_row_group",
                                                  "indices":[1,2]},
                "visible_text":"sin theta = 1/2",
                "original_math_block_hashes_verified":False,
                "mathematical_semantics_verified":False}
        text="We calculate sine theta in the integral."
        self.assertEqual(stable_recommendations(text,[target]),[])
        forged=copy.deepcopy(target)
        forged["original_math_block_hashes_verified"]=True
        forged["mathematical_semantics_verified"]=True
        self.assertEqual(stable_recommendations(text,[forged]),[])
        validated=copy.deepcopy(target)
        validated["original_math_block_hashes_verified"]=True
        result=stable_recommendations(text,[validated])
        self.assertTrue(result)
        self.assertEqual(result[0]["draft_element_id"],validated["draft_element_id"])
        self.assertNotIn("academic_approval",result[0])
        self.assertNotIn("tts_authorized",result[0])

    def test_real_serway_rich_math_proofs_are_unique_and_never_paid(self):
        folder=(Path.home()/"AppData"/"Local"/"MicroGen_AI_Web_Checkpoints"
                /"20261112_PR528_G2_SERWAY6_4_NARRATION_SOURCE_REUSE_V7"
                /"source_tree"/"6"/"6.4")
        if not (folder/"source.pdf").is_file():
            self.skipTest("Authentic original Serway 6.4 only on Dell-115")
        report=propose(source_pdf=folder/"source.pdf",
                       slides_pdf=folder/"slides.pdf",
                       script_txt=folder/"script.txt")
        all_targets=[t for row in report["slides"]
                     for t in row["auto_candidate_targets"]]
        math=[t for t in all_targets if t["kind"]=="math_row_group"]
        proven=[t for t in math
                if t.get("original_math_block_hashes_verified") is True]
        self.assertEqual(len(math),12)
        self.assertEqual(len(proven),11)
        self.assertEqual(len(all_targets),120)
        self.assertEqual(len({t["draft_element_id"] for t in all_targets}),
                         len(all_targets))
        self.assertEqual(report["utterance_count"],74)
        self.assertEqual(report["ambiguous_utterance_count"],41)
        self.assertEqual(MAPPING_DETECTOR_REVISION,5)
        self.assertFalse(report["can_stage_or_synthesize_audio"])
        self.assertFalse(report["academic_approval"])
        self.assertFalse(report["student_publication"])
        self.assertTrue(all(t.get("mathematical_semantics_verified") is False
                            for t in math))
        # A physically detectable-but-unsupported group must NOT influence
        # one-pass mathematical target ranking.
        unsupported=[t for t in math
                     if not t.get("original_math_block_hashes_verified")]
        self.assertEqual([x["draft_element_id"] for x in unsupported],
                         ["s012.math_row.003-004-005"])
        rows=report["slides"][11]["proposed_utterances"]
        for u in rows:
            self.assertFalse(any(r["draft_element_id"]==
                            unsupported[0]["draft_element_id"]
                            for r in u["candidate_target_rankings_unverified"]))


if __name__=="__main__":
    unittest.main()
