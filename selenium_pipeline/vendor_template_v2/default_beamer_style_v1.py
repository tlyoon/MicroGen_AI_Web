"""Enforce the original MicroGen slide appearance independently of model prompts.

The model owns physics content within frames, never document/page styling.
This checks commands, not the precise whitespace or comment arrangement.
No scientific content is auto-rewritten.
"""
from __future__ import annotations

import re
from pathlib import Path

def _without_comments(tex: str) -> str:
    # Preserve escaped percent signs in content, ignore real TeX comments.
    lines = []
    for line in tex.splitlines():
        cut = next((i for i, c in enumerate(line)
                    if c == "%" and (i == 0 or line[i - 1] != "\\")), None)
        lines.append(line if cut is None else line[:cut])
    return "\n".join(lines)

def _one(pattern: str, text: str) -> bool:
    return len(re.findall(pattern, text, re.I | re.S)) == 1

def default_style_errors(latex: str) -> list[str]:
    """Return blocking style errors without changing the LaTeX.

    The package's existing default is 10.5pt Madrid, default aspect
    ratio 4:3, light-blue/black frame title, right-top page counter,
    empty footer. Content-level math packages do not change the theme.
    """
    source = _without_comments(latex or "")
    pre, separator, _ = source.partition(r"\begin{document}")
    errors: list[str] = []
    if not separator:
        return ["default Beamer: document body missing"]

    required = {
        "document class (10.5pt Beamer, default 4:3)": r"\\documentclass\s*\[\s*10\.5pt\s*\]\s*\{\s*beamer\s*\}",
        "Madrid theme": r"\\usetheme\s*\{\s*Madrid\s*\}",
        "default frame title template": r"\\setbeamertemplate\s*\{\s*frametitle\s*\}\s*\[\s*default\s*\]",
        "original lightblue definition": r"\\definecolor\s*\{\s*lightblue\s*\}\s*\{\s*RGB\s*\}\s*\{\s*173\s*,\s*216\s*,\s*230\s*\}",
        "original frame title colours": r"\\setbeamercolor\s*\{\s*frametitle\s*\}\s*\{\s*bg\s*=\s*lightblue\s*,\s*fg\s*=\s*black\s*\}",
        "original top-right headline": r"\\setbeamertemplate\s*\{\s*headline\s*\}\s*\{",
        "empty footline": r"\\setbeamertemplate\s*\{\s*footline\s*\}\s*\{\s*\}",
    }
    for description, pattern in required.items():
        if not _one(pattern, pre):
            errors.append(f"default Beamer: missing or duplicated {description}")

    headpos = re.search(required["original top-right headline"], pre, re.I | re.S)
    footpos = re.search(required["empty footline"], pre, re.I | re.S)
    if headpos:
        headline = pre[headpos.end():(footpos.start() if footpos else len(pre))]
        order = [headline.find(token) for token in
                 (r"\hfill", r"\insertframenumber", "/", r"\inserttotalframenumber", r"\par")]
        if any(position < 0 for position in order) or order != sorted(order):
            errors.append("default Beamer: headline must retain top-right current/total frame counter")

    exact_single = {
        r"\documentclass": 1, r"\usetheme": 1,
        r"\setbeamercolor": 1, r"\definecolor": 1,
        r"\setbeamertemplate": 3,
    }
    for name, count in exact_single.items():
        hits = re.findall(re.escape(name) + r"(?![A-Za-z])", source)
        if len(hits) != count:
            errors.append(f"default Beamer: found {len(hits)} {name} commands, expected {count}")

    forbidden = (
        r"\usecolortheme", r"\usefonttheme", r"\setbeamerfont",
        r"\setbeamersize", r"\useinnertheme", r"\useoutertheme",
        r"\setlength", r"\setmainfont", r"\setsansfont",
    )
    for command in forbidden:
        if re.search(re.escape(command) + r"(?![A-Za-z])", source):
            errors.append(f"default Beamer: unauthorized appearance override {command}")

    # A preamble supplied by a model can introduce font family/point-size
    # overrides without changing the theme. These are not allowed either.
    if re.search(r"\\renewcommand\s*\{\s*\\(?:familydefault|rmdefault|sfdefault)\s*\}", pre):
        errors.append("default Beamer: global font-family override")
    return errors

def validate_default_beamer(latex_path: Path) -> None:
    errors = default_style_errors(Path(latex_path).read_text(encoding="utf8"))
    if errors:
        raise ValueError("; ".join(errors))
