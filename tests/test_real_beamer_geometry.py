"""Optional native Beamer integration: actual pdfLaTeX annotated regions and PDF cleanup."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from selenium_pipeline.pdf_element_geometry import (
    extract_element_geometry, strip_instrumentation_links,
)

BEAMER = r"""
\documentclass{beamer}
\hypersetup{hidelinks}
\newcommand{\MGElement}[2]{\href{microgen-element:#1}{#2}}
\begin{document}
\begin{frame}{Rendered geometry fixture}
\MGElement{part_01.s001.text01}{The acceleration is proportional to force.}
\medskip
\MGElement{part_01.s001.eq01}{$E=mc^2$}
\medskip
\MGElement{part_01.s001.fig01}{\rule{3cm}{1.2cm}}
\medskip
\MGElement{part_01.s001.multi01}{\parbox{4.5cm}{The first line here.\\The second line here.}}
\end{frame}
\end{document}
"""


@unittest.skipUnless(shutil.which("pdflatex"), "pdfLaTeX not installed on this CI host")
class RealBeamerGeometryTest(unittest.TestCase):
    def test_compiled_beamer_regions_and_exact_clean_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tex = root/"test.tex"
            tex.write_text(BEAMER, encoding="utf-8")
            for _ in range(2):
                r = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
                     f"-output-directory={root}", str(tex)],
                    cwd=root, capture_output=True, text=True, timeout=55,
                )
                self.assertEqual(r.returncode, 0, r.stdout[-2000:]+r.stderr[-1000:])
            pdf = root/"test.pdf"
            ids=["text01","eq01","fig01","multi01"]
            board={"slides":[{"slide_id":"part_01.s001","elements":[
                {"element_id":f"part_01.s001.{id}"} for id in ids
            ]}]}
            geo=extract_element_geometry(pdf,board)
            self.assertEqual(len(geo["elements"]),4)
            self.assertGreater(
                next(x for x in geo["elements"] if x["element_id"].endswith("fig01"))["rect_pt"][2]
                -next(x for x in geo["elements"] if x["element_id"].endswith("fig01"))["rect_pt"][0], 80
            )
            clean=strip_instrumentation_links(pdf,root/"clean.pdf",geo)
            self.assertEqual(clean["removed_instrumentation_links"],4)
            self.assertTrue(clean["all_annotations_removed"])


if __name__ == "__main__":
    unittest.main()
