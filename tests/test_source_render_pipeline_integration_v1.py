"""Normal pipeline integration and disabled recovery-registry fault injection."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz

from selenium_pipeline import runner
from selenium_pipeline.figure_recovery_registry_v1 import lookup_mechanism
from selenium_pipeline.output_paths import publish_stage_outputs


class NormalSourceFigureChainIntegrationTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.job=self.root/"job"
        self.job.mkdir()
        doc=fitz.open()
        page=doc.new_page(width=612,height=792)
        page.draw_rect(fitz.Rect(75,75,140,200),fill=(0,0,1))
        page.insert_text((30,250),"Figure 8.2 falling book",fontname="hebo")
        doc.save(self.job/"source.pdf")
        doc.close()
        deck=fitz.open()
        deck.new_page(width=612,height=792)
        deck.save(self.job/"slides.pdf")
        deck.close()
        # The normal slides gate now requires the production default Beamer
        # preamble, even when this test isolates the rendered-figure verifier.
        self.job.joinpath("slides.tex").write_text(
            r"""\documentclass[10.5pt]{beamer}
\usetheme{Madrid}
\setbeamertemplate{frametitle}[default]
\definecolor{lightblue}{RGB}{173,216,230}
\setbeamercolor{frametitle}{bg=lightblue, fg=black}
\setbeamertemplate{headline}{%
    \hfill%
    \insertframenumber{} / \inserttotalframenumber%
    \par%
}
\setbeamertemplate{footline}{}
\usepackage{graphicx}
\title{Test Figure}
\author{}
\date{}
\begin{document}
\begin{frame}{Figure}
\includegraphics{Figure 8.2.png}
\end{frame}
\end{document}
""", encoding="utf8")

    def test_normal_slide_gate_calls_rendered_pixel_verifier(self):
        with patch(
            "selenium_pipeline.source_caption_figure_chain_v1.verify_rendered_pdf_source_figures",
            return_value={"status":"PASS"}
        ) as check:
            self.assertTrue(runner.valid("slides",self.job))
            check.assert_called_once_with(self.job)

    def test_normal_slide_gate_rejects_bad_appearance(self):
        with patch(
            "selenium_pipeline.source_caption_figure_chain_v1.verify_rendered_pdf_source_figures",
            side_effect=ValueError("RASTER_OCCLUDED_OR_ALTERED")
        ):
            self.assertFalse(runner.valid("slides",self.job))

    def test_source_registry_disabled_means_fail_closed(self):
        registry=self.root/"registry.json"
        entry={
          "match_type":"source_figure_recovery",
          "signature":"FIGURE_CAPTIONED_VECTOR_OR_COMPOSITE_CROP_MISSING",
          "mechanism":"GENERATE_SOURCE_BOUND_HYBRID_CROPS_VERIFY_PANELS_THEN_ATOMIC_PROMOTION",
          "handler":"NORMAL_FIGURES_STAGE_ORIGINAL_SOURCE_HYBRID_CROP_POST_MAPPING",
          "attempt_limit":2,
          "enabled":False,
        }
        registry.write_text(json.dumps({
            "schema_version":1,
            "status":"SOURCE_FIGURE_EXECUTABLE_RECOVERY_REGISTRY_V1",
            "entries":[entry],
        }),encoding="utf8")
        with self.assertRaisesRegex(ValueError,"Unregistered/disabled"):
            lookup_mechanism(entry["match_type"],entry["signature"],path=registry)

    def test_commented_latex_reference_is_not_figure_coverage(self):
        from selenium_pipeline.source_caption_figure_chain_v1 import (
            missing_required_latex_figures)
        required=["Figure 8.2.png"]
        commented=r"% \\includegraphics{Figure 8.2.png}"
        self.assertEqual(
            missing_required_latex_figures(commented,required)["missing"],
            required)

    def test_figures_output_publishes_evidence_ledger(self):
        original=self.root/"published"; original.mkdir()
        (original/"source.pdf").write_bytes((self.job/"source.pdf").read_bytes())
        (self.job/"source_figure_chain_v1.json").write_text(
           '{"source_sha256":"unit-fixture"}',encoding="utf8")
        outputs=publish_stage_outputs(self.job,original/"source.pdf","figures")
        self.assertIn(original/"source_figure_chain_v1.json",outputs)
        self.assertTrue((original/"source_figure_chain_v1.json").is_file())


if __name__ == "__main__":
    unittest.main()
