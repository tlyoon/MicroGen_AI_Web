"""Actual text-span PDF geometry, never a model/science acceptance."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
import pymupdf

from selenium_pipeline.physical_fraction_review_targets import (
    physical_fraction_review_targets)
from selenium_pipeline.element_plan_autodraft import stable_recommendations


class PhysicalFractionReviewTargetTests(unittest.TestCase):
    def create(self,kind="both"):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        f=Path(tmp.name)/"slide.pdf"
        doc=pymupdf.open()
        page=doc.new_page(width=400,height=300)
        if kind in ("both","half"):
            page.insert_text((100,100),"1",fontsize=8)
            page.insert_text((100,111),"2",fontsize=8)
        if kind in ("both","square","wrong-exponent","no-exponent"):
            page.insert_text((160,150),"L",fontsize=11)
            page.insert_text((160,169),"T",fontsize=11)
            if kind!="no-exponent":
                page.insert_text((168.5,164),
                                 "3" if kind=="wrong-exponent" else "2",
                                 fontsize=8)
        if kind=="swapped":
            page.insert_text((100,100),"2",fontsize=8)
            page.insert_text((100,111),"1",fontsize=8)
        if kind=="far":
            page.insert_text((100,100),"1",fontsize=8)
            page.insert_text((180,111),"2",fontsize=8)
        doc.save(f);doc.close()
        return f

    def scan(self,path,slide=1):
        with pymupdf.open(path) as doc:
            return physical_fraction_review_targets(doc[0],slide)

    def test_physical_two_distinct_fractions_with_no_semantic_approval(self):
        rows=self.scan(self.create())
        self.assertEqual({x["visible_text"] for x in rows},
                         {"1/2","L/T^2"})
        self.assertEqual(len(rows),2)
        for item in rows:
            self.assertTrue(item["original_pdf_fraction_geometry_verified"])
            self.assertFalse(item["mathematical_semantics_verified"])
            self.assertTrue(item["independent_fraction_meaning_review_required"])
            self.assertEqual(item["anchor"]["type"],"physical_fraction_spans")
            self.assertEqual(len(item["anchor"]["fraction_spans_sha256"]),64)
            self.assertFalse(item["anchor"]["math_semantics_verified"])
            self.assertNotIn("TTS_authorized",item)
            self.assertEqual(item["kind"],"math_fraction_review")

    def test_original_spoken_math_is_review_ranked_not_semantically_approved(self):
        rows=self.scan(self.create())
        half=stable_recommendations(
            "The number one half is dimensionless.", rows)
        ratio=stable_recommendations(
            "The dimension of acceleration is length divided by time squared.",
            rows)
        self.assertEqual(len(half),1)
        self.assertEqual(len(ratio),1)
        self.assertIn("fraction",half[0]["draft_element_id"])
        self.assertIn("fraction",ratio[0]["draft_element_id"])
        self.assertGreaterEqual(half[0]["overlap_hint"],.9)
        self.assertGreaterEqual(ratio[0]["overlap_hint"],.9)
        self.assertNotIn("academic_approval",half[0])

    def test_wrong_glyph_order_missing_exponent_and_far_layout_denied(self):
        for kind in ("swapped","far","wrong-exponent","no-exponent"):
            with self.subTest(kind=kind):
                self.assertEqual(self.scan(self.create(kind)),[])

    def test_wrong_spoken_denominator_never_ranks_fraction(self):
        rows=self.scan(self.create())
        for speech in ("One third is dimensionless.",
                       "The acceleration is length divided by time.",
                       "Length divided by time cubed.",
                       "Time squared is not length divided by time squared."):
            with self.subTest(speech=speech):
                if "not" in speech:
                    # A negated claim requires semantic review, never a
                    # confidence claim from physical glyph arrangement.
                    self.assertFalse(any(
                        x.get("academic_approval") is True
                        for x in stable_recommendations(speech,rows)))
                else:
                    self.assertEqual(stable_recommendations(speech,rows),[])

    def test_forged_fraction_review_target_without_origin_proof_denied(self):
        rows=self.scan(self.create("half"))
        f=dict(rows[0])
        f["original_pdf_fraction_geometry_verified"]=False
        self.assertEqual(stable_recommendations(
            "The number one half is dimensionless.",[f]),[])
        f=dict(rows[0])
        f["mathematical_semantics_verified"]=True
        self.assertEqual(stable_recommendations(
            "The number one half is dimensionless.",[f]),[])

    def test_no_other_spatial_pairing_or_invalid_slide_id(self):
        file=self.create("both")
        with pymupdf.open(file) as doc:
            with self.assertRaises(ValueError):
                physical_fraction_review_targets(doc[0],0)
            with self.assertRaises(ValueError):
                physical_fraction_review_targets(doc[0],"one")


if __name__=="__main__":
    unittest.main()
