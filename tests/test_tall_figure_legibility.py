"""Regression: Thomas 8.4 Figure 8.3 is complete but too small to read."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from selenium_pipeline.figure_legibility import (
    audit_wide_figure_legibility,legibility_retry_instruction
)

TALL = r"""
\begin{frame}{Reversibility and Domain Restrictions}
\begin{itemize}
\item $u=\tan^{-1}(x/a)$
\item $u=\sin^{-1}(x/a)$
\item $u=\sec^{-1}(x/a)$
\end{itemize}
\IfFileExists{Figure 8.3.png}{%
\begin{figure}
\centering
\includegraphics[height=0.23\textheight,keepaspectratio]{Figure 8.3.png}
\end{figure}
}{}
\end{frame}
"""
HORIZONTAL=TALL.replace(
    "Figure 8.3.png","Figure 8.3 horizontal.png"
).replace(
    r"height=0.23\textheight,keepaspectratio",
    r"width=0.92\textwidth,height=0.37\textheight,keepaspectratio"
)

class TallGraphLegibilityTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        Image.new("RGB",(232,480),"white").save(self.root/"Figure 8.3.png")
        Image.new("RGB",(762,204),"white").save(self.root/"Figure 8.3 horizontal.png")

    def test_actual_fig83_layout_must_be_rejected(self):
        issues=audit_wide_figure_legibility(TALL,self.root)
        self.assertEqual(len(issues),1)
        issue=issues[0]
        self.assertEqual(issue["reason"],"tall_figure_squeezed_by_height")
        self.assertEqual(issue["frame"],1)
        self.assertEqual(issue["image"],"Figure 8.3.png")
        self.assertEqual(issue["image_pixels"],[232,480])
        self.assertAlmostEqual(issue["height_fraction"],0.23)
        self.assertLess(issue["estimated_frame_width_fraction"],0.10)
        guidance=legibility_retry_instruction(issues)
        self.assertIn("reflow complete panels side by side",guidance)
        self.assertIn("every complete source panel",guidance)

    def test_horizontal_readable_candidate_passes(self):
        self.assertEqual(audit_wide_figure_legibility(HORIZONTAL,self.root),[])

    def test_small_icon_allowed(self):
        Image.new("RGB",(50,150),"white").save(self.root/"icon.png")
        self.assertEqual(audit_wide_figure_legibility(
            TALL.replace("Figure 8.3.png","icon.png"),self.root),[])

    def test_large_height_cap_allowed(self):
        self.assertEqual(audit_wide_figure_legibility(
            TALL.replace(r"height=0.23\textheight",
                         r"height=0.48\textheight"),self.root),[])

    def test_existing_wide_gate_unchanged(self):
        Image.new("RGB",(784,234),"white").save(self.root/"wide.png")
        code=TALL.replace("Figure 8.3.png","wide.png").replace(
            r"height=0.23\textheight,keepaspectratio",
            r"width=0.3\textwidth,keepaspectratio")
        issues=audit_wide_figure_legibility(code,self.root)
        self.assertEqual(len(issues),1)
        self.assertEqual(issues[0]["reason"],"wide_figure_too_small")

    def test_wide_height_only_reference_strip_not_false_positive(self):
        # The adjacent 8.4 Figure 8.2 is a 3-panel strip and already uses
        # height-only placement spanning roughly 55% of the slide width.
        Image.new("RGB",(412,135),"white").save(self.root/"Figure 8.2.png")
        code=TALL.replace("Figure 8.3.png","Figure 8.2.png").replace(
            r"height=0.23\textheight",r"height=0.25\textheight")
        self.assertEqual(audit_wide_figure_legibility(code,self.root),[])

    def test_unreadably_tiny_wide_height_only_still_rejected(self):
        Image.new("RGB",(412,135),"white").save(self.root/"Figure 8.2.png")
        code=TALL.replace("Figure 8.3.png","Figure 8.2.png").replace(
            r"height=0.23\textheight",r"height=0.10\textheight")
        issues=audit_wide_figure_legibility(code,self.root)
        self.assertEqual(len(issues),1)
        self.assertEqual(issues[0]["reason"],"wide_figure_too_small")

    def test_explicit_portrait_width_in_normal_frame_allowed(self):
        code=TALL.replace(r"height=0.23\textheight,keepaspectratio",
                          r"width=0.4\textwidth,keepaspectratio")
        self.assertEqual(audit_wide_figure_legibility(code,self.root),[])

    def test_comment_does_not_count_as_graphic(self):
        code=TALL.replace(r"\includegraphics",r"% \includegraphics")
        self.assertEqual(audit_wide_figure_legibility(code,self.root),[])

if __name__=="__main__":
    unittest.main()
