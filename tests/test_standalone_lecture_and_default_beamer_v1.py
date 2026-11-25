"""Source-only teaching quality, original Beamer defaults, and standalone lecture QA.

No API calls, browser, remote credentials or paid model requests.
"""
from __future__ import annotations
from pathlib import Path
import pytest

from selenium_pipeline.vendor_template_v2.default_beamer_style_v1 import (
    default_style_errors,
)
from selenium_pipeline.vendor_template_v2.script_tts_risk import (
    analyze_script_text,
    source_reference_findings,
)

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "selenium_pipeline" / "vendor_template_v2"

BASE = r"""\documentclass[10.5pt]{beamer}
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
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{amsfonts}
\usepackage[utf8]{inputenc}
\usepackage{graphicx}
\usepackage{booktabs}
\title{Situations Involving Kinetic Friction}
\author{}
\date{}
\begin{document}
\begin{frame}\titlepage\end{frame}
\begin{frame}{Outline}Overview\end{frame}
\begin{frame}{Derivation}
\[\Delta K = W_{\mathrm{other}} - f_kd\]
\end{frame}
\end{document}
"""

def test_existing_default_look_is_authorized():
    assert default_style_errors(BASE) == []

@pytest.mark.parametrize("old,new", [
    (r"\documentclass[10.5pt]{beamer}", r"\documentclass[aspectratio=169,10pt]{beamer}"),
    (r"\usetheme{Madrid}", r"\usetheme{Berlin}"),
    ("bg=lightblue, fg=black", "bg=darkblue, fg=white"),
    (r"\setbeamertemplate{footline}{}", r"\setbeamertemplate{footline}{\insertframenumber}"),
    (r"\setbeamertemplate{headline}{%", r"\setbeamertemplate{headline}{%"),
])
def test_alternative_templates_fail(old, new):
    candidate = BASE.replace(old, new, 1)
    if old == new: candidate += r"\setbeamerfont{frametitle}{size=\Large}"
    assert default_style_errors(candidate)

def test_no_duplicate_global_style_override():
    assert default_style_errors(BASE.replace(
        r"\begin{document}", r"\definecolor{red}{RGB}{255,0,0}" + "\n" + r"\begin{document}"))
    assert default_style_errors(BASE.replace(
        r"\begin{document}", r"\setbeamercolor{title}{fg=red}" + "\n" + r"\begin{document}"))
    assert default_style_errors(BASE.replace(
        r"\begin{document}", r"\usecolortheme{whale}" + "\n" + r"\begin{document}"))

def test_source_not_mentioned_in_spoken_lecture():
    forbidden = [
        "The textbook explains why kinetic friction converts energy.",
        "According to the textbook, the spring reaches equilibrium.",
        "The textbook points out that the maximum speed is smaller.",
        "The source PDF explains the relation.",
        "According to the author, friction is constant.",
        "Serway says the friction term is positive.",
        "The book states that kinetic energy changes.",
        "On page 191 the derivation continues.",
        "In the source document, the figure illustrates the force.",
        "In the textbook we find the equation.",
    ]
    for sample in forbidden:
        assert any(x["kind"]=="external_source_reference" and x["severity"]=="blocking"
                   for x in source_reference_findings(sample, slide=2)), sample

def test_physical_book_and_visible_diagram_are_not_external_citations():
    allowed = [
        "The book slides across the rough table while friction slows it.",
        "The book moves through distance d as the spring releases.",
        "Figure eight point seven shows two idealized contacting teeth.",
        "The block changes kinetic energy by twelve joules.",
        "The system consists of the book and the table.",
        "The source charge produces an electric field at this location.",
        "We measure the source of the oscillation with a sensor.",
    ]
    for sample in allowed:
        assert source_reference_findings(sample,slide=2)==[],sample

def test_integrated_script_risk_rejects_source_metacommentary():
    script = ("**Slide 1 [10 sec]:\nSituations Involving Kinetic Friction**\n\n"
              "**Slide 2 [45 sec]:\nThe textbook states that friction is proportional to the normal force.**")
    report=analyze_script_text(script)
    assert report["summary"]["slides"]==2
    assert report["summary"]["blocking"]>0
    assert any(item["kind"]=="external_source_reference" and item["slide"]==2
               for item in report["findings"])

def test_integrated_script_risk_accepts_physical_book():
    script = ("**Slide 1 [10 sec]:\nSituations Involving Kinetic Friction**\n\n"
              "**Slide 2 [45 sec]:\nThe book slides across the rough surface and slows down.**")
    report=analyze_script_text(script)
    assert report["summary"]["blocking"]==0

def test_prompts_require_science_and_standalone_narration():
    slides=(VENDOR/"gen_slides_prompt_v23.txt").read_text(encoding="utf8")
    script=(VENDOR/"gen_script_prompt_v10.txt").read_text(encoding="utf8")
    assert "ACADEMIC TEACHING QUALITY CONTRACT" in slides
    assert "NON-NEGOTIABLE DEFAULT LATEX PRESENTATION CONTRACT" in slides
    assert "exact" in slides.lower() and r"\documentclass[10.5pt]{beamer}" in slides
    assert "Show intermediate algebraic steps" in slides
    assert "Every printed source figure" in slides
    assert r"\IfFileExists" in slides and "Never use" in slides
    assert "SELF-CONTAINED LECTURE VOICE" in script
    assert "NEVER speak about the source as a source" in script
    assert "sole scientific basis" in script

def test_guards_wired_into_actual_pipeline_paths():
    code=(VENDOR/"gen_slides_selenium_v11.py").read_text(encoding="utf8")
    runner=(ROOT/"selenium_pipeline"/"runner.py").read_text(encoding="utf8")
    assert code.count("default_style_errors(")>=3
    assert "script-risk-v2:standalone-lecture" in runner
    assert "analyze_script_text" in runner
    assert "default_style_errors" in runner
