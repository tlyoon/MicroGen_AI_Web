"""Regression tests for half-column Beamer images."""
import unittest
from pathlib import Path
from selenium_pipeline.latex_graphics_bounds import bound_beamer_graphics

class BeamerGraphicBoundsTests(unittest.TestCase):
    def test_thomas_2_2_composite_figure_image(self):
        tex = r"""\begin{frame}{When Limits Fail to Exist}
\begin{columns}
\begin{column}{0.5\textwidth}
\item Jumps \item Oscillation
\end{column}
\begin{column}{0.5\textwidth}
\IfFileExists{Figure 2.10.png}{
\includegraphics[height=0.55\textheight,keepaspectratio]{Figure 2.10.png}
}{}
\end{column}
\end{columns}
\end{frame}"""
        result, count = bound_beamer_graphics(tex)
        self.assertEqual(count, 1)
        self.assertIn(r"width=\linewidth", result)
        self.assertIn(r"height=0.55\textheight", result)
        self.assertIn(r"{Figure 2.10.png}", result)
        self.assertIn(r"\IfFileExists{Figure 2.10.png}", result)
        twice, changes = bound_beamer_graphics(result)
        self.assertEqual(twice, result)
        self.assertEqual(changes, 0)

    def test_both_dimensions_added_to_optionless_image(self):
        result, count = bound_beamer_graphics(
            r"\begin{frame}{Example}\includegraphics{image.png}\end{frame}")
        self.assertEqual(count, 1)
        self.assertIn(r"width=\linewidth,height=0.65\textheight,keepaspectratio", result)

    def test_column_textwidth_clamped_to_local_linewidth(self):
        src = (r"\begin{frame}{F}\begin{column}{0.4\textwidth}"
               r"\includegraphics[width=0.9\textwidth,height=0.4\textheight]{x.png}"
               r"\end{column}\end{frame}")
        result, count = bound_beamer_graphics(src)
        self.assertEqual(count, 1)
        self.assertIn(r"width=\linewidth,height=0.4\textheight,keepaspectratio", result)

    def test_preserve_existing_safe_graphic_and_tex_outside_frames(self):
        existing = r"\includegraphics[width=\linewidth,height=0.4\textheight,keepaspectratio]{p.png}"
        result, count = bound_beamer_graphics(
            r"\newcommand{\mygraphic}{}" + "\n" +
            r"\begin{frame}{F}" + existing + r"\end{frame}")
        self.assertEqual(count, 0)
        self.assertIn(existing, result)

    def test_comment_only_graphic_not_changed(self):
        tex = "\\begin{frame}{F}\n% " + r"\includegraphics{bad.png}" + "\n" + r"\end{frame}"
        result, count = bound_beamer_graphics(tex)
        self.assertEqual((result, count), (tex, 0))

    def test_unknown_option_preserved(self):
        tex = r"\begin{frame}{F}\includegraphics[angle=90]{a.png}\end{frame}"
        result, count = bound_beamer_graphics(tex)
        self.assertEqual(count, 1)
        self.assertIn("angle=90", result)

    def test_integration_hook_runs_before_sanity_compile(self):
        vendor = Path(__file__).resolve().parents[1] / (
            "selenium_pipeline/vendor_template_v2/gen_slides_selenium_v11.py")
        source = vendor.read_text(encoding="utf-8")
        i_bound = source.index("latex, bounded_count = bound_beamer_graphics(latex)")
        i_sanity = source.index("sanity_ok, sanity_reasons = beamer_stack_sanity_check(", i_bound)
        self.assertLess(i_bound, i_sanity)

if __name__ == "__main__":
    unittest.main()
