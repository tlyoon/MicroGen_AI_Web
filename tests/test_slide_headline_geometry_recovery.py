"""Beamer slide-counter repairs: physical PDF evidence, not scientific QA."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pymupdf

from selenium_pipeline.slide_headline_geometry_recovery import (
    LEGACY_HEADLINE, SAFE_HEADLINE, normalize_legacy_headline,
    verify_slide_counter_pdf)
from selenium_pipeline.academic_visual_preflight import inspect


OLD=(
    "\\documentclass{beamer}\n"
    "\\setbeamertemplate{headline}{%\n"
    "  \\hfill%\n"
    "  \\insertframenumber{} / \\inserttotalframenumber%\n"
    "  \\par%\n"
    "}\n"
    "\\begin{document}\n"
    "\\begin{frame}{Physics}\n$x = at^2$\n\\end{frame}\n"
    "\\end{document}\n"
)

class SlideHeadlineGeometryTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)

    def pdf(self, counters,*,top=20,right=54):
        file=self.root/(f"case_{len(list(self.root.glob('case*.pdf')))}.pdf")
        doc=pymupdf.open()
        for counter in counters:
            page=doc.new_page(width=400,height=300)
            page.insert_text((400-right,top),counter,fontsize=8)
            page.insert_text((45,95),"Original physics statement",fontsize=12)
        doc.save(file)
        doc.close()
        return file

    def test_legacy_repaired_without_touching_frame_body(self):
        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value="INSET_BEAMER_COUNTER_TWO_PASS_PHYSICAL_PROOF"):
            fixed,status=normalize_legacy_headline(OLD)
        self.assertEqual(status,"KNOWN_LEGACY_HEADLINE_RECOVERED")
        self.assertIn(SAFE_HEADLINE,fixed)
        self.assertEqual(fixed.replace(SAFE_HEADLINE,
                         LEGACY_HEADLINE.search(OLD).group(),1),OLD)
        self.assertIn("$x = at^2$",fixed)

    def test_safely_canonicalize_prompt_indentation_and_idempotent(self):
        variant=SAFE_HEADLINE.replace("  \\vskip7pt", "    \\vskip7pt")
        fixed,status=normalize_legacy_headline(variant+" contents")
        self.assertEqual(status,"SAFE_HEADLINE_CANONICALIZED")
        self.assertEqual(fixed,SAFE_HEADLINE+" contents")
        self.assertEqual(normalize_legacy_headline(fixed),
                         (fixed,"ALREADY_SAFE_HEADLINE"))

    def test_all_production_prompt_templates_use_verified_inset_counter(self):
        root=Path(__file__).resolve().parents[1]
        for relative in (
            "gen_slides_prompt_v19.txt",
            "gen_slides_prompt_v20_hybrid.txt",
            "selenium_pipeline/vendor_template_v2/gen_slides_prompt_v23.txt",
        ):
            with self.subTest(relative=relative):
                contents=(root/relative).read_text(encoding="utf8")
                normalized,status=normalize_legacy_headline(contents)
                self.assertIn(status,("SAFE_HEADLINE_CANONICALIZED",
                                      "ALREADY_SAFE_HEADLINE"))
                self.assertIn(SAFE_HEADLINE,normalized)

    def test_unknown_or_repeated_headline_not_guessed(self):
        unchanged="\\documentclass{beamer}\\begin{document}Physics"
        self.assertEqual(normalize_legacy_headline(unchanged),
                         (unchanged,"NO_RECOGNIZED_LEGACY_HEADLINE"))
        with self.assertRaisesRegex(ValueError,"Multiple legacy"):
            normalize_legacy_headline(OLD+OLD)
        with self.assertRaisesRegex(ValueError,"Ambiguous"):
            normalize_legacy_headline(SAFE_HEADLINE+OLD)

    def test_registry_disables_legacy_repair_without_bypassing_qa(self):
        with patch("selenium_pipeline.recovery_registry.lookup_mechanism",
                   return_value=None):
            with self.assertRaisesRegex(ValueError,"not registered"):
                normalize_legacy_headline(OLD)

    def test_actual_inset_correct_pdf_passes_without_science_claims(self):
        f=self.pdf(["1 / 2","2 / 2"])
        verified=verify_slide_counter_pdf(f)
        self.assertEqual(verified["slide_count"],2)
        self.assertFalse(verified["mathematics_approved"])
        self.assertFalse(verified["student_publication_authorized"])
        inspection=inspect(f)
        self.assertEqual(inspection["blocker_count"],0)
        self.assertEqual(inspection["counts"]["clipped_or_wrong_slide_counters"],0)

    def test_wrong_total_cannot_be_accepted_even_when_not_clipped(self):
        f=self.pdf(["1 / 1","2 / 1"])
        with self.assertRaisesRegex(ValueError,"unique correct"):
            verify_slide_counter_pdf(f)
        r=inspect(f)
        self.assertEqual(r["blocker_count"],2)
        self.assertEqual(r["counts"]["clipped_or_wrong_slide_counters"],2)
        self.assertFalse(r["mathematical_correctness_verified"])

    def test_top_edge_counter_is_proven_clipped(self):
        f=self.pdf(["1 / 2","2 / 2"],top=6)
        with self.assertRaisesRegex(ValueError,"touches/crosses"):
            verify_slide_counter_pdf(f)
        # A partly outside-page string may be omitted by the generic PDF
        # extractor. The strict source-aware counter presence gate is the
        # acceptance authority and reliably rejects the missing glyphs.
        r=inspect(f)
        self.assertFalse(r["mathematical_correctness_verified"])

    def test_right_edge_counter_is_proven_clipped(self):
        f=self.pdf(["1 / 2","2 / 2"],right=15)
        with self.assertRaisesRegex(ValueError,"touches/crosses"):
            verify_slide_counter_pdf(f)
        # The far-right counter is partly outside the PDF crop box and
        # can disappear from text extraction entirely. The strict counter
        # presence gate detects that; generic preflight must not invent it.
        r=inspect(f)
        self.assertFalse(r["mathematical_correctness_verified"])

    def test_missing_counter_not_invented(self):
        f=self.pdf(["ordinary header","another header"])
        with self.assertRaisesRegex(ValueError,"unique correct"):
            verify_slide_counter_pdf(f)
        # A document without the old numbered headline is not corrupted
        # just because it chooses to omit page counters.
        r=inspect(f)
        self.assertEqual(r["counts"]["clipped_or_wrong_slide_counters"],0)

if __name__=="__main__":
    unittest.main()
