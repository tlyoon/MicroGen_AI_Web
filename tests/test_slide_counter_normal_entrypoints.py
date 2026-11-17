"""Regression: known Beamer counter defect is never cache-adopted.

Two ordinary entrypoints: runner.valid and vendored generator's early-exit.
All tests are local, do not contact Gemini or modify any original source.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import pymupdf

from selenium_pipeline.runner import valid
from selenium_pipeline.runner_stage_artifact_evidence import (
    decide_stage_reuse,RunnerReuseError)
from selenium_pipeline.slide_headline_geometry_recovery import (
    LEGACY_HEADLINE,SAFE_HEADLINE,
    verify_existing_slide_counter_contract)

LEGACY=(
    "\\documentclass{beamer}\n"
    "\\setbeamertemplate{headline}{%\n"
    "  \\hfill%\n"
    "  \\insertframenumber{} / \\inserttotalframenumber%\n"
    "  \\par%\n"
    "}\n"
    "\\begin{document}\\begin{frame}Physics\\end{frame}\\end{document}\n"
)
SAFE=LEGACY.replace(LEGACY_HEADLINE.search(LEGACY).group(),SAFE_HEADLINE)
UNKNOWN="\\documentclass{beamer}\\begin{document}Text\\end{document}\n"

class ActualSlideEntrypointTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.work=self.root/"lecture"
        self.work.mkdir()
        self.checkpoint=self.root/"counter_checkpoint"
        self.checkpoint.mkdir()
        self.source=self.work/"source.pdf"
        doc=pymupdf.open()
        page=doc.new_page(width=400,height=300)
        page.insert_text((40,50),"Original physics textbook statement")
        doc.save(self.source)
        doc.close()
        self.tex=self.work/"slides.tex"
        self.pdf=self.work/"slides.pdf"

    def make_deck(self, tex, *, counters=("1 / 2","2 / 2"), x=335, y=20):
        self.tex.write_text(tex,encoding="utf8")
        doc=pymupdf.open()
        for value in counters:
            pg=doc.new_page(width=400,height=300)
            pg.insert_text((x,y),value,fontsize=8)
            pg.insert_text((40,90),"Physics content",fontsize=12)
        doc.save(self.pdf)
        doc.close()

    def generator_early_exit(self):
        root=Path(__file__).resolve().parents[1]
        script=root/"selenium_pipeline"/"vendor_template_v2"/"gen_slides_selenium_v11.py"
        env=os.environ.copy()
        env["PYTHONPATH"]=str(root)+os.pathsep+env.get("PYTHONPATH","")
        env["MICROGEN_COUNTER_CANDIDATE_WORK_ROOT"]=str(self.checkpoint)
        # Use the EXACT normal generator script in an isolated fixture
        # workspace. This has existing slide artifacts and never reaches
        # a model upload, prompt or Send.
        return subprocess.run(
            [sys.executable,str(script)],cwd=self.work,env=env,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=25)

    def test_known_correct_safe_deck_is_accepted_by_both_normal_entrypoints(self):
        self.make_deck(SAFE)
        x=verify_existing_slide_counter_contract(
            tex_file=self.tex,pdf_file=self.pdf)
        self.assertEqual(x["status"],
                         "KNOWN_SAFE_HEADLINE_AND_PHYSICAL_PDF_VERIFIED")
        self.assertFalse(x["source_tex_modified"])
        self.assertTrue(valid("slides",self.work))
        result=self.generator_early_exit()
        self.assertEqual(result.returncode,0,result.stdout[-2000:])
        self.assertEqual(self.tex.read_text("utf8"),SAFE)

    def test_previously_proven_legacy_header_must_not_be_cache_adopted(self):
        self.make_deck(LEGACY)
        old_tex=self.tex.read_bytes()
        old_pdf=self.pdf.read_bytes()
        self.assertFalse(valid("slides",self.work))
        with self.assertRaisesRegex(ValueError,"Known legacy Beamer"):
            verify_existing_slide_counter_contract(
                tex_file=self.tex,pdf_file=self.pdf)
        result=self.generator_early_exit()
        self.assertNotEqual(result.returncode,0)
        self.assertIn("Existing slides have unsafe known Beamer counter geometry",
                      result.stdout)
        self.assertEqual(self.tex.read_bytes(),old_tex)
        self.assertEqual(self.pdf.read_bytes(),old_pdf)

    def test_wrong_total_and_clipped_counter_fail_in_cached_runner_and_generator(self):
        for counters,x,y in (
                (("1 / 1","2 / 1"),335,20),
                (("1 / 2","2 / 2"),335,6),
                (("1 / 2","2 / 2"),390,20),
        ):
            with self.subTest(counters=counters,x=x,y=y):
                self.pdf.unlink(missing_ok=True)
                self.make_deck(SAFE,counters=counters,x=x,y=y)
                old_tex=self.tex.read_bytes()
                old_pdf=self.pdf.read_bytes()
                self.assertFalse(valid("slides",self.work))
                result=self.generator_early_exit()
                self.assertNotEqual(result.returncode,0)
                self.assertEqual(self.tex.read_bytes(),old_tex)
                self.assertEqual(self.pdf.read_bytes(),old_pdf)

    def test_stage_reuse_refuses_legacy_even_with_matching_model_and_bytes(self):
        self.make_deck(LEGACY)
        sha=hashlib.sha256(self.source.read_bytes()).hexdigest()
        with self.assertRaisesRegex(RunnerReuseError,
                                    "fails current technical validation"):
            decide_stage_reuse(
                folder=self.work,stage="slides",source_sha256=sha,
                accepted={"model":"gemini-3.8-flash"},
                model_stamp="gemini-3.8-flash",
                validity_passed=valid("slides",self.work))

    def test_proven_versioned_recovery_is_idempotent_and_detects_tampering(self):
        from shutil import which
        from selenium_pipeline.slide_headline_geometry_recovery import (
            recover_versioned_legacy_counter_deck,verify_slide_counter_pdf)
        if which("pdflatex") is None:
            self.skipTest("Native LaTeX unavailable")
        real_tex=LEGACY.replace(
            "\\begin{document}\\begin{frame}Physics\\end{frame}\\end{document}",
            "\\begin{document}\n\\begin{frame}{One}Physics\\end{frame}\n"
            "\\begin{frame}{Two}$x=vt$\\end{frame}\n\\end{document}")
        self.make_deck(real_tex)
        old=[self.tex.read_bytes(),self.pdf.read_bytes(),self.source.read_bytes()]
        first=recover_versioned_legacy_counter_deck(
            original_folder=self.work,checkpoint_root=self.checkpoint)
        self.assertEqual(first["status"],"VERSIONED_BEAMER_COUNTER_PDF_VERIFIED")
        self.assertEqual(first["original_page_count"],2)
        self.assertFalse(first["original_modified"])
        self.assertFalse(first["academic_approval"])
        self.assertEqual(first["new_model_requests"],0)
        self.assertEqual(verify_slide_counter_pdf(
            Path(first["candidate_pdf_path"]))["slide_count"],2)
        second=recover_versioned_legacy_counter_deck(
            original_folder=self.work,checkpoint_root=self.checkpoint)
        self.assertTrue(second["reused_verified_candidate"])
        self.assertEqual(first["candidate_pdf_sha256"],
                         second["candidate_pdf_sha256"])
        self.assertEqual([self.tex.read_bytes(),self.pdf.read_bytes(),
                          self.source.read_bytes()],old)
        Path(first["candidate_pdf_path"]).write_bytes(b"tampered candidate")
        with self.assertRaisesRegex(ValueError,"candidate content changed"):
            recover_versioned_legacy_counter_deck(
                original_folder=self.work,checkpoint_root=self.checkpoint)

    def test_recovered_deck_rejects_changed_figure_assets(self):
        from shutil import which
        from selenium_pipeline.slide_headline_geometry_recovery import (
            recover_versioned_legacy_counter_deck)
        if which("pdflatex") is None:
            self.skipTest("Native LaTeX unavailable")
        tex=LEGACY.replace(
            "\\begin{document}\\begin{frame}Physics\\end{frame}\\end{document}",
            "\\begin{document}\\begin{frame}{One}Physics\\end{frame}\n"
            "\\begin{frame}{Two}Work\\end{frame}\\end{document}")
        self.make_deck(tex)
        asset=self.work/"Figure test.png"
        asset.write_bytes(b"figure-original-bytes")
        first=recover_versioned_legacy_counter_deck(
            original_folder=self.work,checkpoint_root=self.checkpoint)
        self.assertTrue(first["reused_verified_candidate"])
        asset.write_bytes(b"figure-changed-bytes")
        with self.assertRaisesRegex(ValueError,"figure assets changed"):
            recover_versioned_legacy_counter_deck(
                original_folder=self.work,checkpoint_root=self.checkpoint)
        asset.write_bytes(b"figure-original-bytes")
        first_asset=Path(first["candidate_pdf_path"]).parent/asset.name
        first_asset.write_bytes(b"candidate-image-tampered")
        with self.assertRaisesRegex(ValueError,"figure assets changed"):
            recover_versioned_legacy_counter_deck(
                original_folder=self.work,checkpoint_root=self.checkpoint)

    def test_empty_torn_local_claim_recovered_without_model_send(self):
        from shutil import which
        from selenium_pipeline.slide_headline_geometry_recovery import (
            recover_versioned_legacy_counter_deck)
        from unittest.mock import patch
        if which("pdflatex") is None:
            self.skipTest("Native LaTeX unavailable")
        tex=LEGACY.replace(
            "\\begin{document}\\begin{frame}Physics\\end{frame}\\end{document}",
            "\\begin{document}\\begin{frame}{One}Physics\\end{frame}\n"
            "\\begin{frame}{Two}Work\\end{frame}\\end{document}")
        self.make_deck(tex)
        # Abort after mkdir while writing claim, leaving ONLY an empty dir.
        original_open=Path.open
        attempted={"count":0}
        def crash_once(path,*a,**kw):
            if (path.name=="claim.json" and path.parent.parent.name==
                    "beamer_counter_candidate_v1" and attempted["count"]==0):
                attempted["count"]+=1
                raise OSError("Injected process interruption before local claim")
            return original_open(path,*a,**kw)
        with patch.object(Path,"open",autospec=True,side_effect=crash_once):
            with self.assertRaisesRegex(OSError,"Injected process interruption"):
                recover_versioned_legacy_counter_deck(
                    original_folder=self.work,checkpoint_root=self.checkpoint)
        self.assertEqual(attempted["count"],1)
        repaired=recover_versioned_legacy_counter_deck(
            original_folder=self.work,checkpoint_root=self.checkpoint)
        self.assertEqual(repaired["status"],
                         "VERSIONED_BEAMER_COUNTER_PDF_VERIFIED")
        self.assertEqual(repaired["new_model_requests"],0)
        self.assertTrue(repaired["reused_verified_candidate"])

    def test_normal_generator_creates_verified_candidate_without_gemini(self):
        from shutil import which
        from selenium_pipeline.slide_headline_geometry_recovery import (
            verify_slide_counter_pdf)
        if which("pdflatex") is None:
            self.skipTest("Native LaTeX unavailable")
        real_tex=LEGACY.replace(
            "\\begin{document}\\begin{frame}Physics\\end{frame}\\end{document}",
            "\\begin{document}\n\\begin{frame}{One}Physics\\end{frame}\n"
            "\\begin{frame}{Two}$x=vt$\\end{frame}\n\\end{document}")
        self.make_deck(real_tex)
        before=[self.source.read_bytes(),self.tex.read_bytes(),
                self.pdf.read_bytes()]
        result=self.generator_early_exit()
        self.assertNotEqual(result.returncode,0)
        self.assertIn("Created/reused separately versioned",result.stdout)
        receipts=list(self.checkpoint.rglob("result.json"))
        self.assertEqual(len(receipts),1)
        import json
        saved=json.loads(receipts[0].read_text("utf8"))
        self.assertEqual(saved["status"],"VERSIONED_BEAMER_COUNTER_PDF_VERIFIED")
        candidate=receipts[0].parent/saved["candidate_relative_path"]/"slides.pdf"
        self.assertEqual(verify_slide_counter_pdf(candidate)["slide_count"],2)
        self.assertEqual(saved["new_model_requests"],0)
        self.assertFalse(saved["student_publication_authorized"])
        self.assertEqual(
            [self.source.read_bytes(),self.tex.read_bytes(),self.pdf.read_bytes()],
            before)

    def test_real_native_two_pass_candidate_repair_keeps_original_unchanged(self):
        from shutil import which
        from selenium_pipeline.slide_headline_geometry_recovery import (
            normalize_legacy_headline, verify_slide_counter_pdf)
        if which("pdflatex") is None:
            self.skipTest("Native LaTeX unavailable in this environment")
        actual_legacy=(
            LEGACY.replace(
                "\\begin{document}\\begin{frame}Physics\\end{frame}\\end{document}",
                "\\title{Counter test}\\begin{document}\n"
                "\\begin{frame}\\titlepage\\end{frame}\n"
                "\\begin{frame}{Physics} $x=vt$ \\end{frame}\n"
                "\\end{document}"))
        self.tex.write_text(actual_legacy,encoding="utf8")
        original=self.tex.read_bytes()
        normalized,action=normalize_legacy_headline(actual_legacy)
        self.assertEqual(action,"KNOWN_LEGACY_HEADLINE_RECOVERED")
        candidate=self.work/"isolated_counter_candidate"
        candidate.mkdir()
        rendered=candidate/"slides.tex"
        rendered.write_text(normalized,encoding="utf8")
        for passno in (1,2):
            run=subprocess.run(
                ["pdflatex","-interaction=nonstopmode","-halt-on-error",
                 "-no-shell-escape","slides.tex"],
                cwd=candidate,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                text=True,timeout=120)
            self.assertEqual(run.returncode,0,
                             f"native Beamer pass {passno} failed: "+run.stdout[-1600:])
        physical=verify_slide_counter_pdf(candidate/"slides.pdf")
        self.assertEqual(physical["slide_count"],2)
        self.assertTrue(valid("slides",candidate))
        self.assertEqual(self.tex.read_bytes(),original)

    def test_unknown_no_counter_layout_keeps_existing_scope(self):
        self.make_deck(UNKNOWN)
        x=verify_existing_slide_counter_contract(
            tex_file=self.tex,pdf_file=self.pdf)
        self.assertEqual(x["status"],
                         "NO_RECOGNIZED_MICROGEN_PAGE_COUNTER_LAYOUT")
        self.assertFalse(x["pdf_counter_geometry_verified"])
        self.assertTrue(valid("slides",self.work))
        self.assertEqual(self.generator_early_exit().returncode,0)

    def test_ambiguous_templates_are_rejected(self):
        self.make_deck(SAFE+LEGACY)
        self.assertFalse(valid("slides",self.work))

    def test_linked_slide_pdf_is_rejected_when_os_allows_symlinks(self):
        self.make_deck(SAFE)
        self.pdf.unlink()
        try:
            self.pdf.symlink_to(self.source)
        except (OSError, NotImplementedError):
            self.skipTest("Windows user has no filesystem symlink privilege")
        self.assertFalse(valid("slides",self.work))


if __name__=="__main__":
    unittest.main()
