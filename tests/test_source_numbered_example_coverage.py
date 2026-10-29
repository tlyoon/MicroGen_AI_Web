import tempfile,unittest
from pathlib import Path
import pymupdf
from selenium_pipeline.source_numbered_example_coverage import (
    original_examples,audit_latex_example_coverage,require_coverage,
    feedback,ExampleCoverageError)
from selenium_pipeline import runner

class RealSourceExampleCoverage(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory()
  self.addCleanup(self.t.cleanup)
  self.root=Path(self.t.name)
  self.source=self.root/"source.pdf"
  with pymupdf.open() as pdf:
   p=pdf.new_page()
   p.insert_text((72,72),"EXAMPLE 1 Evaluate integral.")
   p.insert_text((72,92),"EXAMPLE 2 Inverse hyperbolic sine.")
   p.insert_text((72,112),"EXAMPLE 3 Sine substitution.")
   p.insert_text((72,132),"EXAMPLE 4 Secant substitution.")
   pdf.save(self.source)
  self.latex=r"""\documentclass{beamer}
 \begin{frame}{Outline}Comprehensive Worked Examples (Examples 1 to 4)\end{frame}
 \begin{frame}{Example 1: Tangent}\end{frame}
 \begin{frame}{Example 3: Sine}\end{frame}
 \begin{frame}{Example 4: Secant}\end{frame}
 \end{document}"""
 def test_detects_missing_source_example_2_before_paid_tts(self):
  report=audit_latex_example_coverage(source_pdf=self.source,slides_tex=self.latex)
  self.assertEqual(report["source_examples"],[1,2,3,4])
  self.assertEqual(report["missing_promised_source_examples"],[2])
  self.assertFalse(report["ready_for_paid_TTS"])
  self.assertIn("Example 2",feedback(report))
 def test_title_not_figure_reference(self):
  bogus=self.latex.replace(r"\begin{frame}{Example 3: Sine}",
      r"\begin{frame}{Figure 8.5: Example 3}")
  report=audit_latex_example_coverage(source_pdf=self.source,slides_tex=bogus)
  self.assertEqual(report["missing_promised_source_examples"],[2,3])
 def test_corrected_example_2_passes(self):
  full=self.latex.replace(r"\begin{frame}{Example 3: Sine}",
      r"\begin{frame}{Example 2: Inverse hyperbolic sine} Worked from source."
      r"\end{frame}\begin{frame}{Example 3: Sine}")
  report=audit_latex_example_coverage(source_pdf=self.source,slides_tex=full)
  self.assertTrue(report["coverage_pass"])
  self.assertEqual(report["dedicated_worked_example_slide_titles"],[1,2,3,4])
 def test_unverified_promise_rejected(self):
  fake=self.latex.replace("Examples 1 to 4","Examples 1 to 5")
  report=audit_latex_example_coverage(source_pdf=self.source,slides_tex=fake)
  self.assertIn(5,report["unsupported_promised_example_numbers"])
  self.assertFalse(report["coverage_pass"])
 def test_no_numbered_claim_no_false_gate(self):
  n=self.latex.replace("Examples 1 to 4","Selected examples")
  report=audit_latex_example_coverage(source_pdf=self.source,slides_tex=n)
  self.assertTrue(report["coverage_pass"])
 def test_source_tex_missing_rejected(self):
  with self.assertRaises(ExampleCoverageError):
   require_coverage(source_pdf=self.source,latex_path=self.root/"none.tex")
 def test_rendered_source_guard_is_used_by_runner(self):
  from pathlib import Path
  source=Path(runner.__file__).read_text(encoding="utf8")
  self.assertIn("require_coverage",source)
  self.assertIn('if stage in {"narration", "tts", "tts_qa"}',source)

if __name__=="__main__":unittest.main()
