"""RFH Phase 3C: wide figures must not be accepted unreadably small."""
from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from PIL import Image

from selenium_pipeline.figure_legibility import (
    audit_wide_figure_legibility, legibility_retry_instruction,
)
from selenium_pipeline.runner import STAGES, invalidate_downstream

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "selenium_pipeline/vendor_template_v2/gen_slides_selenium_v11.py"
FIRST = r"""
\documentclass{beamer}
\begin{document}
\begin{frame}{When Limits Fail to Exist}
The three different situations are jumps, growth and oscillation.
\begin{columns}
\begin{column}{0.5\textwidth}
\begin{itemize}
\item Jumps
\item Unbounded growth
\item Oscillation
\end{itemize}
\end{column}
\begin{column}{0.5\textwidth}
\includegraphics[height=0.55\textheight,keepaspectratio]{Figure 2.10.png}
\end{column}
\end{columns}
\end{frame}
\end{document}
"""
REDESIGNED = r"""
\documentclass{beamer}
\begin{document}
\begin{frame}{When Limits Fail to Exist}
The three different situations are jumps, growth and oscillation.
\begin{itemize}\item Jumps \item Unbounded growth \item Oscillation\end{itemize}
\end{frame}
\begin{frame}{Three Examples: Figure 2.10}
\centering
\includegraphics[width=0.9\textwidth,height=0.6\textheight,keepaspectratio]{Figure 2.10.png}
\end{frame}
\end{document}
"""

class FigureLegibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        Image.new("RGB", (784, 234), "white").save(self.folder/"Figure 2.10.png")

    def test_thomas_2_2_column_figure_needs_full_width(self):
        from selenium_pipeline.latex_graphics_bounds import bound_beamer_graphics
        bounded, _ = bound_beamer_graphics(FIRST)
        issues = audit_wide_figure_legibility(bounded, self.folder)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["reason"], "wide_figure_too_small_in_column")
        self.assertAlmostEqual(issues[0]["aspect_ratio"], 784/234, delta=0.001)
        self.assertEqual(issues[0]["column_width_fraction"], 0.5)

    def test_dedicated_figure_frame_passes(self):
        self.assertEqual(audit_wide_figure_legibility(REDESIGNED,self.folder), [])

    def test_small_nonwide_figure_does_not_trigger(self):
        Image.new("RGB", (120, 200), "white").save(self.folder/"narrow.png")
        alternate=FIRST.replace("Figure 2.10.png","narrow.png")
        self.assertEqual(audit_wide_figure_legibility(alternate,self.folder), [])

    def test_feedback_is_specific_and_preserves_source_fidelity(self):
        message = legibility_retry_instruction(
            audit_wide_figure_legibility(FIRST, self.folder))
        self.assertIn("Figure 2.10.png",message)
        self.assertIn("full-width",message)
        self.assertIn("all scientific statements",message)

    def test_unreadable_image_is_not_certified(self):
        (self.folder/"Figure 2.10.png").write_bytes(b"not a real PNG")
        issues=audit_wide_figure_legibility(FIRST,self.folder)
        self.assertEqual(issues[0]["reason"],"unreadable_figure")

    def test_commented_figure_not_counted(self):
        source=FIRST.replace(r"\includegraphics",r"% \includegraphics")
        self.assertEqual(audit_wide_figure_legibility(source,self.folder), [])

    def test_full_width_frame_with_tiny_explicit_width_is_rejected(self):
        source=REDESIGNED.replace(r"width=0.9\textwidth",r"width=0.35\textwidth")
        issues=audit_wide_figure_legibility(source,self.folder)
        self.assertEqual(issues[0]["reason"],"wide_figure_too_small")
        self.assertEqual(issues[0]["effective_width_fraction"],0.35)

    def test_full_width_column_is_not_a_narrow_column(self):
        source=FIRST.replace(r"\begin{column}{0.5\textwidth}",
                             r"\begin{column}{\textwidth}")
        from selenium_pipeline.latex_graphics_bounds import bound_beamer_graphics
        bounded, _ = bound_beamer_graphics(source)
        self.assertEqual(audit_wide_figure_legibility(bounded,self.folder),[])

    def _vendor_generator(self):
        tree=ast.parse(VENDOR.read_text(encoding="utf-8-sig"))
        node=next(n for n in tree.body
                  if isinstance(n, ast.FunctionDef) and n.name=="generate_slides_tex")
        compiled=compile(ast.fix_missing_locations(
            ast.Module(body=[node],type_ignores=[])),str(VENDOR),"exec")
        import os
        ns={
            "Path":Path, "os":os, "log":lambda *args,**kwargs:None,
            "find_citation_artifacts":lambda text:[],
            "sanitize_gemini_latex_response":lambda text:text,
            "normalize_unicode_to_latex":lambda text:text,
            "beamer_stack_sanity_check":lambda text,folder,**kwargs:(
                text.count(r"\begin{frame}")>=1,[]),
        }
        exec(compiled,ns)
        return ns["generate_slides_tex"]

    def _run(self, replies):
        generator=self._vendor_generator()
        calls=[]
        plan=[
            SimpleNamespace(backend=SimpleNamespace(value="selenium"))
            for _ in replies
        ]
        def reply(backend,instruction):
            calls.append((backend,instruction))
            return replies[len(calls)-1]
        for name in ("source.pdf","prompt.txt","png_dimensions.json"):
            (self.folder/name).write_text("fixture")
        output=self.folder/"slides.tex"
        try:
            result=generator(None,self.folder/"source.pdf",
                self.folder/"prompt.txt",self.folder/"png_dimensions.json",
                output,30,response_provider=reply,communication_plan=plan)
        except RuntimeError as error:
            return error,calls,output
        return result,calls,output

    def test_actual_generator_retries_specific_full_width_redesign(self):
        _, calls, output = self._run([FIRST,REDESIGNED])
        self.assertEqual(len(calls),2)
        self.assertIn("LEGIBILITY CORRECTION",calls[1][1])
        self.assertNotIn("LEGIBILITY CORRECTION",calls[0][1])
        self.assertEqual(output.read_text().count(r"\begin{frame}"),2)
        self.assertTrue((self.folder/"slides_attempt_1_failed_legibility.json").is_file())
        report=json.loads((self.folder/"slides_attempt_1_failed_legibility.json").read_text())
        self.assertEqual(report["status"],"review_required")
        self.assertTrue("Jumps" in output.read_text())
        self.assertTrue("Figure 2.10.png" in output.read_text())

    def test_all_bad_candidates_fail_without_accepted_slide(self):
        error,calls,output=self._run([FIRST,FIRST])
        self.assertIsInstance(error,RuntimeError)
        self.assertFalse(output.exists())
        self.assertEqual(len(calls),2)
        self.assertTrue((self.folder/"slides_attempt_2_failed_legibility.json").exists())

    def test_added_slide_invalidates_downstream_narration_video(self):
        from selenium_pipeline.slide_narration_sync import inspect
        import pymupdf
        import wave
        slides=self.folder/"slides.pdf"
        doc=pymupdf.open()
        for label in ("Explanation","Figure 2.10: all panels"):
            doc.new_page().insert_text((72,72),label)
        doc.save(slides)
        doc.close()
        (self.folder/"script.txt").write_text("**Slide 1 [10 sec]:\nOld narration**")
        with wave.open(str(self.folder/"slide1.wav"),"wb") as wav:
            wav.setnchannels(1);wav.setsampwidth(2)
            wav.setframerate(8000);wav.writeframes(b"\0\0"*8000)
        with self.assertRaisesRegex(ValueError,"count mismatch"):
            inspect(self.folder)
        state={"completed":{stage:{"model":"old"} for stage in STAGES}}
        invalidated=invalidate_downstream(state,"slides")
        self.assertIn("narration",invalidated)
        self.assertIn("tts_qa",invalidated)
        self.assertIn("video",invalidated)
        self.assertNotIn("video",state["completed"])
        self.assertIn("slides",state["completed"])


if __name__=="__main__":
    unittest.main()
